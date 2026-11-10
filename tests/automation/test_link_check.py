"""Verificação de links com `requests` simulado: nenhuma chamada de rede real."""

from collections.abc import Callable

import pytest
import requests

from triage.automation import link_check
from triage.automation.link_check import check_link

URL = "https://www.gov.br/pt-br/servicos"


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeHttp:
    """Responde, em ordem, a cada chamada de `head`/`get`: um status (int) ou uma exceção a levantar."""

    def __init__(self, head: list, get: list | None = None) -> None:
        self.head_script = list(head)
        self.get_script = list(get or [])
        self.head_calls = 0
        self.get_calls = 0
        self.timeouts: list[float] = []

    def _next(self, script: list, **kwargs) -> FakeResponse:
        self.timeouts.append(kwargs["timeout"])
        outcome = script.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)

    def head(self, url: str, **kwargs) -> FakeResponse:
        self.head_calls += 1
        return self._next(self.head_script, **kwargs)

    def get(self, url: str, **kwargs) -> FakeResponse:
        self.get_calls += 1
        return self._next(self.get_script, **kwargs)


Installer = Callable[[FakeHttp], FakeHttp]


@pytest.fixture
def install(monkeypatch: pytest.MonkeyPatch) -> Installer:
    def _install(fake: FakeHttp) -> FakeHttp:
        monkeypatch.setattr(link_check.requests, "head", fake.head)
        monkeypatch.setattr(link_check.requests, "get", fake.get)
        return fake

    return _install


def test_200_is_ok(install: Installer) -> None:
    fake = install(FakeHttp([200]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code, status.error) == (True, 200, None)
    assert fake.timeouts == [5.0]


def test_redirect_status_is_ok(install: Installer) -> None:
    install(FakeHttp([302]))
    assert check_link(URL, backoff=0).ok


def test_404_fails_without_retry(install: Installer) -> None:
    fake = install(FakeHttp([404], get=[404]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code, status.error) == (False, 404, "HTTP 404")
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_403_with_get_200_is_ok(install: Installer) -> None:
    fake = install(FakeHttp([403], get=[200]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code, status.error) == (True, 200, None)
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_403_with_get_404_is_not_ok(install: Installer) -> None:
    fake = install(FakeHttp([403], get=[404]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code, status.error) == (False, 404, "HTTP 404")
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_403_with_get_503_then_retries_whole_probe(install: Installer) -> None:
    fake = install(FakeHttp([403, 403], get=[503, 200]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code) == (True, 200)
    assert (fake.head_calls, fake.get_calls) == (2, 2)


def test_timeout_is_retried_then_reported_not_raised(install: Installer) -> None:
    fake = install(FakeHttp([requests.Timeout()] * 3))
    status = check_link(URL, timeout=2.0, retries=3, backoff=0)
    assert (status.ok, status.status_code, status.error) == (False, None, "Timeout")
    assert fake.head_calls == 3
    assert fake.timeouts == [2.0, 2.0, 2.0]


def test_connection_error_does_not_propagate(install: Installer) -> None:
    install(FakeHttp([requests.ConnectionError("dns")] * 3))
    status = check_link(URL, backoff=0)
    assert not status.ok and status.error == "ConnectionError"


def test_non_transient_request_error_is_not_retried(install: Installer) -> None:
    fake = install(FakeHttp([requests.exceptions.InvalidURL("ruim")]))
    status = check_link(URL, backoff=0)
    assert not status.ok and status.error == "InvalidURL"
    assert fake.head_calls == 1


def test_503_then_200_recovers(install: Installer) -> None:
    fake = install(FakeHttp([503, 200]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code) == (True, 200)
    assert fake.head_calls == 2


def test_persistent_503_reports_server_error(install: Installer) -> None:
    fake = install(FakeHttp([503, 503, 503]))
    status = check_link(URL, backoff=0)
    assert (status.ok, status.status_code, status.error) == (False, 503, "HTTP 503")
    assert fake.head_calls == 3


def test_falls_back_to_get_when_head_not_implemented(install: Installer) -> None:
    fake = install(FakeHttp([501], get=[200]))
    status = check_link(URL, backoff=0)
    assert status.ok
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_retries_one_means_single_attempt(install: Installer) -> None:
    fake = install(FakeHttp([requests.Timeout(), 200]))
    assert not check_link(URL, retries=1, backoff=0).ok
    assert fake.head_calls == 1

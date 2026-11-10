"""Verificação de links com `requests` simulado: nenhuma chamada de rede real."""

from collections.abc import Callable

import pytest
import requests

from triage.automation import link_check
from triage.automation.link_check import (
    LinkCheckOptions,
    build_link_checker,
    check_link,
)
from triage.config import DEFAULT_LINK_CHECK_USER_AGENT

URL = "https://www.gov.br/pt-br/servicos"
FAST = LinkCheckOptions(backoff=0)


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
        self.headers: list[dict] = []

    def _next(self, script: list, **kwargs) -> FakeResponse:
        self.timeouts.append(kwargs["timeout"])
        self.headers.append(kwargs.get("headers", {}))
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
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code, status.error) == (True, 200, None)
    assert fake.timeouts == [5.0]


def test_redirect_status_is_ok(install: Installer) -> None:
    install(FakeHttp([302]))
    assert check_link(URL, FAST).ok


def test_404_fails_without_retry(install: Installer) -> None:
    fake = install(FakeHttp([404], get=[404]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code, status.error) == (False, 404, "HTTP 404")
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_403_with_get_200_is_ok(install: Installer) -> None:
    fake = install(FakeHttp([403], get=[200]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code, status.error) == (True, 200, None)
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_403_with_get_404_is_not_ok(install: Installer) -> None:
    fake = install(FakeHttp([403], get=[404]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code, status.error) == (False, 404, "HTTP 404")
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_403_with_get_503_then_retries_whole_probe(install: Installer) -> None:
    fake = install(FakeHttp([403, 403], get=[503, 200]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code) == (True, 200)
    assert (fake.head_calls, fake.get_calls) == (2, 2)


def test_timeout_is_retried_then_reported_not_raised(install: Installer) -> None:
    fake = install(FakeHttp([requests.Timeout()] * 3))
    status = check_link(URL, LinkCheckOptions(timeout=2.0, retries=3, backoff=0))
    assert (status.ok, status.status_code, status.error) == (False, None, "Timeout")
    assert fake.head_calls == 3
    assert fake.timeouts == [2.0, 2.0, 2.0]


def test_connection_error_does_not_propagate(install: Installer) -> None:
    install(FakeHttp([requests.ConnectionError("dns")] * 3, get=[requests.ConnectionError("dns")] * 3))
    status = check_link(URL, FAST)
    assert not status.ok and status.error == "ConnectionError"


def test_non_transient_request_error_is_not_retried(install: Installer) -> None:
    fake = install(FakeHttp([requests.exceptions.InvalidURL("ruim")]))
    status = check_link(URL, FAST)
    assert not status.ok and status.error == "InvalidURL"
    assert fake.head_calls == 1


def test_503_then_200_recovers(install: Installer) -> None:
    fake = install(FakeHttp([503, 200]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code) == (True, 200)
    assert fake.head_calls == 2


def test_persistent_503_reports_server_error(install: Installer) -> None:
    fake = install(FakeHttp([503, 503, 503]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code, status.error) == (False, 503, "HTTP 503")
    assert fake.head_calls == 3


def test_falls_back_to_get_when_head_not_implemented(install: Installer) -> None:
    fake = install(FakeHttp([501], get=[200]))
    status = check_link(URL, FAST)
    assert status.ok
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_retries_one_means_single_attempt(install: Installer) -> None:
    fake = install(FakeHttp([requests.Timeout(), 200]))
    assert not check_link(URL, LinkCheckOptions(retries=1, backoff=0)).ok
    assert fake.head_calls == 1


def test_user_agent_is_sent_on_head_and_get(install: Installer) -> None:
    fake = install(FakeHttp([403], get=[200]))
    options = LinkCheckOptions(backoff=0, user_agent="Robo-Teste/1.0")
    assert check_link(URL, options).ok
    assert fake.headers == [{"User-Agent": "Robo-Teste/1.0"}, {"User-Agent": "Robo-Teste/1.0"}]


def test_default_user_agent_names_the_project_and_does_not_mimic_a_browser(install: Installer) -> None:
    fake = install(FakeHttp([200]))
    check_link(URL, FAST)
    sent = fake.headers[0]["User-Agent"]
    assert sent == DEFAULT_LINK_CHECK_USER_AGENT
    assert "Mozilla" not in sent


def test_built_checker_uses_the_given_user_agent(install: Installer) -> None:
    fake = install(FakeHttp([200]))
    assert build_link_checker("Outro-Robo/2.0")(URL).ok
    assert fake.headers == [{"User-Agent": "Outro-Robo/2.0"}]


def test_head_connection_reset_is_repeated_as_get(install: Installer) -> None:
    fake = install(FakeHttp([requests.ConnectionError("reset")], get=[200]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code) == (True, 200)
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_connection_reset_and_get_failure_is_a_failure(install: Installer) -> None:
    fake = install(FakeHttp([requests.ConnectionError("reset")] * 3, get=[requests.ConnectionError("reset")] * 3))
    status = check_link(URL, FAST)
    assert (status.ok, status.error) == (False, "ConnectionError")
    assert (fake.head_calls, fake.get_calls) == (3, 3)


def test_head_connection_reset_then_get_404_decides_without_retry(install: Installer) -> None:
    fake = install(FakeHttp([requests.ConnectionError("reset")], get=[404]))
    status = check_link(URL, FAST)
    assert (status.ok, status.status_code) == (False, 404)
    assert (fake.head_calls, fake.get_calls) == (1, 1)


def test_head_timeout_is_not_repeated_as_get(install: Installer) -> None:
    fake = install(FakeHttp([requests.Timeout()] * 3))
    assert not check_link(URL, FAST).ok
    assert (fake.head_calls, fake.get_calls) == (3, 0)

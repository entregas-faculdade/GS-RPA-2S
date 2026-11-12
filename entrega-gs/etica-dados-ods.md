# Proteção de dados, ética e ODS

O protótipo usa só dados sintéticos e anonimiza CPF, telefone, e-mail, nome de pessoa, endereço (logradouro com
número e complementos), CEP, RG, data completa e números de documento (título de eleitor, CNH, NIS, PIS, cartão SUS,
CNPJ, passaporte, matrícula) antes de qualquer log, gravação ou chamada a API, em linha com a LGPD (minimização e
finalidade). **O dado pessoal só vai anonimizado ao provedor do LLM**, e a **saída do LLM passa por uma guarda** (link e
telefone só das fontes enviadas, categoria só da lista fechada) antes de chegar ao cidadão. A anonimização usa regex,
contexto e uma lista de prenomes, sem modelo de NER, e na dúvida mascara.

Limites declarados (risco residual): nome fora de contexto e fora da lista pode passar; endereço sem logradouro passa;
cidade, estado e bairro não são mascarados. Por isso **nenhum dado pessoal real deve ser digitado** no sistema, com ou sem
LLM, e o CSV de interações e a exportação da revisão, que são texto anonimizado por regras, devem ser revisados antes de
compartilhados. A chave do provedor fica só no `.env`, fora do Git.

Do ponto de vista ético, o robô só responde com links de domínios oficiais da allowlist, prefere pedir **revisão humana**
a arriscar uma resposta errada (urgência, dúvida e fora do catálogo vão para uma pessoa) e deixa claro que é um protótipo.
A fila de revisão não exige login: quem tem acesso à máquina a vê. Os objetivos de desenvolvimento sustentável (ODS)
atendidos, **confirmados pelo grupo**, são o **ODS 16** (instituições eficazes e acesso à informação) e o **ODS 10**
(redução das desigualdades, ao facilitar o acesso a serviços para quem não sabe a qual órgão recorrer).

**ODS 16 e ODS 10 foram confirmados pelo grupo.**

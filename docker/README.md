## Autenticação — Cloudflare Access (edge)

A app NÃO implementa auth. O acesso é restrito por **Cloudflare Access** na frente
da aplicação:

1. Configure um túnel/hostname público apontando para o serviço FastAPI.
2. Crie uma aplicação em Cloudflare Access cobrindo esse hostname.
3. Defina a política (e-mails/grupos com acesso ao ecossistema).

O Cloudflare injeta `Cf-Access-Jwt-Assertion` e `Cf-Access-Authenticated-User-Email`.
Validar esse JWT numa dependency do FastAPI é trabalho FUTURO (fora do M1).

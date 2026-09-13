# Segurança

Não publique segredos, senhas, tokens, `.env`, backups de banco ou dados de alunos no GitHub.

## Regras do projeto

- Segredos somente por variáveis de ambiente.
- `.env` nunca deve ser versionado.
- Toda consulta de dado de negócio deve ser limitada por `organization`.
- IDs/UUIDs recebidos do cliente nunca substituem a validação de autorização.
- Rotas de sessão usam CSRF.
- API mobile usa Bearer Token e não depende de cookie de sessão.
- Tokens devem poder ser revogados.
- Senhas nunca são armazenadas em texto puro.
- Logs de segurança não devem armazenar senha, token ou código de acesso.

## Produção

Antes de publicar:

1. `DJANGO_DEBUG=0`
2. `DJANGO_SECRET_KEY` forte e exclusiva
3. `POSTGRES_PASSWORD` forte
4. HTTPS obrigatório
5. domínio correto em `DJANGO_ALLOWED_HOSTS`
6. configurar `DJANGO_CSRF_TRUSTED_ORIGINS`
7. proteger a origem da VPS atrás do proxy/WAF
8. habilitar backup criptografado e teste de restauração
9. MFA obrigatório para superadmin assim que o módulo de MFA for implantado

# Mapa de Segurança — SaaS Personal

Revisão inicial do código após a Etapa 4A.

| Vetor | Situação | Controle |
|---|---|---|
| SQL Injection | Baixo no código atual | ORM Django; nenhum `raw()`/`cursor.execute()` identificado |
| IDOR / fuga de tenant | Mitigado, exige testes contínuos | consultas por `organization`; aluno limitado ao próprio `StudentAccount` |
| Força bruta login personal | Mitigado | rate limit por IP + e-mail |
| Força bruta login aluno/API | Mitigado | rate limit por IP + identidade |
| Força bruta código 6 dígitos | Mitigado | hash, expiração, contador de falhas, bloqueio temporário e rate limit |
| Roubo de token API | Parcialmente mitigado | token aleatório, somente hash no banco, expiração, revogação e limite de sessões |
| CSRF | Mitigado | middleware CSRF nas rotas com cookie; API Bearer é stateless e não usa cookie |
| XSS | Mitigado parcialmente | autoescape Django + CSP; ainda há `unsafe-inline` enquanto Tailwind Browser CDN existir |
| Clickjacking | Mitigado | `X_FRAME_OPTIONS=DENY` + `frame-ancestors 'none'` |
| SSRF | Baixo | servidor não busca mídia arbitrária; vídeos aceitos apenas de YouTube/Bilibili |
| Upload malicioso | Baixo atualmente | upload de mídia de exercício desativado + limites globais de request |
| Path traversal | Baixo | nenhum caminho fornecido pelo usuário é aberto diretamente |
| Open redirect | Baixo | login não redireciona para URL arbitrária fornecida pelo cliente |
| Enumeração de contas | Mitigado | respostas genéricas de autenticação/ativação |
| Sessão roubada | Mitigado | cookies HttpOnly/Secure/SameSite e expiração deslizante |
| Transporte sem TLS | Produção bloqueada | SSL redirect + HSTS quando `DEBUG=0` |
| Segredo fraco/hardcoded | Mitigado | aplicação falha em produção se SECRET_KEY/DB password forem ausentes/fracas |
| Reset de superadmin no restart | Corrigido | senha não é redefinida sem `SUPERADMIN_ROTATE_PASSWORD=1` |
| Ataque ao Django Admin | Mitigado parcialmente | rate limit, caminho configurável; MFA ainda pendente |
| Abuso de requisição/DoS aplicativo | Mitigado parcialmente | request size, limites Gunicorn e rate limits |
| DDoS volumétrico | Infraestrutura pendente | exige Cloudflare/WAF/rate limit no proxy |
| Container escape / privilégio | Melhorado | processo web não-root, `no-new-privileges`, `cap_drop: ALL`, PID limit |
| Dependência vulnerável | Monitorado | `pip-audit`, Dependabot e Bandit em CI |
| Supply chain frontend | Pendente | Tailwind Browser CDN deve ser substituído por build local antes da produção |
| Logs contendo segredos | Mitigado | SecurityEvent guarda hash do identificador e nunca deve receber senha/token |
| Retenção de logs de segurança | Implementado | comando para remover eventos >90 dias |
| Backups no repositório | Corrigido | `.backup_*` e instaladores ignorados/removidos do índice |
| MFA superadmin/personal | Pendente | recomendação de próxima etapa de segurança |
| RBAC granular OWNER/TRAINER/STAFF | Pendente | Membership existe, mas permissões granulares ainda precisam ser aplicadas por ação |
| Usuário em múltiplos tenants | Pendente | middleware ainda escolhe associação ativa; criar seletor explícito antes de multiempresa |
| Backup de banco / restauração | Infraestrutura pendente | criptografia, retenção e teste de restore na VPS |
| Malware/WAF/Bot management | Infraestrutura pendente | aplicar no deploy com Cloudflare/Dokploy |

## Princípio permanente

UUID oculto na URL não é uma barreira de segurança. A proteção real é autorização no backend
(`organization`, aluno autenticado e escopo do objeto), que deve ser mantida em qualquer nova rota/API.

## Próximos controles prioritários antes de produção

1. MFA para superadmin e personal.
2. RBAC por papel (`OWNER`, `TRAINER`, `STAFF`).
3. Compilar Tailwind localmente e retirar o Browser CDN/`unsafe-inline`.
4. WAF + rate limit no proxy/Cloudflare.
5. Backup PostgreSQL criptografado com teste de restauração.
6. Testes automáticos de isolamento entre tenants e DAST.


## Pacote 4A.2A

- RBAC OWNER / TRAINER / STAFF aplicado no backend.
- Tela de equipe restrita ao OWNER.
- request.membership explícito no middleware.
- Backups e instaladores temporários removidos.

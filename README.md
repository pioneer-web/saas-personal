# SaaS Personal — Etapa 1

Fundação inicial do SaaS para personal trainers privados.

## Incluído
- Django 6.0.8
- PostgreSQL 16
- Docker Compose
- Login por e-mail
- Superadmin criado automaticamente pelo `.env`
- Base multi-tenant lógica (`Organization` + `Membership`)
- Django Admin
- Health check em `/health/`
- Segurança básica de produção

## Subir localmente
```bash
cp .env.example .env
# edite as senhas no .env
docker compose up -d --build
```

Acesse:
- App: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- Health: http://localhost:8000/health/

## Primeiro tenant/personal
Entre no `/admin/`, crie uma `Organization` e depois uma `Membership` ligando o usuário à organização.

## Próxima etapa
Cadastro e gestão de alunos dentro do tenant do personal.

# SaaS Personal — Etapa 3A

Biblioteca de Exercícios, mobile-first, MTV e rotas sem IDs visíveis.

## Instalação

Extraia o ZIP na raiz de `~/SaaS/saas-personal` e rode:

```bash
python3 apply_etapa3a.py
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
```

Teste em `http://localhost:8011/exercicios/`.

Depois de validar:

```bash
git add .
git commit -m "Etapa 3A - Biblioteca de exercicios"
git push
```

import py_compile
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path.home() / "SaaS" / "saas-personal"

if not ROOT.exists():
    raise SystemExit(f"Projeto não encontrado: {ROOT}")


def read(rel):
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(*args, check=True):
    print(">", " ".join(args))
    return subprocess.run(args, cwd=ROOT, check=check)


requirements = read("requirements.txt").splitlines()
requirements = [
    line for line in requirements
    if not line.lower().startswith("pyotp")
    and not line.lower().startswith("cryptography")
]
write("requirements.txt", "\n".join(requirements).rstrip() + "\n")

models_path = "apps/security_center/models.py"
models = read(models_path)
start = models.find("\nclass MFADevice(models.Model):")
if start == -1:
    start = models.find("class MFADevice(models.Model):")
if start != -1:
    models = models[:start].rstrip() + "\n"
    write(models_path, models)

middleware_path = "apps/security_center/middleware.py"
middleware = read(middleware_path)
start = middleware.find("\nclass MFAGateMiddleware:")
if start == -1:
    start = middleware.find("class MFAGateMiddleware:")
if start != -1:
    middleware = middleware[:start].rstrip() + "\n"
    write(middleware_path, middleware)

admin_path = "apps/security_center/admin.py"
admin = read(admin_path)
admin = admin.replace(
    "from .models import MFADevice, SecurityEvent, SecurityThrottle",
    "from .models import SecurityEvent, SecurityThrottle",
)
start = admin.find("\n@admin.register(MFADevice)")
if start != -1:
    admin = admin[:start].rstrip() + "\n"
write(admin_path, admin)

settings_path = "config/settings.py"
settings = read(settings_path)
settings = settings.replace(
    '    "apps.security_center.middleware.MFAGateMiddleware",\n',
    "",
)
settings = re.sub(
    r'\nMFA_SESSION_MAX_AGE = int\(\n'
    r'\s*os\.getenv\("MFA_SESSION_MAX_AGE", "43200"\)\n'
    r'\)\n\n'
    r'MFA_ENCRYPTION_KEY_MATERIAL = os\.getenv\(\n'
    r'\s*"MFA_ENCRYPTION_KEY",\n'
    r'\s*SECRET_KEY,\n'
    r'\)\n',
    "\n",
    settings,
)
write(settings_path, settings)

urls_path = "config/urls.py"
urls = read(urls_path)
urls = urls.replace(
    '    path("seguranca/", include("apps.security_center.urls")),\n',
    "",
)
write(urls_path, urls)

core_path = "apps/core/views.py"
core = read(core_path)
core = core.replace(
    "from apps.security_center.mfa import clear_mfa_verification\n",
    "",
)
core = core.replace(
    "            clear_mfa_verification(request)\n",
    "",
)
write(core_path, core)

base_path = "templates/base.html"
base = read(base_path)
base = re.sub(
    r'\s*<a href="\{% url \'security_center:home\' %\}"\s*'
    r'class="block rounded-2xl px-4 py-3 font-semibold hover:bg-white/5">\s*'
    r'Segurança\s*</a>\s*',
    "\n",
    base,
    flags=re.MULTILINE,
)
write(base_path, base)

for rel in [
    "apps/security_center/mfa.py",
    "apps/security_center/forms.py",
    "apps/security_center/views.py",
    "apps/security_center/urls.py",
    "apps/security_center/tests_mfa.py",
]:
    path = ROOT / rel
    if path.exists():
        path.unlink()

template_dir = ROOT / "apps/security_center/templates/security_center"
if template_dir.exists():
    shutil.rmtree(template_dir)

env_path = ".env.example"
env = read(env_path)
env = re.sub(
    r'\n# MFA\n'
    r'MFA_SESSION_MAX_AGE=43200\n'
    r'# Em produção prefira uma chave aleatória dedicada e estável\.\n'
    r'MFA_ENCRYPTION_KEY=\n?',
    "\n",
    env,
)
write(env_path, env.rstrip() + "\n")

map_path = "SECURITY_MAP.md"
security_map = read(map_path)
security_map = re.sub(
    r'\n## Pacote 4A\.2B — MFA\n.*?(?=\n## |\Z)',
    "",
    security_map,
    flags=re.S,
)
if "MFA removido por decisão de produto" not in security_map:
    security_map += (
        "\n\n## Decisão de segurança\n\n"
        "- MFA removido por decisão de produto.\n"
        "- Mantidos: senha forte, rate limit, cookies seguros, HTTPS/HSTS, "
        "CSRF, CSP, RBAC, isolamento multi-tenant, tokens revogáveis e auditoria.\n"
    )
write(map_path, security_map.rstrip() + "\n")

for rel in [
    "apps/security_center/models.py",
    "apps/security_center/middleware.py",
    "apps/security_center/admin.py",
    "apps/core/views.py",
    "config/settings.py",
    "config/urls.py",
]:
    py_compile.compile(str(ROOT / rel), doraise=True)

print("Sintaxe Python validada.")

run("docker", "compose", "build", "web", "migrate")

uid = subprocess.check_output(["id", "-u"], text=True).strip()
gid = subprocess.check_output(["id", "-g"], text=True).strip()

run(
    "docker",
    "compose",
    "run",
    "--rm",
    "--no-deps",
    "--user",
    f"{uid}:{gid}",
    "-v",
    f"{ROOT}:/app",
    "--entrypoint",
    "python",
    "web",
    "manage.py",
    "makemigrations",
    "security_center",
    "--name",
    "remove_mfa_device",
)

run("docker", "compose", "down")
run("docker", "compose", "up", "-d", "--build")

run(
    "docker", "compose", "exec", "web",
    "python", "manage.py", "check",
)

run(
    "docker", "compose", "exec", "web",
    "python", "manage.py", "makemigrations",
    "--check", "--dry-run",
)

print()
print("========================================")
print("MFA REMOVIDO COM SUCESSO")
print("========================================")
print("Mantidos:")
print("- login/senha normal")
print("- rate limit")
print("- RBAC OWNER/TRAINER/STAFF")
print("- isolamento multi-tenant")
print("- CSRF/CSP/cookies seguros")
print("- HTTPS/HSTS em produção")
print("- tokens API revogáveis")
print("- auditoria de eventos de segurança")

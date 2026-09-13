from pathlib import Path

def update_settings():
    p=Path("config/settings.py"); s=p.read_text(encoding="utf-8")
    if '"apps.exercises",' not in s:
        for anchor in ('"apps.students",','"apps.organizations",'):
            if anchor in s:
                s=s.replace(anchor, anchor+'\n    "apps.exercises",',1); p.write_text(s,encoding="utf-8"); break
        else: raise RuntimeError("INSTALLED_APPS não localizado")

def update_urls():
    p=Path("config/urls.py"); s=p.read_text(encoding="utf-8")
    if "from django.urls import path" in s:
        s=s.replace("from django.urls import path","from django.urls import include, path",1)
    route='    path("exercicios/", include("apps.exercises.urls")),'
    if 'include("apps.exercises.urls")' not in s:
        s=s.replace("urlpatterns = [","urlpatterns = [\n"+route,1)
    p.write_text(s,encoding="utf-8")

if __name__=="__main__":
    update_settings(); update_urls(); print("Etapa 3A aplicada com sucesso.")

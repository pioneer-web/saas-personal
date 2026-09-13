# App do Aluno — Flutter 4B.1

Android Emulator:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8011/api/student
```

Celular físico na mesma rede:

```bash
flutter run --dart-define=API_BASE_URL=http://IP_DO_PC:8011/api/student
```

Produção deve usar HTTPS.

Entregue nesta etapa:
- login do aluno;
- token em secure storage;
- tela inicial;
- treino do dia / treinos ativos;
- execução do treino;
- séries, repetições e carga;
- cronômetro de descanso;
- conclusão do treino;
- histórico;
- logout com revogação do token.

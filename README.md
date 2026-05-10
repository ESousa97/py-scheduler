# py-scheduler

Agendador de tarefas com [APScheduler](https://github.com/agronholm/apscheduler), configuração em YAML, persistência de execuções (SQLite), webhooks e métricas Prometheus.

## Instalação

```bash
pip install py-scheduler
```

## Uso

```bash
py-scheduler caminho/para/config.yaml
```

Ou, a partir do repositório:

```bash
python main.py config.example.yaml
```

Variável de ambiente `PY_SCHEDULER_JOBS_MODULE` define o módulo Python que implementa `register(registry)`.

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

## Docker

```bash
docker build -t py-scheduler .
docker run -p 9100:9100 py-scheduler
```

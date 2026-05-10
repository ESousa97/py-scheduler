# Adicionar novas tarefas sem alterar o código principal

O ponto de extensão é um **módulo Python** que expõe a função `register(registry)`, onde `registry` é um `JobRegistry`. O `main.py` apenas carrega esse módulo e chama `register`; as implementações das tarefas ficam no seu pacote ou arquivo separado.

## Passos

1. **Crie um módulo** (por exemplo `minha_empresa/scheduler_jobs.py`) com funções sem argumentos (ou com argumentos default) que o APScheduler pode chamar, e uma função `register`:

   ```python
   from py_scheduler.registry import JobRegistry

   def backup_diario() -> None:
       ...

   def register(registry: JobRegistry) -> None:
       registry.register("backup_diario", backup_diario)
   ```

2. **Aponte o agendador para o módulo** de uma destas formas:

   - Variável de ambiente `PY_SCHEDULER_JOBS_MODULE=minha_empresa.scheduler_jobs` (útil no Docker/Kubernetes).
   - Ou no YAML raiz: `jobs_register_module: minha_empresa.scheduler_jobs` (tem precedência sobre a variável de ambiente quando definido).

3. **Declare os jobs no YAML** com `name` igual ao nome usado em `registry.register(...)`, e `interval` / `retry` como hoje.

O `main.py` não precisa ser editado quando você adiciona tarefas: basta novo módulo + entradas no YAML (e dependências instaladas no ambiente, por exemplo `pip install -e .` do seu pacote).

## Docker

Monte o ficheiro de configuração em `/app/config/config.yaml` e, se usar um pacote próprio, instale-o na imagem (multi-stage ou `pip install`) ou monte o código em `PYTHONPATH`.

Exemplo:

```bash
docker build -t py-scheduler .
docker run --rm -p 9100:9100 \
  -v /caminho/config.yaml:/app/config/config.yaml:ro \
  -v py-scheduler-data:/data \
  -e PY_SCHEDULER_JOBS_MODULE=minha_empresa.scheduler_jobs \
  py-scheduler
```

Defina `database_path` no YAML para `/data/scheduler.sqlite` se quiser persistência dentro do volume.

## Métricas Prometheus

O endpoint HTTP expõe `/metrics` (porta configurável, por defeito `9100`).

- **`py_scheduler_job_failures_total`** — etiquetas `job_id`, `job_name`. Conta apenas **falhas finais** (depois de esgotar retentativas), alinhado com o envio de webhook de falha.

- **`py_scheduler_job_execution_seconds`** — histograma por `job_id` e `job_name`, com observação da duração de **cada tentativa** (sucesso ou falha). O tempo médio por job em Prometheus costuma ser expresso com PromQL, por exemplo:

  ```text
  sum by (job_id, job_name) (
    rate(py_scheduler_job_execution_seconds_sum[5m])
  )
  /
  sum by (job_id, job_name) (
    rate(py_scheduler_job_execution_seconds_count[5m])
  )
  ```

Ajuste a janela `[5m]` ao seu scrape e SLO.

## Histórico SQLite

Cada tentativa gera uma linha na tabela `job_executions` com `outcome` em `success`, `failed_retry` ou `failed_final`, `duration_ms` e mensagem de erro quando aplicável. Para desativar a escrita, use `database_path: ""` no YAML.

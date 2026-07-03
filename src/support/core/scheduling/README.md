# Scheduler distribuído

Sistema de agendamento estilo Laravel Scheduler sobre **APScheduler** com **jobstore
PostgreSQL**, seguro para rodar em múltiplas réplicas.

## Componentes

| Arquivo | Papel |
|---|---|
| `job.py` | `Job` — base abstrata. Subclasses implementam `action()`. `execute()` envolve com advisory lock + tracking em `job_executions`. |
| `schedule.py` | `Schedule` / `ScheduledJob` — DSL fluente (`.hourly()`, `.daily()`, `.every()`, `.cron()`). |
| `scheduler.py` | `JobScheduler` — wrapper do `AsyncIOScheduler` com `SQLAlchemyJobStore` no engine síncrono. |

## Registrar um job

1. Crie a classe em `src/app/console/jobs/{nome}_job.py` herdando `Job`, implementando `async def action()`.
2. Registre a cadência em `src/app/console/schedule.py`:

```python
schedule.call(SyncKnowledgeBaseJob).hourly()
schedule.call(CleanupConversationsJob).daily(hour=3)
```

3. No boot, se `ENABLE_SCHEDULER=true`, o `LifespanManager` carrega o `schedule.py` e registra tudo.

## Coordenação distribuída

- **Jobstore em PostgreSQL** (`apscheduler_jobs`) + `max_instances=1` → cada disparo acontece uma única vez no cluster.
- **Advisory lock** (`pg_try_advisory_lock`) em `Job.execute()` → segunda linha de defesa contra concorrência.
- **`job_executions`** → trilha de auditoria de cada execução (status, erro, timestamps).

## Deployment

- A tabela `apscheduler_jobs` é gerenciada pelo próprio APScheduler — **excluída** do autogenerate do Alembic via `include_object` em `database/env.py`.
- Todas as réplicas devem apontar para o **mesmo** PostgreSQL.
- Idempotência é responsabilidade da lógica em `action()`: o lock protege contra concorrência, não contra retentativas.

"""Registro central da agenda de jobs.

O LifespanManager carrega este módulo no boot (se ENABLE_SCHEDULER=true) e registra
cada entrada no JobScheduler.

Exemplo (quando houver jobs):

    from src.app.console.jobs.sync_knowledge_base_job import SyncKnowledgeBaseJob

    schedule.call(SyncKnowledgeBaseJob).hourly()
    schedule.call(CleanupConversationsJob).daily(hour=3)
"""

from src.support.core.scheduling import Schedule

schedule = Schedule()

# Nenhum job registrado ainda — ver docs/architecture.md → "Console e jobs".

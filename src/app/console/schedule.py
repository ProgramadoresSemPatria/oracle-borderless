"""Registro central da agenda de jobs.

O LifespanManager carrega este módulo no boot (se ENABLE_SCHEDULER=true) e registra
cada entrada no JobScheduler.

Exemplo (quando houver jobs):

    from src.app.console.jobs.sync_knowledge_base_job import SyncKnowledgeBaseJob

    schedule.call(SyncKnowledgeBaseJob).hourly()
    schedule.call(CleanupConversationsJob).daily(hour=3)
"""

from src.app.console.jobs.sync_knowledge_base_job import SyncKnowledgeBaseJob
from src.support.core.scheduling import Schedule

schedule = Schedule()

# Refresh incremental da base de conhecimento (Notion → pgvector). Diário às 04h;
# ajuste a cadência conforme a frequência de mudança no Notion.
schedule.call(SyncKnowledgeBaseJob).daily(hour=4)

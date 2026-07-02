"""DSL fluente de agendamento (estilo Laravel Scheduler)."""

from dataclasses import dataclass, field
from typing import Any

from src.support.core.scheduling.job import Job


@dataclass
class ScheduledJob:
    """Uma entrada de agenda: a classe de Job + o trigger (APScheduler) escolhido."""

    job_class: type[Job]
    trigger: str = "interval"
    trigger_args: dict[str, Any] = field(default_factory=dict)

    def every(self, *, minutes: int = 0, hours: int = 0, seconds: int = 0) -> "ScheduledJob":
        self.trigger = "interval"
        self.trigger_args = {"minutes": minutes, "hours": hours, "seconds": seconds}
        return self

    def hourly(self, minute: int = 0) -> "ScheduledJob":
        self.trigger = "cron"
        self.trigger_args = {"minute": minute}
        return self

    def daily(self, hour: int = 0, minute: int = 0) -> "ScheduledJob":
        self.trigger = "cron"
        self.trigger_args = {"hour": hour, "minute": minute}
        return self

    def cron(self, **fields: Any) -> "ScheduledJob":
        """Cron cru: cron(minute='*/5', hour='3', day_of_week='mon-fri')."""
        self.trigger = "cron"
        self.trigger_args = dict(fields)
        return self

    @property
    def job_id(self) -> str:
        return self.job_class.__name__


class Schedule:
    """Coleta as entradas de agenda. Populado em `src/app/console/schedule.py`."""

    def __init__(self) -> None:
        self._entries: list[ScheduledJob] = []

    def call(self, job_class: type[Job]) -> ScheduledJob:
        entry = ScheduledJob(job_class=job_class)
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[ScheduledJob]:
        return list(self._entries)

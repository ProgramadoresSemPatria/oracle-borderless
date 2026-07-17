from dataclasses import dataclass


@dataclass
class SyncReport:
    """Resultado de uma sincronização da base de conhecimento."""

    total_approved: int = 0
    ingested: int = 0
    skipped: int = 0
    removed: int = 0

    def __str__(self) -> str:
        return (
            f"aprovadas={self.total_approved} "
            f"ingeridas={self.ingested} inalteradas={self.skipped} removidas={self.removed}"
        )

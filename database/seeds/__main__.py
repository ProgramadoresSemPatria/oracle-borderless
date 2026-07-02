"""Entrypoint: `python -m database.seeds`."""

import asyncio

from database.seeds import run_all_seeders
from src.support.core.logging import configure_logging

if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_all_seeders())

"""Autodiscovery de rotas.

Cada módulo em `src/app/api/routes/` que expõe uma variável `router` (com auth,
quando existir) ou `public_router` (explicitamente sem auth) é registrado
automaticamente. Basta criar o arquivo — nada a registrar manualmente.
"""

import importlib
import logging
import pkgutil

from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)


def register_routes(app: FastAPI) -> None:
    """Descobre e inclui todos os routers dos módulos deste pacote."""
    package = importlib.import_module(__name__)

    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue

        module = importlib.import_module(f"{__name__}.{module_info.name}")

        for attr_name in ("router", "public_router"):
            router = getattr(module, attr_name, None)
            if isinstance(router, APIRouter):
                app.include_router(router)
                logger.info("Rota registrada: %s.%s", module_info.name, attr_name)

"""Bootstrap da aplicação FastAPI: cria o app, registra middlewares, handlers e rotas."""

from fastapi import FastAPI

from src.app.api.exception_handlers import register_exception_handlers
from src.app.api.middlewares import (
    BackgroundTaskMiddleware,
    DBSessionMiddleware,
    ProcessTimeMiddleware,
    RequestContextMiddleware,
)
from src.app.api.routes import register_routes
from src.support.core.lifespan import lifespan
from src.support.core.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Middlewares — add_middleware empilha em ordem inversa de execução.
    # Execução desejada: RequestContext → DBSession → BackgroundTask → ProcessTime.
    app.add_middleware(ProcessTimeMiddleware)
    app.add_middleware(BackgroundTaskMiddleware)
    app.add_middleware(DBSessionMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    register_routes(app)

    return app


app = create_app()

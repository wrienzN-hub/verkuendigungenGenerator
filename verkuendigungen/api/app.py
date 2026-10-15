from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..core.config import ROOT, database_path
from ..infrastructure.database import database, migrate
from .routes import imports, saints, templates


def create_app(db_path: Path | str | None = None):
    @asynccontextmanager
    async def lifespan(app):
        with database(app.state.database_path) as conn:
            migrate(conn)
        yield

    app = FastAPI(
        title='Verkündigungen Generator',
        version='0.1.0',
        description='Heilige und liturgische Feiern der Diözese Gurk verwalten.',
        lifespan=lifespan,
    )
    app.state.database_path = Path(db_path) if db_path is not None else database_path()
    app.include_router(saints.router, prefix='/api/v1')
    app.include_router(imports.router, prefix='/api/v1')
    app.include_router(templates.router, prefix='/api/v1')

    @app.get('/health', tags=['Betrieb'])
    def health():
        with database(app.state.database_path) as conn:
            conn.execute('SELECT 1').fetchone()
        return {'status': 'ok'}

    frontend = ROOT / 'frontend' / 'dist'
    if frontend.is_dir():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')

    return app


app = create_app()

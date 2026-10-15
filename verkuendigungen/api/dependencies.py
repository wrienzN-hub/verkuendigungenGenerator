from fastapi import Request

from ..infrastructure.database import database


def get_database(request: Request):
    with database(request.app.state.database_path) as conn:
        yield conn

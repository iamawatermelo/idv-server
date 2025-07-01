from contextlib import asynccontextmanager
import fastapi
import logging.config
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlmodel import SQLModel
from idv_server.config import config
from idv_server.schema import graphql


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    connection_string = config.postgres_connection_string
    connection_string.scheme = "postgres+asyncpg"
    
    engine = create_async_engine(connection_string.encoded_string())
    
    logging.config.dictConfig({
        "version": 1
    })
    
    yield
    
    await engine.dispose(close=True)


app = fastapi.FastAPI(
    lifespan=lifespan,
    
    # Doesn't really matter, because there aren't any routes
    openapi_url=None,
    docs_url=None
)

app.mount(
    path="/graphql",
    app=graphql
)
from contextlib import asynccontextmanager
import fastapi
import logging.config
from pydantic import PostgresDsn
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlmodel import SQLModel
from idv_server.config import config
from idv_server.schema import graphql
from time import time

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    logging.debug("Shutting down...")
    
    connection_string = make_url(config.postgres_connection_string.encoded_string())
    connection_string = connection_string.set(drivername="postgresql+asyncpg")
    
    engine = create_async_engine(connection_string)
    
    yield
    
    logging.debug("Shutting down...")
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
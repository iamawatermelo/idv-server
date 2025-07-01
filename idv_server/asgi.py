from contextlib import asynccontextmanager
import fastapi
import logging.config
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlmodel import SQLModel
from idv_server.config import config
from idv_server.schema import graphql
from time import time

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    st = time()
    logger.debug("Starting up...")
    
    connection_string = config.postgres_connection_string
    connection_string.scheme = "postgres+asyncpg"
    
    engine = create_async_engine(connection_string.encoded_string())
    
    logger.debug(f"Started in {time() - st:.02}s")
    
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
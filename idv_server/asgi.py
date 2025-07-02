from contextlib import asynccontextmanager
import fastapi
import logging.config
from pydantic import PostgresDsn
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlmodel import SQLModel
from idv_server.config import config
from idv_server.engine import connect
from idv_server.env import Env
from idv_server.schema import graphql
from time import time

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    if config.auth is None:
        logger.error(
            "[red]#####################################[/red]"
            "\n[red]# Authentication is not configured! #[/red]"
            "\n[red]#####################################[/red]"
            "\n"
            "\n[yellow]Please read the docs to configure authentication for idv-server.[/yellow]"
            "\n[yellow]This error will appear on every start up until authentication is configured.[/yellow]"
        )
    elif config.auth.root_subjects != []:
        logger.warning("[yellow]Root subjects are configured for idv-server.[/yellow]")
    
    
    async with Env().enter():
        yield


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
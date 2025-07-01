import asyncio
import logging
import logging.config
import asyncpg
from sqlmodel import SQLModel
import typer
import hypercorn
from hypercorn.asyncio import serve
from idv_server.config import config
from idv_server.asgi import app as asgi_app
from idv_server.engine import connect
from rich import print
from asyncpg.exceptions import InvalidCatalogNameError

logger = logging.getLogger("idv_server.__main__")

app = typer.Typer(
    pretty_exceptions_enable=False
)

@app.command("serve")
def run_server():
    hypercorn_config = hypercorn.Config()
    hypercorn_config.bind = f"{config.hostname}:{config.port}"
    hypercorn_config.loglevel = config.log_level
    hypercorn_config.logconfig_dict = config._logging_config

    try:
        asyncio.run(serve(asgi_app, config=hypercorn_config))
    except Exception as _:
        logger.error(
            "unhandled exception",
            exc_info=True
        )

        return 1


@app.command("init-db")
def init_db():
    async def _init_db():
        engine = await connect()
        
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all, checkfirst=False)
                await conn.run_sync(SQLModel.metadata.create_all)
            
            await engine.dispose(close=True)
        except InvalidCatalogNameError:
            print("[red]The database used in the connection string doesn't exist. Please create it.[/red]")
    
    print("[yellow]Are you sure you want to init-db?[/yellow]")
    print(f"[red]This will delete all of your data on {config.postgres_connection_string}![/red]")
    print("Type [blue]y[/blue] to continue:")
    
    if input("[y/N]: ").strip() == "y":
        print("\n[yellow]Initialising database...[/yellow]")
        asyncio.run(_init_db())
    else:
        print("\nCancelled.")
        

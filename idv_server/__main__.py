import asyncio
import typer
import hypercorn
import logging.config
from hypercorn.asyncio import serve
from idv_server.config import config
from idv_server.schema import graphql

app = typer.Typer(
    pretty_exceptions_enable=False
)


@app.command("serve")
def run_server():
    logging.config.dictConfig(config._logging_config)
    
    hypercorn_config = hypercorn.Config()
    hypercorn_config.bind = f"{config.hostname}:{config.port}"
    hypercorn_config.log
    
    asyncio.run(serve(graphql, config=hypercorn_config))

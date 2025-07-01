import asyncio
import logging
import logging.config
import typer
import hypercorn
from hypercorn.asyncio import serve
from idv_server.config import config
from idv_server.asgi import app as asgi_app

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

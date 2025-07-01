import asyncio
import logging
import typer
import hypercorn
from hypercorn.asyncio import serve
from idv_server.config import config
from idv_server.asgi import app

logger = logging.getLogger()

app = typer.Typer(
    pretty_exceptions_enable=False
)

@app.command("serve")
def run_server():
    hypercorn_config = hypercorn.Config()
    hypercorn_config.bind = f"{config.hostname}:{config.port}"
    
    hypercorn_config.logconfig_dict = config._logging_config
    
    try:
        asyncio.run(serve(app, config=hypercorn_config))
    except Exception as e:
        
        
        return 1

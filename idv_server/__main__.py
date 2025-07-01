import asyncio
import typer
import hypercorn
from hypercorn.asyncio import serve
from idv_server.schema import graphql

app = typer.Typer()


@app.command("serve")
def run_server(host: str = "localhost:8080"):
    config = hypercorn.Config()
    config.bind = host

    asyncio.run(serve(graphql, config=config))

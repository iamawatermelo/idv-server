from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from idv_server.config import config


async def connect():
    """
    Return an SQLAlchemy async engine.
    """
    
    connection_string = make_url(config.postgres_connection_string.encoded_string())
    connection_string = connection_string.set(drivername="postgresql+asyncpg")
    
    return create_async_engine(connection_string)

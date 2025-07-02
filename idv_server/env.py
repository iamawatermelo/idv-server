"""
idv-server's global state
"""

import contextlib
import contextvars
import logging
from time import time
from typing import ClassVar, Self

import aiohttp
from sqlalchemy.ext.asyncio import AsyncEngine

from idv_server.engine import connect

logger = logging.getLogger(__name__)

class Env:
    _contextvar: ClassVar[contextvars.ContextVar[Self]] = contextvars.ContextVar("idv_server.env")
    engine: AsyncEngine
    http: aiohttp.ClientSession
    
    @contextlib.asynccontextmanager
    async def enter(self):
        st = time()
        logger.debug("Entering new environment context")
        
        self.engine = await connect()
        self.http = aiohttp.ClientSession()
        
        async with self.engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 'hello, world!'")
        
        async with self.http:
            token = self._contextvar.set(self)
            
            logger.debug(f"Finished environment setup in {time() - st:.02}s")
            
            yield
            
            logger.debug("Tearing down environment")
            
            self._contextvar.reset(token)
        
        await self.engine.dispose(close=True)
    
    @classmethod
    def ctx(cls) -> Self:
        return cls._contextvar.get()

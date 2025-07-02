"""
idv-server's global state
"""

from __future__ import annotations

import contextlib
import contextvars
import logging
from time import time
from typing import ClassVar, Self

import aiohttp
from sqlalchemy.ext.asyncio import AsyncEngine

from idv_server.engine import connect

logger = logging.getLogger(__name__)

_current_env: Env | None = None


class Env:
    engine: AsyncEngine
    http: aiohttp.ClientSession
    
    @contextlib.asynccontextmanager
    async def enter(self):
        global _current_env
        
        st = time()
        logger.debug("Entering new environment context")
        
        self.engine = await connect()
        self.http = aiohttp.ClientSession()
        
        async with self.engine.begin() as conn:
            await conn.exec_driver_sql("SELECT 'hello, world!'")
        
        _current_env = self
        
        logger.debug(f"Finished environment setup in {time() - st:.02}s")
        
        yield
        
        logger.debug("Tearing down environment")
        
        _current_env = None
        
        await self.engine.dispose(close=True)
        await self.http.close()
    
    @classmethod
    def ctx(cls) -> Env:
        if _current_env is not None:
            return _current_env
        
        raise Exception("attempted to get env but there is none")

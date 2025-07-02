"""
Authentication for idv-server.
"""

import logging
from typing import Literal
import aiohttp
from alembic.op import f
from attr import dataclass

from idv_server.config import config
from idv_server.env import Env

logger = logging.getLogger(__name__)

class Unauthorized(Exception):
    pass


async def authorize(
    method: Literal["READ"] | Literal["MODIFY"],
    resource: str,
    headers: dict[str, str],
    authorized_subject: str | None
):
    if config.auth is None:
        logger.error(f"{method} access on {resource} was allowed because no authentication was configured")
        return
    
    env = Env.ctx()
    
    async with env.http.request(
        "GET" if method == "READ" else "POST",
        f"{config.auth.pdp_endpoint}{resource}"
    ) as req:
        if req.status not in {200, 204}:
            logger.debug(f"rejected {method} access on {resource} with authorized subjects {authorized_subject} because of PDP decision")
            raise Unauthorized()
        
        subject = req.headers.get(config.auth.subject_header)
    
    if authorized_subject is not None:
        if subject in config.auth.root_subjects:
            logger.warning(f"allowed {method} access on {resource} by {subject} because it is a root subject")
            return
        
        if subject != authorized_subject:
            logger.debug(f"rejected {method} access on {resource} with authorized subjects {authorized_subject} because of authorized subject mismatch")
            raise Unauthorized()
    
    logger.debug(f"allowed {authorized_subject or "<anonymous>"} {method} access on {resource} with authorized subjects {authorized_subject}")

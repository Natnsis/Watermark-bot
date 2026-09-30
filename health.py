"""Tiny HTTP responder so hosting platforms that expect a web service see the bot as healthy."""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_RESPONSE = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
_server: asyncio.Server | None = None


async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        writer.write(_RESPONSE)
        await writer.drain()
    except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
        pass
    finally:
        writer.close()


async def start_health_server() -> None:
    """Listens on $PORT when the platform sets it; does nothing otherwise."""
    global _server
    port = os.environ.get("PORT")
    if not port:
        return
    _server = await asyncio.start_server(_handle, "0.0.0.0", int(port))
    logger.info("Health check listening on port %s", port)

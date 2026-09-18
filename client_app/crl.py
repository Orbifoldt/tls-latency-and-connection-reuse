import ssl
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, BinaryIO

import httpx
from httpx import Response

from client_app.config import CRL_URL, TRUSTSTORE
from client_app.models import ServerResponse


async def call_server(url: str) -> ServerResponse:
    # First we need to manually fetch the whole CRL
    crl_response = await _fetch_crl_file()

    # Then manually add it to the ssl context
    async with _create_trust_bundle(crl_response.content) as trust_bundle:
        context = ssl.create_default_context(cafile=trust_bundle.name)

        # Turn on the CRL check
        context.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF

        async with httpx.AsyncClient(verify=context) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return ServerResponse(status_code=response.status_code, body_content=response.text)
            except httpx.ConnectError as e:
                return ServerResponse(status_code=None, body_content=None, error=f"Could not connect to server: {e}")
            except httpx.HTTPError as e:
                return ServerResponse(status_code=500, body_content=None, error=str(e))


async def _fetch_crl_file() -> Response:
    async with httpx.AsyncClient() as crl_client:
        crl_response = await crl_client.get(CRL_URL)
        crl_response.raise_for_status()
    return crl_response


@asynccontextmanager
async def _create_trust_bundle(crl_content: bytes) -> AsyncIterator[BinaryIO]:
    # OpenSSL loads CRLs from the same PEM bundle as the trusted certificates,
    # so write both the truststore and CRL to a shared temporary file.
    with tempfile.NamedTemporaryFile(mode="wb") as trust_bundle:
        trust_bundle.write(Path(TRUSTSTORE).read_bytes())
        trust_bundle.write(crl_content)
        trust_bundle.flush()
        yield trust_bundle


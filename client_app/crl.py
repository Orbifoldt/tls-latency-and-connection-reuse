import asyncio
import ssl
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, BinaryIO
from urllib.parse import urlsplit

import httpx
from cryptography import x509
from cryptography.x509 import ExtensionNotFound

from client_app.config import CRL_URL, TRUSTSTORE
from client_app.models import ServerResponse


async def call_server(url: str) -> ServerResponse:
    # First we need to manually fetch the whole CRL, here using a hardcoded URL
    crl_content = await _fetch_crl_file(CRL_URL)

    # Then manually add it to the ssl context
    async with _create_trust_bundle(crl_content) as trust_bundle:
        context = ssl.create_default_context(cafile=trust_bundle.name)

        # Turn on the CRL check
        context.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF

        async with httpx.AsyncClient(verify=context) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return ServerResponse(status_code=response.status_code, body_content=response.text)
            except httpx.ConnectError as e:
                return ServerResponse(status_code=None, error=f"Could not connect to server: {e}")
            except httpx.HTTPError as e:
                return ServerResponse(status_code=500, error=str(e))


async def call_server_with_discovered_crl(url: str) -> ServerResponse:
    # Here we dynamically "discover" the CRL URL from the certificate
    # The CRL URL is only available after the server has presented its certificate, so discovery and the actual
    # request are two TLS sessions. => very inefficient...
    server_certificate = await _fetch_server_certificate(url)
    crl_urls = _get_crl_urls(server_certificate)
    if not crl_urls:
        return ServerResponse(status_code=None, error="Server certificate has no CRL Distribution Point")

    crl_content = await _fetch_crl_file(crl_urls[0])

    # Then manually add it to the ssl context
    async with _create_trust_bundle(crl_content) as trust_bundle:
        context = ssl.create_default_context(cafile=trust_bundle.name)

        # Turn on the CRL check
        context.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF

        async with httpx.AsyncClient(verify=context) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return ServerResponse(status_code=response.status_code, body_content=response.text)
            except httpx.ConnectError as e:
                return ServerResponse(status_code=None, error=f"Could not connect to server: {e}")
            except httpx.HTTPError as e:
                return ServerResponse(status_code=500, error=str(e))


async def _fetch_crl_file(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


@asynccontextmanager
async def _create_trust_bundle(crl_content: bytes) -> AsyncIterator[BinaryIO]:
    # OpenSSL loads CRLs from the same PEM bundle as the trusted certificates,
    # so write both the truststore and CRL to a shared temporary file.
    with tempfile.NamedTemporaryFile(mode="wb") as trust_bundle:
        trust_bundle.write(Path(TRUSTSTORE).read_bytes())
        trust_bundle.write(crl_content)
        trust_bundle.flush()
        yield trust_bundle


async def _fetch_server_certificate(url: str) -> bytes:
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("CRL discovery requires an HTTPS URL with a hostname")

    port = parsed_url.port or 443
    context = ssl.create_default_context(cafile=TRUSTSTORE)

    _, writer = await asyncio.open_connection(
        parsed_url.hostname,
        port,
        ssl=context,
        server_hostname=parsed_url.hostname,
    )
    try:
        ssl_object = writer.get_extra_info("ssl_object")
        if ssl_object is None:
            raise ssl.SSLError("TLS connection did not expose an SSL object")

        certificate = ssl_object.getpeercert(binary_form=True)
        if certificate is None:
            raise ssl.SSLError("TLS peer did not provide a certificate")
        return certificate
    finally:
        writer.close()
        await writer.wait_closed()


def _get_crl_urls(certificate_der: bytes) -> list[str]:
    certificate = x509.load_der_x509_certificate(certificate_der)
    try:
        distribution_points = certificate.extensions.get_extension_for_class(
            x509.CRLDistributionPoints,
        ).value
    except ExtensionNotFound:
        return []

    urls: list[str] = []
    for distribution_point in distribution_points:
        if distribution_point.full_name is None:
            continue
        urls.extend(
            general_name.value
            for general_name in distribution_point.full_name
            if isinstance(general_name, x509.UniformResourceIdentifier)
            and general_name.value.startswith(("http://", "https://"))
        )
    return urls

from fastapi import FastAPI

from client_app import crl, default_httpx
from client_app.config import get_server_url
from client_app.models import ServerResponse

app = FastAPI()


@app.get("/default")
async def call_with_crl_check(revoked: bool = False) -> ServerResponse:
    return await default_httpx.call_server(get_server_url(revoked))

@app.get("/crl")
async def call_with_crl_check(revoked: bool = False) -> ServerResponse:
    return await crl.call_server(get_server_url(revoked))

@app.get("/crl-auto")
async def call_with_discovered_crl_check(revoked: bool = False) -> ServerResponse:
    return await crl.call_server_with_discovered_crl(get_server_url(revoked))

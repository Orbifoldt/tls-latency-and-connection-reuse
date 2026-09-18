import httpx

from client_app.config import TRUSTSTORE
from client_app.models import ServerResponse


async def call_server(url: str) -> ServerResponse:
    async with httpx.AsyncClient(verify=TRUSTSTORE) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return ServerResponse(status_code=response.status_code, body_content=response.text)
        except httpx.ConnectError as e:
            return ServerResponse(status_code=None, body_content=None, error=f"Could not connect to server: {e}")
        except httpx.HTTPError as e:
            return ServerResponse(status_code=500, body_content=None, error=str(e))

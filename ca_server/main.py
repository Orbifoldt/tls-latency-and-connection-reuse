from pathlib import Path

from fastapi import FastAPI
from starlette.responses import FileResponse

app = FastAPI()

CRL_PATH = Path(__file__).resolve().parents[1] / "certs" / "ca_server" / "intermediate.crl.pem"


@app.get("/crl/intermediate.crl.pem")
async def get_intermediate_crl() -> FileResponse:
    return FileResponse(CRL_PATH, media_type="application/pkix-crl")

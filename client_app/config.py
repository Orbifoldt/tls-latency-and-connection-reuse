from pathlib import Path


TRUSTSTORE = str(Path(__file__).resolve().parents[1] / "certs" / "root" / "root.cert.pem")
CRL_URL = "http://localhost:6080/crl/intermediate.crl.pem"


def get_server_url(revoked: bool) -> str:
    return f"https://localhost:{8442 if revoked else 8443}"

from pydantic import BaseModel


class ServerResponse(BaseModel):
    status_code: int | None
    body_content: str | None = None
    error: str | None = None


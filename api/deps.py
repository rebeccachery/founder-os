import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException

API_KEY = os.getenv("API_KEY", "dev-local-key")


def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

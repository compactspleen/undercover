"""The agent's connection to the UnderCover backend, its only source of records."""

from http import HTTPStatus

import httpx

BACKEND_URL = "http://localhost:8000"

# Answers the model can act on, such as a payment waiting for sign-off.
REFUSALS = (HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY)


def client() -> httpx.Client:
    """Return a client for the backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def get(path: str) -> str:
    """Read from the backend, raising on any error."""
    with client() as backend:
        response = backend.get(path)
    response.raise_for_status()
    return response.text


def post(path: str, body: dict[str, object]) -> str:
    """Write to the backend, raising on any error."""
    with client() as backend:
        response = backend.post(path, json=body)
    response.raise_for_status()
    return response.text


def attempt(path: str, body: dict[str, object]) -> str:
    """Write to the backend for the model, giving a refusal back as text."""
    with client() as backend:
        response = backend.post(path, json=body)
    if response.status_code in REFUSALS:
        return f"Refused ({response.status_code}): {refusal_reason(response)}"
    response.raise_for_status()
    return response.text


def refusal_reason(response: httpx.Response) -> str:
    """Return the backend's reason for a refusal."""
    detail: object = response.json()["detail"]
    return detail if isinstance(detail, str) else response.text

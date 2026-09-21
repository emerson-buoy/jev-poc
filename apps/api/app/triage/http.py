import httpx

from app.triage.port import TriageError

REQUEST_TIMEOUT_SECONDS = 30.0


class HttpEvaluator:
    def __init__(self, url: str, api_key: str, label: str) -> None:
        self._url = url
        self._label = label
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}, timeout=REQUEST_TIMEOUT_SECONDS
        )

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    def post(self, payload: dict) -> dict:
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.HTTPError as error:
            raise TriageError(f"Could not reach {self._label}: {error}") from error
        if response.is_error:
            raise TriageError(
                f"{self._label} returned {response.status_code}: {_error_message(response)}"
            )
        try:
            body = response.json()
        except ValueError as error:
            raise TriageError(f"Unexpected {self._label} response: not JSON") from error
        if not isinstance(body, dict):
            raise TriageError(f"Unexpected {self._label} response: not an object")
        return body

    def close(self) -> None:
        self._client.close()


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict):
        detail = body.get("error", body)
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("detail")
            if isinstance(message, str):
                return message
    return response.text[:200]

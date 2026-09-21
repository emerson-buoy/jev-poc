import httpx

from app.triage.port import MalformedResponse, ProviderRejected, ProviderUnavailable

REQUEST_TIMEOUT_SECONDS = 30.0
TOO_MANY_REQUESTS = 429


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
            raise ProviderUnavailable(f"Could not reach {self._label}: {error}") from error
        if response.is_error:
            raise self._status_error(response)
        try:
            body = response.json()
        except ValueError as error:
            raise MalformedResponse(f"Unexpected {self._label} response: not JSON") from error
        if not isinstance(body, dict):
            raise MalformedResponse(f"Unexpected {self._label} response: not an object")
        return body

    def close(self) -> None:
        self._client.close()

    def _status_error(self, response: httpx.Response) -> ProviderUnavailable | ProviderRejected:
        message = f"{self._label} returned {response.status_code}: {_error_message(response)}"
        if response.status_code == TOO_MANY_REQUESTS or response.is_server_error:
            return ProviderUnavailable(message, retry_after=_retry_after(response))
        return ProviderRejected(message)


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return None


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

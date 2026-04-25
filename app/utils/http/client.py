from fastapi import HTTPException
import httpx
from typing import Dict, Optional, Any
from app.utils.logger import logger


class Client:
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.timeout = timeout
        self.base_url = base_url.rstrip('/')

    def _build_url(self, endpoint: str) -> str:
        """Build full URL by combining backend URL with endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        """
        Internal base request handler to manage execution and error handling.
        """
        url = self._build_url(endpoint)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Making {method} request to {url}")
                response = await client.request(method, url, headers=headers, **kwargs)

                # Raises httpx.HTTPStatusError if response is 4xx or 5xx
                response.raise_for_status()

                return response.json()

            except httpx.HTTPStatusError as e:
                # Pass through the actual status code from the external service
                status_code = e.response.status_code
                detail = e.response.text or f"External service error: {status_code}"
                logger.error(f"External API error {status_code} at {url}: {detail}")
                raise HTTPException(status_code=status_code, detail=detail)

            except httpx.RequestError as e:
                # Handle connection issues, timeouts, DNS failures
                logger.error(f"Network error reaching {url}: {e}")
                raise HTTPException(status_code=503, detail="External service is unreachable")

            except Exception as e:
                # Catch-all for unexpected logic or parsing errors
                logger.error(f"Unexpected error in {method} {url}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    # --- Public Methods ---

    async def get(self, endpoint: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict] = None):
        return await self._request("GET", endpoint, headers=headers, params=params)

    async def post(self, endpoint: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict] = None, data: Optional[Dict] = None, files: Optional[Dict] = None):
        return await self._request("POST", endpoint, headers=headers, json=json_data, data=data, files=files)

    async def put(self, endpoint: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict] = None, data: Optional[Dict] = None):
        return await self._request("PUT", endpoint, headers=headers, json=json_data, data=data)

    async def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        return await self._request("DELETE", endpoint, headers=headers)

    # Note: These aliases exist to maintain compatibility with your current calls.
    # In a JSON-based API, get and get_json usually behave identically.

    get_json = get
    post_json = post
    put_json = put
    delete_json = delete

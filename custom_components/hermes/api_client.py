"""HTTP client for the Hermes OpenAI-compatible API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .exceptions import (
    HermesAuthenticationError,
    HermesConnectionError,
    HermesTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


class HermesApiClient:
    """Client for the Hermes OpenAI-compatible API server."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        api_key: str | None,
        timeout: int,
    ) -> None:
        self._hass = hass
        self._base_url = f"http://{host}:{port}"
        self._api_key = api_key
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def health(self) -> bool:
        """Check connectivity. Returns True if healthy."""
        session = aiohttp_client.async_get_clientsession(self._hass)
        try:
            async with session.get(
                f"{self._base_url}/health",
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    raise HermesAuthenticationError("Invalid API key")
                return resp.status == 200
        except asyncio.TimeoutError as err:
            raise HermesTimeoutError("Health check timed out") from err
        except HermesAuthenticationError:
            raise
        except Exception as err:
            raise HermesConnectionError(str(err)) from err

    async def chat(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> str:
        """Send a message and return the assistant's response text."""
        import aiohttp

        session = aiohttp_client.async_get_clientsession(self._hass)

        messages = [{"role": "user", "content": message}]

        payload: dict[str, Any] = {
            "model": "hermes-agent",
            "messages": messages,
            "stream": False,
        }

        # Use conversation_id as a named conversation so Hermes maintains context
        if conversation_id:
            payload["conversation"] = conversation_id

        try:
            async with session.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                if resp.status == 401:
                    raise HermesAuthenticationError("Invalid API key")
                if resp.status != 200:
                    body = await resp.text()
                    raise HermesConnectionError(f"HTTP {resp.status}: {body}")
                data = await resp.json()

        except asyncio.TimeoutError as err:
            raise HermesTimeoutError("Request timed out") from err
        except (HermesAuthenticationError, HermesConnectionError):
            raise
        except Exception as err:
            raise HermesConnectionError(str(err)) from err

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            raise HermesConnectionError(f"Unexpected response format: {data}") from err

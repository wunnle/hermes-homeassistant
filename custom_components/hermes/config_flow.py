"""Config flow for the Hermes integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api_client import HermesApiClient
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_STRIP_EMOJIS,
    CONF_TIMEOUT,
    CONF_TTS_MAX_CHARS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_STRIP_EMOJIS,
    DEFAULT_TIMEOUT,
    DEFAULT_TTS_MAX_CHARS,
    DOMAIN,
)
from .exceptions import (
    HermesAuthenticationError,
    HermesConnectionError,
    HermesTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_connection(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Raise an exception if the connection is invalid."""
    client = HermesApiClient(
        hass=hass,
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        api_key=data.get(CONF_API_KEY),
        timeout=10,
    )
    await client.health()


class HermesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hermes."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await _validate_connection(self.hass, user_input)
            except HermesAuthenticationError:
                errors["base"] = "invalid_auth"
            except HermesTimeoutError:
                errors["base"] = "timeout"
            except HermesConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                self._connection_data = user_input
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        int, vol.Range(min=1, max=65535)
                    ),
                    vol.Optional(CONF_API_KEY): str,
                    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
                        int, vol.Range(min=5, max=300)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            data = {**self._connection_data, **user_input}
            return self.async_create_entry(
                title=f"Hermes ({self._connection_data[CONF_HOST]})",
                data=data,
            )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_STRIP_EMOJIS, default=DEFAULT_STRIP_EMOJIS
                    ): bool,
                    vol.Optional(
                        CONF_TTS_MAX_CHARS, default=DEFAULT_TTS_MAX_CHARS
                    ): vol.All(int, vol.Range(min=0, max=2000)),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return HermesOptionsFlow()


class HermesOptionsFlow(config_entries.OptionsFlow):
    """Handle Hermes options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            try:
                await _validate_connection(self.hass, {**current, **user_input})
            except HermesAuthenticationError:
                errors["base"] = "invalid_auth"
            except HermesTimeoutError:
                errors["base"] = "timeout"
            except HermesConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                    options=user_input,
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=current.get(CONF_HOST, DEFAULT_HOST)
                    ): str,
                    vol.Required(
                        CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
                    ): vol.All(int, vol.Range(min=1, max=65535)),
                    vol.Optional(
                        CONF_API_KEY, default=current.get(CONF_API_KEY, "")
                    ): str,
                    vol.Optional(
                        CONF_TIMEOUT,
                        default=current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    ): vol.All(int, vol.Range(min=5, max=300)),
                    vol.Optional(
                        CONF_STRIP_EMOJIS,
                        default=current.get(CONF_STRIP_EMOJIS, DEFAULT_STRIP_EMOJIS),
                    ): bool,
                    vol.Optional(
                        CONF_TTS_MAX_CHARS,
                        default=current.get(CONF_TTS_MAX_CHARS, DEFAULT_TTS_MAX_CHARS),
                    ): vol.All(int, vol.Range(min=0, max=2000)),
                }
            ),
            errors=errors,
        )

"""Conversation entity for the Hermes integration."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_client import HermesApiClient
from .const import (
    CONF_STRIP_EMOJIS,
    CONF_TTS_MAX_CHARS,
    DEFAULT_STRIP_EMOJIS,
    DEFAULT_TTS_MAX_CHARS,
    DOMAIN,
)
from .exceptions import (
    HermesAuthenticationError,
    HermesConnectionError,
    HermesTimeoutError,
)

_LOGGER = logging.getLogger(__name__)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def _strip_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub("", text).strip()


def _trim_tts(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."


def _should_continue(text: str) -> bool:
    """Return True if the response ends with a question."""
    stripped = text.strip()
    return bool(re.search(r"\?[\s\"'\u201c\u201d\u2018\u2019]*$", stripped))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hermes conversation entity."""
    client: HermesApiClient = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([HermesConversationEntity(config_entry, client)])


class HermesConversationEntity(conversation.ConversationEntity):
    """Hermes conversation entity."""

    _attr_has_entity_name = True
    _attr_name = "Hermes"
    _attr_supported_languages = "*"

    def __init__(self, config_entry: ConfigEntry, client: HermesApiClient) -> None:
        self._config_entry = config_entry
        self._client = client
        self._attr_unique_id = config_entry.entry_id

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "Hermes Agent",
            "manufacturer": "Hermes",
            "model": "API Server",
        }

    @property
    def available(self) -> bool:
        return True

    @property
    def supported_languages(self) -> list[str] | str:
        return "*"

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Handle a voice/text message from HA."""
        _LOGGER.debug("Hermes handling: %s", user_input.text)

        try:
            response_text = await self._client.chat(
                message=user_input.text,
                conversation_id=user_input.conversation_id,
            )
        except HermesAuthenticationError:
            response_text = "Authentication failed. Please check your Hermes API key in the integration settings."
        except HermesTimeoutError:
            response_text = "Hermes took too long to respond. Please try again."
        except HermesConnectionError as err:
            _LOGGER.error("Hermes connection error: %s", err)
            response_text = "I couldn't reach the Hermes agent. Please check that it's running."

        # Add to chat log
        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=user_input.agent_id,
                content=response_text,
            )
        )

        # Build TTS speech text
        config = {**self._config_entry.data, **self._config_entry.options}
        speech_text = response_text
        if config.get(CONF_STRIP_EMOJIS, DEFAULT_STRIP_EMOJIS):
            speech_text = _strip_emojis(speech_text)
        max_chars = config.get(CONF_TTS_MAX_CHARS, DEFAULT_TTS_MAX_CHARS)
        speech_text = _trim_tts(speech_text, max_chars)

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(speech_text)

        # Keep mic open if Hermes asked a question
        continue_conversation = _should_continue(response_text)

        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
            continue_conversation=continue_conversation,
        )

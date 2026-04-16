# Hermes Voice Assistant for Home Assistant

A Home Assistant custom integration that connects your voice PE to [Hermes Agent](https://github.com/ddrayne/hermes-agent) via its OpenAI-compatible API server.

## Features

- Full Hermes agent behind your voice: Spotify, calendar, Linear, camera, smart home, and more
- **`continue_conversation` support** — mic stays open when Hermes asks a follow-up question
- Emoji stripping and TTS character limits for clean voice output
- Simple Bearer token auth

## Requirements

- Hermes Agent running with the API server enabled
- Home Assistant 2024.1.0+

## Hermes Setup

Add to `~/.hermes/.env`:

```bash
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8642
API_SERVER_KEY=your-secret-key
```

Restart the Hermes gateway.

## Installation via HACS

1. In HACS, go to **Integrations** → **Custom repositories**
2. Add `https://github.com/ddrayne/hermes-homeassistant` as an **Integration**
3. Install **Hermes Voice Assistant**
4. Restart Home Assistant

## Manual Installation

Copy `custom_components/hermes/` into your HA config's `custom_components/` folder and restart.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Hermes**
3. Enter your Pi's IP, port (`8642`), and API key

## Voice PE Setup

1. Go to **Settings** → **Voice assistants** → your assistant
2. Set **Conversation agent** to **Hermes**
3. Done — wake word routes to Hermes

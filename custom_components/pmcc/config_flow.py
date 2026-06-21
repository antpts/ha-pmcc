"""Config flow for the Porsche Mobile Charger Connect."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    DOMAIN,
    JWT_LOGIN_PATH,
    WEB_USER,
    WS_PATH,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


async def _validate(hass, host: str, password: str | None) -> None:
    """Verify the charger is reachable and the password (if any) is valid.

    Raises ``CannotConnect`` or ``InvalidAuth``.
    """
    session = async_get_clientsession(hass, verify_ssl=False)

    # Reading the metric stream needs no auth, so a successful WS handshake is
    # our reachability + "this is a Webconnect charger" check.
    try:
        async with asyncio.timeout(10):
            async with session.ws_connect(
                f"wss://{host}{WS_PATH}",
                headers={"Origin": f"https://{host}"},
                ssl=False,
            ) as ws:
                await ws.close()
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
        raise CannotConnect from err

    if not password:
        return

    # The charger's nginx drops the first request on a fresh connection, so
    # retry a couple of times before declaring it unreachable.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": f"https://{host}/",
    }
    last_err: Exception | None = None
    for _ in range(3):
        try:
            async with asyncio.timeout(10):
                async with session.post(
                    f"https://{host}{JWT_LOGIN_PATH}",
                    data={"user": WEB_USER, "pass": password},
                    headers=headers,
                    ssl=False,
                ) as resp:
                    if resp.status == 200:
                        return
                    if resp.status in (401, 403):
                        raise InvalidAuth
                    raise CannotConnect(f"HTTP {resp.status}")
        except (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError) as err:
            last_err = err
            await asyncio.sleep(0.5)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise CannotConnect from err
    raise CannotConnect from last_err


class PmccConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input.get(CONF_PASSWORD)
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            try:
                await _validate(self.hass, host, password)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors[CONF_PASSWORD] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating charger")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Charger ({host})",
                    data={CONF_HOST: host, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )


class CannotConnect(Exception):
    """Cannot reach the charger."""


class InvalidAuth(Exception):
    """The supplied password was rejected."""

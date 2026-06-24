"""Push coordinator for the Porsche Mobile Charger Connect.

The charger streams JSON property updates over a WebSocket (``wss://<host>/ws``).
Reading requires no authentication; changing the current limit goes through the
web UI's JWT-protected REST API. We keep a persistent listener task that merges
incoming fragments into a single state dict and pushes debounced updates to HA.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from datetime import datetime

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CURRENT_LIMIT_PATH,
    JWT_LOGIN_PATH,
    MAX_CURRENT,
    MIN_NONZERO_CURRENT,
    UPDATE_DEBOUNCE,
    WEB_USER,
    WS_HEARTBEAT,
    WS_PATH,
)
from .parser import convert_properties

_LOGGER = logging.getLogger(__name__)

# The charger's embedded nginx drops the first request on a connection and
# wants a browser-like client; a browser User-Agent + force_close + retry make
# the control calls reliable (proven via tools/probe.py).
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_CONTROL_RETRIES = 3
# Seconds between control-call retries. This covers the transient first-request
# drop the charger shows *while awake*. It does NOT wake a sleeping charger —
# that only happens via the physical power button or an actual charging event —
# so we keep the budget small to avoid hanging against an asleep device.
_RETRY_DELAY = 1.0


class PmccCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Maintains charger state from the WebSocket stream (local push)."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, host: str, password: str | None
    ) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=f"PMCC {host}")
        self.host = host
        self.password = password
        self.data = {}
        self.current_limit: int | None = None
        self.connected = False
        self.last_message_time: datetime | None = None

        self._session = async_get_clientsession(hass, verify_ssl=False)
        self._control_session: aiohttp.ClientSession | None = None
        self._ws_task: asyncio.Task | None = None
        self._flush_handle: asyncio.TimerHandle | None = None
        self._token: str | None = None

    # ---- lifecycle -------------------------------------------------------

    async def async_start(self) -> None:
        """Launch the background WebSocket listener."""
        self._ws_task = self.config_entry.async_create_background_task(
            self.hass, self._ws_loop(), name=f"pmcc-ws-{self.host}"
        )

    async def async_shutdown(self) -> None:
        """Stop the listener and cancel any pending flush."""
        if self._flush_handle is not None:
            self._flush_handle.cancel()
            self._flush_handle = None
        if self._ws_task is not None:
            self._ws_task.cancel()
            self._ws_task = None
        if self._control_session is not None:
            await self._control_session.close()
            self._control_session = None
        await super().async_shutdown()

    # ---- websocket -------------------------------------------------------

    async def _ws_loop(self) -> None:
        """Connect, stream, and reconnect forever."""
        url = f"wss://{self.host}{WS_PATH}"
        headers = {"Origin": f"https://{self.host}"}
        backoff = 5
        while True:
            try:
                async with self._session.ws_connect(
                    url, headers=headers, heartbeat=WS_HEARTBEAT, ssl=False
                ) as ws:
                    _LOGGER.info("Connected to charger %s", self.host)
                    self._set_connected(True)
                    backoff = 5
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._handle_message(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - resilient reconnect loop
                _LOGGER.debug("Charger %s connection error: %s", self.host, err)

            self._mark_offline()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    def _handle_message(self, raw: str) -> None:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            _LOGGER.debug("Dropping non-JSON charger frame")
            return
        updates = convert_properties(obj)
        if not updates:
            return
        self.data.update(updates)
        self.last_message_time = dt_util.utcnow()
        self._schedule_update()

    @callback
    def _schedule_update(self) -> None:
        """Coalesce rapid stream updates into one HA state refresh."""
        if self._flush_handle is None:
            self._flush_handle = self.hass.loop.call_later(
                UPDATE_DEBOUNCE, self._flush_update
            )

    @callback
    def _flush_update(self) -> None:
        self._flush_handle = None
        self.async_set_updated_data(dict(self.data))

    @callback
    def _set_connected(self, value: bool) -> None:
        """Update connectivity and notify entities if it changed."""
        if self.connected != value:
            self.connected = value
            self.async_update_listeners()

    @callback
    def _mark_offline(self) -> None:
        self._set_connected(False)
        if self.last_update_success:
            self.last_update_success = False
            self.async_update_listeners()

    # ---- control (JWT REST API) -----------------------------------------

    def _get_control_session(self) -> aiohttp.ClientSession:
        """A dedicated session for REST control calls.

        Uses ``force_close`` (fresh socket per request) and a browser
        User-Agent, which the charger's firmware needs; reading still uses the
        shared HA session over the WebSocket.
        """
        if self._control_session is None or self._control_session.closed:
            self._control_session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False, force_close=True),
                headers={
                    "User-Agent": _USER_AGENT,
                    "Referer": f"https://{self.host}/",
                    "Origin": f"https://{self.host}",
                },
            )
        return self._control_session

    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Issue a control request, retrying the transient first-request drop.

        While awake the charger occasionally drops the first request on a fresh
        connection; a retry then succeeds. If the charger is asleep (only the
        power button or a charging event wakes it) every attempt fails and we
        raise after a small fixed budget rather than blocking.
        """
        session = self._get_control_session()
        last_err: Exception | None = None
        for _ in range(_CONTROL_RETRIES):
            try:
                return await session.request(method, url, ssl=False, **kwargs)
            except (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError) as err:
                last_err = err
                await asyncio.sleep(_RETRY_DELAY)
        raise PmccError(f"Charger unreachable (asleep?) after retries: {last_err}")

    async def _login(self) -> None:
        url = f"https://{self.host}{JWT_LOGIN_PATH}"
        resp = await self._request(
            "POST",
            url,
            data={"user": WEB_USER, "pass": self.password},
            headers={"Accept": "application/json"},
        )
        async with resp:
            if resp.status != 200:
                raise PmccAuthError(f"Login failed: HTTP {resp.status}")
            self._token = (await resp.json(content_type=None))["token"]

    async def async_set_current_limit(self, value: int) -> None:
        """Set the HMI current limit (Amps) via the authenticated REST API."""
        if not self.password:
            raise PmccAuthError("No password configured; cannot set current limit")
        value = min(value, MAX_CURRENT)
        if 1 <= value < MIN_NONZERO_CURRENT:
            value = MIN_NONZERO_CURRENT  # charger rejects currents below the minimum

        if self._token is None:
            await self._login()

        # One automatic re-login if the token has expired.
        for attempt in (1, 2):
            resp = await self._request(
                "PUT",
                f"https://{self.host}{CURRENT_LIMIT_PATH}?value={value}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            async with resp:
                if resp.status in (401, 403) and attempt == 1:
                    await self._login()
                    continue
                text = await resp.text()
                if resp.status != 200 or "OK" not in text:
                    raise PmccError(f"Set current limit failed: HTTP {resp.status}")
                break

        self.current_limit = value
        self.async_update_listeners()


class PmccError(Exception):
    """Generic charger error."""


class PmccAuthError(PmccError):
    """Authentication against the charger web UI failed."""

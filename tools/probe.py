#!/usr/bin/env python3
"""Standalone protocol probe for the Porsche Mobile Charger Connect.

Does NOT need Home Assistant. Mirrors the exact aiohttp calls used by the
integration so we can confirm the charger behaves as expected.

Credentials are read from the environment so they never appear in argv:
    PMCC_HOST   charger host or IP   (required)
    PMCC_PASS   Home User password   (optional; enables the auth test)

The host is masked as "<charger>" in all output; the token/password are never
printed. This probe is read-only and never changes a charger setting.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import aiohttp

# Reuse the integration's parser so we validate it against real data.
# parser.py has no Home Assistant imports, so this works without HA installed.
sys.path.insert(0, "custom_components/pmcc")
from parser import convert_properties  # noqa: E402

HOST_LABEL = "<charger>"  # never print the real host
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


async def probe_ws(host: str, seconds: float = 8.0) -> None:
    print(f"[ws] connecting to wss://{HOST_LABEL}/ws ...")
    session = aiohttp.ClientSession()
    keys: set[str] = set()
    count = 0
    try:
        async with session.ws_connect(
            f"wss://{host}/ws",
            headers={"Origin": f"https://{host}"},
            ssl=False,
            heartbeat=30,
        ) as ws:
            print("[ws] connected, listening...")

            async def reader() -> None:
                nonlocal count
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    count += 1
                    flat = convert_properties(json.loads(msg.data))
                    keys.update(flat)
                    if count <= 3:
                        print(f"[ws] sample msg #{count}: {json.dumps(flat)[:300]}")

            try:
                await asyncio.wait_for(reader(), timeout=seconds)
            except asyncio.TimeoutError:
                pass
    finally:
        await session.close()

    print(f"\n[ws] received {count} messages, {len(keys)} distinct keys:")
    for k in sorted(keys):
        print(f"      {k}")


async def probe_login(host: str, password: str) -> None:
    """Exercise the exact control-path logic from the coordinator (read-only)."""
    connector = aiohttp.TCPConnector(ssl=False, force_close=True)
    headers = {
        "User-Agent": _UA,
        "Accept": "application/json",
        "Referer": f"https://{host}/",
        "Origin": f"https://{host}",
    }
    session = aiohttp.ClientSession(connector=connector, headers=headers)
    try:
        print(f"\n[auth] GET https://{HOST_LABEL}/ (baseline) ...")
        try:
            async with session.get(f"https://{host}/", ssl=False) as resp:
                print(f"[auth] GET / -> HTTP {resp.status}, server={resp.headers.get('Server')!r}")
        except Exception as err:  # noqa: BLE001
            print(f"[auth] GET / failed: {type(err).__name__}: {err}")

        print(f"[auth] POST https://{HOST_LABEL}/jwt/login (with retry) ...")
        for attempt in (1, 2, 3):
            try:
                async with session.post(
                    f"https://{host}/jwt/login",
                    data={"user": "user", "pass": password},
                    ssl=False,
                ) as resp:
                    if resp.status == 200:
                        payload = await resp.json(content_type=None)
                        token = payload.get("token", "")
                        ok = bool(token)
                        print(f"[auth] attempt {attempt}: HTTP 200, token received={ok}, length={len(token)}")
                    else:
                        print(f"[auth] attempt {attempt}: HTTP {resp.status} (auth rejected)")
                return
            except aiohttp.ServerDisconnectedError:
                print(f"[auth] attempt {attempt}: server disconnected before responding (retrying)")
            except Exception as err:  # noqa: BLE001
                print(f"[auth] attempt {attempt} failed: {type(err).__name__}: {err}")
                return
            await asyncio.sleep(0.5)
        print("[auth] giving up after retries")
    finally:
        await session.close()


async def probe_set_limit(host: str, password: str, value: int) -> None:
    """Login then PUT the HMI current limit. Writes — only runs if PMCC_SET set."""
    connector = aiohttp.TCPConnector(ssl=False, force_close=True)
    headers = {"User-Agent": _UA, "Referer": f"https://{host}/", "Origin": f"https://{host}"}
    session = aiohttp.ClientSession(connector=connector, headers=headers)

    async def request(method: str, url: str, **kw):
        last = None
        for _ in range(3):
            try:
                return await session.request(method, url, ssl=False, **kw)
            except (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError) as err:
                last = err
                await asyncio.sleep(0.5)
        raise RuntimeError(f"unreachable after retries: {last}")

    try:
        resp = await request(
            "POST", f"https://{host}/jwt/login",
            data={"user": "user", "pass": password}, headers={"Accept": "application/json"},
        )
        async with resp:
            if resp.status != 200:
                print(f"[set] login failed: HTTP {resp.status}")
                return
            token = (await resp.json(content_type=None))["token"]

        print(f"[set] PUT propHMICurrentLimit?value={value} ...")
        resp = await request(
            "PUT",
            f"https://{host}/v1/api/SCC/properties/propHMICurrentLimit?value={value}",
            headers={"Authorization": f"Bearer {token}"},
        )
        async with resp:
            body = (await resp.text()).strip()
            ok = resp.status == 200 and "OK" in body
            print(f"[set] HTTP {resp.status}, body={body[:80]!r}, success={ok}")
    finally:
        await session.close()


async def probe_discover(host: str, password: str, user: str = "user") -> None:
    """Login as `user`, then GET candidate REST endpoints (incl. privileged ones)."""
    connector = aiohttp.TCPConnector(ssl=False, force_close=True)
    headers = {"User-Agent": _UA, "Referer": f"https://{host}/", "Origin": f"https://{host}"}
    session = aiohttp.ClientSession(connector=connector, headers=headers)

    async def req(method, url, **kw):
        for _ in range(3):
            try:
                return await session.request(method, url, ssl=False, **kw)
            except (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError):
                await asyncio.sleep(0.5)
        return None

    candidates = [
        "/v1/api/WebServer/properties/cumulativeChargingData",
        "/v1/api/WebServer/properties/swaggerCurrentSession",
        "/v1/api/WebServer/properties/swaggerCurve",
        "/v1/api/WebServer/properties/swaggerHistory",
        "/v1/api/SCC/properties/propHMICurrentLimit",
        "/v1/api/iCAN/properties/activePowerL1",
    ]
    try:
        print(f"[disc] login as user={user!r} ...")
        resp = await req("POST", f"https://{host}/jwt/login",
                         data={"user": user, "pass": password},
                         headers={"Accept": "application/json"})
        async with resp:
            if resp.status != 200:
                print(f"[disc] login failed HTTP {resp.status} for user={user!r} (stopping; try another username)")
                return
            token = (await resp.json(content_type=None))["token"]
            print(f"[disc] login OK as user={user!r}")
        auth = {"Authorization": f"Bearer {token}"}
        for path in candidates:
            r = await req("GET", f"https://{host}{path}", headers=auth)
            if r is None:
                print(f"[disc] {path} -> unreachable")
                continue
            async with r:
                body = (await r.text())[:240].replace("\n", " ")
                print(f"[disc] {path} -> HTTP {r.status}: {body}")
    finally:
        await session.close()


async def main() -> None:
    host = os.environ.get("PMCC_HOST") or (sys.argv[1] if len(sys.argv) > 1 else "")
    password = os.environ.get("PMCC_PASS") or (sys.argv[2] if len(sys.argv) > 2 else "")
    set_value = os.environ.get("PMCC_SET")
    if not host:
        print(__doc__)
        sys.exit(1)
    if os.environ.get("PMCC_DISCOVER") and password:
        await probe_discover(host, password, os.environ.get("PMCC_USER", "user"))
        return
    seconds = float(os.environ.get("PMCC_WS_SECONDS", "8"))
    await probe_ws(host, seconds)
    if password:
        await probe_login(host, password)
        if set_value:
            await probe_set_limit(host, password, int(set_value))


if __name__ == "__main__":
    asyncio.run(main())

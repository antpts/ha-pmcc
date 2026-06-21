# Porsche Mobile Charger Connect — Home Assistant integration

A native Home Assistant custom integration for the **Porsche Mobile Charger
Connect** (PMCC) wallbox and other Webconnect-based VW-group chargers. It talks
to the charger **locally** — no cloud, no MQTT broker.

- **Local push** — subscribes to the charger's WebSocket (`wss://<host>/ws`) and
  streams live metrics. Reading needs no credentials.
- **Sensors** — active power per phase, total/session energy, state of charge,
  charging rate, solar share, vehicle brand/model, charge state, plus a set of
  diagnostic entities (WiFi, self-test, fault codes) that are disabled by default.
- **Current limit control** — a `number` entity (6–20 A) that sets the HMI
  charging current via the charger's JWT-protected REST API. Only added when you
  provide the "Home User" web password.

## Installation

### HACS (custom repository)
1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/antpts/ha-pmcc` as an *Integration*.
3. Install **Porsche Mobile Charger Connect** and restart Home Assistant.

### Manual
Copy `custom_components/pmcc/` into your Home Assistant `config/custom_components/`
directory and restart.

## Configuration
*Settings → Devices & Services → Add Integration → Porsche Mobile Charger Connect.*

- **Host / IP** — the charger's address on your network (required).
- **Home User password** — optional; only needed to expose the current-limit
  control. It's the password from the charger's access-data letter.

## Notes & limitations
- The charger uses a self-signed TLS certificate, so certificate verification is
  disabled for the local connection. Use only on a trusted network.
- Many low-level diagnostic metrics are exposed but **disabled by default** —
  enable them per entity if you need them.
- The current limit ranges from 6 A to 20 A (this unit's HMI range); values
  below 6 A are rounded up to the 6 A minimum charging current. The HMI limit
  reverts to maximum when the charger goes idle, so a set value is not
  necessarily persistent.
- **The charger sleeps when idle and only wakes via its power button or an
  actual charging event — not from network requests.** While asleep it's
  unreachable, so sensors stop updating and the **Connected** binary sensor goes
  off. Values refresh whenever it's awake; the total-energy sensor is restored
  across restarts so it doesn't reset to unknown.

## Credits
Protocol reverse-engineering derived from
[arisada/webconnect_mqtt](https://github.com/arisada/webconnect_mqtt)
(BSD-2-Clause). This project re-implements it as a native, broker-free
integration.

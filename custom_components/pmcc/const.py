"""Constants and the metric registry for the Porsche Mobile Charger Connect."""

from __future__ import annotations

DOMAIN = "pmcc"

# Config entry keys
CONF_HOST = "host"
CONF_PASSWORD = "password"

# WebSocket / HTTP
WS_PATH = "/ws"
JWT_LOGIN_PATH = "/jwt/login"
JWT_REFRESH_PATH = "/jwt/refresh"
CURRENT_LIMIT_PATH = "/v1/api/SCC/properties/propHMICurrentLimit"
WEB_USER = "user"

# State of charge fields report -1 when the vehicle doesn't share SoC.
SOC_UNKNOWN = -1

# The lifetime energy total gets special handling (hold last value + restore).
KEY_TOTAL_ENERGY = "de.bebro.WebServer.cumulativeChargingData.totalEnergy"

# Current limit bounds (Amps), per this charger's HMI range (6-20 A).
# Values below the minimum charging current are rounded up to it.
MIN_CURRENT = 6
MAX_CURRENT = 20
MIN_NONZERO_CURRENT = 6

# Debounce window (seconds) for coalescing the charger's message stream into
# Home Assistant state updates.
UPDATE_DEBOUNCE = 0.5

# How long the WebSocket may stay idle before we consider it dead.
WS_HEARTBEAT = 30

# ==========================================================
# METRIC REGISTRY
# ----------------------------------------------------------
# Keys are the flattened "de.bebro.<Interface>....<field>" paths streamed by
# the charger over the WebSocket. Each value carries Home Assistant metadata.
# Recognised metadata fields:
#   pretty_name           -> entity name
#   unit                  -> unit_of_measurement
#   device_class          -> SensorDeviceClass (only applied when a unit is set)
#   state_class           -> SensorStateClass
#   entity_category       -> "diagnostic" / "config"
#   enabled_by_default    -> override; defaults to (pretty_name present)
# Derived from arisada/webconnect_mqtt (BSD-2-Clause).
# ==========================================================

METRICS: dict[str, dict] = {
    # ---- iCAN: Active power per phase ----
    "de.bebro.iCAN.activePowerL1.value": {
        "pretty_name": "Active power L1",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "de.bebro.iCAN.activePowerL2.value": {
        "pretty_name": "Active power L2",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },
    "de.bebro.iCAN.activePowerL3.value": {
        "pretty_name": "Active power L3",
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
    },

    # ---- SelfTest: EMMC ----
    "de.bebro.SelfTest.EMMC.EMMC.identifier": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.EMMC.EMMC.PersistencyFreeSpaceError": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.EMMC.EMMC.PersistencyFreeSpaceWarning": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.EMMC.EMMC.PersistencyMountStatusError": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.EMMC.EMMC.SystemFreeSpaceError": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.EMMC.EMMC.SystemFreeSpaceWarning": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.EMMC.EMMC.SystemMountStatusError": {"entity_category": "diagnostic"},

    # ---- SelfTest: RAM ----
    "de.bebro.SelfTest.RAM.RAM.error": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.RAM.RAM.sensorType": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.RAM.RAM.warning": {"entity_category": "diagnostic"},

    # ---- SelfTest: Temperature ----
    "de.bebro.SelfTest.Temperature.Temp_CPU.error": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_CPU.sensorType": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_CPU.warning": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LCD.error": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LCD.sensorType": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LCD.warning": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LED1.error": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LED1.sensorType": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LED1.warning": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LED2.error": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LED2.sensorType": {"entity_category": "diagnostic"},
    "de.bebro.SelfTest.Temperature.Temp_LED2.warning": {"entity_category": "diagnostic"},

    # ---- WebServer: Charge state ----
    "de.bebro.WebServer.chargeState": {"pretty_name": "Charge state", "entity_category": "diagnostic"},

    # ---- iCAN: Power / LED state ----
    "de.bebro.iCAN.pwr_stategm_value": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.LedcState.LEDCstate": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.Mode.halfringLEDs": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.halfringLed.brightness": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.halfringLed.color": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.halfringLed.transition": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.halfringLedPulseSettings.curve": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.halfringLedPulseSettings.max": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.halfringLedPulseSettings.period": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.powerButtonLed.brightness": {"entity_category": "diagnostic"},
    "de.bebro.iCAN.propjLedState.powerButtonLed.color": {"entity_category": "diagnostic"},

    # ---- HMI ----
    "de.bebro.HMI.fahMessage": {"entity_category": "diagnostic"},

    # ---- SCC: Charge type / PLC ----
    "de.bebro.SCC.sigChargeType": {"pretty_name": "Charge type", "entity_category": "diagnostic"},
    "de.bebro.SCC.propIsV2GPLCEnabled": {"pretty_name": "V2G PLC enabled", "entity_category": "diagnostic"},

    # ---- SCC: EV charge parameters ----
    "de.bebro.SCC.propChargeParamEV.EVCapaClass": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVMaxEnergyReq": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVMinEnergyReq": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVMinPower": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVNumCurrentPhases": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVOwnCurrentReq": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVSymmCurrentsOnly": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVTargetEnergyReq": {"entity_category": "diagnostic"},
    "de.bebro.SCC.propChargeParamEV.EVTargetSoc": {"entity_category": "diagnostic"},

    # ---- SCC: Device name / identity ----
    "de.bebro.SCC.name.OEMId": {"entity_category": "diagnostic"},
    "de.bebro.SCC.name.UserDefinedName": {"pretty_name": "Charger name", "entity_category": "diagnostic"},
    "de.bebro.SCC.name.brand": {"entity_category": "diagnostic"},
    "de.bebro.SCC.name.isInWhitelist": {"entity_category": "diagnostic"},
    "de.bebro.SCC.name.model": {"pretty_name": "Charger model", "entity_category": "diagnostic"},
    "de.bebro.SCC.name.pcid": {"entity_category": "diagnostic"},

    # ---- DTCHandler: Fault codes ----
    "de.bebro.DTCHandler.dtclist": {"pretty_name": "Fault codes", "entity_category": "diagnostic"},
    "de.bebro.DTCHandler.dtccode": {"pretty_name": "Last fault code", "entity_category": "diagnostic"},
    "de.bebro.DTCHandler.bDTCAdded": {"pretty_name": "Fault code added", "entity_category": "diagnostic"},

    # ---- ConnectionManager: WiFi ----
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.ssid": {"pretty_name": "WiFi SSID", "entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.profile_name": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.ap_id": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.security_type": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.wifi_signal_strength": {
        "pretty_name": "WiFi signal strength",
        "unit": "dBm",
        "device_class": "signal_strength",
        "state_class": "measurement",
        "entity_category": "diagnostic",
    },
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.ip_address": {"pretty_name": "IP address", "entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.netmask": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.search_domains": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.nameservers": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.length": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.toState": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.WifiNetStatus.NetworkStatus.last_wifi_status": {"entity_category": "diagnostic"},

    # ---- ConnectionManager: Network controller / PLC / global / profiles ----
    "de.bebro.ConnectionManager.NetworkController.NetworkController.scanResults": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.PlcNetStatus.NetworkStatus.nameservers": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.PlcNetStatus.NetworkStatus.search_domains": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.GlobalNetStatus.NetworkStatus.toState": {"entity_category": "diagnostic"},
    "de.bebro.ConnectionManager.NetworkProfileManagement.Config.newCount": {"entity_category": "diagnostic"},

    # ---- WebServer: Charging history ----
    "de.bebro.WebServer.swaggerHistory": {"pretty_name": "Charging history", "entity_category": "diagnostic"},

    # ---- WebServer: Cumulative charging data ----
    # Lifetime total, pushed over the WebSocket while charging (REST endpoint is
    # 403 for the home user). This is the Energy Dashboard source.
    "de.bebro.WebServer.cumulativeChargingData.totalEnergy": {
        "pretty_name": "Total charging energy",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
    },
    # Lifetime charging time, reported as an "H:MM:SS" string; parsed to seconds
    # by the sensor's numeric coercion.
    "de.bebro.WebServer.cumulativeChargingData.totalTime": {
        "pretty_name": "Total charging time",
        "unit": "s",
        "device_class": "duration",
        "state_class": "total_increasing",
    },

    # ---- WebServer: Current session ----
    "de.bebro.WebServer.swaggerCurrentSession.account": {},
    "de.bebro.WebServer.swaggerCurrentSession.chargingRate": {
        "pretty_name": "Charging rate", "unit": "kW", "device_class": "power", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.chargingType": {"pretty_name": "Charging type"},
    "de.bebro.WebServer.swaggerCurrentSession.clockSrc": {},
    "de.bebro.WebServer.swaggerCurrentSession.costs": {"pretty_name": "Session costs", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurrentSession.currency": {},
    "de.bebro.WebServer.swaggerCurrentSession.departTime": {"pretty_name": "Departure time"},
    "de.bebro.WebServer.swaggerCurrentSession.duration": {
        "pretty_name": "Session duration", "unit": "s", "device_class": "duration", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.endOfChargeTime": {"pretty_name": "End of charge time"},
    "de.bebro.WebServer.swaggerCurrentSession.endSoc": {
        "pretty_name": "End SoC", "unit": "%", "device_class": "battery", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.endTime": {"pretty_name": "Session end time"},
    "de.bebro.WebServer.swaggerCurrentSession.energySumKwh": {
        "pretty_name": "Current session energy", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing",
    },
    "de.bebro.WebServer.swaggerCurrentSession.evChargingRatekW": {
        "pretty_name": "Charging rate (EV)", "unit": "kW", "device_class": "power", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.evTargetSoc": {
        "pretty_name": "Target SoC", "unit": "%", "device_class": "battery", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.evVasAvailability": {},
    "de.bebro.WebServer.swaggerCurrentSession.pcid": {},
    "de.bebro.WebServer.swaggerCurrentSession.powerRange": {"pretty_name": "Power range", "unit": "km", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurrentSession.profileChargingState": {"pretty_name": "Profile charging state"},
    "de.bebro.WebServer.swaggerCurrentSession.remainingChargingTime": {
        "pretty_name": "Remaining charging time", "unit": "s", "device_class": "duration", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.selfEnergy": {
        "pretty_name": "Self-generated energy", "unit": "kWh", "device_class": "energy", "state_class": "total_increasing",
    },
    "de.bebro.WebServer.swaggerCurrentSession.sessionId": {"pretty_name": "Session ID"},
    "de.bebro.WebServer.swaggerCurrentSession.soc": {
        "pretty_name": "State of charge", "unit": "%", "device_class": "battery", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.solarEnergyShare": {"pretty_name": "Solar energy share", "unit": "%", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurrentSession.startSoc": {
        "pretty_name": "Start SoC", "unit": "%", "device_class": "battery", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurrentSession.startTime": {"pretty_name": "Session start time"},
    "de.bebro.WebServer.swaggerCurrentSession.timerChargingState": {"pretty_name": "Timer charging state"},
    "de.bebro.WebServer.swaggerCurrentSession.totalRange": {"pretty_name": "Total range", "unit": "km", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurrentSession.vehicleBrand": {"pretty_name": "Vehicle brand"},
    "de.bebro.WebServer.swaggerCurrentSession.vehicleModel": {"pretty_name": "Vehicle model"},
    "de.bebro.WebServer.swaggerCurrentSession.whitelist": {},

    # ---- WebServer: Live power curve ----
    "de.bebro.WebServer.swaggerCurve.availableSelfGeneratedPower": {
        "pretty_name": "Available self-generated power", "unit": "kW", "device_class": "power", "state_class": "measurement",
    },
    "de.bebro.WebServer.swaggerCurve.currentEnergyCost": {"pretty_name": "Current energy cost", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerL1": {"pretty_name": "Power L1", "unit": "kW", "device_class": "power", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerL2": {"pretty_name": "Power L2", "unit": "kW", "device_class": "power", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerL3": {"pretty_name": "Power L3", "unit": "kW", "device_class": "power", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerLimitL1": {"pretty_name": "Power limit L1", "unit": "kW", "device_class": "power", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerLimitL2": {"pretty_name": "Power limit L2", "unit": "kW", "device_class": "power", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerLimitL3": {"pretty_name": "Power limit L3", "unit": "kW", "device_class": "power", "state_class": "measurement"},
    "de.bebro.WebServer.swaggerCurve.powerLimitReasonL1": {"pretty_name": "Power limit reason L1"},
    "de.bebro.WebServer.swaggerCurve.powerLimitReasonL2": {"pretty_name": "Power limit reason L2"},
    "de.bebro.WebServer.swaggerCurve.powerLimitReasonL3": {"pretty_name": "Power limit reason L3"},
    "de.bebro.WebServer.swaggerCurve.sessionId": {"pretty_name": "Curve session ID"},
    "de.bebro.WebServer.swaggerCurve.startTime": {"pretty_name": "Curve start time"},
    "de.bebro.WebServer.swaggerCurve.timestamp": {},
}

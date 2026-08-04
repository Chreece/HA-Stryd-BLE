# Stryd BLE 3.5.0

This is the first repository-ready release of the Stryd BLE custom integration.

## Highlights

- Robust discovery based on manufacturer ID `0xAAAA` and RSC service `0x1814`
- Passive battery, RSSI, and last-advertisement monitoring
- Manual live-data connection controls
- Live running power, speed, pace, cadence, stride length, distance, and movement state
- Automatic one-shot metadata retrieval and product-generation naming
- Non-blocking Home Assistant startup behavior
- English and Greek translations

## Installation

Install through HACS as a custom integration repository or copy `custom_components/strydx_ble` manually into the Home Assistant configuration directory.

See the README for complete setup, connection behavior, and troubleshooting instructions.

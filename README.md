# Stryd BLE for Home Assistant

[![HACS validation](https://github.com/Chreece/ha-stryd-ble/actions/workflows/validate.yml/badge.svg)](https://github.com/Chreece/ha-stryd-ble/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/Chreece/ha-stryd-ble)](https://github.com/Chreece/ha-stryd-ble/releases)
[![License](https://img.shields.io/github/license/Chreece/ha-stryd-ble)](LICENSE)

A local Home Assistant custom integration for Stryd running pods.

It continuously reads passive Bluetooth advertisements for battery and signal information, while keeping the pod's active BLE connection free for a sports watch or phone. Live running measurements are available only when explicitly requested with the **Connect live data** button.

> [!IMPORTANT]
> This is an unofficial community integration and is not affiliated with, endorsed by, or supported by Stryd.

## Features

- Automatic Bluetooth discovery without relying on the advertised name `StrydX`
- Identification using Stryd manufacturer ID `0xAAAA` and the standard Running Speed & Cadence service (`0x1814`)
- Manual Bluetooth MAC-address setup
- Works with local Bluetooth adapters and connectable Home Assistant Bluetooth proxies
- Passive data remains available without reserving the BLE connection
- One-shot metadata connection when model information has not yet been read
- Manual connect/disconnect controls for live measurements
- Product-generation naming after the model number is retrieved
- English and Greek translations
- Multiple Stryd pods supported

## Entities

### Always available from passive advertisements

| Entity | Description |
|---|---|
| Battery | Battery percentage broadcast by the pod |
| Bluetooth signal strength | RSSI of the most recent advertisement |
| Last advertisement | Time the latest advertisement was received |
| Advertisement count | Diagnostic packet counter; disabled by default |

### Available during a manual live-data connection

| Entity | Description |
|---|---|
| Live power | Running power in watts |
| Live speed | Instantaneous speed |
| Live pace | Calculated pace in min/km |
| Live cadence | Running cadence |
| Live stride length | Stride length when included by the pod |
| Live distance | Distance reported during the active connection |
| Live movement state | Still, walking, or running |
| Last live measurement | Timestamp; disabled by default to avoid frequent recorder writes |

Live entities become unavailable when the BLE connection is closed.

### Device and diagnostic information

The integration can retrieve and retain:

- Model number
- Product generation
- Firmware version
- Software version
- Hardware revision
- Serial number
- ANT ID derived from the pod identifier
- Live-data connection state

If identifying information is missing, the next matching advertisement triggers one short GATT connection. The integration reads the device information, saves it to the config entry, updates the device name, disconnects, and returns to passive mode.

## Supported product naming

The BLE advertisement initially appears as **Stryd running pod**. After reading the model number, the integration assigns the corresponding product-generation name, such as:

- Stryd
- Stryd Wind
- Next Gen Stryd
- Stryd 5.0

Unknown or future model numbers remain usable and receive a safe generic Stryd name.

## Installation

### HACS custom repository

1. Open HACS in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Add `https://github.com/Chreece/ha-stryd-ble` as an **Integration** repository.
4. Install **Stryd BLE**.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration → Stryd BLE**.

### Manual installation

1. Download the latest release.
2. Copy `custom_components/strydx_ble` into your Home Assistant configuration directory:

   ```text
   /config/custom_components/strydx_ble
   ```

3. Restart Home Assistant.
4. Add **Stryd BLE** from **Settings → Devices & services**.

## Setup and discovery

Move or shake the pod so it starts advertising. Home Assistant should offer it automatically, or you can use the integration's scan flow.

Discovery requires both:

- Manufacturer ID `43690` (`0xAAAA`)
- Running Speed & Cadence service UUID `00001814-0000-1000-8000-00805f9b34fb`

The local Bluetooth name is intentionally not used as an identity criterion, making discovery more robust across product generations.

## Live connection behavior

The integration starts in passive-only mode after every Home Assistant restart.

- Press **Connect live data** to reserve the BLE connection and subscribe to live measurements.
- Press **Disconnect live data** to release it for a watch or phone.
- The integration does not automatically reconnect for live data after a manual disconnect.
- Passive battery, RSSI, and last-seen data continue updating while disconnected.

A Stryd pod may permit only a limited number of simultaneous Bluetooth connections. Disconnect Home Assistant live data before pairing or syncing with another device if necessary.

## Bluetooth proxies

Passive information works through passive-capable proxies. Live GATT data and metadata retrieval require a **connectable** adapter or proxy.

For best results:

- Keep the pod near the chosen adapter/proxy while connecting.
- Close the Stryd app temporarily when testing GATT access.
- Wake the pod immediately before pressing **Connect live data**.

## Stored runs

Stryd stores completed activities internally, but offline-history synchronization uses a separate proprietary protocol that is not implemented here. This integration currently supports passive advertisements, standard live BLE measurements, and Device Information characteristics only.

## Troubleshooting

### The pod is not discovered

- Wake it by moving or shaking it.
- Confirm that Home Assistant receives manufacturer ID `0xAAAA` and service `0x1814`.
- Ensure at least one Bluetooth adapter or proxy is in range.
- Use manual MAC-address setup when discovery is unavailable.

### Live entities stay unavailable

- Press **Connect live data**.
- Ensure the adapter/proxy is connectable.
- Disconnect the pod from a phone app or watch temporarily.
- Wake the pod and retry.

### Names do not update

The integration needs one successful metadata connection to read the model number. Wake the pod and keep it near a connectable adapter. Existing manually customized entity names are preserved by Home Assistant.

### Debug logging

Add this to `configuration.yaml`, restart Home Assistant, and reproduce the problem:

```yaml
logger:
  logs:
    custom_components.strydx_ble: debug
```

Attach the relevant log section when reporting an issue. Remove or redact Bluetooth addresses if desired.

## Privacy

All communication is local over Bluetooth. No cloud account or external service is required by this integration.

## Contributing

Bug reports, protocol observations, translations, and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Released under the [MIT License](LICENSE).

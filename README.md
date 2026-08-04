# Stryd BLE for Home Assistant

[![HACS validation](https://github.com/Chreece/ha-stryd-ble/actions/workflows/validate.yml/badge.svg)](https://github.com/Chreece/ha-stryd-ble/actions/workflows/validate.yml)
[![GitHub release](https://img.shields.io/github/v/release/Chreece/ha-stryd-ble)](https://github.com/Chreece/ha-stryd-ble/releases)
[![License](https://img.shields.io/github/license/Chreece/ha-stryd-ble)](LICENSE)

A fully local Home Assistant custom integration for **Stryd running pods**.

Unlike integrations that keep a permanent Bluetooth connection open, **Stryd BLE** is designed around passive Bluetooth advertisements. Battery and diagnostic information are always available without reserving the pod's BLE connection, allowing it to remain available for your sports watch, bike computer or the official Stryd app.

Whenever you want live running metrics, simply press **Connect live data**. Once finished, press **Disconnect live data** and the pod is immediately released again.

> [!IMPORTANT]
> This is an unofficial community integration and is **not affiliated with, endorsed by, or supported by Stryd**.

---

## Compatibility

- Home Assistant 2026.7 or newer
- Home Assistant Bluetooth integration
- Local Bluetooth adapters
- ESPHome and Home Assistant **connectable Bluetooth proxies**

---

## Features

- Automatic Bluetooth discovery
- Manual Bluetooth MAC address setup
- Identification using **Manufacturer ID `0xAAAA`** and the standard **Running Speed & Cadence** BLE service (`0x1814`)
- Works without relying on the advertised device name (`StrydX`)
- Passive battery and diagnostic monitoring
- Optional live BLE connection
- Manual **Connect live data** / **Disconnect live data** buttons
- Automatic one-shot metadata retrieval
- Automatic product generation detection
- Multiple Stryd pods supported
- HACS compatible
- Fully local operation
- No cloud
- No Stryd account required

---

## Translations

The integration currently includes native translations for:

- 🇬🇧 English
- 🇬🇷 Greek
- 🇩🇪 German
- 🇫🇷 French
- 🇪🇸 Spanish
- 🇮🇹 Italian
- 🇳🇱 Dutch
- 🇵🇱 Polish
- 🇵🇹 Portuguese

Additional translations and improvements are always welcome.

---

## Entities

### Passive Bluetooth entities (always available)

| Entity | Description |
|---|---|
| Battery | Battery percentage broadcast by the pod |
| Bluetooth signal strength | RSSI of the latest advertisement |
| Last advertisement | Timestamp of the latest advertisement |
| Advertisement count | Diagnostic advertisement counter *(disabled by default)* |

Passive entities continue updating without establishing a BLE connection.

---

### Live running entities

Available after pressing **Connect live data**:

| Entity | Description |
|---|---|
| Live power | Running power (W) |
| Live speed | Instantaneous speed |
| Live pace | Calculated pace (min/km) |
| Live cadence | Running cadence |
| Live stride length | Stride length |
| Live distance | Distance during the active session |
| Live movement state | Still / Walking / Running |
| Last live measurement | Timestamp *(disabled by default to reduce Recorder writes)* |

After pressing **Disconnect live data**, all live entities become unavailable while passive monitoring continues uninterrupted.

---

### Device information

The integration automatically retrieves and stores:

- Product generation
- Model number
- Firmware version
- Software version
- Hardware revision
- Serial number
- ANT ID
- Live connection state

If device information has never been read before, the next advertisement automatically triggers a short metadata connection. The integration reads the information, stores it, updates the device name, disconnects again and returns to passive mode.

---

## Product naming

Initially, newly discovered devices appear as **Stryd running pod**.

After the model number has been read, the device is automatically renamed to the appropriate generation, for example:

- Stryd
- Stryd Wind
- Next Gen Stryd
- Stryd 5.0

Unknown or future models remain fully supported and receive a generic Stryd name.

---

## Installation

### HACS

1. Open **HACS**.
2. Select **Custom repositories**.
3. Add:

```
https://github.com/Chreece/HA-Stryd-BLE
```

Category:

```
Integration
```

4. Install **Stryd BLE**.
5. Restart Home Assistant.
6. Add the integration via **Settings → Devices & Services**.

### Manual

1. Download the latest release.
2. Copy:

```
custom_components/strydx_ble
```

to:

```
/config/custom_components/
```

3. Restart Home Assistant.
4. Add **Stryd BLE** from **Settings → Devices & Services**.

---

## Discovery

Move or shake the pod so it starts advertising.

Discovery requires:

- Manufacturer ID `0xAAAA`
- Running Speed & Cadence service (`0x1814`)

The advertised Bluetooth name is intentionally **not** used for identification, ensuring compatibility across current and future Stryd generations.

---

## Live connection behaviour

The integration always starts in **passive mode** after a Home Assistant restart.

This design intentionally avoids permanently reserving the pod's BLE connection.

- Press **Connect live data** whenever live metrics are required.
- Press **Disconnect live data** to immediately release the pod.
- Passive battery and diagnostic data continue updating while disconnected.

> [!NOTE]
> This behaviour allows the same Stryd pod to remain available for sports watches, cycling computers and the official Stryd mobile app.

---

## Bluetooth proxies

Passive monitoring works with passive Bluetooth adapters and proxies.

Live running data and metadata retrieval require a **connectable** Bluetooth adapter or ESPHome Bluetooth proxy.

For best results:

- Keep the pod close to the Bluetooth adapter.
- Wake the pod immediately before connecting.
- Close the Stryd app while testing if another device already holds the BLE connection.

---

## Stored runs

Stryd stores completed activities internally, but synchronization uses a proprietary protocol that has not yet been reverse engineered.

This integration currently supports:

- Passive Bluetooth advertisements
- Standard Bluetooth live running metrics
- Bluetooth Device Information characteristics

---

## Troubleshooting

### The pod isn't discovered

- Wake it by moving or shaking it.
- Verify Manufacturer ID `0xAAAA`.
- Verify Running Speed & Cadence service `0x1814`.
- Ensure a Bluetooth adapter or proxy is nearby.
- Use manual MAC address setup if necessary.

### Live entities remain unavailable

- Press **Connect live data**.
- Ensure your Bluetooth adapter or proxy is connectable.
- Disconnect the pod from any watch or phone.
- Wake the pod and try again.

### Product name doesn't update

One successful metadata connection is required to retrieve the model number.

Move the pod close to a connectable Bluetooth adapter and wake it once.

---

## Debug logging

```yaml
logger:
  logs:
    custom_components.strydx_ble: debug
```

Please include the relevant log output when reporting issues.

---

## Privacy

All communication is performed locally over Bluetooth.

No cloud services, internet access or Stryd account are required.

---

## Contributing

Bug reports, feature requests, protocol discoveries, translations and pull requests are always welcome.

See **CONTRIBUTING.md** for more information.

---

## License

Released under the **MIT License**.

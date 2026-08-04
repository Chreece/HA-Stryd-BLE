# Changelog

All notable changes to this project are documented here.

## [3.5.0] - 2026-08-04

- Identify Stryd pods using manufacturer ID `0xAAAA` and RSC service `0x1814`.
- Remove dependency on the advertised local name `StrydX`.
- Show `Stryd running pod` during discovery until product metadata is read.

## [3.4.0] - 2026-08-04

- Give entities explicit descriptive names.
- Report movement as `Still` when live speed is zero.
- Make live entities unavailable while disconnected.
- Add one-shot metadata retrieval and persistence.

## [3.3.0] - 2026-08-04

- Add manual Connect and Disconnect buttons.
- Default to passive-only operation so watches and phones can use the connection.

## [3.2.0] - 2026-08-04

- Add product-generation naming based on model number.
- Clarify live entity names.

## [3.1.0] - 2026-08-04

- Add model, firmware, software, and ANT ID diagnostics.
- Disable the frequently updating last-live-measurement timestamp by default.
- Improve entity names, translations, and icons.

## [3.0.1] - 2026-08-04

- Run GATT work as Home Assistant background tasks to avoid delaying startup.
- Add local integration branding assets.

## [3.0.0] - 2026-08-04

- Add active GATT support for standard running measurements and Device Information.

## [1.0.0] - 2026-08-04

- Initial passive Stryd battery integration.

## 3.6.0

- Generate useful entity IDs from the detected Stryd model, for example `sensor.next_gen_stryd_live_power`.
- Migrate existing `strydx_*` entity IDs while preserving their unique IDs.
- Keep entity IDs descriptive for live data, diagnostics, and connection buttons.
- Add bundled translations for English, German, Greek, French, Spanish, Italian, Dutch, Portuguese, and Polish.

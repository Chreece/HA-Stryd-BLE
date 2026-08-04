# Contributing

Thanks for helping improve Stryd BLE.

## Reporting bugs

Use the bug-report issue form and include:

- Home Assistant version and installation type
- Integration version
- Bluetooth adapter or proxy type
- Relevant debug logs
- Whether the pod was connected to a watch or phone
- A sanitized advertisement when the issue concerns discovery or decoding

Do not publish account credentials, tokens, or information you consider private.

## Development setup

1. Fork and clone the repository.
2. Copy or symlink `custom_components/stryd_ble` into a Home Assistant development configuration.
3. Restart Home Assistant after backend-code changes.
4. Enable debug logging for `custom_components.stryd_ble`.
5. Run the repository validation workflows before opening a pull request.

## Code guidelines

- Keep Home Assistant startup non-blocking.
- Do not hold an active BLE connection unless the user requests live data or metadata is missing.
- Preserve passive battery and advertisement functionality independently of GATT.
- Treat undocumented bytes and characteristics as unknown until supported by repeatable observations.
- Add or update English source strings and all maintained translations when introducing entities or config-flow text.
- Avoid changing existing unique IDs, because doing so creates duplicate entities for existing users.

## Pull requests

Keep each pull request focused. Explain the problem, the behavioral change, and how it was tested. Include logs or captured BLE payloads where they are needed to verify protocol changes.

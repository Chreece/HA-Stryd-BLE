"""Config flow for Stryd BLE."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_NAME, DOMAIN, MANUFACTURER_ID, RSC_SERVICE_UUID

_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


@dataclass(slots=True)
class DiscoveredStryd:
    """A Stryd device found by Home Assistant Bluetooth."""

    title: str
    info: BluetoothServiceInfoBleak


def _local_name(info: BluetoothServiceInfoBleak) -> str | None:
    """Return the advertised local name across Home Assistant Bluetooth API versions."""
    # Older HA/habluetooth releases exposed ``local_name`` directly. Newer
    # releases expose it through the advertisement object instead. ``getattr``
    # keeps the custom integration compatible with both representations.
    direct_name = getattr(info, "local_name", None)
    if direct_name:
        return direct_name

    advertisement = getattr(info, "advertisement", None)
    return getattr(advertisement, "local_name", None) if advertisement else None


def _display_name(info: BluetoothServiceInfoBleak) -> str:
    """Return a useful generic name until the pod model is read over GATT."""
    return DEFAULT_NAME


def _normalize_uuid(uuid: str) -> str:
    """Normalize 16-bit and full Bluetooth UUIDs for reliable matching."""
    value = uuid.strip().lower()
    if len(value) == 4:
        return f"0000{value}-0000-1000-8000-00805f9b34fb"
    return value


def _is_stryd(info: BluetoothServiceInfoBleak) -> bool:
    """Identify a Stryd pod without relying on its advertised local name."""
    service_uuids = {
        _normalize_uuid(uuid) for uuid in (getattr(info, "service_uuids", None) or [])
    }
    return (
        MANUFACTURER_ID in (getattr(info, "manufacturer_data", None) or {})
        and RSC_SERVICE_UUID in service_uuids
    )


def _normalize_address(address: str) -> str:
    return address.strip().upper().replace("-", ":")


class StrydXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stryd BLE."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, DiscoveredStryd] = {}
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Offer automatic scan or manual address entry."""
        return self.async_show_menu(step_id="user", menu_options=["scan", "manual"])

    async def async_step_scan(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Select a currently visible Stryd device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery = self._discovered[address]
            return await self._async_create_for_device(discovery.info)

        configured = self._async_current_ids(include_ignore=False)
        for info in async_discovered_service_info(self.hass, connectable=False):
            address = _normalize_address(info.address)
            if address in configured or address in self._discovered or not _is_stryd(info):
                continue
            display_name = _display_name(info)
            self._discovered[address] = DiscoveredStryd(
                title=f"{display_name} ({address})", info=info
            )

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        choices = {address: item.title for address, item in self._discovered.items()}
        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(choices)}),
        )

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Set up a Stryd pod by Bluetooth MAC address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = _normalize_address(user_input[CONF_ADDRESS])
            if not _MAC_RE.fullmatch(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                name = user_input.get(CONF_NAME, DEFAULT_NAME).strip() or DEFAULT_NAME
                return self.async_create_entry(
                    title=f"{name} ({address[-5:]})",
                    data={CONF_ADDRESS: address, CONF_NAME: name},
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> FlowResult:
        """Handle automatic Home Assistant Bluetooth discovery."""
        if not _is_stryd(discovery_info):
            return self.async_abort(reason="not_supported")

        address = _normalize_address(discovery_info.address)
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        display_name = _display_name(discovery_info)
        self.context["title_placeholders"] = {"name": display_name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm a Bluetooth-discovered Stryd pod."""
        assert self._discovery_info is not None
        if user_input is not None:
            return await self._async_create_for_device(self._discovery_info)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def _async_create_for_device(self, info: BluetoothServiceInfoBleak) -> FlowResult:
        address = _normalize_address(info.address)
        await self.async_set_unique_id(address, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        name = _display_name(info)
        return self.async_create_entry(
            title=f"{name} ({address[-5:]})",
            data={CONF_ADDRESS: address, CONF_NAME: name},
        )

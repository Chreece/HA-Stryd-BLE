"""Buttons for manually controlling the Stryd GATT connection."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import callback

from . import StrydXConfigEntry
from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, GENERIC_NAMES
from .coordinator import StrydXCoordinator
from .naming import suggested_object_id


@dataclass(frozen=True, kw_only=True)
class StrydButtonDescription(ButtonEntityDescription):
    """Describe a Stryd connection button."""

    press_fn: Callable[[StrydXCoordinator], Awaitable[None]]


BUTTONS: tuple[StrydButtonDescription, ...] = (
    StrydButtonDescription(
        key="connect",
        translation_key="connect",
        icon="mdi:bluetooth-connect",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_request_connect(),
    ),
    StrydButtonDescription(
        key="disconnect",
        translation_key="disconnect",
        icon="mdi:bluetooth-off",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_request_disconnect(),
    ),
)


async def async_setup_entry(
    hass, entry: StrydXConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Stryd connection buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        StrydConnectionButton(coordinator, entry, description)
        for description in BUTTONS
    )


class StrydConnectionButton(ButtonEntity):
    """Button used to connect or disconnect active GATT data."""

    _attr_has_entity_name = True
    entity_description: StrydButtonDescription

    def __init__(self, coordinator, entry, description):
        self.coordinator = coordinator
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_{description.key}"
        self._attr_suggested_object_id = suggested_object_id(
            coordinator.data.product_name, description.key
        )

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        configured_name = self._entry.data.get(CONF_NAME)
        device_name = (
            data.product_name
            if not configured_name or configured_name in GENERIC_NAMES
            else configured_name
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data[CONF_ADDRESS])},
            connections={(CONNECTION_BLUETOOTH, self._entry.data[CONF_ADDRESS])},
            name=device_name,
            manufacturer=data.manufacturer or "Stryd",
            model=(
                f"{data.product_name} (model {data.model})"
                if data.model
                else data.product_name
            ),
            sw_version=data.firmware,
            hw_version=data.hardware,
            serial_number=data.serial_number,
        )

    @property
    def available(self) -> bool:
        """Avoid meaningless duplicate presses where possible."""
        if self.entity_description.key == "connect":
            return not self.coordinator.data.connected
        return self.coordinator.data.connected or self.coordinator.connection_requested

    async def async_added_to_hass(self) -> None:
        """Refresh button availability when connection state changes."""
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator)

"""Sensor entities for StrydX BLE."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import StrydXConfigEntry
from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, GENERIC_NAMES
from .coordinator import StrydXCoordinator, StrydXData
from .naming import suggested_object_id


@dataclass(frozen=True, kw_only=True)
class StrydXSensorDescription(SensorEntityDescription):
    """Describe a StrydX sensor."""

    value_fn: Callable[[StrydXData], Any]
    live: bool = False


SENSORS: tuple[StrydXSensorDescription, ...] = (
    StrydXSensorDescription(
        key="battery",
        name="Battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
        value_fn=lambda data: data.battery,
    ),
    StrydXSensorDescription(
        key="power",
        name="Live power",
        translation_key="power",
        live=True,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:lightning-bolt",
        value_fn=lambda data: data.power,
    ),
    StrydXSensorDescription(
        key="speed",
        name="Live speed",
        translation_key="speed",
        live=True,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        suggested_display_precision=2,
        icon="mdi:speedometer",
        value_fn=lambda data: data.speed,
    ),
    StrydXSensorDescription(
        key="pace",
        name="Live pace",
        translation_key="pace",
        live=True,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="min/km",
        suggested_display_precision=2,
        icon="mdi:run-fast",
        value_fn=lambda data: data.pace,
    ),
    StrydXSensorDescription(
        key="cadence",
        name="Live cadence",
        translation_key="cadence",
        live=True,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="steps/min",
        icon="mdi:shoe-print",
        value_fn=lambda data: data.cadence,
    ),
    StrydXSensorDescription(
        key="stride_length",
        name="Live stride length",
        translation_key="stride_length",
        live=True,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_display_precision=2,
        icon="mdi:ruler",
        value_fn=lambda data: data.stride_length,
    ),
    StrydXSensorDescription(
        key="total_distance",
        name="Live distance",
        translation_key="total_distance",
        live=True,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_display_precision=1,
        icon="mdi:map-marker-distance",
        value_fn=lambda data: data.total_distance,
    ),
    StrydXSensorDescription(
        key="motion_state",
        name="Live movement state",
        translation_key="motion_state",
        live=True,
        device_class=SensorDeviceClass.ENUM,
        options=["still", "walking", "running", "unknown"],
        icon="mdi:run",
        value_fn=lambda data: (
            "unknown"
            if data.speed is None
            else "still"
            if data.speed == 0
            else "running"
            if data.running
            else "walking"
        ),
    ),
    StrydXSensorDescription(
        key="connection",
        name="Live data connection",
        translation_key="connection",
        device_class=SensorDeviceClass.ENUM,
        options=["connected", "disconnected"],
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bluetooth-connect",
        value_fn=lambda data: "connected" if data.connected else "disconnected",
    ),
    StrydXSensorDescription(
        key="last_measurement",
        name="Last live measurement",
        translation_key="last_measurement",
        live=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:clock-outline",
        value_fn=lambda data: data.last_measurement,
    ),
    StrydXSensorDescription(
        key="signal_strength",
        name="Bluetooth signal strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bluetooth-audio",
        value_fn=lambda data: data.rssi,
    ),
    StrydXSensorDescription(
        key="last_seen",
        name="Last advertisement",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-check-outline",
        value_fn=lambda data: data.last_seen,
    ),
    StrydXSensorDescription(
        key="firmware",
        name="Firmware version",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.firmware,
    ),
    StrydXSensorDescription(
        key="model_number",
        name="Model number",
        translation_key="model_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
        value_fn=lambda data: data.model,
    ),
    StrydXSensorDescription(
        key="product_generation",
        name="Product generation",
        translation_key="product_generation",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shoe-sneaker",
        value_fn=lambda data: data.product_generation,
    ),
    StrydXSensorDescription(
        key="software_version",
        name="Software version",
        translation_key="software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:package-variant-closed",
        value_fn=lambda data: data.software,
    ),
    StrydXSensorDescription(
        key="ant_id",
        name="ANT ID",
        translation_key="ant_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:antenna",
        value_fn=lambda data: data.ant_id,
    ),
    StrydXSensorDescription(
        key="hardware",
        name="Hardware revision",
        translation_key="hardware",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.hardware,
    ),
    StrydXSensorDescription(
        key="serial_number",
        name="Serial number",
        translation_key="serial_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.serial_number,
    ),
    StrydXSensorDescription(
        key="advertisement_count",
        name="Advertisement count",
        translation_key="advertisement_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.advertisement_count,
    ),
)


async def async_setup_entry(
    hass, entry: StrydXConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up StrydX sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        StrydXSensor(coordinator, entry, description) for description in SENSORS
    )


class StrydXSensor(SensorEntity):
    """Representation of one StrydX sensor."""

    _attr_has_entity_name = True
    entity_description: StrydXSensorDescription

    def __init__(
        self,
        coordinator: StrydXCoordinator,
        entry: StrydXConfigEntry,
        description: StrydXSensorDescription,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}_{description.key}"
        self._attr_suggested_object_id = suggested_object_id(
            coordinator.data.product_name, description.key
        )
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information, enriched from GATT when available."""
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
        """Live metrics are available only while the pod has an active GATT connection."""
        if self.entity_description.live:
            return self.coordinator.data.connected
        return True

    @property
    def native_value(self) -> int | float | str | datetime | None:
        """Return the latest sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Expose raw advertisement and GATT identity data on battery."""
        if self.entity_description.key != "battery":
            return None
        data = self.coordinator.data
        attributes: dict[str, str] = {}
        if data.manufacturer_data_hex:
            attributes["manufacturer_data"] = data.manufacturer_data_hex
        if data.manufacturer:
            attributes["gatt_manufacturer"] = data.manufacturer
        if data.model:
            attributes["gatt_model"] = data.model
        return attributes or None

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

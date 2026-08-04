"""Entity naming and entity-registry migration helpers for Stryd BLE."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

# Human-readable, stable object-ID suffixes. Unique IDs remain unchanged.
ENTITY_OBJECT_ID_SUFFIXES: dict[str, str] = {
    "battery": "battery",
    "power": "live_power",
    "speed": "live_speed",
    "pace": "live_pace",
    "cadence": "live_cadence",
    "stride_length": "live_stride_length",
    "total_distance": "live_distance",
    "motion_state": "live_movement_state",
    "connection": "live_data_connection",
    "last_measurement": "last_live_measurement",
    "signal_strength": "bluetooth_signal_strength",
    "last_seen": "last_advertisement",
    "advertisement_count": "advertisement_count",
    "firmware": "firmware_version",
    "model_number": "model_number",
    "software_version": "software_version",
    "ant_id": "ant_id",
    "hardware": "hardware_revision",
    "serial_number": "serial_number",
    "product_generation": "product_generation",
    "connect": "connect_live_data",
    "disconnect": "disconnect_live_data",
}


def suggested_object_id(product_name: str, entity_key: str) -> str:
    """Return an entity object ID based on product model and entity purpose."""
    product_slug = slugify(product_name or "Stryd")
    suffix = ENTITY_OBJECT_ID_SUFFIXES.get(entity_key, slugify(entity_key))
    return f"{product_slug}_{suffix}"


async def async_migrate_entity_ids(
    hass: HomeAssistant, entry: ConfigEntry, product_name: str
) -> None:
    """Rename registered entities to model-based, useful entity IDs.

    Unique IDs are deliberately preserved, so no duplicate entities are created.
    Existing YAML references cannot be rewritten automatically by Home Assistant.
    """
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)

    for entity_entry in entries:
        unique_id = entity_entry.unique_id
        key = unique_id.rsplit("_", 1)[-1]

        # Keys containing underscores cannot be recovered with a simple split.
        # Match the longest known key against the unique-ID suffix instead.
        matching_keys = [
            candidate
            for candidate in ENTITY_OBJECT_ID_SUFFIXES
            if unique_id.endswith(f"_{candidate}")
        ]
        if matching_keys:
            key = max(matching_keys, key=len)

        if key not in ENTITY_OBJECT_ID_SUFFIXES:
            continue

        domain = entity_entry.entity_id.split(".", 1)[0]
        target_entity_id = f"{domain}.{suggested_object_id(product_name, key)}"
        if target_entity_id == entity_entry.entity_id:
            continue

        existing = registry.async_get(target_entity_id)
        if existing is not None and existing.id != entity_entry.id:
            _LOGGER.warning(
                "Could not rename %s to %s because the target entity ID already exists",
                entity_entry.entity_id,
                target_entity_id,
            )
            continue

        try:
            registry.async_update_entity(
                entity_entry.entity_id, new_entity_id=target_entity_id
            )
            _LOGGER.info(
                "Renamed Stryd entity %s to %s",
                entity_entry.entity_id,
                target_entity_id,
            )
        except ValueError:
            _LOGGER.exception(
                "Failed to rename Stryd entity %s to %s",
                entity_entry.entity_id,
                target_entity_id,
            )

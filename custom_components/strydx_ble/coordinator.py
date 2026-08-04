"""Bluetooth advertisement and GATT handling for Stryd BLE."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import struct
from time import monotonic

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import BleakError, establish_connection

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .naming import async_migrate_entity_ids

from .const import (
    CONF_ADDRESS,
    CONNECT_RETRY_COOLDOWN,
    CYCLING_POWER_MEASUREMENT_UUID,
    FIRMWARE_REVISION_UUID,
    HARDWARE_REVISION_UUID,
    MANUFACTURER_ID,
    MANUFACTURER_NAME_UUID,
    MODEL_NUMBER_UUID,
    RSC_MEASUREMENT_UUID,
    SERIAL_NUMBER_UUID,
    SOFTWARE_REVISION_UUID,
)

_LOGGER = logging.getLogger(__name__)

_METADATA_KEYS = (
    "manufacturer",
    "model",
    "firmware",
    "software",
    "hardware",
    "serial_number",
)


@dataclass(slots=True)
class StrydXData:
    """Latest data received from Stryd."""

    battery: int | None = None
    rssi: int | None = None
    last_seen: datetime | None = None
    advertisement_count: int = 0
    manufacturer_data_hex: str | None = None

    connected: bool = False
    speed: float | None = None
    pace: float | None = None
    cadence: int | None = None
    stride_length: float | None = None
    total_distance: float | None = None
    running: bool | None = None
    power: int | None = None
    cycling_cadence: float | None = None
    last_measurement: datetime | None = None

    manufacturer: str | None = None
    model: str | None = None
    firmware: str | None = None
    software: str | None = None
    hardware: str | None = None
    serial_number: str | None = None
    ant_id: int | None = None
    product_name: str = "Stryd"
    product_generation: str | None = None


def product_from_model(model: str | None) -> tuple[str, str | None]:
    """Return the official product generation inferred from a numeric model number."""
    if not model:
        return "Stryd", None
    try:
        number = int(model.strip())
    except (TypeError, ValueError):
        return "Stryd", None

    if number == 1:
        return "Stryd", "Chest-mounted Stryd (2015)"
    if 2 <= number <= 13:
        return "Stryd", "Stryd non-wind model (2016)"
    if 14 <= number <= 25:
        return "Stryd Wind", "Stryd wind model (2019)"
    if 26 <= number <= 27:
        return "Next Gen Stryd", "Next Gen Stryd (2022)"
    if number >= 30:
        return "Stryd 5.0", "Stryd 5.0 (2025)"
    return f"Stryd model {number}", f"Stryd model {number}"


class StrydXCoordinator:
    """Receive passive advertisements and optionally subscribe to live GATT data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.data = StrydXData(ant_id=int(self.address.replace(":", "")[-4:], 16))
        for key in _METADATA_KEYS:
            setattr(self.data, key, entry.data.get(key))
        self.data.product_name, self.data.product_generation = product_from_model(
            self.data.model
        )

        self._listeners: set[Callable[[], None]] = set()
        self._cancel_callback: Callable[[], None] | None = None
        self._connect_task: asyncio.Task[None] | None = None
        self._client: BleakClient | None = None
        self._stopping = False
        self._connection_requested = False
        self._last_connect_attempt = 0.0
        self._last_metadata_attempt = 0.0
        self._last_crank_revolutions: int | None = None
        self._last_crank_event_time: int | None = None

    @property
    def metadata_complete(self) -> bool:
        """Return whether enough identity data has been read to name the pod."""
        return bool(self.data.model and self.data.firmware and self.data.software)

    @callback
    def async_start(self) -> None:
        """Start passive advertisement listening."""
        self._cancel_callback = async_register_callback(
            self.hass,
            self._async_on_advertisement,
            BluetoothCallbackMatcher(address=self.address),
            BluetoothScanningMode.PASSIVE,
        )

    async def async_stop(self) -> None:
        """Stop callbacks and disconnect cleanly."""
        self._stopping = True
        if self._cancel_callback is not None:
            self._cancel_callback()
            self._cancel_callback = None
        if self._connect_task is not None:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
            self._connect_task = None
        await self._async_disconnect_client(clear_live=True)

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    @callback
    def _async_on_advertisement(
        self, service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        """Handle a matching passive advertisement."""
        manufacturer_data = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if manufacturer_data and len(manufacturer_data) >= 2:
            candidate = manufacturer_data[1]
            if 0 <= candidate <= 100:
                self.data.battery = candidate

        self.data.rssi = service_info.rssi
        self.data.last_seen = dt_util.utcnow()
        self.data.advertisement_count += 1
        if manufacturer_data:
            self.data.manufacturer_data_hex = manufacturer_data.hex()
        self._notify_listeners()

        if self._stopping or self.data.connected:
            return
        if self._connect_task is not None and not self._connect_task.done():
            return

        now = monotonic()
        if self._connection_requested:
            if now - self._last_connect_attempt < CONNECT_RETRY_COOLDOWN:
                return
            self._last_connect_attempt = now
            self._connect_task = self.hass.async_create_background_task(
                self._async_connect(metadata_only=False), "Stryd live-data connection"
            )
            return

        # If identity data has never been obtained, briefly connect once when the pod
        # advertises, read Device Information, persist it, and immediately disconnect.
        if not self.metadata_complete and now - self._last_metadata_attempt >= CONNECT_RETRY_COOLDOWN:
            self._last_metadata_attempt = now
            self._connect_task = self.hass.async_create_background_task(
                self._async_connect(metadata_only=True), "Stryd identity read"
            )

    @property
    def connection_requested(self) -> bool:
        return self._connection_requested

    async def async_request_connect(self) -> None:
        """Request an active live-data connection."""
        if self._stopping:
            return
        self._connection_requested = True
        if self.data.connected or (
            self._connect_task is not None and not self._connect_task.done()
        ):
            self._notify_listeners()
            return
        self._last_connect_attempt = monotonic()
        self._connect_task = self.hass.async_create_background_task(
            self._async_connect(metadata_only=False), "Stryd manual live-data connection"
        )
        self._notify_listeners()

    async def async_request_disconnect(self) -> None:
        """Release GATT while keeping passive advertisement data available."""
        self._connection_requested = False
        task = self._connect_task
        self._connect_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._async_disconnect_client(clear_live=True)
        self._notify_listeners()

    async def _async_connect(self, *, metadata_only: bool) -> None:
        """Connect for identity only or keep a live measurement subscription."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            _LOGGER.debug("No connectable Bluetooth path currently reaches %s", self.address)
            return

        client: BleakClient | None = None
        try:
            client = await establish_connection(
                BleakClient,
                device=ble_device,
                name=f"Stryd {self.address}",
                disconnected_callback=self._disconnected_callback,
                max_attempts=1 if metadata_only else 2,
            )
            self._client = client

            await self._async_read_device_information(client)
            if metadata_only or not self._connection_requested or self._stopping:
                await client.disconnect()
                return

            self.data.connected = True
            self._notify_listeners()

            subscribed = 0
            for characteristic, callback_fn in (
                (RSC_MEASUREMENT_UUID, self._rsc_notification),
                (CYCLING_POWER_MEASUREMENT_UUID, self._power_notification),
            ):
                try:
                    if client.services.get_characteristic(characteristic) is not None:
                        await client.start_notify(characteristic, callback_fn)
                        subscribed += 1
                except (BleakError, AttributeError) as err:
                    _LOGGER.debug("Could not subscribe to %s: %s", characteristic, err)

            if not subscribed:
                _LOGGER.warning("No standard live measurement characteristic found on %s", self.address)
                await client.disconnect()
                return

            while client.is_connected and not self._stopping and self._connection_requested:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except (BleakError, TimeoutError, EOFError) as err:
            _LOGGER.debug("Unable to connect to Stryd %s: %s", self.address, err)
        except Exception:
            _LOGGER.exception("Unexpected error while communicating with Stryd %s", self.address)
        finally:
            current_task = asyncio.current_task()
            if self._connect_task is current_task:
                self._connect_task = None
            if metadata_only and client is not None and client.is_connected:
                try:
                    await client.disconnect()
                except BleakError:
                    pass

    async def _async_disconnect_client(self, *, clear_live: bool) -> None:
        client = self._client
        self._client = None
        if client is not None and client.is_connected:
            try:
                await client.disconnect()
            except BleakError:
                pass
        self.data.connected = False
        self._last_crank_revolutions = None
        self._last_crank_event_time = None
        if clear_live:
            self._clear_live_data()

    @callback
    def _clear_live_data(self) -> None:
        self.data.speed = None
        self.data.pace = None
        self.data.cadence = None
        self.data.stride_length = None
        self.data.total_distance = None
        self.data.running = None
        self.data.power = None
        self.data.cycling_cadence = None
        self.data.last_measurement = None

    def _disconnected_callback(self, client: BleakClient) -> None:
        self.hass.loop.call_soon_threadsafe(self._async_disconnected, client)

    @callback
    def _async_disconnected(self, client: BleakClient) -> None:
        if self._client is client:
            self._client = None
        was_live = self.data.connected
        self.data.connected = False
        self._last_crank_revolutions = None
        self._last_crank_event_time = None
        if was_live:
            self._clear_live_data()
        self._notify_listeners()
        if self._connection_requested:
            bluetooth.async_clear_advertisement_history(self.hass, self.address)

    @callback
    def _rsc_notification(
        self, characteristic: BleakGATTCharacteristic, payload: bytearray
    ) -> None:
        data = bytes(payload)
        if len(data) < 4:
            return
        flags = data[0]
        speed_raw = int.from_bytes(data[1:3], "little")
        cadence = data[3]
        offset = 4

        self.data.speed = round(speed_raw / 256.0, 3)
        self.data.pace = (
            round(1000.0 / (self.data.speed * 60.0), 2) if self.data.speed > 0 else None
        )
        self.data.cadence = cadence
        self.data.running = bool(flags & 0x04)

        if flags & 0x01 and len(data) >= offset + 2:
            self.data.stride_length = round(
                int.from_bytes(data[offset : offset + 2], "little") / 100.0, 2
            )
            offset += 2
        if flags & 0x02 and len(data) >= offset + 4:
            self.data.total_distance = round(
                int.from_bytes(data[offset : offset + 4], "little") / 10.0, 1
            )

        self.data.last_measurement = dt_util.utcnow()
        self._notify_listeners()

    @callback
    def _power_notification(
        self, characteristic: BleakGATTCharacteristic, payload: bytearray
    ) -> None:
        data = bytes(payload)
        if len(data) < 4:
            return
        flags = int.from_bytes(data[0:2], "little")
        self.data.power = struct.unpack_from("<h", data, 2)[0]
        offset = 4
        if flags & (1 << 0):
            offset += 1
        if flags & (1 << 2):
            offset += 2
        if flags & (1 << 4):
            offset += 6
        if flags & (1 << 5) and len(data) >= offset + 4:
            self._update_crank_cadence(
                int.from_bytes(data[offset : offset + 2], "little"),
                int.from_bytes(data[offset + 2 : offset + 4], "little"),
            )
        self.data.last_measurement = dt_util.utcnow()
        self._notify_listeners()

    def _update_crank_cadence(self, revolutions: int, event_time: int) -> None:
        if self._last_crank_revolutions is not None and self._last_crank_event_time is not None:
            rev_delta = (revolutions - self._last_crank_revolutions) & 0xFFFF
            time_delta = (event_time - self._last_crank_event_time) & 0xFFFF
            if rev_delta and time_delta:
                rpm = rev_delta * 60.0 * 1024.0 / time_delta
                if 0 < rpm < 300:
                    self.data.cycling_cadence = round(rpm, 1)
        self._last_crank_revolutions = revolutions
        self._last_crank_event_time = event_time

    @callback
    def _async_update_product_identity(self) -> None:
        product_name, generation = product_from_model(self.data.model)
        self.data.product_name = product_name
        self.data.product_generation = generation

        updates = {key: getattr(self.data, key) for key in _METADATA_KEYS if getattr(self.data, key)}
        new_data = {**self.entry.data, **updates}
        self.hass.config_entries.async_update_entry(
            self.entry,
            title=product_name,
            data=new_data,
        )

        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={("strydx_ble", self.address)})
        if device is not None:
            registry.async_update_device(
                device.id,
                name=product_name,
                manufacturer=self.data.manufacturer or "Stryd",
                model=f"{product_name} (model {self.data.model})" if self.data.model else product_name,
                sw_version=self.data.firmware,
                hw_version=self.data.hardware,
                serial_number=self.data.serial_number,
            )

        self.hass.async_create_background_task(
            async_migrate_entity_ids(self.hass, self.entry, product_name),
            "Migrate Stryd entity IDs",
        )

    async def _async_read_device_information(self, client: BleakClient) -> None:
        fields = (
            (MANUFACTURER_NAME_UUID, "manufacturer"),
            (MODEL_NUMBER_UUID, "model"),
            (FIRMWARE_REVISION_UUID, "firmware"),
            (SOFTWARE_REVISION_UUID, "software"),
            (HARDWARE_REVISION_UUID, "hardware"),
            (SERIAL_NUMBER_UUID, "serial_number"),
        )
        for uuid, field in fields:
            try:
                if client.services.get_characteristic(uuid) is None:
                    continue
                raw = await client.read_gatt_char(uuid)
                value = bytes(raw).decode("utf-8", errors="replace").strip("\x00 ")
                if value:
                    setattr(self.data, field, value)
            except (BleakError, UnicodeError):
                _LOGGER.debug("Could not read Device Information characteristic %s", uuid)
        self._async_update_product_identity()
        self._notify_listeners()

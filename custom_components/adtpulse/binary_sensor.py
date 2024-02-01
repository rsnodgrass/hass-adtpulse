"""ADT Pulse HA binary sensor integration.

This adds a sensor for ADT Pulse alarm systems so that all the ADT
motion sensors and switches automatically appear in Home Assistant. This
automatically discovers the ADT sensors configured within Pulse and
exposes them into HA.
"""

from __future__ import annotations

from logging import getLogger
from datetime import datetime
from typing import Any, Mapping

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import as_local
from pyadtpulse.site import ADTPulseSite
from pyadtpulse.zones import ADTPulseZoneData

from .base_entity import ADTPulseEntity
from .const import ADTPULSE_DOMAIN
from .coordinator import ADTPulseDataUpdateCoordinator
from .utils import (
    get_alarm_unique_id,
    get_gateway_unique_id,
    migrate_entity_name,
    zone_is_in_trouble,
    zone_is_open,
)

LOG = getLogger(__name__)

# please keep these alphabetized to make changes easier
ADT_DEVICE_CLASS_TAG_MAP = {
    "co": BinarySensorDeviceClass.CO,
    "doorWindow": BinarySensorDeviceClass.DOOR,
    "flood": BinarySensorDeviceClass.MOISTURE,
    "garage": BinarySensorDeviceClass.GARAGE_DOOR,  # FIXME: need ADT type
    "fire": BinarySensorDeviceClass.HEAT,
    "motion": BinarySensorDeviceClass.MOTION,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "glass": BinarySensorDeviceClass.TAMPER,
}

ADT_SENSOR_ICON_MAP = {
    BinarySensorDeviceClass.CO: ("mdi:molecule-co", "mdi:checkbox-marked-circle"),
    BinarySensorDeviceClass.DOOR: ("mdi:door-open", "mdi:door"),
    BinarySensorDeviceClass.GARAGE_DOOR: (
        "mdi:garage-open-variant",
        "mdi:garage-variant",
    ),
    BinarySensorDeviceClass.HEAT: ("mdi:fire", "mdi:smoke-detector-variant"),
    BinarySensorDeviceClass.MOISTURE: ("mdi:home-flood", "mdi:heat-wave"),
    BinarySensorDeviceClass.MOTION: ("mdi:run-fast", "mdi:motion-sensor"),
    BinarySensorDeviceClass.PROBLEM: ("mdi:alert-circle", "mdi:hand-okay"),
    BinarySensorDeviceClass.SMOKE: ("mdi:fire", "mdi:smoke-detector-variant"),
    BinarySensorDeviceClass.TAMPER: ("mdi:window-open", "mdi:window-closed"),
    BinarySensorDeviceClass.WINDOW: (
        "mdi:window-open-variant",
        "mdi:window-closed-variant",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for an ADT Pulse installation."""
    coordinator: ADTPulseDataUpdateCoordinator = hass.data[ADTPULSE_DOMAIN][
        entry.entry_id
    ]
    site = coordinator.adtpulse.site
    migrate_entity_name(hass, site, "binary_sensor", get_gateway_unique_id(site))
    async_add_entities([ADTPulseGatewaySensor(coordinator, site)])
    if not site.zones_as_dict:
        LOG.error(
            "ADT's Pulse service returned NO zones (sensors) for site %s:", site.id
        )
        return
    entities = [
        ADTPulseZoneSensor(coordinator, site, zone_id, trouble_indicator)
        for zone_id in site.zones_as_dict.keys()
        for trouble_indicator in (True, False)
    ]

    _ = (
        migrate_entity_name(
            hass,
            site,
            "binary_sensor",
            entity.unique_id,
        )
        for entity in entities
    )

    async_add_entities(entities)


class ADTPulseZoneSensor(ADTPulseEntity, BinarySensorEntity):
    """HASS zone binary sensor implementation for ADT Pulse."""

    # zone = {'id': 'sensor-12', 'name': 'South Office Motion',
    # 'tags': ['sensor', 'motion'], 'status': 'Motion', 'activityTs': 1569078085275}

    @staticmethod
    def _get_my_zone(site: ADTPulseSite, zone_id: int) -> ADTPulseZoneData:
        if site.zones_as_dict is None:
            raise RuntimeError("ADT pulse returned null zone")
        return site.zones_as_dict[zone_id]

    @staticmethod
    def _determine_device_class(zone_data: ADTPulseZoneData) -> BinarySensorDeviceClass:
        # map the ADT Pulse device type tag to a binary_sensor class
        # so the proper status codes and icons are displayed. If device class
        # is not specified, binary_sensor defaults to a generic on/off sensor

        tags = zone_data.tags
        device_class: BinarySensorDeviceClass | None = None

        if "sensor" in tags:
            for tag in tags:
                try:
                    device_class = ADT_DEVICE_CLASS_TAG_MAP[tag]
                    break
                except KeyError:
                    continue
        # since ADT Pulse does not separate the concept of a door or window sensor,
        # we try to autodetect window type sensors so the appropriate icon is displayed
        if device_class is None:
            LOG.warning(
                "Ignoring unsupported sensor type from ADT Pulse cloud "
                "service, configured tags: %s",
                tags,
            )
            raise ValueError(f"Unknown ADT Pulse device class {device_class}")
        if device_class == BinarySensorDeviceClass.DOOR:
            if "Window" in zone_data.name or "window" in zone_data.name:
                device_class = BinarySensorDeviceClass.WINDOW
        LOG.info(
            "Determined %s device class %sfrom ADT Pulse service configured tags %s",
            zone_data.name,
            device_class,
            tags,
        )
        return device_class

    def __init__(
        self,
        coordinator: ADTPulseDataUpdateCoordinator,
        site: ADTPulseSite,
        zone_id: int,
        trouble_indicator: bool,
    ):
        """Initialize the binary_sensor."""
        if trouble_indicator:
            LOG.debug(
                "%s: adding zone trouble sensor for site %s", ADTPULSE_DOMAIN, site.id
            )
        else:
            LOG.debug("%s: adding zone sensor for site %s", ADTPULSE_DOMAIN, site.id)
        self._zone_id = zone_id
        self._is_trouble_indicator = trouble_indicator
        self._my_zone = self._get_my_zone(site, zone_id)
        if trouble_indicator:
            self._device_class = BinarySensorDeviceClass.PROBLEM
            self._name = f"Trouble Sensor - {self._my_zone.name}"
        else:
            self._device_class = self._determine_device_class(self._my_zone)
            self._name = f"{self._my_zone.name}"
        super().__init__(coordinator, self._name)
        LOG.debug("Created ADT Pulse '%s' sensor %s", self._device_class, self.name)

    @property
    def name(self) -> str | None:
        """Return the name of the zone."""
        if self._is_trouble_indicator:
            return "Trouble"
        return None

    @property
    def unique_id(self) -> str:
        """Return HA unique id."""
        if self._is_trouble_indicator:
            return f"adt_pulse_trouble_sensor_{self._site.id}_{self._my_zone.id_}"
        return f"adt_pulse_sensor_{self._site.id}_{self._my_zone.id_}"

    @property
    def icon(self) -> str:
        """Get icon.

        Returns:
            str: returns mdi:icon corresponding to current state
        """
        if self.device_class not in ADT_SENSOR_ICON_MAP:
            LOG.error(
                "Unknown ADT Pulse binary sensor device type %s", self.device_class
            )
            return "mdi:alert-octogram"
        if self.is_on:
            return ADT_SENSOR_ICON_MAP[self.device_class][0]
        return ADT_SENSOR_ICON_MAP[self.device_class][1]

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        # sensor is considered tripped if the state is anything but OK
        if self._is_trouble_indicator:
            return zone_is_in_trouble(self._my_zone)
        return zone_is_open(self._my_zone)

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of the binary sensor."""
        return self._device_class

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra state attributes.

        currently status and last_activity_timestamp
        """
        if self._is_trouble_indicator:
            if self.is_on:
                return {"trouble_type": self._my_zone.state}
            else:
                return {"trouble_type": None}
        return {
            "status": self._my_zone.status,
            "last_activity_timestamp": as_local(
                datetime.fromtimestamp(self._my_zone.last_activity_timestamp)
            ),
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(ADTPULSE_DOMAIN, f"{self._site.id}-{self._my_zone.name}")},
            via_device=(ADTPULSE_DOMAIN, get_alarm_unique_id(self._site)),
            name=self._my_zone.name,
            manufacturer="ADT",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug(
            "Setting ADT Pulse zone %s to on = %s at timestamp %d",
            self.name,
            self.is_on,
            self._my_zone.last_activity_timestamp,
        )
        self.async_write_ha_state()


class ADTPulseGatewaySensor(ADTPulseEntity, BinarySensorEntity):
    """HASS Gateway Online Binary Sensor."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator, site: ADTPulseSite):
        """Initialize gateway sensor.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator):
                HASS data update coordinator
            service (PyADTPulse): API Pulse connection object
        """
        LOG.debug(
            "%s: adding gateway status sensor for site %s", ADTPULSE_DOMAIN, site.name
        )
        self._device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._name = "Connection"
        super().__init__(coordinator, self._name)

    @property
    def is_on(self) -> bool:
        """Return if gateway is online."""
        return self._gateway.is_online

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return HA unique id."""
        return get_gateway_unique_id(self._site)

    @property
    def icon(self) -> str:
        if self.is_on:
            return "mdi:lan-connect"
        return "mdi:lan-disconnect"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the device state attributes."""
        return {
            "primary_connection_type": self._gateway.primary_connection_type,
            "broadband_connection_status": self._gateway.broadband_connection_status,
            "cellular_connection_status": self._gateway.cellular_connection_status,
            "cellular_connection"
            "_signal_strength": self._gateway.cellular_connection_signal_strength,
            "broadband_lan_ip_address": str(self._gateway.broadband_lan_ip_address),
            "device_lan_ip_address": str(self._gateway.device_lan_ip_address),
            "router_lan_ip_address": str(self._gateway.router_lan_ip_address),
            "router_wan_ip_address": str(self._gateway.router_wan_ip_address),
            "current_poll_interval": self._gateway.backoff.get_current_backoff_interval(),
            "initial_poll_interval": self._gateway.backoff.initial_backoff_interval,
            "next_update": as_local(datetime.fromtimestamp(self._gateway.next_update)),
            "last_update": as_local(datetime.fromtimestamp(self._gateway.last_update)),
        }

    @property
    def device_info(self) -> DeviceInfo:
        mac_addresses = set()
        for i in ("broadband_lan_mac", "device_lan_mac"):
            if getattr(self._gateway, i) is not None:
                mac_addresses.add((CONNECTION_NETWORK_MAC, getattr(self._gateway, i)))
        di = DeviceInfo(
            connections=mac_addresses,
            model=self._gateway.model,
            manufacturer=self._gateway.manufacturer,
            hw_version=self._gateway.hardware_version,
            sw_version=self._gateway.firmware_version,
        )
        if self._gateway.serial_number is not None:
            di["identifiers"] = {(ADTPULSE_DOMAIN, self._gateway.serial_number)}
            di["name"] = f"ADT Pulse Gateway {self._gateway.serial_number}"
        else:
            di["name"] = f"ADT Pulse Gateway {self._site.id}"
        return di

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug("Setting Pulse Gateway online status to %s", self._gateway.is_online)
        LOG.debug("Gateway attributes: %s", self.extra_state_attributes)
        LOG.debug("Gateway state: %s", self._gateway)
        self.async_write_ha_state()

"""ADT Pulse HA binary sensor integration.

This adds a sensor for ADT Pulse alarm systems so that all the ADT
motion sensors and switches automatically appear in Home Assistant. This
automatically discovers the ADT sensors configured within Pulse and
exposes them into HA.
"""
from __future__ import annotations

from typing import Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyadtpulse import PyADTPulse
from pyadtpulse.const import STATE_OK
from pyadtpulse.site import ADTPulseSite
from pyadtpulse.zones import ADTPulseZoneData

from .base_entity import ADTPulseEntity
from .const import ADTPULSE_DOMAIN, LOG
from .coordinator import ADTPulseDataUpdateCoordinator

# FIXME: should be BinarySensorEntityDescription?
ADT_DEVICE_CLASS_TAG_MAP = {
    "doorWindow": BinarySensorDeviceClass.DOOR,
    "motion": BinarySensorDeviceClass.WINDOW,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "glass": BinarySensorDeviceClass.TAMPER,
    "co": BinarySensorDeviceClass.GAS,
    "fire": BinarySensorDeviceClass.HEAT,
    "flood": BinarySensorDeviceClass.MOISTURE,
    "garage": BinarySensorDeviceClass.GARAGE_DOOR,  # FIXME: need ADT type
}


async def async_setup_enry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for an ADT Pulse installation."""
    coordinator: ADTPulseDataUpdateCoordinator = hass.data[ADTPULSE_DOMAIN][
        entry.entry_id
    ]
    adt_service = coordinator.adtpulse
    if not adt_service:
        LOG.error("ADT Pulse service not initialized, cannot create sensors")
        return

    if not adt_service.sites:
        LOG.error(f"ADT's Pulse service returned NO sites: {adt_service}")
        return

    for site in adt_service.sites:
        if not isinstance(site, ADTPulseSite):
            raise RuntimeError("pyadtpulse returned invalid site object type")
        if not site.zones_as_dict:
            LOG.error(
                "ADT's Pulse service returned NO zones (sensors) for site: "
                f"{adt_service.sites} ... {adt_service}"
            )
            continue
        entities = [
            ADTPulseZoneSensor(coordinator, site, zone_id)
            for zone_id in site.zones_as_dict.keys()
        ]
        async_add_entities(entities)
        async_add_entities([ADTPulseGatewaySensor(coordinator, adt_service)])


class ADTPulseZoneSensor(ADTPulseEntity, BinarySensorEntity):
    """HASS zone binary sensor implementation for ADT Pulse."""

    # zone = {'id': 'sensor-12', 'name': 'South Office Motion',
    # 'tags': ['sensor', 'motion'], 'status': 'Motion', 'activityTs': 1569078085275}

    def __init__(
        self,
        coordinator: ADTPulseDataUpdateCoordinator,
        site: ADTPulseSite,
        zone_id: int,
    ):
        """Initialize the binary_sensor."""
        LOG.debug(f"{ADTPULSE_DOMAIN}: adding zone sensor for site {site.id}")
        self._site = site
        self._zone_id = zone_id
        my_zone = self._get_my_zone()
        super().__init__(coordinator, my_zone.name, my_zone.state)
        LOG.debug(f"Created ADT Pulse '{self._device_class}' sensor '{self.name}'")

    def _get_my_zone(self) -> ADTPulseZoneData:
        if self._site.zones_as_dict is None:
            raise RuntimeError("ADT pulse returned null zone")
        return self._site.zones_as_dict[self._zone_id]

    # FIXME: this should be a BinarySensorEntityDescription
    def _determine_device_class(self, zone_data: ADTPulseZoneData) -> None:
        # map the ADT Pulse device type tag to a binary_sensor class
        # so the proper status codes and icons are displayed. If device class
        # is not specified, binary_sensordefault to a generic on/off sensor
        self._device_class = None
        tags = zone_data.tags  # type: ignore

        if "sensor" in tags:
            for tag in tags:
                device_class = ADT_DEVICE_CLASS_TAG_MAP[tag]
                if device_class:
                    self._device_class = device_class
                    break

        # since ADT Pulse does not separate the concept of a door or window sensor,
        # we try to autodetect window type sensors so the appropriate icon is displayed
        if self._device_class == "door":
            if "Window" in self.name or "window" in self.name:
                self._device_class = BinarySensorDeviceClass.WINDOW

        if not self._device_class:
            LOG.warn(
                "Ignoring unsupported sensor type from ADT Pulse cloud service "
                f"configured tags: {tags}"
            )
            raise ValueError(f"Unknown ADT Pulse device class {self._device_class}")
        else:
            LOG.info(
                f"Determined {self._name} device class {self._device_class} "
                f"from ADT Pulse service configured tags {tags}"
            )

    @property
    def id(self) -> str:
        """Return the id of the ADT sensor."""
        return self._get_my_zone().id_

    @property
    def unique_id(self) -> str:
        """Return HA unique id.

        Returns:
           str : HA unique entity id
        """
        return f"adt_pulse_sensor_{self._site.id}_{self._zone_id}"

    @property
    def icon(self) -> str:
        """Get icon.

        Returns:
            str: returns mdi:icon corresponding to current state
        """
        return self._icon

    def _set_icon(self):
        """Return icon for the ADT sensor."""
        sensor_type = self._device_class
        if sensor_type == "doorWindow":
            if self.state:
                self._icon = "mdi:door-open"
            else:
                self._icon = "mdi:door"
            return
        elif sensor_type == "motion":
            if self.state:
                self._icon = "mdi:run-fast"
            else:
                self._icon = "mdi:motion-sensor"
            return
        elif sensor_type == "smoke":
            if self.state:
                self._icon = "mdi:fire"
            else:
                self._icon = "mdi:smoke-detector"
            return
        elif sensor_type == "glass":
            self._icon = "mdi:window-closed-variant"
            return
        elif sensor_type == "co":
            self._icon = "mdi:molecule-co"
            return
        self._icon = "mdi:window-closed-variant"

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        # sensor is considered tripped if the state is anything but OK
        zones = self._site.zones_as_dict
        if zones is None:
            return False
        return not zones[self._zone_id] == STATE_OK

    @property
    def device_class(self) -> Optional[str]:
        """Return the class of the binary sensor."""
        return self._device_class

    @property
    def last_activity(self) -> float:
        """Return the timestamp for the last sensor activity."""
        return self._get_my_zone().last_activity_timestamp

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug(
            f"Setting ADT Pulse zone {self.id}, to {self.state} "
            f"at timestamp {self.last_activity}"
        )
        return super()._handle_coordinator_update()


class ADTPulseGatewaySensor(ADTPulseEntity, BinarySensorEntity):
    """HASS Gateway Online Binary Sensor."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator, service: PyADTPulse):
        """Initialize gateway sensor.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator):
                HASS data update coordinator
            service (PyADTPulse): API Pulse connection object
        """
        LOG.debug(f"{ADTPULSE_DOMAIN}: adding gateway status sensor for site")
        self._service = service
        self._device_class = BinarySensorDeviceClass.CONNECTIVITY
        super().__init__(
            coordinator,
            f"ADT Pulse Gateway for {self._service.username}",
            self._service.gateway_online,
        )

    @property
    def is_on(self) -> bool:
        """Return if gatway is online.

        Returns:
            bool: True if online
        """
        return self._service.gateway_online

    # FIXME: Gateways only support one site?
    @property
    def unique_id(self) -> str:
        """Return HA unique id.

        Returns:
           str : HA unique entity id
        """
        return f"adt_pulse_gateway_connection_{self._service.sites[0].id}"

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug(f"Setting Pulse Gateway status to {self._service.gateway_online}")
        return super()._handle_coordinator_update()

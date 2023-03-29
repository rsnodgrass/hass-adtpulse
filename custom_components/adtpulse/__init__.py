"""ADT Pulse for Home Assistant.

See https://github.com/rsnodgrass/hass-adtpulse
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import voluptuous as vol
from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyadtpulse import PyADTPulse
from pyadtpulse.site import ADTPulseSite

from custom_components.adtpulse.alarm_control_panel import ADTPulseAlarm

from .binary_sensor import ADTPulseGatewaySensor, ADTPulseZoneSensor
from .coordinator import ADTPulseDataUpdateCoordinator

LOG = logging.getLogger(__name__)

ADTPULSE_DOMAIN = "adtpulse"

ADTPULSE_SERVICE = "adtpulse_service"

SIGNAL_ADTPULSE_UPDATED = "adtpulse_updated"

EVENT_ALARM = "adtpulse_alarm"
EVENT_ALARM_END = "adtpulse_alarm_end"

NOTIFICATION_TITLE = "ADT Pulse"
NOTIFICATION_ID = "adtpulse_notification"

ATTR_SITE_ID = "site_id"
ATTR_DEVICE_ID = "device_id"

SUPPORTED_PLATFORMS = ["alarm_control_panel", "binary_sensor"]

DEFAULT_SCAN_INTERVAL = 60

CONFIG_SCHEMA = vol.Schema(
    {
        ADTPULSE_DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL  # type: ignore
                ): cv.positive_int,
                vol.Optional(
                    CONF_HOST, default="portal.adtpulse.com"  # type: ignore
                ): cv.string,
                vol.Optional(CONF_DEVICE_ID, default=""): cv.string,  # type: ignore
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigType, async_add_entities: AddEntitiesCallback
) -> bool:
    """Initialize the ADTPulse integration."""
    conf = config[ADTPULSE_DOMAIN]

    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)
    fingerprint = conf.get(CONF_DEVICE_ID)

    # share reference to the service with other components/platforms
    # running within HASS

    host = conf.get(CONF_HOST)
    if host:
        LOG.debug("Using ADT Pulse API host %s", host)
    service = PyADTPulse(
        username,
        password,
        fingerprint,
        service_host=host,
        websession=async_create_clientsession(hass),
        do_login=False,
    )

    hass.data[ADTPULSE_SERVICE] = service
    try:
        if not await service.async_login():
            raise ConfigEntryAuthFailed(
                f"{ADTPULSE_DOMAIN} could not login using supplied credentials"
            )
    except ClientConnectionError as ex:
        LOG.error(f"Unable to connect to ADT Pulse: {str(ex)}")
        hass.components.persistent_notification.create(
            f"Error: {ex}<br />You will need to restart Home Assistant after fixing.",
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID,
        )
        raise ConfigEntryNotReady(
            f"{ADTPULSE_DOMAIN} could not log in due to a protocol error"
        )

    site_list: List[ADTPulseSite] = service.sites
    if site_list is None:
        LOG.error(f"{ADTPULSE_DOMAIN} could not retrieve any sites")
        raise ConfigEntryNotReady(f"{ADTPULSE_DOMAIN} could not retrieve any sites")

    # FIXME: should probably get rid of this for loop since only support 1 site per
    # login and gateway
    for site in site_list:
        coordinator = ADTPulseDataUpdateCoordinator(hass, service)
        async_add_entities([ADTPulseAlarm(coordinator, site)])
        async_add_entities([ADTPulseGatewaySensor(coordinator, service)])
        zone_list = site.zones_as_dict
        if zone_list is None:
            LOG.error(
                f"{ADTPULSE_DOMAIN} could not retrieve any zones for site {site.name}"
            )
            raise ConfigEntryNotReady(
                f"{ADTPULSE_DOMAIN} could not retrieve any zone for site {site.name}"
            )

        async_add_entities(
            ADTPulseZoneSensor(coordinator, site, zone) for zone in zone_list.keys()
        )

    # FIXME: use async task -> forward entry?
    for platform in SUPPORTED_PLATFORMS:
        discovery.load_platform(hass, platform, ADTPULSE_DOMAIN, {}, config)

    return True


class ADTPulseEntity(CoordinatorEntity[ADTPulseDataUpdateCoordinator]):
    """Base Entity class for ADT Pulse devices."""

    def __init__(
        self,
        coordinator: ADTPulseDataUpdateCoordinator,
        name: str,
        initial_state: Optional[str | bool],
    ):
        """Initialize an ADTPulse entity.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator): update coordinator to use
            name (str): entity name
            state (str): inital state
        """
        self._name = name

        self._state = initial_state
        self._attrs: Dict = {}
        super().__init__(coordinator)

    @property
    def name(self) -> str:
        """Return the display name for this sensor."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon.

        Returns:
            str: mdi icon name
        """
        return "mdi:gauge"

    @property
    def state(self) -> Optional[str | bool]:
        """Return the entity state.

        Returns:
            Optional[str|bool]: the entity state
        """
        return self._state

    @property
    def extra_state_attributes(self) -> Dict:
        """Return the device state attributes."""
        return self._attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Call update method."""
        LOG.debug(
            f"Scheduling ADT Pulse entity {self._name} " f"update to {self._state}"
        )
        # inform HASS that ADT Pulse data for this entity has been updated
        self.async_schedule_update_ha_state()

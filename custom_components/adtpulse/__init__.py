"""ADT Pulse for Home Assistant.

See https://github.com/rsnodgrass/hass-adtpulse
"""
from __future__ import annotations

from typing import List

import voluptuous as vol
from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.check_config import ConfigType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyadtpulse import PyADTPulse
from pyadtpulse.site import ADTPulseSite

from .alarm_control_panel import ADTPulseAlarm

from .binary_sensor import ADTPulseGatewaySensor, ADTPulseZoneSensor
from .const import ADTPULSE_DOMAIN, ADTPULSE_SERVICE, LOG, ADT_PULSE_COORDINATOR
from .coordinator import ADTPulseDataUpdateCoordinator

NOTIFICATION_TITLE = "ADT Pulse"
NOTIFICATION_ID = "adtpulse_notification"

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Start up the ADT Pulse HA integration.

    Args:
        hass (HomeAssistant): Home Assistant Object
        config (ConfigType): Configuration type

    Returns:
        bool: True if successful
    """
    return True


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Initialize the ADTPulse integration."""
    conf = config.data[ADTPULSE_DOMAIN]
    hass.data.setdefault(ADTPULSE_DOMAIN, {})
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)
    fingerprint = conf.get(CONF_DEVICE_ID)

    # share reference to the service with other components/platforms
    # running within HASS

    host = conf.get(CONF_HOST)
    if host:
        LOG.debug(f"Using ADT Pulse API host {host}")
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
            LOG.error(f"{ADTPULSE_DOMAIN} could not log in as user {username}")
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
        hass.data[ADTPULSE_DOMAIN][f"{ADT_PULSE_COORDINATOR}-{site.id}"] = coordinator
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

    for platform in SUPPORTED_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config, platform)
        )

    return True

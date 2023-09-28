"""ADT Pulse for Home Assistant.

See https://github.com/rsnodgrass/hass-adtpulse
"""
from __future__ import annotations

from logging import getLogger
from asyncio import TimeoutError, gather
from typing import Any
from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    CONF_HOST,
    CONF_DEVICE_ID
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType
from pyadtpulse import PyADTPulse
from pyadtpulse.site import ADTPulseSite

from .const import (
    ADTPULSE_DOMAIN,
    CONF_FINGERPRINT,
    CONF_HOSTNAME,
    CONF_KEEPALIVE_INTERVAL,
    CONF_RELOGIN_INTERVAL,
)
from .coordinator import ADTPulseDataUpdateCoordinator

LOG = getLogger(__name__)

SUPPORTED_PLATFORMS = ["alarm_control_panel", "binary_sensor"]


def get_gateway_unique_id(site: ADTPulseSite) -> str:
    """Get unique ID for gateway."""
    return f"adt_pulse_gateway_{site.id}"


def get_alarm_unique_id(site: ADTPulseSite) -> str:
    """Get unique ID for alarm."""
    return f"adt_pulse_alarm_{site.id}"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Start up the ADT Pulse HA integration.

    Args:
        hass (HomeAssistant): Home Assistant Object
        config (ConfigType): Configuration type

    Returns:
        bool: True if successful
    """
    hass.data.setdefault(ADTPULSE_DOMAIN, {})
    return True


async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
    """Import a config entry from configuration.yaml."""
    new_config = {**import_config}
    if self.hass.data[CONF_HOST] is not None:
        new_config.update({CONF_HOSTNAME: self.hass.data[CONF_HOST]})
        new_config.pop(CONF_HOST)
    if self.hass.data[CONF_DEVICE_ID] is not None:
        new_config.update({CONF_FINGERPRINT: self.hass.data[CONF_DEVICE_ID]})
        new_config.pop(CONF_DEVICE_ID)
    return await self.async_step_user(new_config)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize the ADTPulse integration."""
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    fingerprint = entry.data.get(CONF_FINGERPRINT)
    poll_interval = entry.options.get(CONF_SCAN_INTERVAL)
    keepalive = entry.options.get(CONF_KEEPALIVE_INTERVAL)
    relogin = entry.options.get(CONF_RELOGIN_INTERVAL)
    # share reference to the service with other components/platforms
    # running within HASS

    host = entry.data[CONF_HOSTNAME]
    if host:
        LOG.debug(f"Using ADT Pulse API host {host}")
    if username is None or password is None or fingerprint is None:
        raise ConfigEntryAuthFailed("Null value for username, password, or fingerprint")
    service = PyADTPulse(
        username,
        password,
        fingerprint,
        service_host=host,
        do_login=False,
        keepalive_interval=keepalive,
        poll_interval=poll_interval,
        relogin_interval=relogin,
    )

    hass.data[ADTPULSE_DOMAIN][entry.entry_id] = service
    try:
        if not await service.async_login():
            LOG.error(f"{ADTPULSE_DOMAIN} could not log in as user {username}")
            raise ConfigEntryAuthFailed(
                f"{ADTPULSE_DOMAIN} could not login using supplied credentials"
            )
    except (ClientConnectionError, TimeoutError) as ex:
        LOG.error(f"Unable to connect to ADT Pulse: {ex}")
        raise ConfigEntryNotReady(
            f"{ADTPULSE_DOMAIN} could not log in due to a protocol error"
        )

    if service.sites is None:
        LOG.error(f"{ADTPULSE_DOMAIN} could not retrieve any sites")
        raise ConfigEntryNotReady(f"{ADTPULSE_DOMAIN} could not retrieve any sites")

    coordinator = ADTPulseDataUpdateCoordinator(hass, service)
    hass.data.setdefault(ADTPULSE_DOMAIN, {})
    hass.data[ADTPULSE_DOMAIN][entry.entry_id] = coordinator
    for platform in SUPPORTED_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
    await coordinator.async_refresh()
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, coordinator.stop)
    )
    entry.async_on_unload(entry.add_update_listener(options_listener))
    return True


async def options_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    new_poll = entry.options.get(CONF_SCAN_INTERVAL)
    new_relogin = entry.options.get(CONF_RELOGIN_INTERVAL)
    new_keepalive = entry.options.get(CONF_KEEPALIVE_INTERVAL)
    coordinator = entry.data[ADTPULSE_DOMAIN][entry.entry_id].adtpulse
    old_relogin = coordinator.relogin_interval
    old_keepalive = coordinator.keepalive_interval

    if new_poll is not None:
        LOG.debug(f"Setting new poll interval to {new_poll} seconds")
        coordinator.site.gateway.poll_interval = int(new_poll)

    new_relogin = new_relogin or old_relogin
    new_keepalive = new_keepalive or old_keepalive

    if new_keepalive > new_relogin:
        LOG.error(
            f"Cannot set new keepalive to {new_keepalive}, "
            f"must be less than {new_relogin}"
        )
        return

    LOG.debug(
        f"Setting new keepalive to {new_keepalive} minutes,"
        f"new relogin interval to {new_relogin} minutes"
    )
    coordinator.keepalive_interval = new_keepalive
    coordinator.relogin_interval = new_relogin


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = all(
        await gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in SUPPORTED_PLATFORMS
            ]
        )
    )

    if unload_ok:
        coordinator: ADTPulseDataUpdateCoordinator = hass.data[ADTPULSE_DOMAIN][
            entry.entry_id
        ]
        await coordinator.stop(None)
        await coordinator.adtpulse.async_logout()
        hass.data[ADTPULSE_DOMAIN].pop(entry.entry_id)

    return unload_ok

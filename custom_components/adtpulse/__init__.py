"""ADT Pulse for Home Assistant.

See https://github.com/rsnodgrass/hass-adtpulse
"""
from __future__ import annotations

from logging import getLogger
from asyncio import gather
from typing import Any

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
from homeassistant.helpers.config_entry_flow import FlowResult
from homeassistant.helpers.config_validation import config_entry_only_config_schema
from homeassistant.helpers.typing import ConfigType
from pyadtpulse.const import (
    ADT_DEFAULT_KEEPALIVE_INTERVAL,
    ADT_DEFAULT_POLL_INTERVAL,
    ADT_DEFAULT_RELOGIN_INTERVAL,
)
from pyadtpulse.exceptions import (
    PulseAccountLockedError,
    PulseAuthenticationError,
    PulseGatewayOfflineError,
    PulseServiceTemporarilyUnavailableError,
)
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync

from .const import (
    ADTPULSE_DOMAIN,
    CONF_FINGERPRINT,
    CONF_HOSTNAME,
    CONF_KEEPALIVE_INTERVAL,
    CONF_RELOGIN_INTERVAL,
)
from .coordinator import ADTPulseDataUpdateCoordinator

LOG = getLogger(__name__)

SUPPORTED_PLATFORMS = ["alarm_control_panel", "binary_sensor", "sensor"]

CONFIG_SCHEMA = config_entry_only_config_schema(ADTPULSE_DOMAIN)


async def async_setup(
    hass: HomeAssistant,
    config: ConfigType,  # pylint: disable=unused-argument
) -> bool:
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
    poll_interval = entry.options.get(CONF_SCAN_INTERVAL, ADT_DEFAULT_POLL_INTERVAL)
    keepalive = entry.options.get(
        CONF_KEEPALIVE_INTERVAL, ADT_DEFAULT_KEEPALIVE_INTERVAL
    )
    relogin = entry.options.get(CONF_RELOGIN_INTERVAL, ADT_DEFAULT_RELOGIN_INTERVAL)
    # share reference to the service with other components/platforms
    # running within HASS

    host = entry.data[CONF_HOSTNAME]
    if host:
        LOG.debug("Using ADT Pulse API host %s", host)
    if username is None or password is None or fingerprint is None:
        raise ConfigEntryAuthFailed("Null value for username, password, or fingerprint")
    service = PyADTPulseAsync(
        username,
        password,
        fingerprint,
        service_host=host,
        keepalive_interval=keepalive,
        relogin_interval=relogin,
    )

    hass.data[ADTPULSE_DOMAIN][entry.entry_id] = service
    try:
        await service.async_login()
    except PulseAuthenticationError as ex:
        LOG.error("Unable to connect to ADT Pulse: %s", ex)
        raise ConfigEntryAuthFailed(
            f"{ADTPULSE_DOMAIN} could not log in due to a protocol error"
        ) from ex
    except (
        PulseAccountLockedError,
        PulseServiceTemporarilyUnavailableError,
        PulseGatewayOfflineError,
    ) as ex:
        LOG.error("Unable to connect to ADT Pulse: %s", ex)
        raise ConfigEntryNotReady(
            f"{ADTPULSE_DOMAIN} could not log in due to service unavailability"
        ) from ex

    if service.sites is None:
        LOG.error("%s could not retrieve any sites", ADTPULSE_DOMAIN)
        raise ConfigEntryNotReady(f"{ADTPULSE_DOMAIN} could not retrieve any sites")
    try:
        service.site.gateway.poll_interval = poll_interval
    except ValueError as ex:
        LOG.warning(
            "Could not set poll interval to %f seconds: %s",
            poll_interval,
            ex,
        )
    coordinator = ADTPulseDataUpdateCoordinator(hass, service)
    hass.data.setdefault(ADTPULSE_DOMAIN, {})
    hass.data[ADTPULSE_DOMAIN][entry.entry_id] = coordinator
    for platform in SUPPORTED_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
    # entities already have their data, no need to call async_refresh()
    entry.async_on_unload(entry.add_update_listener(options_listener))
    return True


async def options_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    new_poll = entry.options.get(CONF_SCAN_INTERVAL)
    new_relogin = entry.options.get(CONF_RELOGIN_INTERVAL)
    new_keepalive = entry.options.get(CONF_KEEPALIVE_INTERVAL)
    coordinator: ADTPulseDataUpdateCoordinator = hass.data[ADTPULSE_DOMAIN][
        entry.entry_id
    ]
    pulse_service = coordinator.adtpulse

    if new_poll is not None and new_poll != "":
        LOG.info("Setting new poll interval to %f seconds", new_poll)
    else:
        new_poll = ADT_DEFAULT_POLL_INTERVAL
        LOG.info("Re-setting poll interval to default %f seconds", new_poll)
    try:
        pulse_service.site.gateway.poll_interval = new_poll
        coordinator.async_set_updated_data(None)
    except ValueError as ex:
        LOG.warning(
            "Could not set poll interval to  %f seconds: %s",
            new_poll,
            ex,
        )

    if new_relogin is None or new_relogin == "":
        new_relogin = ADT_DEFAULT_RELOGIN_INTERVAL
        LOG.info("Re-setting relogin interval to default %d seconds", new_relogin)
    else:
        LOG.info("Setting new relogin interval to %d seconds", new_relogin)

    if new_keepalive is None or new_keepalive == "":
        new_keepalive = ADT_DEFAULT_KEEPALIVE_INTERVAL
        LOG.info("Re-setting keepalive interval to default %d seconds", new_keepalive)
    else:
        LOG.info("Setting new keepalive interval to %d seconds", new_keepalive)

    try:
        pulse_service.keepalive_interval = new_keepalive
    except ValueError as ex:
        LOG.warning(
            "Could not set keepalive interval to %d seconds: %s", new_keepalive, ex
        )

    try:
        pulse_service.relogin_interval = new_relogin
    except ValueError as ex:
        LOG.warning("Could not set relogin interval to %d seconds: %s", new_relogin, ex)


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
        await coordinator.adtpulse.async_logout()
        hass.data[ADTPULSE_DOMAIN].pop(entry.entry_id)

    return unload_ok

"""
ADT Pulse for Home Assistant
See https://github.com/rsnodgrass/hass-adtpulse
"""
import logging
import asyncio

import time
from datetime import timedelta
import voluptuous as vol
from requests.exceptions import HTTPError, ConnectTimeout

from pyadtpulse import PyADTPulse

from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.event import track_time_interval

from homeassistant import exceptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from pyadtpulse.const import ADT_DEFAULT_HTTP_HEADERS

from .const import (  # pylint:disable=unused-import
    ADTPULSE_DOMAIN,
    CONF_PASSWORD,
    CONF_FINGERPRINT,
    CONF_USERNAME,
    ADTPULSE_DOMAIN,
    CONF_HOSTNAME,
    CONF_POLLING,
)

LOG = logging.getLogger(__name__)

ADTPULSE_SERVICE = 'adtpulse_service'

SIGNAL_ADTPULSE_UPDATED = 'adtpulse_updated'

EVENT_ALARM = 'adtpulse_alarm'
EVENT_ALARM_END = 'adtpulse_alarm_end'

NOTIFICATION_TITLE = 'ADT Pulse'
NOTIFICATION_ID = 'adtpulse_notification'

ATTR_SITE_ID   = 'site_id'
ATTR_DEVICE_ID = 'device_id'

SUPPORTED_PLATFORMS = [ 'alarm_control_panel', 'binary_sensor' ]


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(ADTPULSE_DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    polling = 3
    adtpulse = await hass.async_add_executor_job(PyADTPulse,entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], entry.data[CONF_FINGERPRINT], entry.data[CONF_HOSTNAME],ADT_DEFAULT_HTTP_HEADERS, None, True, polling, False)
    hass.data[ADTPULSE_DOMAIN][entry.entry_id] = adtpulse

    coordinator = ADTPulseDataUpdateCoordinator(hass, adtpulse, int(polling))
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(ADTPULSE_DOMAIN, {})
    hass.data[ADTPULSE_DOMAIN][entry.entry_id] = coordinator

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    for component in SUPPORTED_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in SUPPORTED_PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[ADTPULSE_DOMAIN].pop(entry.entry_id)

    return unload_ok

class ADTPulseDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage the refresh of the adtpulse data api"""

    def __init__(self, hass, adtpulse, pollingRate):
        self._adtpulse = adtpulse
        self._hass = hass
        self._pollingRate = pollingRate
        super().__init__(
            hass,
            LOG,
            name=ADTPULSE_DOMAIN,
            update_interval=timedelta(seconds=pollingRate),
        )

    @property
    def adtpulse(self):
        return self._adtpulse

    @property
    def pollingRate(self):
        return self._pollingRate

    async def _async_update_data(self):
        """Update data via library."""
        try:
            LOG.info(f"Updating ADT Statuses")
            await self._hass.async_add_executor_job(self.adtpulse.update)
            #await self._hass.async_add_executor_job(self.adtpulse.wait_for_update)
            LOG.info(f"Finsihed Updating ADT Statuses")
        except Exception as error:
            LOG.error("Error updating ADT Pulse data\n{error}")
            raise UpdateFailed(error) from error
        return self.adtpulse

class ADTPulseEntity(Entity):
    #Base Entity class for ADT Pulse devices

    def __init__(self, hass, service, name):
        self.hass = hass
        self._service = service
        self._name = name

        self._state = None
        self._attrs = {}
        
    @property
    def name(self):
        #Return the display name for this sensor
        return self._name

    @property
    def icon(self):
        return 'mdi:gauge'

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        #Return the device state attributes.
        return self._attrs

    async def async_added_to_hass(self):
        #Register callbacks.
        # register callback when cached ADTPulse data has been updated
        async_dispatcher_connect(self.hass, SIGNAL_ADTPULSE_UPDATED, self._update_callback)

    @callback
    def _update_callback(self):
        #Call update method.

        # inform HASS that ADT Pulse data for this entity has been updated
        self.async_schedule_update_ha_state()

async def async_connect_or_timeout(hass, adtpulse):
    userId = None
    try:
        userId = adtpulse._userId
        if userId != None or "":
            LOG.info("Success Connecting to ADTPulse")
    except Exception as err:
        LOG.error("Error connecting to ADTPulse")
        raise CannotConnect from err


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidPolling(exceptions.HomeAssistantError):
    """Error to indicate polling is incorrect value."""
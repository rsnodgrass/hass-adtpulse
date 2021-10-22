"""
ADT Pulse for Home Assistant
See https://github.com/rsnodgrass/hass-adtpulse
"""
import logging

import time
from datetime import timedelta
import voluptuous as vol
from requests.exceptions import HTTPError, ConnectTimeout

from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.event import track_time_interval
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_DEVICE_ID

LOG = logging.getLogger(__name__)

ADTPULSE_DOMAIN = 'adtpulse'

ADTPULSE_SERVICE = 'adtpulse_service'

SIGNAL_ADTPULSE_UPDATED = 'adtpulse_updated'

EVENT_ALARM = 'adtpulse_alarm'
EVENT_ALARM_END = 'adtpulse_alarm_end'

NOTIFICATION_TITLE = 'ADT Pulse'
NOTIFICATION_ID = 'adtpulse_notification'

ATTR_SITE_ID   = 'site_id'
ATTR_DEVICE_ID = 'device_id'

SUPPORTED_PLATFORMS = [ 'alarm_control_panel', 'binary_sensor' ]

DEFAULT_SCAN_INTERVAL=60

CONFIG_SCHEMA = vol.Schema({
        ADTPULSE_DOMAIN: vol.Schema({
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
            vol.Optional(CONF_HOST, default='portal.adtpulse.com'): cv.string,
            vol.Optional(CONF_DEVICE_ID, default=''): cv.string
        })
    }, extra=vol.ALLOW_EXTRA
)

def setup(hass, config):
    """Initialize the ADTPulse integration"""
    conf = config[ADTPULSE_DOMAIN]

    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)
    fingerprint = conf.get(CONF_DEVICE_ID)

    try:
        # share reference to the service with other components/platforms running within HASS
        from pyadtpulse import PyADTPulse
        service = PyADTPulse(username, password, fingerprint)

        host = conf.get(CONF_HOST)
        if host:
            LOG.debug("Using ADT Pulse API host %s", host)
            service.set_service_host(host)

        hass.data[ADTPULSE_SERVICE] = service

    except (ConnectTimeout, HTTPError) as ex:
        LOG.error("Unable to connect to ADT Pulse: %s", str(ex))
        hass.components.persistent_notification.create(
            f"Error: {ex}<br />You will need to restart Home Assistant after fixing.",
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID,
        )
        return False

    def refresh_adtpulse_data(event_time):
        """Call ADTPulse service to refresh latest data"""
        LOG.debug("Checking ADT Pulse cloud service for updates")

        adtpulse_service = hass.data[ADTPULSE_SERVICE]
        if adtpulse_service.updates_exist:
            adtpulse_service.update()

            # notify all listeners (alarm and sensors) that they may have new data
            dispatcher_send(hass, SIGNAL_ADTPULSE_UPDATED)

    # subscribe for notifications that an update should be triggered
    hass.services.register(ADTPULSE_DOMAIN, 'update', refresh_adtpulse_data)

    # automatically update ADTPulse data (samples) on the scan interval
    scan_interval = timedelta(seconds = conf.get(CONF_SCAN_INTERVAL))
    track_time_interval(hass, refresh_adtpulse_data, scan_interval)

    for platform in SUPPORTED_PLATFORMS:
        discovery.load_platform(hass, platform, ADTPULSE_DOMAIN, {}, config)

    return True


class ADTPulseEntity(Entity):
    """Base Entity class for ADT Pulse devices"""

    def __init__(self, hass, service, name):
        self.hass = hass
        self._service = service
        self._name = name

        self._state = None
        self._attrs = {}
        
    @property
    def name(self):
        """Return the display name for this sensor"""
        return self._name

    @property
    def icon(self):
        return 'mdi:gauge'

    @property
    def state(self):
        return self._state

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return self._attrs

    async def async_added_to_hass(self):
        """Register callbacks."""
        # register callback when cached ADTPulse data has been updated
        async_dispatcher_connect(self.hass, SIGNAL_ADTPULSE_UPDATED, self._update_callback)

    @callback
    def _update_callback(self):
        """Call update method."""

        # inform HASS that ADT Pulse data for this entity has been updated
        self.async_schedule_update_ha_state()

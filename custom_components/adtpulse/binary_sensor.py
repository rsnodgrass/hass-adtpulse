"""
This adds a sensor for ADT Pulse alarm systems so that all the ADT
motion sensors and switches automatically appear in Home Assistant. This
automatically discovers the ADT sensors configured within Pulse and
exposes them into HA.
"""
import logging
import re
import json
import requests
import datetime
#from datetime import timedelta

from requests import Session
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from pyadtpulse.const import STATE_OK

from . import ADTPULSE_SERVICE, SIGNAL_ADTPULSE_UPDATED

LOG = logging.getLogger(__name__)

ADTPULSE_DATA = 'adtpulse'

ADT_DEVICE_CLASS_TAG_MAP = {
    'doorWindow': 'door',
    'motion':     'motion',
    'smoke':      'smoke',
    'glass':      'vibration',
    'co':         'gas',
    'fire':       'heat',
    'flood':      'moisture',
    'garage':     'garage_door' # FIXME: need ADT type
}

def setup_platform(hass, config, add_entities_callback, discovery_info=None):
    """Set up sensors for an ADT Pulse installation."""
    sensors = []
    adt_service = hass.data.get(ADTPULSE_SERVICE)
    if not adt_service:
        LOG.error("ADT Pulse service not initialized, cannot create sensors")
        return

    if not adt_service.sites:
        LOG.error("ADT's Pulse service returned NO sites: %s", adt_service)
        return

    for site in adt_service.sites:
        if not site.zones:
            LOG.error("ADT's Pulse service returned NO zones (sensors) for site: %s ... %s", adt_service.sites, adt_service)
            continue
            
        for zone in site.zones:
            sensors.append( ADTPulseSensor(hass, adt_service, site, zone) )

    add_entities_callback(sensors)

class ADTPulseSensor(BinarySensorEntity):
    """HASS binary sensor implementation for ADT Pulse."""

    # zone = {'id': 'sensor-12', 'name': 'South Office Motion', 'tags': ['sensor', 'motion'],
    #         'status': 'Motion', 'activityTs': 1569078085275}

    def __init__(self, hass, adt_service, site, zone_details):
        """Initialize the binary_sensor."""
        self.hass = hass
        self._adt_service = adt_service
        self._site = site

        self._zone_id = zone_details.get('id')
        self._name = zone_details.get('name')
        self._update_zone_status(zone_details)

        self._determine_device_class()

        LOG.info(f"Created ADT Pulse '{self._device_class}' sensor '{self.name}'")

    def _determine_device_class(self):
        # map the ADT Pulse device type tag to a binary_sensor class so the proper status
        # codes and icons are displayed. If device class is not specified, binary_sensor
        # default to a generic on/off sensor
        self._device_class = None
        tags = self._zone.get('tags')

        if 'sensor' in tags:
            for tag in tags:
                device_class = ADT_DEVICE_CLASS_TAG_MAP.get(tag)
                if device_class:
                    self._device_class = device_class
                    break

        # since ADT Pulse does not separate the concept of a door or window sensor,
        # we try to autodetect window type sensors so the appropriate icon is displayed
        if self._device_class is 'door':
            if 'Window' in self.name or 'window' in self.name:
                self._device_class = 'window'

        if not self._device_class:
            LOG.warn(f"Ignoring unsupported sensor type from ADT Pulse cloud service configured tags: {tags}")
            # FIXME: throw exception
        else:
           LOG.info(f"Determined {self._name} device class {self._device_class} from ADT Pulse service configured tags {tags}")

    @property
    def id(self):
        """Return the id of the ADT sensor."""
        return self._zone_id

    @property
    def unique_id(self):
        return f"adt_pulse_sensor_{self._site.id}_{self._zone_id}"
    
    @property
    def icon(self):
        """Return icon for the ADT sensor."""
        sensor_type = self._zone.get('')
        if sensor_type == 'doorWindow':
            if self.state:
                return 'mdi:door-open'
            else:
                return 'mdi:door'
        elif sensor_type == 'motion':
            if self.state:
                return 'mdi:run-fast'
            else:
                return 'mdi:motion-sensor'
        elif sensor_type == 'smoke':
            if self.state:
                return 'mdi:fire'
            else:
                return 'mdi:smoke-detector'
        elif sensor_type == 'glass':
            return 'mdi:window-closed-variant'
        elif sensor_type == 'co':
            return 'mdi:molecule-co'
        return 'mdi:window-closed-variant'

    @property
    def name(self):
        """Return the name of the ADT sensor."""
        return self._name

    @property
    def should_poll(self):
        """Updates occur periodically from __init__ when changes detected"""
        return True

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        status = self._zone.get('state')
        # sensor is considered tripped if the state is anything but OK
        return not status == STATE_OK

    @property
    def device_class(self):
        """Return the class of the binary sensor."""
        return self._device_class

    @property
    def last_activity(self):
        """Return the timestamp for the last sensor activity."""
        return self._zone.get('timestamp')

    def _update_zone_status(self, zone_details):
        self._zone = zone_details

    def _adt_updated_callback(self):
        # find the latest data for each zone
        for zone in self._site.zones:
            if zone.get('id') == self._zone_id:
                self._update_zone_status(zone)

    async def async_added_to_hass(self):
        """Register callbacks."""
        # register callback to learn ADT Pulse data has been updated
        async_dispatcher_connect(self.hass, SIGNAL_ADTPULSE_UPDATED, self._adt_updated_callback)

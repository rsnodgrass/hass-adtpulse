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
from homeassistant.components.binary_sensor import BinarySensorDevice

from . import ADTPULSE_SERVICE

LOG = logging.getLogger(__name__)

ADTPULSE_DATA = 'adtpulse'

ADT_STATUS_MAP = {
    'Closed':    False,
    'Open':      True,
    'No Motion': False,
    'Motion':    True
}

ADT_DEVICE_CLASS_TAG_MAP = {
    'doorWindow': 'door',
    'motion':     'motion',
    'smoke':      'smoke'
}

def setup_platform(hass, config, add_entities_callback, discovery_info=None):
    """Set up sensors for an ADT Pulse installation."""
    sensors = []
    adt_service = hass.data.get(ADTPULSE_SERVICE)
    if not adt_service:
        LOG.error("ADT Pulse service not initialized, cannot create sensors")
        return

    for site in adt_service.sites:
        for zone in site.zones:
            sensors.append( ADTPulseSensor(hass, adt_service, site, zone) )

    add_entities_callback(sensors)

class ADTPulseSensor(BinarySensorDevice):
    """HASS binary sensor implementation for ADT Pulse."""

    # zone = {'id': 'sensor-12', 'name': 'South Office Motion', 'tags': ['sensor', 'motion'],
    #         'status': 'Motion', 'activityTs': 1569078085275}

    def __init__(self, hass, adt_service, site, zone):
        """Initialize the binary_sensor."""
        self._hass = hass
        self._adt_service = adt_service
        self._site = site
        self._zone = zone

        self._name = zone.get('name')
        self._determine_device_class()

        self._last_activity_timestamp = zone.get('activityTs')

        LOG.info(f"Created ADT Pulse '{self._device_class}' sensor '{self._name}'")

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
            if 'Window' in self._name or 'window' in self._name:
                self._device_class = 'window'

        if not self._device_class:
            LOG.warn(f"Ignoring unsupported ADT Pulse sensor type {tags}")
            # FIXME: throw exception
        
    @property
    def id(self):
        """Return the id of the ADT sensor."""
        return self._zone.get('id')

    @property
    def name(self):
        """Return the name of the ADT sensor."""
        return self._name

    @property
    def should_poll(self):
        """Polling needed until periodic refresh of JSON data supported."""
        return True

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._zone.get('status')

    @property
    def device_class(self):
        """Return the class of the binary sensor."""
        return self._device_class

    @property
    def last_activity(self):
        """Return the timestamp for the last sensor actvity."""
        return self._zone.get('activityTs')

    def update(self):
        """Trigger the process to update this sensors state."""
        self._adtpulseservice.trigger_update() 

    def update_state(self, state, last_activity_timestamp):
        # compare timestamp to determine if an event occured, since comparing state values
        # might have missed a previous state change before flipping back to the same state
        state_changed = last_activity_timestamp > self._last_activity_timestamp
  
        self._last_activity_timestamp = last_activity_timestamp
        self._state = state

        # emit message on state change
#        if state_changed:
#            LOG.error(f"ADT Pulse state change notifications not available: {desc['name']}")

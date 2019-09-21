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
    "Closed":    False,
    "Open":      True,
    "No Motion": False,
    "Motion":    True
}

ADT_DEVICE_CLASS_TAG_MAP = {
    "doorWindow": "door",
    "motion": "motion",
    "smoke": "smoke"
}

# TODO: default username to hass_adtpulse

def setup_platform(hass, config, add_entities_callback, discovery_info=None):
    """Set up sensors for an ADT Pulse installation."""
    sensors = []

    adt_service = hass.data[ADTPULSE_SERVICE]
    for site in adt_service.sites:
        sensors.append( ADTPulseSensor(hass, adt_service, site) )

class ADTPulseService():
    def __init__(self, username, password, refresh_interval):
        self._username = username
        self._password = password

        self._session = None
        self._last_response = None

        self._refresh_interval = refresh_interval
        self._last_update_timestamp = 0
        self._last_adtpulse_timestamp = 0

        self._binary_sensors = {}

#        adt_pulse_timestamp = int(response['ts'])
#        if self._last_adtpulse_timestamp is adt_pulse_timestamp:
#            _LOGGER.warning('Strange: ADT Pulse reported same %d timestamp as last request', adt_pulse_timestamp)

#        self._last_response = response
#        self._last_update_timestamp = datetime.datetime.now()
#        self._last_adtpulse_timestamp = adt_pulse_timestamp

        # apply the latest state values to all the sensors
#        for desc in response['items']:
#            tags = desc['tags'].split(',')
#            if 'sensor' not in tags:
#                _LOGGER.error("Currently does not support ADT sensor %s = '%s' (tags %S)",
#                                desc['id'], desc['name'], desc['tags'])
#               continue
  
#            sensor = self._get_sensor(desc)
#            self._update_sensor_state(sensor, desc)

    def _construct_sensor(self, desc):
        name = desc['name']

        # map the ADT Pulse device type tag to a binary_sensor class so the proper status
        # codes and icons are displayed. If device class is not specified, binary_sensor
        # default to a generic on/off sensor
        device_class = ADT_DEVICE_CLASS_TAG_MAP[ desc['tags'].split(',')[1] ]
        if device_class:
            self._device_class = device_class

        # since ADT Pulse does not separate the concept of a door or window sensor,
        # we try to autodetect window type sensors so the appropriate icon is displayed
        if self._device_class is 'door':
            if 'Window' in name or 'window' in name:
                self._device_class = 'window'

        state = self._parse_sensor_state(desc)
        last_activity_timestamp = int(desc['state']['activityTs'])

        return ADTBinarySensor(device_class, desc['id'], desc['name'], 
                               state, last_activity_timestamp, self)

    def _get_sensor(self, desc):
        id = desc['id'] 
        if id in self._binary_sensors:
            return self._binary_sensors[id]

        sensor = self._construct_sensor(desc)
        self._binary_sensors[id] = sensor
        return sensor

    def _parse_sensor_state(self, desc):
        # NOTE: it may be better to determine state by using the "icon" to determine status,
        # or at least compare as a safety check
        #       devStatOpen -> open
        #       devStatOK   -> closed
        #       devStatTamper (for shock devices)
        state = 'devStatOpen' in desc['state']['icon']

        # extract the sensor status from the text description
        # e.g.:  Front Side Door - Closed\nLast Activity: 9/7 4:02 PM
        match = re.search(r'-\s(.+)\n', desc['state']['statusTxt'])
        if match:
            status = match.group(1)
            if status in ADT_STATUS_MAP:
                state = ADT_STATUS_MAP[status]

        return state

    def _update_sensor_state(self, sensor, desc):
        last_activity_timestamp = int( desc['state']['activityTs'] )
        state = self._parse_sensor_state( desc )
        sensor.update_state(state, last_activity_timestamp)

    # return all the known sensors
    def sensors(self):
        return self._binary_sensors.values()

class ADTPulseSensor(BinarySensorDevice):
    """A binary sensor implementation for ADT Pulse."""

    def __init__(self, device_class, id, name, state, last_activity_timestamp, adtpulseservice):
        """Initialize the binary_sensor."""
        self._device_class = device_class
        self._name = name
        self._id = id
        self._state = state
        self._last_activity_timestamp = last_activity_timestamp
        self._adtpulseservice = adtpulseservice

        LOG.debug(f"Created ADTPulseSensor {name}")

    @property
    def id(self):
        """Return the id of the ADT sensor."""
        return self._id

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
        return self._state

    @property
    def device_class(self):
        """Return the class of the binary sensor."""
        return self._device_class

    @property
    def last_activity(self):
        """Return the timestamp for the last sensor actvity."""
        return self._last_activity_timestamp

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
        if state_changed:
            LOG.error(f"ADT Pulse state change notifications not available: {desc['name']}")

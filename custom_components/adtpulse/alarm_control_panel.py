"""Support for ADT Pulse alarm control panels."""
import logging

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
)

from . import ADTPulseEntity, ADTPULSE_SERVICE

LOG = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities_callback, discovery_info=None):
    """Set up an alarm control panel for ADT Pulse."""
    adt_service = hass.data[ADTPULSE_SERVICE]

    alarm_devices = []
    for site in adt_service.sites:
        alarm_devices.append( ADTPulseAlarm(hass, adt_service, site) )

    # FIXME: why this??? data.devices.extend(alarm_devices)
    add_entities_callback(alarm_devices)

class ADTPulseAlarm(ADTPulseEntity, alarm.AlarmControlPanel):
    """An alarm_control_panel implementation for ADT Pulse."""

    def __init__(self, hass, service, site):
        """Initialize the alarm control panel."""
        name = f"ADT {site.name} Alarm"
        self._site = site
        super().__init__(hass, service, name)

    @property
    def icon(self):
        """Return the icon."""
        return 'mdi:security'

    @property
    def state(self):
        """Return the state of the device."""        
        if self._site.is_disarmed:
            self._state = STATE_ALARM_DISARMED
        elif self._site.is_away:
            self._state = STATE_ALARM_ARMED_AWAY
        elif self._site.is_home:
            self._state = STATE_ALARM_ARMED_HOME
        else:
            self._state = None
        return self._state

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._site.disarm()

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._site.arm_home()

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._site.arm_away()

    @property
    def name(self):
        """Return the name of the alarm."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            # FIXME: add timestamp for this state change?
            "site_id": self._site.id
        }

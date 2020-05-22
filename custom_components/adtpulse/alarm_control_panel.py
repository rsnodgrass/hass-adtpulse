"""Support for ADT Pulse alarm control panels."""
import logging

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
)
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
)

from . import ADTPulseEntity, ADTPULSE_SERVICE, SIGNAL_ADTPULSE_UPDATED

LOG = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities_callback, discovery_info=None):
    """Set up an alarm control panel for ADT Pulse."""
    adt_service = hass.data.get(ADTPULSE_SERVICE)
    if not adt_service:
        LOG.error("ADT Pulse service not initialized, cannot setup alarm platform")
        return

    if not adt_service.sites:
        LOG.error("ADT Pulse service failed to return sites: %s", adt_service)
        return

    alarm_devices = []
    for site in adt_service.sites:
        alarm_devices.append( ADTPulseAlarm(hass, adt_service, site) )

    # FIXME: why this??? data.devices.extend(alarm_devices)
    add_entities_callback(alarm_devices)

class ADTPulseAlarm(ADTPulseEntity, alarm.AlarmControlPanelEntity):
    """An alarm_control_panel implementation for ADT Pulse."""

    def __init__(self, hass, service, site):
        """Initialize the alarm control panel."""
        name = f"ADT {site.name}"
        self._site = site
        super().__init__(hass, service, name)

    @property
    def icon(self):
        """Return the icon."""
        return 'mdi:security'

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY

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

    # FIXME: change to async def alarm_disarm(self, code=None)!!!
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

    @property
    def unique_id(self):
        return f"adt_pulse_alarm_{self._site.id}"
    
    @property
    def code_format(self):
        return None

    def _adt_updated_callback(self):
        #LOG.warning("ADT Pulse data updated...actually update state!")
        
        # FIXME: is this even needed?  can we disable this sensor from polling, since the __init__ update mechanism updates this
        self.async_schedule_update_ha_state() # notify HASS this entity has been updated

    async def async_added_to_hass(self):
        """Register callbacks."""
        # register callback to learn ADT Pulse data has been updated
        async_dispatcher_connect(self._hass, SIGNAL_ADTPULSE_UPDATED, self._adt_updated_callback)

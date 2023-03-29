"""Support for ADT Pulse alarm control panels."""
from __future__ import annotations
import logging
from typing import Dict

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_CUSTOM_BYPASS,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMING,
)

from homeassistant.helpers.update_coordinator import callback
from custom_components.adtpulse.coordinator import ADTPulseDataUpdateCoordinator

from . import ADTPulseEntity
from pyadtpulse.site import (
    ADTPulseSite,
    ADT_ALARM_UNKNOWN,
    ADT_ALARM_ARMING,
    ADT_ALARM_AWAY,
    ADT_ALARM_DISARMING,
    ADT_ALARM_HOME,
    ADT_ALARM_OFF,
)

LOG = logging.getLogger(__name__)

ALARM_MAP = {
    ADT_ALARM_ARMING: STATE_ALARM_ARMING,
    ADT_ALARM_AWAY: STATE_ALARM_ARMED_AWAY,
    ADT_ALARM_DISARMING: STATE_ALARM_DISARMING,
    ADT_ALARM_HOME: STATE_ALARM_ARMED_HOME,
    ADT_ALARM_OFF: STATE_ALARM_DISARMED,
    ADT_ALARM_UNKNOWN: None,
}


class ADTPulseAlarm(ADTPulseEntity, alarm.AlarmControlPanelEntity):
    """An alarm_control_panel implementation for ADT Pulse."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator, site: ADTPulseSite):
        """Initialize the alarm control panel."""
        name = f"ADT {site.name}"
        self._site = site
        self._data_from_fetch = True
        super().__init__(coordinator, name, ALARM_MAP[self._site.status])

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:security"

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            SUPPORT_ALARM_ARM_HOME
            | SUPPORT_ALARM_ARM_AWAY
            | SUPPORT_ALARM_ARM_CUSTOM_BYPASS
        )

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        if await self._site.async_disarm():
            self._state = STATE_ALARM_DISARMING
            self._data_from_fetch = False
        else:
            LOG.warning(f"Could not disam ADT alarm for site {self._site.id}")

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        if await self._site.async_arm_home():
            self._state = STATE_ALARM_ARMING
            self._data_from_fetch = False
        else:
            LOG.warning(f"Could not arm home ADT alarm for site {self._site.id}")

    async def async_alarm_arm_away(self):
        """Send arm away command."""
        if await self._site.async_arm_away():
            self._state = STATE_ALARM_ARMING
            self._data_from_fetch = False
        else:
            LOG.warning(f"Could not arm away ADT alarm for site {self._site.id}")

    # Pulse can arm away or home with bypass
    async def async_alarm_arm_custom_bypass(self) -> None:
        """Send force arm command."""
        if await self._site.async_arm_away(True):
            self._state = STATE_ALARM_ARMING
            self._data_from_fetch = False
        else:
            LOG.warning(f"Could not force arm ADT alarm for site {self._site.id}")

    @property
    def name(self) -> str:
        """Return the name of the alarm."""
        return self._name

    @property
    def extra_state_attributes(self) -> Dict:
        """Return the state attributes."""
        return {
            # FIXME: add timestamp for this state change?
            "site_id": self._site.id,
            "site_name": self._site.name,
        }

    @property
    def unique_id(self) -> str:
        """Return HA unique id.

        Returns:
            str: the unique id
        """
        return f"adt_pulse_alarm_{self._site.id}"

    @property
    def code_format(self) -> None:
        """Return code format.

        Returns:
            None (not implmented)
        """
        return None

    @property
    def assumed_state(self) -> bool:
        """Return if state has been fetched or assumed.

        Returns:
            bool: True means data assumed
        """
        return self._data_from_fetch

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug(
            f"Updating Pulse alarm from {self._state} "
            f"to {ALARM_MAP[self._site.status]} for site {self._site.id}"
        )
        self._state = ALARM_MAP[self._site.status]
        self._data_from_fetch = True
        super()._handle_coordinator_update()

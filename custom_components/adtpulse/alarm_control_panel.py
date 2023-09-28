"""Support for ADT Pulse alarm control panels."""
from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import Coroutine

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_DISARMING,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyadtpulse.alarm_panel import (
    ADT_ALARM_ARMING,
    ADT_ALARM_AWAY,
    ADT_ALARM_DISARMING,
    ADT_ALARM_HOME,
    ADT_ALARM_OFF,
    ADT_ALARM_UNKNOWN,
)
from pyadtpulse.site import ADTPulseSite

from . import get_alarm_unique_id, get_gateway_unique_id
from .const import ADTPULSE_DATA_ATTRIBUTION, ADTPULSE_DOMAIN
from .coordinator import ADTPulseDataUpdateCoordinator

LOG = getLogger(__name__)

ALARM_MAP = {
    ADT_ALARM_ARMING: STATE_ALARM_ARMING,
    ADT_ALARM_AWAY: STATE_ALARM_ARMED_AWAY,
    ADT_ALARM_DISARMING: STATE_ALARM_DISARMING,
    ADT_ALARM_HOME: STATE_ALARM_ARMED_HOME,
    ADT_ALARM_OFF: STATE_ALARM_DISARMED,
    ADT_ALARM_UNKNOWN: None,
}

ALARM_ICON_MAP = {
    ADT_ALARM_AWAY: "mdi:shield-lock",
    ADT_ALARM_HOME: "mdi:shield-home",
    ADT_ALARM_OFF: "mdi:shield-off",
    ADT_ALARM_UNKNOWN: "mdi:shield-bug",
}


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up an alarm control panel for ADT Pulse."""
    coordinator: ADTPulseDataUpdateCoordinator = hass.data[ADTPULSE_DOMAIN][
        config.entry_id
    ]
    if not coordinator:
        LOG.error("ADT Pulse service not initialized, cannot setup alarm platform")
        return

    alarm_devices = [ADTPulseAlarm(coordinator, coordinator.adtpulse.site)]

    async_add_entities(alarm_devices)


class ADTPulseAlarm(
    CoordinatorEntity[ADTPulseDataUpdateCoordinator], alarm.AlarmControlPanelEntity
):
    """An alarm_control_panel implementation for ADT Pulse."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator, site: ADTPulseSite):
        """Initialize the alarm control panel."""
        LOG.debug(f"{ADTPULSE_DOMAIN}: adding alarm control panel for {site.id}")
        self._name = f"ADT {site.name}"
        self._site = site
        self._alarm = site.alarm_control_panel
        super().__init__(coordinator, self._name)

    @property
    def state(self) -> str:
        """Return the alarm status.

        Returns:
            str: the status
        """
        if self._alarm.status in ALARM_MAP:
            return ALARM_MAP[self._alarm.status]
        return STATE_UNAVAILABLE

    @property
    def attribution(self) -> str | None:
        """Return API data attribution."""
        return ADTPULSE_DATA_ATTRIBUTION

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self._alarm.status not in ALARM_ICON_MAP:
            return "mdi:shield-alert"
        return ALARM_ICON_MAP[self._alarm.status]

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
            | AlarmControlPanelEntityFeature.ARM_HOME
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info.

        We set the identifiers to the site id since it is unique across all sites
        and the zones can be identified by site id and zone name"""
        return DeviceInfo(
            identifiers={(ADTPULSE_DOMAIN, self._site.id)},
            manufacturer=self._alarm.manufacturer,
            model=self._alarm.model,
            via_device=(ADTPULSE_DOMAIN, get_gateway_unique_id(self._site)),
        )

    async def _perform_alarm_action(
        self, arm_disarm_func: Coroutine[bool | None, None, bool], action: str
    ) -> None:
        LOG.debug(f"{ADTPULSE_DOMAIN}: Setting Alarm to  {action}")
        if await arm_disarm_func:
            self.async_write_ha_state()
        else:
            LOG.warning(f"Could not {action} ADT Pulse alarm")

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._perform_alarm_action(self._site.async_disarm(), "disarm")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._perform_alarm_action(self._site.async_arm_home(), "arm home")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._perform_alarm_action(self._site.async_arm_away(), "arm away")

    # Pulse can arm away or home with bypass
    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Send force arm command."""
        await self._perform_alarm_action(
            self._site.async_arm_away(force_arm=True), "force arm"
        )

    @property
    def name(self) -> str:
        """Return the name of the alarm."""
        return self._name

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            # FIXME: add timestamp for this state change?
            "site_id": self._site.id,
            "last_update_time": datetime.fromtimestamp(self._alarm.last_update),
            "alarm_state": self._alarm.status,
        }

    @property
    def unique_id(self) -> str:
        """Return HA unique id.

        Returns:
            str: the unique id
        """
        return get_alarm_unique_id(self._site)

    @property
    def code_format(self) -> None:
        """Return code format.

        Returns:
            None (not implmented)
        """
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug(
            f"Updating Pulse alarm to "
            f"{ALARM_MAP[self._site.alarm_control_panel.status]} "
            f"for site {self._site.id}"
        )
        self.async_write_ha_state()

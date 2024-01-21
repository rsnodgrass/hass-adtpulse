"""ADT Pulse Entity Base class."""
from __future__ import annotations

from logging import getLogger
from typing import Any, Mapping

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync

from .const import ADTPULSE_DATA_ATTRIBUTION
from .coordinator import ADTPulseDataUpdateCoordinator

LOG = getLogger(__name__)


class ADTPulseEntity(CoordinatorEntity[ADTPulseDataUpdateCoordinator]):
    """Base Entity class for ADT Pulse devices."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator, name: str):
        """Initialize an ADTPulse entity.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator): update coordinator to use
            name (str): entity name
        """
        self._name = name
        # save references to commonly used objects
        self._pulse_connection: PyADTPulseAsync = coordinator.adtpulse
        self._site = self._pulse_connection.site
        self._gateway = self._site.gateway
        self._alarm = self._site.alarm_control_panel
        self._attrs: dict = {}
        super().__init__(coordinator)

    # Base level properties that can be overridden by subclasses
    @property
    def name(self) -> str | None:
        """Return the display name for this sensor.

        Should generally be none since using has_entity_name."""
        return None

    @property
    def has_entity_name(self) -> bool:
        """Returns has_entity_name.  Should generally be true."""
        return True

    @property
    def icon(self) -> str:
        """Return the mdi icon.

        Returns:
            str: mdi icon name
        """
        return "mdi:gauge"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the device state attributes."""
        return self._attrs

    @property
    def available(self) -> bool:
        """Returns whether an entity is available.

        Generally false if gateway is offline."""
        return self._gateway.is_online and self.coordinator.last_exception is None

    @property
    def attribution(self) -> str:
        """Return API data attribution."""
        return ADTPULSE_DATA_ATTRIBUTION

    @callback
    def _handle_coordinator_update(self) -> None:
        """Call update method."""
        LOG.debug("Scheduling update ADT Pulse entity %s", self._name)
        # inform HASS that ADT Pulse data for this entity has been updated
        self.async_write_ha_state()

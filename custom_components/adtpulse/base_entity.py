"""ADT Pulse Entity Base class."""
from __future__ import annotations

from typing import Dict, Optional

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import LOG
from .coordinator import ADTPulseDataUpdateCoordinator


class ADTPulseEntity(CoordinatorEntity[ADTPulseDataUpdateCoordinator]):
    """Base Entity class for ADT Pulse devices."""

    def __init__(
        self,
        coordinator: ADTPulseDataUpdateCoordinator,
        name: str,
        initial_state: Optional[str | bool],
    ):
        """Initialize an ADTPulse entity.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator): update coordinator to use
            name (str): entity name
            state (str): inital state
        """
        self._name = name

        self._state = initial_state
        self._attrs: Dict = {}
        super().__init__(coordinator)

    @property
    def name(self) -> str:
        """Return the display name for this sensor."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon.

        Returns:
            str: mdi icon name
        """
        return "mdi:gauge"

    @property
    def state(self) -> Optional[str | bool]:
        """Return the entity state.

        Returns:
            Optional[str|bool]: the entity state
        """
        return self._state

    @property
    def extra_state_attributes(self) -> Dict:
        """Return the device state attributes."""
        return self._attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Call update method."""
        LOG.debug(
            f"Scheduling ADT Pulse entity {self._name} " f"update to {self._state}"
        )
        # inform HASS that ADT Pulse data for this entity has been updated
        self.async_schedule_update_ha_state()

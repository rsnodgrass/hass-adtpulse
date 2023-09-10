"""ADT Pulse Update Coordinator."""
from __future__ import annotations

from asyncio import Task
from logging import getLogger
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import PyADTPulse
from .const import ADTPULSE_DOMAIN

LOG = getLogger(__name__)


class ADTPulseDataUpdateCoordinator(DataUpdateCoordinator):
    """Update Coordinator for ADT Pulse entities."""

    def __init__(self, hass: HomeAssistant, pulse_service: PyADTPulse):
        """Initialize Pulse data update coordinator.

        Args:
            hass (HomeAssistant): hass object
            pulse_site (ADTPulseSite): ADT Pulse site
        """
        LOG.debug(f"{ADTPULSE_DOMAIN}: creating update coordinator")
        self._adt_pulse = pulse_service
        self._push_wait_task: Task[None] | None = None
        super().__init__(hass, LOG, name=ADTPULSE_DOMAIN)

    @property
    def adtpulse(self) -> PyADTPulse:
        return self._adt_pulse

    async def stop(self, _: Any) -> None:
        if self._push_wait_task:
            self._push_wait_task.cancel()

    async def _async_update_data(self) -> None:
        self._push_wait_task = self.hass.async_create_background_task(
            self._pulse_push_task(), "ADT Pulse push wait task"
        )
        return None

    async def _pulse_push_task(self) -> None:
        while True:
            LOG.debug(f"{ADTPULSE_DOMAIN}: coordinator waiting for updates")
            await self._adt_pulse.wait_for_update()
            LOG.debug(f"{ADTPULSE_DOMAIN}: coordinator received update notification")
            self.async_set_updated_data(None)

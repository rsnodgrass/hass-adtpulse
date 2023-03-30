"""ADT Pulse Update Coordinator."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import PyADTPulse
from .const import ADTPULSE_DOMAIN, LOG


class ADTPulseDataUpdateCoordinator(DataUpdateCoordinator):
    """Update Coordinator for ADT Pulse entities."""

    def __init__(self, hass: HomeAssistant, pulse_service: PyADTPulse):
        """Initialize Pulse data update coordinator.

        Args:
            hass (HomeAssistant): hass object
            pulse_site (ADTPulseSite): ADT Pulse site
        """
        LOG.debug(f"{ADTPULSE_DOMAIN}: creating update coordinator")
        super().__init__(hass, LOG, name=ADTPULSE_DOMAIN)
        self._service = pulse_service

    async def _async_update_data(self) -> None:
        LOG.debug(f"{ADTPULSE_DOMAIN}: coordinator waiting for updates")
        await self._service.wait_for_update()
        LOG.debug(f"{ADTPULSE_DOMAIN}: coordinator received update notification")

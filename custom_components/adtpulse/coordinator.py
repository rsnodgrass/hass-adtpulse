"""ADT Pulse Update Coordinator."""
from __future__ import annotations

from logging import getLogger
from asyncio import Task
from time import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pyadtpulse.exceptions import (
    PulseExceptionWithBackoff,
    PulseExceptionWithRetry,
    PulseLoginException,
)
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync

from .const import ADTPULSE_DOMAIN

LOG = getLogger(__name__)


class ADTPulseDataUpdateCoordinator(DataUpdateCoordinator):
    """Update Coordinator for ADT Pulse entities."""

    def __init__(self, hass: HomeAssistant, pulse_service: PyADTPulseAsync):
        """Initialize Pulse data update coordinator.

        Args:
            hass (HomeAssistant): hass object
            pulse_site (ADTPulseSite): ADT Pulse site
        """
        LOG.debug("%s: creating update coordinator", ADTPULSE_DOMAIN)
        self._adt_pulse = pulse_service
        self._push_wait_task: Task[None] | None = None
        self._exception: Exception | None = None
        super().__init__(hass, LOG, name=ADTPULSE_DOMAIN)

    @property
    def adtpulse(self) -> PyADTPulseAsync:
        """Return the ADT Pulse service object."""
        return self._adt_pulse

    @property
    def last_exception(self) -> Exception | None:
        """Return the last exception."""
        return self._exception

    async def stop(self, _: Any) -> None:
        """Stop the update coordinator."""
        if self._push_wait_task:
            self._push_wait_task.cancel()

    async def _async_update_data(self) -> None:
        """Fetch data from ADT Pulse."""
        ce = self.config_entry
        if not ce:
            raise ConfigEntryNotReady
        self._push_wait_task = ce.async_create_background_task(
            self.hass, self._pulse_push_task(), "ADT Pulse push wait task"
        )
        if not self._push_wait_task:
            raise ConfigEntryNotReady
        next_refresh = 0
        try:
            await self._push_wait_task
        except PulseLoginException as ex:
            raise ConfigEntryAuthFailed from ex
        except PulseExceptionWithRetry as ex:
            self._exception = ex
            if ex.retry_time:
                next_refresh = ex.retry_time - time()
        except PulseExceptionWithBackoff as ex:
            self._exception = ex
            next_refresh = ex.backoff.get_current_backoff_interval()
        else:
            self._exception = None
        self.update_interval = next_refresh
        self._schedule_refresh()

    async def _pulse_push_task(self) -> None:
        while True:
            LOG.debug("%s: coordinator waiting for updates", ADTPULSE_DOMAIN)
            await self._adt_pulse.wait_for_update()
            LOG.debug("%s: coordinator received update notification", ADTPULSE_DOMAIN)
            self.async_set_updated_data(None)

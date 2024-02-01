"""ADT Pulse Update Coordinator."""

from __future__ import annotations

from logging import getLogger
from asyncio import CancelledError, Task

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
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
        self._update_task: Task | None = None
        super().__init__(
            hass,
            LOG,
            name=ADTPULSE_DOMAIN,
        )

    @property
    def adtpulse(self) -> PyADTPulseAsync:
        """Return the ADT Pulse service object."""
        return self._adt_pulse

    async def start(self) -> None:
        """Start ADT Pulse update coordinator.

        This doesn't really need to be async, but it is to yield the event loop.
        """
        if not self._update_task:
            ce = self.config_entry
            if ce:
                self._update_task = ce.async_create_background_task(
                    self.hass, self._async_update_data(), "ADT Pulse Data Update"
                )
            else:
                raise ConfigEntryNotReady

    async def stop(self):
        """Stop ADT Pulse update coordinator."""
        if self._update_task:
            if not self._update_task.cancelled():
                self._update_task.cancel()
            await self._update_task
            self._update_task = None

    async def _async_update_data(self) -> None:
        """Fetch data from ADT Pulse."""
        while not self._shutdown_requested and not self.hass.is_stopping:
            LOG.debug("%s: coordinator waiting for updates", ADTPULSE_DOMAIN)
            update_exception: Exception | None = None
            try:
                await self._adt_pulse.wait_for_update()
            except PulseLoginException as ex:
                # this should never happen
                LOG.error(
                    "%s: ADT Pulse login failed during coordinator update: %s",
                    ADTPULSE_DOMAIN,
                    ex,
                )
                if self.config_entry:
                    self.config_entry.async_start_reauth(self.hass)
                return
            except (PulseExceptionWithRetry, PulseExceptionWithBackoff) as ex:
                update_exception = ex
            except CancelledError:
                LOG.debug("%s: coordinator received cancellation", ADTPULSE_DOMAIN)
                return
            except Exception as ex:
                LOG.error(
                    "%s: coordinator received unknown exception %s, exiting...",
                    ADTPULSE_DOMAIN,
                    ex,
                )
                raise
            LOG.debug("%s: coordinator received update notification", ADTPULSE_DOMAIN)

            if update_exception:
                self.async_set_update_error(update_exception)
            else:
                self.async_set_updated_data(None)

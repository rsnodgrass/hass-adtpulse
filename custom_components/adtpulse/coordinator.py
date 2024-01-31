"""ADT Pulse Update Coordinator."""
from __future__ import annotations

from logging import getLogger
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import now
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
        super().__init__(
            hass, LOG, name=ADTPULSE_DOMAIN, update_interval=timedelta(seconds=0)
        )

    @property
    def adtpulse(self) -> PyADTPulseAsync:
        """Return the ADT Pulse service object."""
        return self._adt_pulse

    async def _async_update_data(self) -> None:
        """Fetch data from ADT Pulse."""
        LOG.debug("%s: coordinator waiting for updates", ADTPULSE_DOMAIN)
        next_check = 0
        update_exception: Exception | None = None
        try:
            await self._adt_pulse.wait_for_update()
        except PulseLoginException as ex:
            raise ConfigEntryAuthFailed from ex
        except PulseExceptionWithRetry as ex:
            update_exception = ex
            if ex.retry_time:
                next_check = max(ex.retry_time - now().timestamp(), 0)
        except PulseExceptionWithBackoff as ex:
            update_exception = ex
            next_check = ex.backoff.get_current_backoff_interval()
        except Exception as ex:
            raise UpdateFailed from ex
        LOG.debug("%s: coordinator received update notification", ADTPULSE_DOMAIN)
        if update_exception:
            self.async_set_update_error(update_exception)
        else:
            self.async_set_updated_data(None)
        if next_check != 0:
            LOG.debug(
                "%s: coordinator scheduling next update in %f seconds",
                ADTPULSE_DOMAIN,
                next_check,
            )
        self.update_interval = timedelta(seconds=next_check)

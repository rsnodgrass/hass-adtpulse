"""ADT Pulse Update Coordinator."""

from __future__ import annotations

import datetime
from logging import getLogger, DEBUG
from asyncio import CancelledError, Task
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback, CALLBACK_TYPE
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import as_local, utc_from_timestamp, utcnow
from pyadtpulse.exceptions import (
    PulseExceptionWithBackoff,
    PulseExceptionWithRetry,
    PulseLoginException,
)
from pyadtpulse.pyadtpulse_async import PyADTPulseAsync

from .const import ADTPULSE_DOMAIN

LOG = getLogger(__name__)

ALARM_CONTEXT = "alarm"
ZONE_CONTEXT_PREFIX = "Zone "
ZONE_TROUBLE_PREFIX = ZONE_CONTEXT_PREFIX + " Trouble"


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
        self._listener_dictionary: dict[str, CALLBACK_TYPE] = {}

    @property
    def adtpulse(self) -> PyADTPulseAsync:
        """Return the ADT Pulse service object."""
        return self._adt_pulse

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        """Listen for data updates."""
        self._listener_dictionary[context] = update_callback
        return super().async_add_listener(update_callback, context)

    @callback
    def async_update_listeners(self) -> None:
        """Update listeners based update returned data."""

        start_time = utcnow()
        if not self.data:
            super().async_update_listeners()
            LOG.debug(
                "%s: async_update_listeners took %s",
                ADTPULSE_DOMAIN,
                utcnow() - start_time,
            )
            return
        data_to_update: tuple[bool, set[int]] = self.data
        if data_to_update[0]:
            self._listener_dictionary[ALARM_CONTEXT]()
        for zones in data_to_update[1]:
            self._listener_dictionary[ZONE_CONTEXT_PREFIX + str(zones)]()
            self._listener_dictionary[
                ZONE_CONTEXT_PREFIX + str(zones) + ZONE_TROUBLE_PREFIX
            ]()
        LOG.debug(
            "%s: partial async_update_listeners took %s",
            ADTPULSE_DOMAIN,
            utcnow() - start_time,
        )

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
            data = None
            LOG.debug("%s: coordinator waiting for updates", ADTPULSE_DOMAIN)
            update_exception: Exception | None = None
            try:
                data = await self._adt_pulse.wait_for_update()
            except PulseLoginException as ex:
                LOG.error(
                    "%s: ADT Pulse login failed during coordinator update: %s",
                    ADTPULSE_DOMAIN,
                    ex,
                )
                if self.config_entry:
                    self.config_entry.async_start_reauth(self.hass)
                return
            except PulseExceptionWithRetry as ex:
                if ex.retry_time:
                    LOG.debug(
                        "%s: coordinator received retryable exception will retry at %s",
                        ADTPULSE_DOMAIN,
                        as_local(utc_from_timestamp(ex.retry_time)),
                    )
                update_exception = ex
            except PulseExceptionWithBackoff as ex:
                update_exception = ex
                LOG.debug(
                    "%s: coordinator received backoff exception, backing off for %s seconds",
                    ADTPULSE_DOMAIN,
                    ex.backoff.get_current_backoff_interval(),
                )
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
            finally:
                if update_exception:
                    self.async_set_update_error(update_exception)
                    # async_set_update_error will only notify listeners on first error
                    if not self.last_update_success:
                        self.async_update_listeners()
                else:
                    self.last_exception = None
                    self.async_set_updated_data(data)

            LOG.debug("%s: coordinator received update notification", ADTPULSE_DOMAIN)

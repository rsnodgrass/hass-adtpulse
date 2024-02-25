"""ADT Pulse sensors."""

from __future__ import annotations

from logging import getLogger
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import as_timestamp, now
from pyadtpulse.exceptions import (
    PulseAccountLockedError,
    PulseClientConnectionError,
    PulseExceptionWithBackoff,
    PulseExceptionWithRetry,
    PulseGatewayOfflineError,
    PulseServerConnectionError,
    PulseServiceTemporarilyUnavailableError,
    PulseAuthenticationError,
    PulseMFARequiredError,
    PulseNotLoggedInError,
)

from .base_entity import ADTPulseEntity
from .const import ADTPULSE_DOMAIN
from .coordinator import ADTPulseDataUpdateCoordinator
from .utils import get_gateway_unique_id

LOG = getLogger(__name__)

COORDINATOR_EXCEPTION_MAP: dict[type[Exception], tuple[str, str]] = {
    PulseAccountLockedError: ("Account Locked", "mdi:account-network-off"),
    PulseClientConnectionError: ("Client Connection Error", "mdi:network-off"),
    PulseServerConnectionError: ("Server Connection Error", "mdi:server-network-off"),
    PulseGatewayOfflineError: ("Gateway Offline", "mdi:cloud-lock"),
    PulseServiceTemporarilyUnavailableError: (
        "Service Temporarily Unavailable",
        "mdi:lan-pending",
    ),
    PulseAuthenticationError: ("Authentication Error", "mdi:account-alert"),
    PulseMFARequiredError: ("MFA Required", "mdi:account-reactivate"),
    PulseNotLoggedInError: ("Not Logged In", "mdi:account-off"),
}
CONNECTION_STATUS_OK = ("Connection OK", "mdi:hand-okay")
CONNECTION_STATUSES = list(COORDINATOR_EXCEPTION_MAP.values())
CONNECTION_STATUSES.append(CONNECTION_STATUS_OK)
CONNECTION_STATUS_STRINGS = [value[0] for value in CONNECTION_STATUSES]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for an ADT Pulse installation."""
    coordinator: ADTPulseDataUpdateCoordinator = hass.data[ADTPULSE_DOMAIN][
        entry.entry_id
    ]

    async_add_entities(
        [
            ADTPulseConnectionStatus(coordinator),
            ADTPulseNextRefresh(coordinator),
        ]
    )


class ADTPulseConnectionStatus(SensorEntity, ADTPulseEntity):
    """ADT Pulse connection status sensor."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator):
        """Initialize connection status sensor.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator):
                HASS data update coordinator
        """
        site_name = coordinator.adtpulse.site.id
        LOG.debug(
            "%s: adding connection status sensor for site %s",
            ADTPULSE_DOMAIN,
            site_name,
        )

        self._name = f"ADT Pulse Connection Status - Site: {site_name}"
        super().__init__(coordinator, self._name)

    @property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        return "Pulse Connection Status"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{self.coordinator.adtpulse.site.id}-connection-status"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True

    @property
    def device_class(self) -> str | None:
        """Return the class of this sensor."""
        return SensorDeviceClass.ENUM

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return CONNECTION_STATUS_STRINGS

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.last_exception:
            return CONNECTION_STATUS_OK[0]
        coordinator_exception = COORDINATOR_EXCEPTION_MAP.get(
            type(self.coordinator.last_exception), ("", "")
        )
        if coordinator_exception:
            return coordinator_exception[0]
        return None

    @property
    def icon(self) -> str:
        """Return the icon of this sensor."""
        if not self.coordinator.last_exception:
            return CONNECTION_STATUS_OK[1]
        coordinator_exception = COORDINATOR_EXCEPTION_MAP.get(
            type(self.coordinator.last_exception), ("", "")
        )
        if coordinator_exception:
            return coordinator_exception[1]
        return "mdi:alert-octogram"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        if self._gateway.serial_number:
            return DeviceInfo(
                identifiers={(ADTPULSE_DOMAIN, self._gateway.serial_number)},
            )
        return DeviceInfo(
            identifiers={(ADTPULSE_DOMAIN, get_gateway_unique_id(self._site))},
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug("Setting %s status to %s", self.name, self.native_value)
        self.async_write_ha_state()


class ADTPulseNextRefresh(SensorEntity, ADTPulseEntity):
    """ADT Pulse next refresh sensor."""

    def __init__(self, coordinator: ADTPulseDataUpdateCoordinator):
        """Initialize next refresh sensor.

        Args:
            coordinator (ADTPulseDataUpdateCoordinator):
                HASS data update coordinator
        """
        site_name = coordinator.adtpulse.site.id
        LOG.debug(
            "%s: adding next refresh sensor for site %s",
            ADTPULSE_DOMAIN,
            site_name,
        )

        self._name = f"ADT Pulse Next Refresh - Site: {site_name}"
        super().__init__(coordinator, self._name)

    @property
    def device_class(self) -> str | None:
        """Return the class of this sensor."""
        return SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        timediff = 0
        curr_time = now()
        last_ex = self.coordinator.last_exception
        if not last_ex:
            return None
        if isinstance(last_ex, PulseExceptionWithRetry):
            if last_ex.retry_time is None:
                return None
            timediff = last_ex.retry_time - as_timestamp(now())
        elif isinstance(last_ex, PulseExceptionWithBackoff):
            timediff = last_ex.backoff.get_current_backoff_interval()
        if timediff < 60:
            return None
        return curr_time + timedelta(seconds=timediff)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        if self._gateway.serial_number:
            return DeviceInfo(
                identifiers={(ADTPULSE_DOMAIN, self._gateway.serial_number)},
            )

        return DeviceInfo(
            identifiers={(ADTPULSE_DOMAIN, get_gateway_unique_id(self._site))},
        )

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{self.coordinator.adtpulse.site.id}-next-refresh"

    @property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        return "Pulse Next Refresh"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_exception is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        LOG.debug("Setting %s status to %s", self.name, self.native_value)
        self.async_write_ha_state()

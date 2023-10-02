"""HASS ADT Pulse Config Flow."""
from __future__ import annotations

from logging import getLogger
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_PUSH,
    ConfigEntry,
    ConfigFlow,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from pyadtpulse import PyADTPulse
from pyadtpulse.const import (
    ADT_DEFAULT_KEEPALIVE_INTERVAL,
    ADT_DEFAULT_POLL_INTERVAL,
    ADT_DEFAULT_RELOGIN_INTERVAL,
    ADT_MAX_KEEPALIVE_INTERVAL,
    ADT_MIN_RELOGIN_INTERVAL,
    API_HOST_CA,
    DEFAULT_API_HOST,
)
from pyadtpulse.site import ADTPulseSite

from .const import (
    ADTPULSE_DOMAIN,
    CONF_FINGERPRINT,
    CONF_HOSTNAME,
    CONF_KEEPALIVE_INTERVAL,
    CONF_RELOGIN_INTERVAL,
)

LOG = getLogger(__name__)


class PulseConfigFlow(ConfigFlow, domain=ADTPULSE_DOMAIN):  # type: ignore
    """Handle a config flow for ADT Pulse."""

    @staticmethod
    async def validate_input(data: dict[str, str]) -> dict[str, str]:
        """Validate form input.

        Args:
            hass (core.HomeAssistant): hass object
            data (Dict): voluptuous Schema

        Raises:
            CannotConnect: Cannot connect to ADT Pulse site
            InvalidAuth: login failed

        Returns:
            Dict[str, str | bool]: "title" : username used to validate
                                "login result": True if login succeeded
        """
        result = False
        adtpulse = PyADTPulse(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            data[CONF_FINGERPRINT],
            service_host=data[CONF_HOSTNAME],
            do_login=False,
        )
        try:
            result = await adtpulse.async_login()
            site: ADTPulseSite = adtpulse.site
            site_id = site.id
        except Exception as ex:
            LOG.error("ERROR VALIDATING INPUT")
            raise CannotConnect from ex
        finally:
            await adtpulse.async_logout()
        if not result:
            LOG.error("Could not validate login info for ADT Pulse")
            raise InvalidAuth("Could not validate ADT Pulse login info")
        return {"title": f"ADT: Site {site_id}"}

    @staticmethod
    def _get_data_schema(orig_input: dict[str, Any] | None) -> vol.Schema:
        DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(
                    CONF_FINGERPRINT,
                ): cv.string,
                vol.Required(
                    CONF_HOSTNAME,
                ): vol.In([DEFAULT_API_HOST, API_HOST_CA]),
            }
        )
        return DATA_SCHEMA

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> PulseOptionsFlowHandler:
        """Create the options flow."""
        return PulseOptionsFlowHandler(config_entry)

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_PUSH

    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step.

        Args:
            user_input (Optional[Dict[str, Any]], optional): user input.
                    Defaults to None.

        Returns:
            FlowResult: the flow result
        """
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
        errors = info = {}
        if user_input is not None:
            try:
                info = await self.validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOG.exception("Unexpected exception")
                errors["base"] = "unknown"
            if not errors:
                if not self._reauth_entry:
                    return super().async_create_entry(
                        title=info["title"], data=user_input
                    )
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, title=info["title"], data=user_input
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        # If there is no user input or there were errors, show the form again,
        # including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=self._get_data_schema(user_input), errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            orig_input = {}
            if self._reauth_entry is not None:
                orig_input = self._reauth_entry.data
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=self._get_data_schema(orig_input)
            )
        return await self.async_step_user(user_input)


class PulseOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle options flow for Pulse integration."""

    def _validate_options(self, options: dict[str, Any]) -> dict[str, Any]:
        """Validate options."""
        new_relogin = options.get(CONF_RELOGIN_INTERVAL, ADT_DEFAULT_RELOGIN_INTERVAL)
        new_keepalive = options.get(
            CONF_KEEPALIVE_INTERVAL, ADT_DEFAULT_KEEPALIVE_INTERVAL
        )
        if new_relogin != 0 and new_relogin < ADT_MIN_RELOGIN_INTERVAL:
            return {"base": "min_relogin"}
        if new_keepalive > ADT_MAX_KEEPALIVE_INTERVAL:
            return {"base": "max_keepalive"}
        return {"title": "Pulse Integration Options"}

    @staticmethod
    def _get_options_schema(original_input: dict[str, Any] | None) -> vol.Schema:
        if original_input is None:
            original_input = {}
        OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=original_input.get(
                        CONF_SCAN_INTERVAL, ADT_DEFAULT_POLL_INTERVAL
                    ),
                ): cv.positive_float,
                vol.Optional(
                    CONF_RELOGIN_INTERVAL,
                    default=original_input.get(
                        CONF_RELOGIN_INTERVAL, ADT_DEFAULT_RELOGIN_INTERVAL
                    ),
                ): cv.positive_int,
                vol.Optional(
                    CONF_KEEPALIVE_INTERVAL,
                    default=original_input.get(
                        CONF_KEEPALIVE_INTERVAL, ADT_DEFAULT_KEEPALIVE_INTERVAL
                    ),
                ): cv.positive_int,
            }
        )
        return OPTIONS_SCHEMA

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        result: dict[str, Any] | None = None
        if user_input is not None:
            result = self._validate_options(user_input)
            if result["title"] != "error":
                return self.async_create_entry(title=result["title"], data=user_input)
        else:
            user_input = self.options

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(user_input),
            errors=result,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

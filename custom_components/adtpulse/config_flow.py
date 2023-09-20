"""HASS ADT Pulse Config Flow."""
from __future__ import annotations

from logging import getLogger
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_PUSH,
    ConfigFlow,
    ConfigEntry,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from pyadtpulse import PyADTPulse
from pyadtpulse.const import (
    DEFAULT_API_HOST,
    API_HOST_CA,
    ADT_DEFAULT_POLL_INTERVAL,
    ADT_DEFAULT_RELOGIN_INTERVAL,
    ADT_DEFAULT_KEEPALIVE_INTERVAL,
)
from pyadtpulse.site import ADTPulseSite

from .const import (
    ADTPULSE_DOMAIN,
    CONF_FINGERPRINT,
    CONF_HOSTNAME,
    CONF_RELOGIN_INTERVAL,
    CONF_KEEPALIVE_INTERVAL,
)

LOG = getLogger(__name__)

class PulseConfigFlow(ConfigFlow, domain=ADTPULSE_DOMAIN):  # type: ignore
    """Handle a config flow for ADT Pulse."""

    @staticmethod
    async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> dict[str, str]:
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
    def _get_data_schema(previous_input: dict[str, Any] | None) -> vol.Schema:
        if previous_input is None:
            new_input = {}
        else:
            new_input = previous_input
        DATA_SCHEMA = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    description={
                        "Username for logging into ADT Pulse": new_input.get(CONF_USERNAME)
                    },
                ): cv.string,
                vol.Required(
                    CONF_PASSWORD,
                    description={
                        "Password for logging into ADT Pulse": new_input.get(CONF_PASSWORD)
                    },
                ): cv.string,
                vol.Required(
                    CONF_FINGERPRINT,
                    description={"Browser fingerprint", new_input.get(CONF_FINGERPRINT)},
                ): cv.string,
                vol.Required(
                    CONF_HOSTNAME,
                    description={
                        "ADT Pulse host": new_input.get(CONF_HOSTNAME, DEFAULT_API_HOST)
                    },
                ): vol.In([DEFAULT_API_HOST, API_HOST_CA]),
            }
        )
        return DATA_SCHEMA

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
        ) -> OptionsFlow:
        """Create the options flow."""
        return PulseOptionsFlowHandler(config_entry)

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_PUSH

    _reauth_entry: ConfigEntry | None = None

    # FIXME: this isn't being called for some reason
    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        new_config = {**import_config}
        if self.hass.data[CONF_HOST] is not None:
            new_config.update({CONF_HOSTNAME: self.hass.data[CONF_HOST]})
            new_config.pop(CONF_HOST)
        if self.hass.data[CONF_DEVICE_ID] is not None:
            new_config.update({CONF_FINGERPRINT: self.hass.data[CONF_DEVICE_ID]})
            new_config.pop(CONF_DEVICE_ID)
        return await self.async_step_user(new_config)

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
                info = await validate_input(self.hass, user_input)
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
                    self._reauth_entry, data=user_input
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        # If there is no user input or there were errors, show the form again,
        # including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=_get_data_schema(user_input), errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=_get_data_schema(None)
            )
        return await self.async_step_user(user_input)

    

class PulseOptionsFlowHandler(OptionsFlow):
    
    @staticmethod
    def _get_options_schema(previous_input: dict[str, Any] | None) -> vol.Schema:
        if previous_input is None:
            new_input = {}
        else:
            new_input = previous_input
        OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    description={
                        "How many seconds between background for update checks "
                        f" (default {ADT_DEFAULT_POLL_INTERVAL} seconds)": new_input.get(
                            CONF_SCAN_INTERVAL
                        )
                    },
                ): cv.small_float,
                vol.Optional(
                    CONF_RELOGIN_INTERVAL,
                    description={
                        "Number of minutes to relogin to Pulse "
                        f"(0 = disable, default {ADT_DEFAULT_RELOGIN_INTERVAL} minutes), "
                        "must be greater than keepalive interval": new_input.get(
                            CONF_PASSWORD
                        )
                    },
                ): cv.positive_int,
                vol.Optional(
                    CONF_KEEPALIVE_INTERVAL,
                    description={
                        "Number of minutes between keepalive checks "
                        f"(default {ADT_DEFAULT_KEEPALIVE_INTERVAL} minutes)",
                        new_input.get(CONF_FINGERPRINT),
                    },
                ): cv.positive_int,
            }
        )
        return OPTIONS_SCHEMA

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            relog_interval = user_input.get(CONF_RELOGIN_INTERVAL)
            keepalive_interval = user_input.get(CONF_KEEPALIVE_INTERVAL)
            if keepalive_interval is None:
                keepalive_interval = self._config_entry.options.get(CONF_KEEPALIVE_INTERVAL)
            if relog_interval is None:
                relog_interval = self._config_entry.options.get(CONF_RELOGIN_INTERVAL)
            if keepalive_interval is None:
                keepalive_interval = ADT_DEFAULT_KEEPALIVE_INTERVAL
            if relog_interval is None:
                relog_interval = ADT_DEFAULT_RELOGIN_INTERVAL

            if relog_interval > keepalive_interval:
                return self.async_create_entry(
                    title="Pulse Integration Options", data=user_input
                )

        return self.async_show_form(
            step_id="init", data_schema=self._get_options_schema(user_input))
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

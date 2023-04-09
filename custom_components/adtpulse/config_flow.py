"""HASS ADT Pulse Config Flow."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID
from homeassistant.core import callback
from pyadtpulse import PyADTPulse
from typing import Dict

from .const import ADTPULSE_DOMAIN, LOG

# This is the schema that used to display the UI to the user. This simple
# schema has a single required host field, but it could include a number of fields
# such as username, password etc. See other components in the HA core code for
# further examples.
# Note the input displayed to the user will be translated. See the
# translations/<lang>.json file and strings.json. See here for further information:
# https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#translations
# At the time of writing I found the translations created by the scaffold didn't
# quite work as documented and always gave me the "Lokalise key references" string
# (in square brackets), rather than the actual translated value. I did not attempt to
# figure this out or look further into it.
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_ID): str,
    }
)


async def validate_input(hass: core.HomeAssistant, data: Dict) -> Dict[str, str | bool]:
    """Validates form input.

    Args:
        hass (core.HomeAssistant): hass object
        data (Dict): voluptuous Schema

    Raises:
        CannotConnect: Cannot connect to ADT Pulse site

    Returns:
        Dict[str, str | bool]: "title" : username used to validate
                               "login result": True if login succeeded
    """
    result = False
    adtpulse = PyADTPulse(
        data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_DEVICE_ID], do_login=False
    )
    try:
        result = await adtpulse.async_login()
    except Exception:
        LOG.error("ERROR VALIDATING INPUT")
    if not result:
        LOG.error("Could not validate login info for ADT Pulse")
        raise CannotConnect("Could not validate ADT Pulse login info")
    return {"title": data[CONF_USERNAME], "login result": result}


class ConfigFlow(config_entries.ConfigFlow, domain=ADTPULSE_DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                if info["login result"]:
                    return self.async_create_entry(
                        title=info["title"],  # type:ignore
                        data=user_input,
                    )
                else:
                    errors["base"] = "Cannot validate credentials"
            except Exception:  # pylint: disable=broad-except
                LOG.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again,
        # including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
        )

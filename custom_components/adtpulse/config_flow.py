import logging

import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from pyadtpulse import PyADTPulse

from . import CannotConnect, async_connect_or_timeout
from .const import ( 
    CONF_PASSWORD,
    CONF_FINGERPRINT,
    CONF_USERNAME,
    ADTPULSE_DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    ADTPULSE_URL_US,
    ADTPULSE_URL_CA,
    CONF_HOSTNAME,
    CONF_POLLING,
)

from pyadtpulse.const import ADT_DEFAULT_HTTP_HEADERS, ADT_DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

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
        vol.Required(CONF_FINGERPRINT): str,
        vol.Required(CONF_HOSTNAME, default=ADTPULSE_URL_US): vol.In([ADTPULSE_URL_US, ADTPULSE_URL_CA]),
        vol.Required(CONF_POLLING, default=DEFAULT_SCAN_INTERVAL): str,
    }
)

async def validate_input(hass: core.HomeAssistant, data: dict):
    try:
        polling = 0
        try:
            polling = float(data[CONF_POLLING])
            if polling <= 0:
                _LOGGER.error(f"ADT Pulse: Invalid Polling Setting. Value that was provided was: {data[CONF_POLLING]}. Please select an integer greater than 0.")
                raise InvalidPolling
        except Exception as e:
            _LOGGER.error(f"ADT Pulse: Invalid Polling Setting. Value that was provided was: {data[CONF_POLLING]}. Please select an integer greater than 0.")
            _LOGGER.debug(e)
            raise InvalidPolling
        adtpulse = await hass.async_add_executor_job(PyADTPulse, data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_FINGERPRINT], data[CONF_HOSTNAME], ADT_DEFAULT_HTTP_HEADERS, None, True, polling, False)
    except Exception as e:
        _LOGGER.error(f"ADT Pulse: Cannot Connect. Please check your username, password, etc. Error was: {e}")
        raise CannotConnect

    info = await async_connect_or_timeout(hass, adtpulse)

    return {"title": "ADT: " + data[CONF_USERNAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=ADTPULSE_DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

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
                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidPolling:
                errors["base"] = "invalid_polling"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

async def async_connect_or_timeout(hass, adtpulse):
    #Need to add appropriate logic
    if adtpulse:
        _LOGGER.info("Valid Object continuing")

    else:
        _LOGGER.error("Error with ADT object (probably a connection issue)")
        raise CannotConnect

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidPolling(exceptions.HomeAssistantError):
    """Error to indicate polling is incorrect value."""


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
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLLING_RATE,
                        default=self.config_entry.options.get(
                            CONF_POLLING_RATE, DEFAULT_SCAN_INTERVAL
                        ),
                    ): str,
                }
            ),
        )



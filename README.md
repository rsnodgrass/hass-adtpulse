# ADT Pulse for Home Assistant (adtpulse)

***DEVELOPMENT ON THIS HAS STOPPED/PAUSED on a native HA ADT Pulse component: See [adt-pulse-mqtt](https://github.com/haruny/adt-pulse-mqtt) for a working solution (requires MQTT)***

A native Home Assistant component that automatically creates all Home Assistant sensors, switches
and alarms based on whatever is configured in [ADT Pulse](https://portal.adtpulse.com/).

# See Also

* [adt-pulse-mqtt](https://github.com/haruny/adt-pulse-mqtt) – comprehensive in supporting both ADT Pulse alarm panels as well as sense.
* [ADT Pulse integration for Home Assistant support community](https://community.home-assistant.io/t/adt-pulse-integration/10160/149)
* [ADT Pulse management portal](https://portal.adtpulse.com/)

# TODO

NOTE: Development is currently suspended on this. If someone would like to work on implementing this contact me a
as I may have time to help get this fully working, but my priorities are on other projects currently.

- automatically create an ADT Pulse alarm panel (alarm_control_panel/adtpulse.py)
- support multiple alarm systems configured within a single ADT Pulse account
- consider making this just an automatic adapter for [adt-pulse-mqtt] which auto-discovers all the sensors and populated Home Assistant with integration to the MQTT topics 

### Installation

To install, manually copy the adtpulse.py file into the binary_sensor folder
underneath your Home Assistant installation's custom_components folder.
For example, on hassio, this would need to be copied to:
<pre>/config/custom_components/sensor/adtpulse.py</pre>

It is recommended that you create a new separate ADT Pulse account login
for accessing the sensors as well as using the HASS !secret feature in
your configuration files.

Example configuration:
<pre>  binary_sensor:
    - platform: adtpulse:
      username: your_email.com
      password: your_adt_pulse_password</pre>

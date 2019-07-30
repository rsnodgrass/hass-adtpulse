# adtpulse (ADT Pulse for Home Assistant)

***DEVELOPMENT ON THIS HAS STOPPED/PAUSED on a native HA ADT Pulse component: See [adt-pulse-mqtt](https://github.com/haruny/adt-pulse-mqtt) for a working solution (requires MQTT)***

This adds a sensor for ADT Pulse alarm systems so that all the ADT
motion sensors and switches automatically appear in Home Assistant. This
automatically discovers the ADT sensors configured within Pulse and
exposes them into HA.

FUTURE WORK:
- create an ADT Pulse alarm panel (alarm_control_panel/adtpulse.py)
- As the MQTT version seems to be more comprehensive, this might be
  better to be an automatic adapter for the MQTT version to auto-discover
  all the sensors.

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

### See Also

* [adt-pulse-mqtt](https://github.com/haruny/adt-pulse-mqtt) – comprehensive in supporting both ADT Pulse alarm panels as well as sense.
* [ADT Pulse integration for Home Assistant support community](https://community.home-assistant.io/t/adt-pulse-integration/10160/149)

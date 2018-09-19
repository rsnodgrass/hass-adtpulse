# adtpulse

This adds ADT Pulse sensor support to Home Assistant, automatically
exposing to Home Assistant all sensors that are configured with a
Pulse account.

### Installation

To install, you must manually copy the adtpulse.py file into your
custom_components folder, for example on Mac:

 <pre>  ~/.homeassistant/custom_components/sensor/adtpulse.py
 </pre>

It is recommended that you create a new separate ADT Pulse account login
for accessing the sensors as well as using the HASS !secret feature in
your configuration files.

### Configuration

Example configuration:

<pre>binary_sensor:
  - platform: adtpulse:
    username: your@email.com
    password: password
</pre>

### TODO

* Create an ADT Pulse alarm panel alarm_control_panel/adtpulse.py
* Support events whenever a change in state is detected for one of the sensors
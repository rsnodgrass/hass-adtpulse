# adtpulse

This adds support for ADT Pulse sensors to Home Assistant, automatically
exposing to HA all sensors that are configured within the specified Pulse
account.

Currently this only reads the current state of the sensors by polling the
ADT Pulse site, however eventually this should support notificatons upon
state changes of sensors.

### Installation

To install, you must manually copy the adtpulse.py file into your
custom_components folder, for example on HassOS:

'''
/config/custom_components/binary_sensor/adtpulse.py
'''

It is recommended that you create a new separate ADT Pulse account login
for accessing the sensors as well as using the HASS !secret feature in
your configuration files.

### Configuration

Example configuration:

'''
binary_sensor:
  - platform: adtpulse:
    username: your_email.com
    password: password
'''

### See Also

* adt-pulse-mqtt:  https://github.com/haruny/adt-pulse-mqtt
  Seems to be comprehense in supporting both ADT Pulse alarm panels as well as sense.
* https://community.home-assistant.io/t/adt-pulse-integration/10160/149

### FUTURE

* Create an ADT Pulse alarm panel alarm_control_panel/adtpulse.py
* Support events whenever a change in state is detected for one of the sensors

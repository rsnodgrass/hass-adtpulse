## 0.3.2 (2023-10-08)

Alarm control panel updates:
* update alarm capabilities based upon existing state of alarm
* disable setting alarm to existing state
* add arming/disarming icons
* add assumed state
* remove site id from attributes
* raise HomeAssistant exception on alarm set failure
* write ha state even if alarm action fails

## 0.3.1 (2023-10-07)

* fix typo in manifest preventing install

## 0.3.0 (2023-10-07)

* bump pyadtpulse to 1.1.2
* add options flow for poll interval, relogin interval, keepalive interval
* add reauth config flow
* change code owner to rlippmann
* add gateway and alarm devices

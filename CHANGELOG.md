## 0.4.6 (2024-04-21)

* add arm night
* bump pyadtpulse to 1.2.9
  This should fix some more instances where it is needed to recover from errors/disconnects
  
## 0.4.5 (2024-04-04)

* bump minimum HA version to 2024.04.0
* fix import of FlowResult

## 0.4.4 (2024-03-06)

* update connection status and next update sensors on successful data fetch
* bump pyadtpulse to 1.2.8 which should provide better error logging and more stability for failures from Pulse site

## 0.4.3 (2024-03-02)

* fix not updating when exception is raised
* change glass break type to sound binary sensor

## 0.4.2 (2024-02-25)

* use default Home Assistant icons where possible
* remove gateway serial number/site id from gateway name

## 0.4.1 (2024-02-24)

* bump pyadtpulse to 1.2.7.
  This will:
  * perform a full re-login approximately every 6 hours
  * speed up zone and alarm update times
  * allow Home Assistant to just refresh updated zones/alarm instead all all entities
  * fix various "you have not logged in yet" errors
* have connection status show authentication errors
* correctly handle coordinator update authentication errors to perform configuration reauthentication flow

## 0.4.0 (2024-02-02)

* bump pyadtpulse to 1.2.0.  This should provide more robust error handling and stability
* add connection status and next update sensors
* remove quick re-login service

## 0.3.5 (2023-12-22)

* bump pyadtpulse to 1.1.5 to fix more changes in Pulse v27

## 0.3.4 (2023-12-13)

* bump pyadtpulse to 1.1.4 to fix changes in Pulse V27

## 0.3.3 (2023-10-12)

* bump pyadtpulse to 1.1.3.  This should fix alarm not updating issue
* add force stay and force away services
* add relogin service
* refactor code to use base entity.  This should cause most entities to become unavailable if the gateway goes offline
* disallow invalid alarm state changes
* revert alarm card functionality.  All states will be available, but exceptions will be thrown if an invalid state is requested.

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

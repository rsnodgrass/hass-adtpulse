# ADT Pulse for Home Assistant

A native Home Assistant component to enable integration with [ADT Pulse](https://portal.adtpulse.com/) security systems for both alarming/disarming, as well as current status of all sensors (motion, door/window).

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/v/release/rsnodgrass/hass-adtpulse.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-adtpulse.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/DYks67r)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

## THIS IS NOT SUPPORTED!

NOTE: *Since this uses ADT's Pulse cloud service, which is not real-time, there are delays detecting state changes to panels, sensors, switches. This delay is based on the refresh_interval you have configured (default is 5 seconds). This package works fine for standard security panel interactions, as well as motion/door sensor status updates, in most cases where "real time" latency is not an issue.

This platform supports the following services:

* `alarm_arm_away`
* `alarm_arm_home`
* `alarm_disarm`

## WARNING: ADT Accounts with 2FA May Not Work

As of August 29, 2021 ADT Pulse has had 2FA added. This breaks any integration that relies on logging in with a user and password. However, the following is a workaround from `@mrholshi`:

*Create an additional "service" account user and give that account access to your site. This can be used as long as that "service" account does not op-in to 2FA in either the Pulse app or portal. Login using the Pulse web portal to set up the security question. This account can only log in the first time to set security questions, since any login after that will prompt to set up 2FA.*

## Installation

If you have trouble with installation and configuration, visit the [ADT Pulse Home Assistant community discussion](https://community.home-assistant.io/t/adt-pulse-integration/10160/).

### Step 1: Install Custom Components

Make sure that [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) is installed and then add the "Integration" repository: *rsnodgrass/hass-adtpulse*.

Note: Manual installation by direct download and copying is not supported, if you have issues, please first try installing this integration with HACS.

### Step 2: Configure ADT Pulse

To enable ADT Pulse, add the following to your configuration.yaml:

```yaml
adtpulse:
  username: your@email.com
  password: your_password
```

Additionally, for Canada ADT Pulse customers, the ADT Pulse service host is configurable:

```yaml
adtpulse:
  host: portal-ca.adtpulse.com
```

For accounts that have 2FA enabled, there is an alternative solution by setting the optional setting below. The option below uses the "trusted device" option that ADT provides so that you can bypass 2FA.

```yaml
adtpulse:
  device_id: SOMEUNIQUEDEVICEID
```

#### Step to Get Your Trusted Device
1. Go to the ADT Pulse Login page but do not login.
2. Open up the developer tools for your browser and make sure you enable the network capturing option and recording is enabled
3. Login to your account
4. If the device isn't trusted, it will prompt you for a code, afterwards you will be asked if you want to trust the device. Give it a name and click Save and Continue.

![ADT Save Device](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_save_device.jpg?raw=true)

5. Open up the developer tools and look for the page called "signin.jsp". Under the form data, look for "fingerprint". Copy that value and use it for the device_id value in your configuration.yaml file. If for some reason you didn't record, just re-login to your account again with the same browser.

![ADT Form Data](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_form_data.jpg?raw=true)

## Lovelace

#### Sensors

![Lovelace Example](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_motion_status.png?raw=true)

Current status of motion detectors:

```yaml
entities:
  - entity: binary_sensor.entry_motion
    name: Entry
  - entity: binary_sensor.office_motion
    name: Office
  - entity: binary_sensor.kids_room_motion
    name: Kid's Area
  - entity: binary_sensor.garage_motion
    name: Garage
type: glance
title: Motion Sensors
show_header_toggle: false
```

![Lovelace Example](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_motion_history.png?raw=true)

Motion detected history:

```yaml
entities:
  - entity: binary_sensor.entry_motion
    name: Entry
  - entity: binary_sensor.office_motion
    name: Office
  - entity: binary_sensor.kids_room_motion
    name: Kid's Area
  - entity: binary_sensor.garage_motion
    name: Garage
title: Motion History
type: history-graph
hours_to_show: 2
```

Door status:

```yaml
entities:
  - label: House
    type: section
  - entity: binary_sensor.front_door
    name: Front Door
  - entity: binary_sensor.office_door
    name: Office Door
  - entity: binary_sensor.garage_door
    name: Garage Door
type: entities
show_header_toggle: false
```

#### Alarm Panel

Using [Home Assistant's built-in Alarm Panel Card](https://www.home-assistant.io/lovelace/alarm-panel/):

![Lovelace Example](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_alarm_panel.png?raw=true)

```yaml
type: alarm-panel
entity: alarm_control_panel.adt_pulse
states:
  - arm_away
  - arm_home
```

## Automation Example

```yaml
automation:
  - alias: "Alarm: Disarmed Daytime"
    trigger:
      platform: state
      entity_id: alarm_control_panel.your_adt_alarm
      to: 'disarmed'
    condition:
      condition: sun
      before: sunset
    action:
      service: lights.turn_on
  - alias: "Alarm: Armed Away"
    trigger:
      platform: state
      entity_id: alarm_control_panel.your_adt_alarm
      to: 'armed_away'
    action:
      service: lights.turn_off
```

## See Also

* [ADT Pulse Home Assistant support community](https://community.home-assistant.io/t/adt-pulse-integration/10160/)
* [pyadtpulse](https://github.com/rsnodgrass/pyadtpulse)
* [adt-pulse-mqtt](https://github.com/haruny/adt-pulse-mqtt)
* [ADT Pulse management portal](https://portal.adtpulse.com/)

## TODO

* add notification when alarm is triggered and when alarm end

## Support

This integration was developed to cover use cases for my home integration, which I wanted to contribute to the community. Additional features beyond what has already been provided are the responsibility of the community to implement (unless trivial to add). 

### Not Supported

No plans to implement support for the following (however, feel free to contribute):

* Home Assistant config flow (would be nice to add)
* ADT Pulse cameras, lighting and dimmers

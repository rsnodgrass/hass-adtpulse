# ADT Pulse for Home Assistant

A native Home Assistant component to enable integration with [ADT Pulse](https://portal.adtpulse.com/) security systems for both alarming/disarming, as well as current status of all sensors (motion, door/window).

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/v/release/rsnodgrass/hass-adtpulse.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-adtpulse.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

This platform supports the following services:

* `alarm_arm_away`
* `alarm_arm_home`
* `alarm_disarm`

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

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)

This integration was developed to cover use cases for my home integration, which I wanted to contribute to the community. Additional features beyond what has already been provided are the responsibility of the community to implement (unless trivial to add). 

### Not Supported

No plans to implement support for the following (however, feel free to contribute):

* ADT Pulse cameras, lighting and dimmers

# ADT Pulse for Home Assistant

A native Home Assistant component to enable integration with [ADT Pulse](https://portal.adtpulse.com/) security systems for both alarming/disarming, as well as current status of all sensors (motion, door/window).

This platform supports the following services: alarm_arm_away, alarm_arm_home, and alarm_disarm.

## Installation

If you have trouble with installation and configuration, visit the [ADT Pulse Home Assistant community discussion](https://community.home-assistant.io/t/adt-pulse-integration/10160/).

### Step 1: Install Custom Components

Easiest is by setting up [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) and then adding the "Integration" repository: *rsnodgrass/hass-adtpulse*. However you can also manually copy all the files in [custom_components/adtpulse/](https://github.com/rsnodgrass/hass-adtpulse/custom_components/adtpulse) directory to `/config/custom_components/adtpulse` on your Home Assistant installation.

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

### Not Supported

No plans to implement support for the following (however, feel free to contribute):

* ADT Pulse cameras, lighting and dimmers

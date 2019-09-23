# ADT Pulse for Home Assistant

A native Home Assistant component to enable integration with [ADT Pulse](https://portal.adtpulse.com/) security systems for both alarming/disarming, as well as current status of all sensors (motion, door/window).

## Installation

If you have trouble with installation and configuration, visit the [ADT Pulse Home Assistant community discussion](https://community.home-assistant.io/t/adt-pulse-integration/10160/204).

### Step 1: Install Custom Components

Easiest is by setting up [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) and then adding the "Integration" repository: *rsnodgrass/hass-sensorpush*. However you can also manually copy all the files in [custom_components/adtpulse/](https://github.com/rsnodgrass/hass-adtpulse/custom_components/adtpulse) directory to `/config/custom_components/adtpulse` on your Home Assistant installation.

### Step 2: Configure ADT Pulse

Example configuration.yaml entry:

```yaml
adtpulse:
  username: your@email.com
  password: your_password

alarm_control_panel:
  - platform: adtpulse

binary_sensors:
  - platform: adtpulse
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
    name: Kid's Rom
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
  - entity: binary_sensor.south_warehouse_motion
    name: Ryan's Side
  - entity: binary_sensor.north_warehouse_motion
    name: Ron's Side
  - entity: binary_sensor.north_office_motion
    name: Office
  - entity: binary_sensor.south_office_motion
    name: Kid's Area
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

## See Also

* [adt-pulse-mqtt](https://github.com/haruny/adt-pulse-mqtt)
* [ADT Pulse integration for Home Assistant support community](https://community.home-assistant.io/t/adt-pulse-integration/10160/)
* [ADT Pulse management portal](https://portal.adtpulse.com/)

## Not Supported

No plans to implement support for the following (however, feel free to contribute):

* ADT Pulse cameras, lighting and dimmers

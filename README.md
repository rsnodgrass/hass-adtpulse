# ADT Pulse for Home Assistant

Home Assistant integration for [ADT Pulse](https://portal.adtpulse.com/) security systems for both alarming/disarming, as well as sensor status (motion, door, window, etc).

![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png)
![release_badge](https://img.shields.io/github/v/release/rsnodgrass/hass-adtpulse.svg)
![release_date](https://img.shields.io/github/release-date/rsnodgrass/hass-adtpulse.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/DYks67r)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=WREP29UDAMB6G)


## THIS IS NOT SUPPORTED

NOTE: \*Since this uses ADT's Pulse cloud service, which is not real-time, there are delays detecting state changes to panels, sensors, switches. This delay should be minimal as the integration will be pushed the data from ADT Pulse's cloud service when updates are detected. This package works fine for standard security panel interactions, as well as motion/door sensor status updates, in most cases where "real time" latency is not an issue.

This platform supports the following services:

* `alarm_arm_away`
* `alarm_arm_home`
* `alarm_disarm`
* `alarm_arm_custom_bypass`


## WARNING: ADT Accounts with 2FA May Not Work

As of August 29, 2021 ADT Pulse has had 2FA added and is currently required for all ADT Pulse access. This breaks any integration that relies on logging in with a user and password.  Because of this, a separate username/password should be created exclusively for Home Assistant login.  A browser fingerprint is used by Pulse to indicate when a user "saves" the browser via 2FA.  Details on obtaining this fingerprint is given below.



## Installation

If you have trouble with installation and configuration, visit the [ADT Pulse Home Assistant community discussion](https://community.home-assistant.io/t/adt-pulse-integration/10160/).

### Step 1: Install Custom Components

Make sure that [Home Assistant Community Store (HACS)](https://github.com/custom-components/hacs) is installed and then add the "Integration" repository: *rsnodgrass/hass-adtpulse*.

Note: Manual installation by direct download and copying is not supported, if you have issues, please first try installing this integration with HACS.

### Step 2: Configure ADT Pulse

**NOTE: As of April 2023, the ADT Pulse integration now can be configured via a config flow!**

To enable ADT Pulse, add the following integration like any other integration in HA. Input the necessary details including username, password, fingerprint (please see the below step "Step to Get Your Trusted Device") and select the URL and frequency for updates.

#### Step to Get Your Trusted Device

**<ins>Important:</ins>** If you are logged into ADT Pulse with the same fingerprint, the first login will be logged out when the second login is attempted.  For this reason it is recommended that you not use the same machine/browser that you would normally use for logging into Pulse when you generate the fingerprint.

1. Go to the ADT Pulse Login page but do not login.
2. Open up the developer tools for your browser and make sure you enable the network capturing option and recording is enabled
3. Login to your account.
4. If the device isn't trusted, it will prompt you for a code, afterwards you will be asked if you want to trust the device. Give it a name and click Save and Continue.

![ADT Save Device](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_save_device.jpg?raw=true)

5. Get the fingerprint. There are 2 ways to do this:

   - Using the same browser you used to authenticate with ADT Pulse, navigate to [this page](https://rawcdn.githack.com/rlippmann/pyadtpulse/b3a0e7097e22446623d170f0a971726fbedb6a2d/doc/browser_fingerprint.html) It will show you the browser fingerprint and allow you to copy it to your clipboard. If this doesn't work, try the next step.

   - Open up the developer tools and look for the page called "signin.jsp". Under the form data, look for "fingerprint". Copy that value and use it for the device_id value in your configuration.yaml file. If for some reason you didn't record, just re-login to your account again with the same browser.

![ADT Form Data](https://github.com/rsnodgrass/hass-adtpulse/blob/master/docs/adt_form_data.jpg?raw=true)


## Options

This integration supports the following options:

* `poll interval`: How often to poll ADT Pulse for updates (in seconds) - default 0.75
* `keepalive interval`: How often to keep the connection alive (in minutes) - default 5
* `relogin interval`: How often to re-authenticate with ADT Pulse (in minutes) - default 120

`poll interval` will determine how quickly Home Assistant will receive updates from ADT Pulse.  The Pulse website does this in the background multiple times per second, so setting the poll interval less than a second should be fine.  Of course, this will generate more network traffic from your Home Assistant instance to the internet.

`keepalive interval` will determine how often a background call to ADT pulse to keep the connection alive will be made.  This is performed by the ADT site to automatically log out after a set time period if the user is inactive.  The default of 5 minutes should be fine, but it can be increased if needed, probably to no more than 10 minutes.  The minimum value is 1 minute, the maximum is 15 minutes.

`relogin interval` will determine how often a background call to ADT pulse will be made to re-authenticate with ADT Pulse.  The ADT servers stop responding automatically after a set time period, even if the user is still active.  This attempts to work around this issue.  The default of 120 minutes should be fine, but it can be changed if needed, probably to no more than 180 minutes. The minimum value is 20 minutes.  Frequently re-authenticating with ADT Pulse more than the default is probably not a good idea, but hasn't been tested.

## Devices

The integration provides the following devices:
* `Alarm Panel`
* `Gateway`
* `Sensors for each zone`:  These include 2 entities, one for the sensor status (i.e. Open, Closed, etc).  This sensor is named binary_sensor.{zone_name}.  The other entity is for a trouble code (i.e. low battery, tamper, etc). Trouble sensors are named binary_sensor.trouble_sensor_{zone name}

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
  - arm_custom_bypass
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
* https://github.com/mrjackyliang/homebridge-adt-pulse

## TODO

* add notification when alarm is triggered and when alarm end

## Support

This integration was developed to cover use cases for my home integration, which I wanted to contribute to the community. Additional features beyond what has already been provided are the responsibility of the community to implement (unless trivial to add).

### Not Supported

No plans to implement support for the following (however, feel free to contribute):

~~* Home Assistant config flow (would be nice to add)~~
 * ADT Pulse cameras, lighting and dimmers


# Credits

* Huge thanks to [Richard Lippmann / rlippmann@](https://github.com/rlippmann). During 2023-2024 Richard made major contributions to pyadtpulse to support async behavior, including switching Home Assistant integration to fully use the async mechanism.
* [Ryan Snodgrass](https://github.com/rsnodgrass) for originally contributing a skeleton and initial working implementation to have a Home Assistant integration.

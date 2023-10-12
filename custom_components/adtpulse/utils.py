"""ADT Pulse utility functions."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.util import slugify
from pyadtpulse.const import STATE_OK, STATE_ONLINE
from pyadtpulse.site import ADTPulseSite
from pyadtpulse.zones import ADTPulseZoneData

from .const import ADTPULSE_DOMAIN


def migrate_entity_name(
    hass: HomeAssistant, site: ADTPulseSite, platform_name: str, entity_uid: str
) -> None:
    """Migrate old entity names."""
    registry = entity_registry.async_get(hass)
    if registry is None:
        return
    # this seems backwards
    entity_id = registry.async_get_entity_id(
        platform_name,
        ADTPULSE_DOMAIN,
        entity_uid,
    )
    if entity_id is not None:
        # change has_entity_name to True and set name to None for devices
        registry.async_update_entity(entity_id, has_entity_name=True, name=None)
        # rename site name to site id for entities which have site name
        slugified_site_name = slugify(site.name)
        if slugified_site_name in entity_id:
            registry.async_update_entity(
                entity_id, new_entity_id=entity_id.replace(slugified_site_name, site.id)
            )


def get_gateway_unique_id(site: ADTPulseSite) -> str:
    """Get entity unique id for the gateway."""
    return f"adt_pulse_gateway_{site.id}"


def get_alarm_unique_id(site: ADTPulseSite) -> str:
    """Get entity unique ID for alarm."""
    return f"adt_pulse_alarm_{site.id}"


def zone_open(zone: ADTPulseZoneData) -> bool:
    """Determine if a zone is opened."""
    return not zone.state == STATE_OK


def zone_trouble(zone: ADTPulseZoneData) -> bool:
    """Determine if a zone is in trouble state."""
    return not zone.status == STATE_ONLINE


def system_can_be_armed(site: ADTPulseSite) -> bool:
    """Determine is the system is able to be armed without being forced."""
    zones = site.zones_as_dict
    if zones is None:
        return False
    for zone in zones.values():
        if zone_open(zone) or zone_trouble(zone):
            return False
    return True

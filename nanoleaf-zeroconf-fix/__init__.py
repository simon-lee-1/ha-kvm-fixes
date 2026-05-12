"""Nanoleaf integration — custom override to prevent Zeroconf host update.

When running HA behind KVM NAT, Nanoleaf devices advertise IPv6 ULA addresses
via Zeroconf/mDNS. The built-in integration updates the config entry host on
every discovery event, overwriting the reachable IPv4 with an unreachable IPv6.

This custom component overrides only the config_flow to suppress that update.
All other functionality delegates to the built-in integration.
"""

from homeassistant.components.nanoleaf import (
    async_setup_entry,
    async_unload_entry,
)

__all__ = ["async_setup_entry", "async_unload_entry"]

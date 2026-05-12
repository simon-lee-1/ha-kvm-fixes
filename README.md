# Home Assistant on KVM/libvirt — Fixes & Workarounds

Workarounds for running Home Assistant OS on KVM/libvirt with NAT networking.

## The Problem

HAOS on KVM typically runs behind a NAT bridge (`virbr0` at `192.168.122.0/24`). This breaks several things that work out of the box on bare metal or bridged networking:

- **UDP broadcast** — VM can't send broadcasts to the LAN
- **mDNS/Zeroconf** — Multicast doesn't cross NAT boundaries
- **UPnP callbacks** — Devices can't reach the VM directly
- **Port access** — LAN devices can't reach HA web UI or MQTT

## Recommended Network Setup

Use dual interfaces on the VM:

| Interface | Mode | Purpose |
|-----------|------|---------|
| enp1s0 | NAT (virbr0) | Primary IPv4, host↔VM communication |
| enp7s0 | macvtap (passthrough) | IPv6 only, Matter/mDNS multicast |

**Do NOT enable IPv4 on the macvtap interface** — it causes routing conflicts and breaks host WiFi.

---

## Fixes

### 1. Port Forwarding (`libvirt-hooks/`)

DNAT rules that forward host LAN ports to the NAT'd VM, making HA reachable from LAN devices.

**Forwards:** 8123 (HA web), 1883 (MQTT)

```bash
sudo cp libvirt-hooks/qemu /etc/libvirt/hooks/qemu
sudo chmod +x /etc/libvirt/hooks/qemu
sudo systemctl restart libvirtd
```

Edit `GUEST_IP` and `HOST_IFACE` to match your setup.

### 2. Tuya UDP Wake (`tuya-udp-wake/`)

Some Tuya devices (especially Aubess smart plugs) put their TCP server to sleep unless they receive periodic UDP discovery broadcasts. The VM can't send these broadcasts through NAT.

This service runs on the **host** and broadcasts wake packets every 30s.

```bash
sudo cp tuya-udp-wake/tuya-udp-wake.service /etc/systemd/system/
# Edit ExecStart path and INTERFACE in tuya_wake.py
sudo systemctl daemon-reload
sudo systemctl enable --now tuya-udp-wake
```

### 3. KVM CPU Fix (`kvm/`)

Disable halt_poll to reduce idle CPU from ~30% to ~10%.

```bash
sudo cp kvm/kvm.conf /etc/modprobe.d/kvm.conf
# Reboot or: sudo modprobe -r kvm_intel && sudo modprobe kvm_intel
```

### 4. Nanoleaf Zeroconf Fix (`nanoleaf-zeroconf-fix/`)

Nanoleaf devices advertise IPv6 ULA addresses via Zeroconf. On every HA boot, discovery overwrites the config entry host from a reachable IPv4 to an unreachable IPv6 (can't route through NAT).

This custom component overrides `config_flow.py` to suppress host updates from Zeroconf discovery.

```bash
# Copy to HA custom_components (via SSH addon or samba)
scp -r nanoleaf-zeroconf-fix/ root@<ha-ip>:/config/custom_components/nanoleaf/
# Restart HA
```

**After HA updates:** Verify the re-exported files (`light.py`, `button.py`, `event.py`, `coordinator.py`) still match the built-in integration's API.

### 5. Cast Integration — known_hosts

For Chromecast/Cast devices that can't be discovered via mDNS through NAT, add their IPs to the Cast integration config:

**Settings → Integrations → Google Cast → Configure → Known hosts: `["192.168.51.236"]`**

### 6. Sonos — REST Bridge on Host

The native Sonos integration relies on UPnP callbacks that can't cross NAT. Run a REST bridge on the host with `--net=host`:

```bash
sudo docker run -d --name sonos-api --restart always --net=host \
  chrisns/docker-node-sonos-http-api
```

Then use HA REST commands targeting `http://192.168.122.1:5005` (host's virbr0 IP from VM's perspective).

---

## Topology

```
LAN (192.168.51.0/24)
  │
  ├── Host (192.168.51.10) ← WiFi
  │     │
  │     ├── virbr0 NAT (192.168.122.1)
  │     │     └── HA VM (192.168.122.12)
  │     │
  │     ├── tuya-udp-wake (broadcasts to LAN)
  │     ├── sonos-api docker (--net=host)
  │     └── iptables DNAT (8123, 1883)
  │
  ├── IoT devices (Tuya, Broadlink, Nanoleaf...)
  └── Phones/tablets (access HA via host:8123)
```

## License

MIT

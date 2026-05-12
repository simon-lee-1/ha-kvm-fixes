#!/usr/bin/env python3
"""Send periodic UDP broadcast on Tuya discovery ports to keep devices' TCP servers alive.

The HA VM is behind NAT (192.168.122.0/24) and cannot send UDP broadcasts to the
LAN. Some Tuya devices (especially Aubess smart plugs) put their TCP server
(port 6668) to sleep unless they receive periodic UDP discovery packets.
This service runs on the host to bridge that gap.
"""

import socket
import time
import sys

# --- Configuration ---
BROADCAST_ADDR = "255.255.255.255"
TUYA_PORTS = [6666, 6667]
INTERFACE = "wlp58s0"  # Host's LAN interface (WiFi or ethernet)
INTERVAL = 30  # seconds between broadcasts

# Minimal Tuya discovery message (enough to wake sleeping devices)
MSG = b'{"from":"app","ip":"192.168.51.10"}'


def send_wake():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, INTERFACE.encode())
    sock.settimeout(2)
    for port in TUYA_PORTS:
        try:
            sock.sendto(MSG, (BROADCAST_ADDR, port))
        except Exception as e:
            print(f"Error sending to port {port}: {e}", file=sys.stderr)
    sock.close()


def main():
    print(f"Tuya UDP wake service started (interval={INTERVAL}s)", flush=True)
    while True:
        send_wake()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

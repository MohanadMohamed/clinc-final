"""Validate a deployment plan without changing network or service settings."""

import argparse
import ipaddress
import re
import tomllib
from pathlib import Path, PureWindowsPath


def validate(path):
    with Path(path).open("rb") as stream:
        data = tomllib.load(stream)
    required = {
        "hostname",
        "listen_address",
        "https_port",
        "reception_addresses",
        "public_origin",
        "postgres_listen_addresses",
        "certificate",
        "private_key",
    }
    if set(data) != required:
        raise ValueError(
            "Unexpected or missing plan fields; secrets do not belong here"
        )
    hostname = data["hostname"]
    if not isinstance(hostname, str) or not re.fullmatch(
        r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", hostname
    ):
        raise ValueError("A stable lowercase DNS hostname is required")
    port = data["https_port"]
    if type(port) is not int or not 1024 <= port <= 65535 or port == 5432:
        raise ValueError("Use a dedicated unprivileged HTTPS port")
    peers = data["reception_addresses"]
    if not isinstance(peers, list) or not peers:
        raise ValueError("Explicit receptionist address allowlist required")
    for value in [data["listen_address"], *peers]:
        address = ipaddress.ip_address(value)
        if (
            address.version != 4
            or not any(
                address in ipaddress.ip_network(network)
                for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
            )
            or address.is_unspecified
            or address.is_multicast
            or address.is_loopback
            or address.is_link_local
        ):
            raise ValueError("Use reserved private LAN IPv4 addresses")
    if data["listen_address"] in peers or len(peers) != len(set(peers)):
        raise ValueError("Doctor and receptionist reservations must be distinct")
    if data["public_origin"] != f"https://{hostname}:{port}":
        raise ValueError(
            "Origin must exactly match the canonical HTTPS hostname and port"
        )
    if data["postgres_listen_addresses"] != "127.0.0.1,::1":
        raise ValueError("PostgreSQL must bind exclusively to loopback")
    for name in ("certificate", "private_key"):
        if not PureWindowsPath(data[name]).is_absolute():
            raise ValueError("TLS paths must be absolute Windows paths")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    args = parser.parse_args()
    validate(args.plan)
    print("PASS: non-secret LAN plan parsed; no machine configuration changed")

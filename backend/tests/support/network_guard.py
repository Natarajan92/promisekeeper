"""Loopback-only TCP/DNS guard shared by pytest and offline Python children."""
import ipaddress
import socket


def install(set_attribute=setattr):
    def allowed(host):
        if isinstance(host, bytes):
            host = host.decode("ascii")
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    connect, connect_ex, getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def guard_connect(sock, address):
        if isinstance(address, tuple) and not allowed(address[0]):
            raise RuntimeError("External networking is blocked in offline tests")
        return connect(sock, address)

    def guard_connect_ex(sock, address):
        if isinstance(address, tuple) and not allowed(address[0]):
            raise RuntimeError("External networking is blocked in offline tests")
        return connect_ex(sock, address)

    def guard_resolve(host, *args, **kwargs):
        if host is not None and not allowed(host):
            raise RuntimeError("External networking is blocked in offline tests")
        return getaddrinfo(host, *args, **kwargs)

    set_attribute(socket.socket, "connect", guard_connect)
    set_attribute(socket.socket, "connect_ex", guard_connect_ex)
    set_attribute(socket, "getaddrinfo", guard_resolve)

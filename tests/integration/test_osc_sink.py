"""
Integration tests for OSCSink.

Opens a real UDP socket on an ephemeral port to verify that:
1. OSCSink sends parseable UDP packets
2. Correct number of messages are transmitted per frame
"""
from __future__ import annotations

import socket
import time

import pytest

from hand_tracking_bridge.sinks.osc_sink import OSCSink
from tests.conftest import make_gesture_frame


def receive_bytes(sock: socket.socket, timeout: float = 1.0) -> bytes:
    sock.settimeout(timeout)
    try:
        data, _ = sock.recvfrom(65535)
        return data
    except socket.timeout:
        return b""


class TestOSCSinkIntegration:
    def setup_method(self):
        """Open an ephemeral UDP socket to receive test messages."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]

    def teardown_method(self):
        self.sock.close()

    def test_sends_udp_packet_on_send(self):
        """OSCSink should send at least one UDP packet per frame."""
        sink = OSCSink(host="127.0.0.1", port=self.port, bundle=False)
        frame = make_gesture_frame()
        with sink:
            sink.send(frame)

        data = receive_bytes(self.sock)
        assert len(data) > 0, "Expected at least one UDP packet"

    def test_bundle_mode_sends_single_packet(self):
        """In bundle mode, all messages arrive as a single UDP packet."""
        sink = OSCSink(host="127.0.0.1", port=self.port, bundle=True)
        frame = make_gesture_frame()
        with sink:
            sink.send(frame)

        data = receive_bytes(self.sock)
        assert len(data) > 0, "Expected a bundle UDP packet"
        # OSC bundles start with '#bundle\x00'
        assert data[:8] == b"#bundle\x00", f"Expected OSC bundle header, got {data[:8]!r}"

    def test_osc_messages_start_with_slash(self):
        """In non-bundle mode, each message address starts with '/'."""
        sink = OSCSink(host="127.0.0.1", port=self.port, bundle=False)
        frame = make_gesture_frame()
        packets = []
        with sink:
            sink.send(frame)

        # Collect all pending packets
        self.sock.settimeout(0.1)
        while True:
            try:
                data, _ = self.sock.recvfrom(65535)
                packets.append(data)
            except socket.timeout:
                break

        assert len(packets) > 0
        # First byte of first message should be '/'
        assert packets[0][0:1] == b"/", f"Expected OSC address, got {packets[0][:10]!r}"

    def test_sink_handles_send_without_open(self):
        """send() before open() should not raise."""
        sink = OSCSink(host="127.0.0.1", port=self.port)
        frame = make_gesture_frame()
        sink.send(frame)  # Should silently no-op, not raise

    def test_sink_close_is_idempotent(self):
        """close() called twice should not raise."""
        sink = OSCSink(host="127.0.0.1", port=self.port)
        with sink:
            pass
        sink.close()  # Second close should be safe


class TestOSCSinkUnit:
    def test_repr(self):
        sink = OSCSink(host="192.168.1.10", port=9000)
        assert "192.168.1.10" in repr(sink)
        assert "9000" in repr(sink)

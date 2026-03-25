"""
OSC output sink — transmits gesture data via UDP to TouchDesigner (or any OSC host).

OSC address scheme:
  /hand/{hand_index}/present        int  0 or 1
  /hand/{hand_index}/wrist/x        float [0, 1]
  /hand/{hand_index}/wrist/y        float [0, 1]
  /hand/{hand_index}/pinch          float [0, 1]
  /hand/{hand_index}/openness       float [0, 1]
  /hand/{hand_index}/gesture        str   e.g. "fist"
  /hand/{hand_index}/palm/roll      float radians
  /hand/{hand_index}/palm/pitch     float radians
  /hand/{hand_index}/palm/yaw       float radians
  /hand/{hand_index}/velocity/x     float
  /hand/{hand_index}/velocity/y     float
  /hand/{hand_index}/finger/{name}  float [0, 1] per-finger flexion
"""
from __future__ import annotations

import logging
from typing import Optional

from pythonosc import udp_client
from pythonosc.osc_bundle_builder import OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
import pythonosc.osc_bundle_builder as bundle_builder_module

from hand_tracking_bridge.gestures.types import GestureFrame
from hand_tracking_bridge.sinks.base import OutputSink

logger = logging.getLogger(__name__)


class OSCSink(OutputSink):
    """
    Sends gesture data as OSC messages over UDP.

    When bundle=True (default), all messages for a single frame are sent
    as a single OscBundle for atomic delivery. This prevents TouchDesigner
    from seeing a partial update where, say, wrist/x has been updated but
    pinch has not yet.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7000,
        bundle: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.bundle = bundle
        self._client: Optional[udp_client.SimpleUDPClient] = None

    def open(self) -> None:
        self._client = udp_client.SimpleUDPClient(self.host, self.port)
        logger.info("OSCSink: transmitting to %s:%d", self.host, self.port)

    def send(self, frame: GestureFrame) -> None:
        if self._client is None:
            return
        try:
            if self.bundle:
                self._send_bundle(frame)
            else:
                self._send_individual(frame)
        except Exception as exc:
            logger.warning("OSCSink: send error: %s", exc)

    def _send_bundle(self, frame: GestureFrame) -> None:
        builder = OscBundleBuilder(bundle_builder_module.IMMEDIATELY)
        for hand in frame.hands:
            prefix = f"/hand/{hand.hand_index}"
            msgs = [
                (f"{prefix}/present",      int(hand.present)),
                (f"{prefix}/wrist/x",      hand.wrist_x),
                (f"{prefix}/wrist/y",      hand.wrist_y),
                (f"{prefix}/pinch",        hand.pinch),
                (f"{prefix}/openness",     hand.openness),
                (f"{prefix}/gesture",      hand.discrete_gesture),
                (f"{prefix}/palm/roll",    hand.palm_roll),
                (f"{prefix}/palm/pitch",   hand.palm_pitch),
                (f"{prefix}/palm/yaw",     hand.palm_yaw),
                (f"{prefix}/velocity/x",   hand.velocity_x),
                (f"{prefix}/velocity/y",   hand.velocity_y),
            ]
            for finger in hand.fingers:
                msgs.append((f"{prefix}/finger/{finger.name}", finger.flexion))

            for address, value in msgs:
                msg = OscMessageBuilder(address=address)
                msg.add_arg(value)
                builder.add_content(msg.build())

        bundle = builder.build()
        self._client._sock.sendto(bundle.dgram, (self._client._address, self._client._port))

    def _send_individual(self, frame: GestureFrame) -> None:
        for hand in frame.hands:
            prefix = f"/hand/{hand.hand_index}"
            self._client.send_message(f"{prefix}/present",    int(hand.present))
            self._client.send_message(f"{prefix}/wrist/x",    hand.wrist_x)
            self._client.send_message(f"{prefix}/wrist/y",    hand.wrist_y)
            self._client.send_message(f"{prefix}/pinch",      hand.pinch)
            self._client.send_message(f"{prefix}/openness",   hand.openness)
            self._client.send_message(f"{prefix}/gesture",    hand.discrete_gesture)
            self._client.send_message(f"{prefix}/palm/roll",  hand.palm_roll)
            self._client.send_message(f"{prefix}/palm/pitch", hand.palm_pitch)
            self._client.send_message(f"{prefix}/palm/yaw",   hand.palm_yaw)
            self._client.send_message(f"{prefix}/velocity/x", hand.velocity_x)
            self._client.send_message(f"{prefix}/velocity/y", hand.velocity_y)
            for finger in hand.fingers:
                self._client.send_message(f"{prefix}/finger/{finger.name}", finger.flexion)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client._sock.close()
            except Exception:
                pass
            self._client = None
        logger.info("OSCSink: closed")

    def __repr__(self) -> str:
        return f"OSCSink(host={self.host!r}, port={self.port})"

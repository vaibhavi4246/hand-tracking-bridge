"""
Abstract base class for all gesture output sinks.

Adding a new output target (MIDI, DMX, file, network) requires only:
1. Subclass OutputSink
2. Implement open(), send(), close()
3. Register it in cli.py build_sinks()

No pipeline changes needed — Open/Closed Principle in practice.
"""
from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hand_tracking_bridge.gestures.types import GestureFrame


class OutputSink(abc.ABC):
    """
    Abstract interface for all gesture data output targets.

    Lifecycle:
        with sink:           # calls open()
            sink.send(frame) # transmit data, called from DispatcherThread
        # calls close() on exit
    """

    @abc.abstractmethod
    def open(self) -> None:
        """Initialize connection or resources. Called once before pipeline starts."""

    @abc.abstractmethod
    def send(self, frame: "GestureFrame") -> None:
        """
        Transmit gesture data.
        Must be thread-safe — called from DispatcherThread.
        Implementations should not block for more than ~5ms.
        """

    @abc.abstractmethod
    def close(self) -> None:
        """Release all resources. Called on shutdown."""

    def __enter__(self) -> "OutputSink":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

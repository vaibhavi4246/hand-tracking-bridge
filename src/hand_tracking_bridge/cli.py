"""
CLI entry point for Hand Tracking Bridge.

After `pip install -e .`, run:
    hand-tracker                          # defaults: OSC → localhost:7000
    hand-tracker --osc-port 9000
    hand-tracker --dashboard              # also starts web dashboard at :8000
    hand-tracker --ws                     # also starts WebSocket server at :8765
    hand-tracker --record session.jsonl   # record gesture data
    hand-tracker --playback session.jsonl # replay without webcam
    hand-tracker --calibrate              # run calibration wizard
    hand-tracker --no-osc                 # disable OSC (useful with --dashboard)
"""
from __future__ import annotations

import argparse
import logging
import queue
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

from hand_tracking_bridge.config import (
    AppConfig,
    CalibrationConfig,
    CaptureConfig,
    DashboardConfig,
    InferenceConfig,
    OSCConfig,
    RecordingConfig,
    VisualizationConfig,
    WebSocketConfig,
)
from hand_tracking_bridge.sinks.base import OutputSink


def build_sinks(config: AppConfig) -> List[OutputSink]:
    """Instantiate and open configured output sinks."""
    from hand_tracking_bridge.sinks.osc_sink import OSCSink
    from hand_tracking_bridge.sinks.file_sink import FileSink

    sinks: List[OutputSink] = []

    if config.osc.enabled:
        sink = OSCSink(host=config.osc.host, port=config.osc.port, bundle=config.osc.bundle)
        sink.open()
        sinks.append(sink)

    if config.websocket.enabled:
        try:
            from hand_tracking_bridge.sinks.websocket_sink import WebSocketSink
            sink = WebSocketSink(host=config.websocket.host, port=config.websocket.port)
            sink.open()
            sinks.append(sink)
        except ImportError:
            logging.warning("WebSocket sink requires 'websockets' package. Skipping.")

    if config.recording.enabled:
        sink = FileSink(path=config.recording.path)
        sink.open()
        sinks.append(sink)

    if config.dashboard.enabled:
        from hand_tracking_bridge.sinks.dashboard_sink import DashboardSink
        sink = DashboardSink()
        sink.open()
        sinks.append(sink)

    return sinks


def run_pipeline(config: AppConfig, playback_path: Optional[Path] = None) -> None:
    """Build and run the full pipeline until shutdown."""
    from hand_tracking_bridge.pipeline.capture import CaptureThread
    from hand_tracking_bridge.pipeline.inference import InferenceThread
    from hand_tracking_bridge.pipeline.dispatcher import DispatcherThread
    from hand_tracking_bridge.pipeline.visualization import Visualizer

    shutdown = threading.Event()
    frame_queue: queue.Queue = queue.Queue(maxsize=2)
    gesture_queue: queue.Queue = queue.Queue(maxsize=4)
    viz_queue: queue.Queue = queue.Queue(maxsize=1)

    sinks = build_sinks(config)

    # Load calibration profile if requested
    calibration_profile = None
    if config.calibration.enabled and not config.calibration.profile_name == "none":
        try:
            from hand_tracking_bridge.calibration.calibrator import AutoCalibrator
            calibration_profile = AutoCalibrator.load_profile(
                config.calibration.profile_name,
                config.calibration.profiles_dir,
            )
            logging.info("Loaded calibration profile: %s", config.calibration.profile_name)
        except FileNotFoundError:
            logging.warning("Calibration profile '%s' not found. Using defaults.",
                            config.calibration.profile_name)

    threads: List[threading.Thread] = []

    if playback_path:
        from hand_tracking_bridge.playback.player import PlaybackThread
        producer = PlaybackThread(
            recording_path=playback_path,
            gesture_queue=gesture_queue,
            shutdown=shutdown,
        )
    else:
        producer = CaptureThread(frame_queue, shutdown, config.capture)
        inference = InferenceThread(
            frame_queue, gesture_queue, viz_queue, shutdown,
            config.inference, calibration_profile,
        )
        threads.append(inference)

    dispatcher = DispatcherThread(gesture_queue, sinks, shutdown)
    threads.append(producer)
    threads.append(dispatcher)

    for t in threads:
        t.start()

    # Optional: start web dashboard
    if config.dashboard.enabled:
        _start_dashboard(config.dashboard)

    visualizer: Optional[Visualizer] = None
    if config.visualization.show_window and not playback_path:
        visualizer = Visualizer(viz_queue, title=config.visualization.window_title)

    logging.info("Hand Tracking Bridge running. Press 'q' in window or Ctrl+C to stop.")

    try:
        while not shutdown.is_set():
            if visualizer:
                if not visualizer.render():
                    break
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Shutting down...")
        shutdown.set()
        for t in threads:
            t.join(timeout=3.0)
        for sink in sinks:
            try:
                sink.close()
            except Exception:
                pass
        if visualizer:
            visualizer.close()
        logging.info("Shutdown complete.")


def _start_dashboard(config: DashboardConfig) -> None:
    """Start the FastAPI dashboard in a background thread."""
    try:
        import uvicorn
        from hand_tracking_bridge.dashboard.server import create_app
        app = create_app()
        server_config = uvicorn.Config(
            app, host=config.host, port=config.port, log_level="warning"
        )
        server = uvicorn.Server(server_config)
        t = threading.Thread(target=server.run, name="DashboardThread", daemon=True)
        t.start()
        logging.info("Dashboard: http://%s:%d", config.host, config.port)
    except ImportError:
        logging.warning("Dashboard requires 'fastapi' and 'uvicorn'. Skipping.")


def run_calibration(config: AppConfig) -> None:
    """Run the interactive calibration wizard."""
    from hand_tracking_bridge.calibration.calibrator import run_calibration_wizard
    run_calibration_wizard(config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hand-tracker",
        description="Real-time hand tracking bridge: MediaPipe → OSC / WebSocket / File",
    )

    # OSC
    osc = parser.add_argument_group("OSC output")
    osc.add_argument("--osc-host", default="127.0.0.1", metavar="HOST")
    osc.add_argument("--osc-port", type=int, default=7000, metavar="PORT")
    osc.add_argument("--no-osc", action="store_true", help="Disable OSC output")
    osc.add_argument("--no-bundle", action="store_true", help="Send individual OSC messages")

    # WebSocket
    ws = parser.add_argument_group("WebSocket output")
    ws.add_argument("--ws", action="store_true", help="Enable WebSocket server")
    ws.add_argument("--ws-host", default="0.0.0.0", metavar="HOST")
    ws.add_argument("--ws-port", type=int, default=8765, metavar="PORT")

    # Recording / playback
    rec = parser.add_argument_group("Recording / Playback")
    rec.add_argument("--record", metavar="FILE", help="Record gestures to JSONL file")
    rec.add_argument("--playback", metavar="FILE", help="Replay a recorded JSONL file")
    rec.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier")

    # Dashboard
    dash = parser.add_argument_group("Web Dashboard")
    dash.add_argument("--dashboard", action="store_true", help="Enable web dashboard")
    dash.add_argument("--dashboard-port", type=int, default=8000, metavar="PORT")

    # Camera
    cam = parser.add_argument_group("Camera")
    cam.add_argument("--camera", type=int, default=0, metavar="INDEX")
    cam.add_argument("--fps", type=int, default=30, metavar="FPS")
    cam.add_argument("--width", type=int, default=1280)
    cam.add_argument("--height", type=int, default=720)

    # Inference
    inf = parser.add_argument_group("Inference")
    inf.add_argument("--smoother", choices=["ema", "one_euro"], default="one_euro")
    inf.add_argument("--ema-alpha", type=float, default=0.7)

    # Calibration
    cal = parser.add_argument_group("Calibration")
    cal.add_argument("--calibrate", action="store_true", help="Run calibration wizard")
    cal.add_argument("--profile", default="default", metavar="NAME",
                     help="Calibration profile name to load/save")

    # Misc
    parser.add_argument("--no-window", action="store_true", help="Disable visualization window")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    return parser.parse_args()


def args_to_config(args: argparse.Namespace) -> AppConfig:
    return AppConfig(
        capture=CaptureConfig(
            camera_index=args.camera,
            width=args.width,
            height=args.height,
            target_fps=args.fps,
        ),
        inference=InferenceConfig(
            smoother=args.smoother,
            ema_alpha=args.ema_alpha,
        ),
        osc=OSCConfig(
            enabled=not args.no_osc,
            host=args.osc_host,
            port=args.osc_port,
            bundle=not args.no_bundle,
        ),
        websocket=WebSocketConfig(
            enabled=args.ws,
            host=args.ws_host,
            port=args.ws_port,
        ),
        recording=RecordingConfig(
            enabled=bool(args.record),
            path=Path(args.record) if args.record else Path("recordings/session.jsonl"),
        ),
        dashboard=DashboardConfig(
            enabled=args.dashboard,
            port=args.dashboard_port,
        ),
        calibration=CalibrationConfig(
            enabled=bool(args.profile),
            profile_name=args.profile,
        ),
        visualization=VisualizationConfig(
            show_window=not args.no_window,
        ),
        log_level=args.log_level,
    )


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = args_to_config(args)

    if args.calibrate:
        run_calibration(config)
        return

    playback_path = Path(args.playback) if args.playback else None
    run_pipeline(config, playback_path=playback_path)


if __name__ == "__main__":
    main()

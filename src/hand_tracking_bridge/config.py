"""
Structured application configuration using Pydantic v2.

All settings have sensible defaults and can be overridden via:
  1. Direct instantiation (programmatic use)
  2. CLI flags (parsed in cli.py and merged here)
  3. Environment variables with HTB_ prefix (Pydantic v2 feature)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    from pydantic import BaseModel, Field, field_validator
    from pydantic_settings import BaseSettings
    _PYDANTIC_SETTINGS = True
except ImportError:
    from pydantic import BaseModel, Field, field_validator
    _PYDANTIC_SETTINGS = False
    BaseSettings = BaseModel  # fallback


class CaptureConfig(BaseModel):
    camera_index: int = Field(default=0, ge=0, description="Webcam device index")
    width: int = Field(default=1280, ge=320)
    height: int = Field(default=720, ge=240)
    target_fps: int = Field(default=30, ge=1, le=120)


class InferenceConfig(BaseModel):
    max_num_hands: int = Field(default=2, ge=1, le=2)
    min_detection_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    min_tracking_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    # "ema" or "one_euro"
    smoother: str = Field(default="one_euro")
    ema_alpha: float = Field(default=0.7, ge=0.01, le=1.0)
    one_euro_min_cutoff: float = Field(default=0.5, gt=0.0)
    one_euro_beta: float = Field(default=0.01, ge=0.0)


class OSCConfig(BaseModel):
    enabled: bool = True
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=7000, ge=1024, le=65535)
    bundle: bool = True  # send as OscBundle for atomic delivery


class WebSocketConfig(BaseModel):
    enabled: bool = False
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8765, ge=1024, le=65535)


class RecordingConfig(BaseModel):
    enabled: bool = False
    path: Path = Field(default=Path("recordings/session.jsonl"))


class DashboardConfig(BaseModel):
    enabled: bool = False
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000, ge=1024, le=65535)


class CalibrationConfig(BaseModel):
    enabled: bool = False
    profile_name: str = Field(default="default")
    profiles_dir: Path = Field(default=Path("calibration_profiles"))
    warmup_frames: int = Field(default=90, ge=10)


class VisualizationConfig(BaseModel):
    show_window: bool = True
    window_title: str = "Hand Tracking Bridge"


class SoundConfig(BaseModel):
    enabled: bool = False


class AppConfig(BaseModel):
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    osc: OSCConfig = Field(default_factory=OSCConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    recording: RecordingConfig = Field(default_factory=RecordingConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    sound: SoundConfig = Field(default_factory=SoundConfig)
    log_level: str = Field(default="INFO")


def default_config() -> AppConfig:
    return AppConfig()

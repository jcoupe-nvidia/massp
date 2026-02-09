"""Build WS baseline as WAES with AES disabled (deadlines forced to zero)."""

from __future__ import annotations

from src.build_waes import WAESModel, build_waes_model
from src.instance import InstanceData


def build_ws_model(instance: InstanceData) -> WAESModel:
    """WS baseline builder (paper: WAES with deadlines set to zero)."""
    return build_waes_model(instance=instance, ws_mode=True)


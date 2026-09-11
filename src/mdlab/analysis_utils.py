from __future__ import annotations

import numpy as np


def trajectory_times_from_log(log, time_column: str, n_frames: int) -> np.ndarray:
    times = np.asarray(log[time_column], dtype=float)
    if len(times) != n_frames:
        raise RuntimeError(
            f"Thermodynamic rows ({len(times)}) do not match trajectory frames ({n_frames})"
        )
    if not np.isfinite(times).all():
        raise RuntimeError("Trajectory time values are not finite")
    return times

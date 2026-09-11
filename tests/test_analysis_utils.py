from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mdlab.analysis_utils import trajectory_times_from_log


def test_trajectory_times_come_from_thermodynamic_log():
    log = pd.DataFrame({"Time (ps)": [82.0, 84.0, 86.0]})

    times = trajectory_times_from_log(log, "Time (ps)", 3)

    np.testing.assert_array_equal(times, [82.0, 84.0, 86.0])


def test_trajectory_times_require_one_row_per_frame():
    log = pd.DataFrame({"Time (ps)": [82.0, 84.0]})

    with pytest.raises(RuntimeError, match="do not match"):
        trajectory_times_from_log(log, "Time (ps)", 3)

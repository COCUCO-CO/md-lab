import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase1_analyze import cumulative_displacement_magnitudes, passes_maximum


def test_passes_maximum_returns_json_serializable_bool():
    result = passes_maximum(np.float64(0.25), 1.0)

    assert type(result) is bool
    assert json.loads(json.dumps({"pass": result})) == {"pass": True}


def test_cumulative_displacement_uses_minimum_image():
    xyz_nm = np.array([[[0.95, 0.0, 0.0]], [[0.05, 0.0, 0.0]], [[0.15, 0.0, 0.0]]])
    box_lengths_nm = np.ones((3, 3))

    displacement = cumulative_displacement_magnitudes(xyz_nm, box_lengths_nm)

    np.testing.assert_allclose(displacement, [0.2])

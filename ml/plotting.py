"""ML_01 / ML_02 · salida gráfica reproducible con textos en español."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sipde-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ml.common import FIGURES_DIR


def save_figure(figure: plt.Figure, filename: str) -> Path:
    """INT_03: guarda a 150 dpi y libera la figura."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / filename
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)
    return path

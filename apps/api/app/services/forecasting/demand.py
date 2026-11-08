"""Demand-pattern classification (Syntetos-Boylan) to choose between model families.

ADI = average interval between non-zero demands; CV² = squared coefficient of variation of the
non-zero demand sizes. Cut-offs 1.32 and 0.49 are the published ones.
"""

from collections.abc import Sequence
from statistics import mean, pstdev

ADI_CUT = 1.32
CV2_CUT = 0.49


def classify(series: Sequence[float]) -> dict[str, float | str | None]:
    nonzero = [x for x in series if x > 0]
    if len(nonzero) < 2:
        return {"pattern": "insufficient", "adi": None, "cv2": None}
    adi = len(series) / len(nonzero)
    m = mean(nonzero)
    cv2 = (pstdev(nonzero) / m) ** 2 if m else 0.0
    if adi < ADI_CUT:
        pattern = "smooth" if cv2 < CV2_CUT else "erratic"
    else:
        pattern = "intermittent" if cv2 < CV2_CUT else "lumpy"
    return {"pattern": pattern, "adi": round(adi, 3), "cv2": round(cv2, 3)}


def stockout_suspects(series: Sequence[float], min_run: int = 5) -> list[tuple[int, int]]:
    """Zero runs of at least ``min_run`` days inside a series that otherwise sells often.

    These may be stock-outs rather than zero demand, so models should treat them with care.
    Returns (start, length) pairs.
    """
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(series):
        if series[i] == 0:
            j = i
            while j < len(series) and series[j] == 0:
                j += 1
            if j - i >= min_run and i > 0 and j < len(series):  # interior runs only
                runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs

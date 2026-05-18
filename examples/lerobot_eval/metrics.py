"""Trajectory metrics for the lerobot_eval demo."""

import numpy as np


def rmse(actions: np.ndarray) -> float:
    """RMSE of frame-to-frame action differences (smoothness proxy).

    No external reference trajectory is available for lerobot/pusht's
    recorded actions, so we use the self-difference as a smoothness
    signal: smaller deltas between consecutive frames -> smoother control.
    Constant trajectory -> 0.0.
    """
    diffs = np.diff(actions, axis=0)
    return float(np.sqrt(np.mean(diffs ** 2)))


def jerk(actions: np.ndarray) -> float:
    """Sum of |third-order differences| across joints and time.

    Discrete-time proxy for the integral of |d^3 x / dt^3|. Linear ramps
    have zero jerk; smooth curves have low jerk; jagged trajectories
    have high jerk.
    """
    d3 = np.diff(actions, n=3, axis=0)
    return float(np.sum(np.abs(d3)))


def end_variance(actions: np.ndarray) -> float:
    """Sum of per-joint variance over the last 10% of frames.

    Lower means the trajectory settles cleanly at episode end. A
    constant tail -> 0.0.
    """
    n_tail = max(1, int(0.1 * len(actions)))
    tail = actions[-n_tail:]
    return float(np.sum(np.var(tail, axis=0)))

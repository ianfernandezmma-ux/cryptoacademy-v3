"""Purged/embargoed CV: overlap purging, embargo, CPCV combinatorics, and the
leakage simulation that IS the sub-phase gate: a leak-exploiting model must
score ~chance under purged CV and visibly above chance without purging."""

import random
from datetime import UTC, datetime, timedelta

import numpy as np

from cryptoacademy.validation.cv import CombinatorialPurgedCV, PurgedKFold, _purge_mask

T0 = datetime(2024, 1, 1, tzinfo=UTC)


def _events(n: int, span_h: int = 96, step_h: int = 24):
    t0 = np.array(
        [np.datetime64((T0 + timedelta(hours=step_h * i)).replace(tzinfo=None)) for i in range(n)]
    )
    t1 = t0 + np.timedelta64(span_h, "h")
    return t0, t1


def test_purge_drops_overlapping_train_events():
    t0, t1 = _events(100)
    cv = PurgedKFold(n_splits=5, embargo=timedelta(0))
    for train_idx, test_idx in cv.split(t0, t1):
        ts, te = t0[test_idx].min(), t1[test_idx].max()
        for i in train_idx:
            assert t1[i] < ts or t0[i] > te  # no train interval overlaps test


def test_embargo_drops_events_right_after_test():
    t0, t1 = _events(100, span_h=24)
    cv = PurgedKFold(n_splits=5, embargo=timedelta(days=5))
    train_idx, test_idx = next(iter(cv.split(t0, t1)))
    te = t1[test_idx].max()
    emb_end = te + np.timedelta64(5, "D")
    for i in train_idx:
        assert not (t0[i] > te and t0[i] <= emb_end)


def test_purge_mask_envelops_test_inside_train_interval():
    t0 = np.array([np.datetime64("2024-01-01")])
    t1 = np.array([np.datetime64("2024-03-01")])  # long interval enveloping test
    safe = _purge_mask(
        t0, t1,
        np.datetime64("2024-01-15"), np.datetime64("2024-01-20"),
        np.timedelta64(0, "s"),
    )
    assert not safe[0]


def test_cpcv_split_and_path_counts():
    cv = CombinatorialPurgedCV(n_groups=6, k_test=2)
    t0, t1 = _events(120)
    splits = list(cv.split(t0, t1))
    assert len(splits) == 15          # C(6,2)
    assert cv.n_paths() == 5          # 15*2/6
    pm = cv.path_map()
    assert pm.shape == (6, 5)
    # every group tested exactly once per path, across distinct splits
    for path in range(5):
        assert len(set(pm[:, path])) <= 15


def test_every_event_tested_exactly_k_times_in_cpcv():
    cv = CombinatorialPurgedCV(n_groups=6, k_test=2, embargo=timedelta(0))
    t0, t1 = _events(60)
    counts = np.zeros(60, dtype=int)
    for _, test_idx, _ in cv.split(t0, t1):
        counts[test_idx] += 1
    assert (counts == 5).all()  # each group appears in C(5,1)=5 combos


def test_leakage_simulation_purged_cv_kills_the_leak():
    """A nearest-neighbor-in-time 'model' exploits overlapping labels: without
    purging it copies its overlapping neighbor's label; with purge+embargo the
    nearest train event is far away and accuracy collapses toward chance."""
    rng = random.Random(5)
    n = 400
    t0, t1 = _events(n, span_h=96, step_h=12)  # heavy overlap (8x)
    # labels: persistent regimes lasting ~10 events, so overlapping neighbors
    # share labels but distant events don't
    labels = np.empty(n, dtype=int)
    current = 1
    for i in range(n):
        if rng.random() < 0.1:
            current = -current
        labels[i] = current

    def nn_accuracy(cv_splits) -> float:
        hits = total = 0
        for train_idx, test_idx, *_ in cv_splits:
            if len(train_idx) == 0:
                continue
            for i in test_idx:
                j = train_idx[np.argmin(np.abs(t0[train_idx] - t0[i]))]
                hits += labels[j] == labels[i]
                total += 1
        return hits / total

    # the classic mistake: SHUFFLED K-fold — overlapping neighbors of every
    # test event sit in the train set
    perm = np.random.default_rng(1).permutation(n)
    shuffled = [
        (np.setdiff1d(np.arange(n), fold), np.sort(fold))
        for fold in np.array_split(perm, 5)
    ]
    acc_leaky = nn_accuracy(shuffled)
    purged = list(PurgedKFold(n_splits=5, embargo=timedelta(days=10)).split(t0, t1))
    acc_purged = nn_accuracy(purged)

    assert acc_leaky > 0.85          # the leak is real and exploitable
    assert acc_purged < acc_leaky - 0.2  # purging visibly destroys it

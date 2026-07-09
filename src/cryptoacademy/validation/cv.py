"""Purged & embargoed cross-validation over labeled events (AFML Ch. 7/12).

Every event carries its label interval [t0, t1] (t1 = actual barrier-touch
time). Purging drops any training event whose interval overlaps a test
group's envelope; the embargo additionally drops training events starting
within `embargo` AFTER a test group (serially-correlated features leak
forward even when labels don't).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from itertools import combinations

import numpy as np


def _purge_mask(
    t0: np.ndarray,
    t1: np.ndarray,
    test_start: np.datetime64,
    test_end: np.datetime64,
    embargo: np.timedelta64,
) -> np.ndarray:
    """True for events SAFE to train on w.r.t. one test window."""
    overlaps = (t0 <= test_end) & (t1 >= test_start)
    in_embargo = (t0 > test_end) & (t0 <= test_end + embargo)
    return ~(overlaps | in_embargo)


@dataclass
class PurgedKFold:
    """K contiguous test folds over events sorted by t0, with purge + embargo."""

    n_splits: int = 5
    embargo: timedelta = timedelta(days=22)

    def split(self, t0: np.ndarray, t1: np.ndarray):
        if len(t0) < self.n_splits:
            raise ValueError(f"{len(t0)} events < {self.n_splits} splits")
        order = np.argsort(t0, kind="stable")
        folds = np.array_split(order, self.n_splits)
        emb = np.timedelta64(int(self.embargo.total_seconds()), "s")
        for fold in folds:
            test_idx = np.sort(fold)
            test_start, test_end = t0[test_idx].min(), t1[test_idx].max()
            safe = _purge_mask(t0, t1, test_start, test_end, emb)
            train_idx = np.setdiff1d(np.where(safe)[0], test_idx)
            yield train_idx, test_idx


@dataclass
class CombinatorialPurgedCV:
    """CPCV (AFML Ch.12): N contiguous groups, k test groups per split ->
    C(N,k) splits and phi = C(N,k)*k/N reassembled backtest paths.

    Purge/embargo applied against EACH test group separately (groups may be
    non-adjacent, so one envelope would over- or under-purge).
    """

    n_groups: int = 6
    k_test: int = 2
    embargo: timedelta = timedelta(days=22)

    def group_bounds(self, t0: np.ndarray) -> list[np.ndarray]:
        order = np.argsort(t0, kind="stable")
        return [np.sort(g) for g in np.array_split(order, self.n_groups)]

    def split(self, t0: np.ndarray, t1: np.ndarray):
        groups = self.group_bounds(t0)
        emb = np.timedelta64(int(self.embargo.total_seconds()), "s")
        for combo in combinations(range(self.n_groups), self.k_test):
            test_idx = np.sort(np.concatenate([groups[g] for g in combo]))
            safe = np.ones(len(t0), dtype=bool)
            for g in combo:
                gs, ge = t0[groups[g]].min(), t1[groups[g]].max()
                safe &= _purge_mask(t0, t1, gs, ge, emb)
            train_idx = np.setdiff1d(np.where(safe)[0], test_idx)
            yield train_idx, test_idx, combo

    def n_paths(self) -> int:
        from math import comb

        return comb(self.n_groups, self.k_test) * self.k_test // self.n_groups

    def path_map(self) -> np.ndarray:
        """[n_groups x n_paths] -> split index whose test set covers that
        group in that path. Standard assignment: the i-th split that tests a
        group belongs to path i."""
        combos = list(combinations(range(self.n_groups), self.k_test))
        n_paths = self.n_paths()
        out = np.full((self.n_groups, n_paths), -1, dtype=int)
        seen = np.zeros(self.n_groups, dtype=int)
        for split_i, combo in enumerate(combos):
            for g in combo:
                out[g, seen[g]] = split_i
                seen[g] += 1
        assert (seen == n_paths).all() and (out >= 0).all()
        return out

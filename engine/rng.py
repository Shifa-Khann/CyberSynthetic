"""
engine/rng.py
Centralised seeded randomness. All generation code MUST import from here.
No bare random.*, np.random.* globals, or uuid4().
"""
from __future__ import annotations

import uuid
from numpy.random import SeedSequence, Generator, default_rng


class RNGTree:
    """
    Spawns one child Generator per named stage so every stage is
    independently reproducible from the root seed.

    Usage::
        tree = RNGTree(42)
        rng_world = tree.child("world")
        rng_attacks = tree.child("attacks")
    """

    _STAGE_NAMES = [
        "world",
        "background",
        "attacks",
        "detection",
        "labels",
        "localize",
        "upload",
        "evaluate",
        "misc",
    ]

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._ss = SeedSequence(seed)
        self._children: dict[str, Generator] = {}

    # -----------------------------------------------------------------
    # public
    # -----------------------------------------------------------------
    def child(self, stage: str) -> Generator:
        """Return (or create) the Generator for *stage*."""
        if stage not in self._children:
            # deterministic index so the same name always yields the same child
            idx = self._stage_index(stage)
            child_ss = self._ss.spawn(idx + 1)[idx]
            self._children[stage] = default_rng(child_ss)
        return self._children[stage]

    def uuid4(self, stage: str) -> str:
        """Generate a reproducible UUID4-like string via stage RNG bytes."""
        rng = self.child(stage)
        raw = rng.integers(0, 256, size=16, dtype="uint8").tobytes()
        return str(uuid.UUID(bytes=raw, version=4))

    @property
    def seed(self) -> int:
        return self._seed

    # -----------------------------------------------------------------
    # private
    # -----------------------------------------------------------------
    def _stage_index(self, stage: str) -> int:
        if stage in self._STAGE_NAMES:
            return self._STAGE_NAMES.index(stage)
        # unknown stage: hash name to a stable large index
        return (hash(stage) % 1_000) + len(self._STAGE_NAMES)


def make_rng_tree(seed: int) -> RNGTree:
    """Factory used by all callers."""
    return RNGTree(seed)

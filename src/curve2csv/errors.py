"""User-facing errors. Algorithmic uncertainty is an :class:`Abstain`, not an exception."""

from __future__ import annotations


class Curve2CSVError(Exception):
    """Base error for curve2csv."""


class InputError(Curve2CSVError):
    """The input image or override file cannot be read."""

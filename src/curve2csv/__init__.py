"""Digitize scientific charts into CSV and JSON."""

from curve2csv.api import extract
from curve2csv.types import ExtractionResult

__version__ = "0.1.0.dev0"
__all__ = ["ExtractionResult", "__version__", "extract"]

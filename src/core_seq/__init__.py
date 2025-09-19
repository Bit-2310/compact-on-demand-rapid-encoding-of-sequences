"""
CORE-seq Package Initializer

This file makes the `core_seq` directory a Python package and defines the
public API, making it easy for users to import the main classes.
"""

__version__ = "0.1.0"

from .writer import CSEQWriter, convert_from_fasta
from .reader import CSEQReader
from .loader import MLDataLoader

# This allows a user to type `from core_seq import CSEQReader`
# instead of the more verbose `from core_seq.reader import CSEQReader`.
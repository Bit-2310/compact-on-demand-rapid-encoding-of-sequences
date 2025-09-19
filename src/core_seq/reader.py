"""
coreRead: The CSEQ File Reader Module

This module provides the main CSEQReader class for opening and reading
data from .cseq files with high performance.
"""

from ._codec import decode_sequence, verify_checksum

class CSEQReader:
    """
    Provides fast, random-access to sequences within a .cseq file.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._file = None
        self.index = {}
        self.metadata = {}

    def open(self):
        """Opens the .cseq file, validates it, and loads the index."""
        # TODO: Open file, read and validate header, seek to index, and load it.
        return self

    def get(self, sequence_id: str, validate_checksum: bool = False) -> str:
        """
        Fetches and decodes a single sequence by its ID.
        
        Args:
            sequence_id (str): The ID of the sequence to retrieve.
            validate_checksum (bool): If True, verifies the data integrity.
        
        Returns:
            str: The decoded DNA sequence, or None if not found.
        """
        # TODO: Look up in index, seek, read, optionally verify, and decode.
        return "GATTACA..." # Placeholder

    def get_metadata(self) -> dict:
        """Returns the user-defined metadata from the file."""
        return self.metadata

    def list_ids(self) -> list:
        """Returns a list of all sequence IDs in the file."""
        return list(self.index.keys())
    
    def __getitem__(self, key):
        """Allows dictionary-style access, e.g., reader['chrM']"""
        return self.get(key)

    def __len__(self):
        """Allows getting the number of sequences with len(reader)"""
        return len(self.index)
        
    def close(self):
        """Closes the file."""
        if self._file:
            self._file.close()

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

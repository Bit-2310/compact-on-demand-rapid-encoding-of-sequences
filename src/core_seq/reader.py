"""
coreRead: The CSEQ File Reader Module

This is the librarian of the CORE-seq project. It provides a fast
and easy way to read data from a .cseq file.
"""
import json
import struct
from ._codec import decode_sequence, verify_checksum

class CSEQReader:
    """
    Reads a .cseq file and provides fast, on-demand access to sequences.

    It's designed to be used as a context manager (in a `with` block)
    to ensure the file is always properly handled. It loads the entire
    index into memory for instant lookups.
    """
    def __init__(self, filepath: str):
        """Prepares the reader with the path to a .cseq file."""
        if not isinstance(filepath, str):
            raise TypeError("Filepath must be a string.")
        
        self._filepath = filepath
        self._file = None
        self._index = {}
        self._metadata = {}

    def open(self):
        """
        Opens the file, verifies the header, and loads the index into memory.
        This is called automatically when you use a `with` block.
        """
        try:
            self._file = open(self._filepath, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: No such file '{self._filepath}'")

        # --- Read and Verify the Header ---
        header_bytes = self._file.read(16)
        if len(header_bytes) < 16:
            raise IOError("File is too small to be a valid .cseq file.")

        magic, flags, index_offset = struct.unpack('>6sHQ', header_bytes)

        if not magic.startswith(b'CSEQ'):
            raise IOError(f"Not a valid .cseq file. Incorrect magic number: {magic}")
        
        # --- Seek to and Read the Index ---
        self._file.seek(index_offset)
        index_bytes = self._file.read()
        index_obj = json.loads(index_bytes.decode('utf-8'))
        
        self._index = index_obj.get("index", {})
        
        # --- (Optional) Load Metadata ---
        metadata_offset = index_obj.get("metadata_offset")
        if metadata_offset:
            self._file.seek(metadata_offset)
            # We need to read from metadata start to index start
            metadata_bytes = self._file.read(index_offset - metadata_offset)
            self._metadata = json.loads(metadata_bytes.decode('utf-8'))

    def get(self, sequence_id: str, start: int = None, end: int = None, validate_checksum: bool = False) -> str:
        """
        Fetches a sequence or a subsequence by its ID.

        Args:
            sequence_id (str): The ID of the sequence to retrieve.
            start (int, optional): The 0-based start coordinate for a subsequence.
            end (int, optional): The 0-based end coordinate for a subsequence.
            validate_checksum (bool): If True, verifies data integrity (only for full sequences).

        Returns:
            The decoded DNA sequence or subsequence string.
        """
        if self._file is None:
            raise IOError("File is not open. Use 'with CSEQReader(...) as reader:'.")
        
        if sequence_id not in self._index:
            raise KeyError(f"Sequence ID '{sequence_id}' not found in the file.")

        offset, compressed_length, original_length = self._index[sequence_id]
        
        # --- Handle subsequence requests ---
        if start is not None or end is not None:
            # If getting a subsequence, checksum validation is skipped as we aren't reading the whole block.
            s_start = start or 0
            s_end = end or original_length
            
            if s_start < 0 or s_end > original_length or s_start >= s_end:
                raise ValueError(f"Invalid slice coordinates for sequence of length {original_length}: start={s_start}, end={s_end}")

            # Calculate which bytes we need to read. Each byte holds 2 bases.
            byte_start = s_start // 2
            byte_end = (s_end + 1) // 2
            
            self._file.seek(offset + byte_start)
            encoded_slice = self._file.read(byte_end - byte_start)
            
            # Decode the slice we read
            # The length we pass here might be larger than needed, but decode_sequence can handle it.
            decoded_full_slice = decode_sequence(encoded_slice, len(encoded_slice) * 2)
            
            # Trim the decoded slice to the exact start and end requested
            # This accounts for when the slice starts in the middle of a byte.
            slice_internal_start = s_start % 2
            slice_internal_end = slice_internal_start + (s_end - s_start)
            
            return decoded_full_slice[slice_internal_start:slice_internal_end]

        # --- Handle full sequence requests ---
        self._file.seek(offset)
        
        data_length = compressed_length - 4
        encoded_data = self._file.read(data_length)
        
        if validate_checksum:
            checksum_bytes = self._file.read(4)
            expected_checksum, = struct.unpack('>I', checksum_bytes)
            if not verify_checksum(encoded_data, expected_checksum):
                raise IOError(f"Data corruption detected for sequence '{sequence_id}'. Checksum mismatch.")

        return decode_sequence(encoded_data, original_length)

    def get_metadata(self) -> dict:
        """Returns the metadata dictionary stored in the file."""
        return self._metadata

    def list_ids(self) -> list:
        """Returns a list of all sequence IDs in the file."""
        return list(self._index.keys())

    def get_length(self, sequence_id: str) -> int:
        """
        Returns the original length of a sequence without reading the data.
        This is very fast as it just reads from the index.
        """
        if sequence_id not in self._index:
            raise KeyError(f"Sequence ID '{sequence_id}' not found in the file.")
        return self._index[sequence_id][2]

    def close(self):
        """Closes the file handle."""
        if self._file:
            self._file.close()
            self._file = None

    def __enter__(self):
        """Called when entering a `with` block."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called when exiting a `with` block."""
        self.close()

    def __getitem__(self, key: str) -> str:
        """Allows dictionary-style access, e.g., reader['chrM']"""
        return self.get(key)

    def __len__(self) -> int:
        """Allows `len(reader)` to return the number of sequences."""
        return len(self._index)

    def __contains__(self, key: str) -> bool:
        """Allows `'chrM' in reader` to check for a sequence's existence."""
        return key in self._index

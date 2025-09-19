"""
coreWrite: The CSEQ File Writer Module

This module contains the high-level API for creating .cseq files from
various data sources.
"""

from ._codec import encode_sequence, calculate_checksum

class CSEQWriter:
    """
    A class for creating .cseq files programmatically.
    
    This provides fine-grained control for adding sequences one by one from
    any source, not just a FASTA file.
    """
    def __init__(self, output_path: str, encoding_mode: str = 'lossless'):
        # TODO: Initialize file handles and index dictionary
        pass

    def add_sequence(self, seq_id: str, sequence: str):
        """Adds a single sequence to the .cseq file."""
        # TODO: Encode the sequence, write the data block, and update the index.
        pass

    def add_metadata(self, metadata: dict):
        """Adds a user-defined metadata dictionary to the file."""
        # TODO: Store the metadata to be written at the end.
        pass

    def close(self):
        """
        Finalizes the .cseq file by writing the metadata and index blocks
        and updating the header.
        """
        # TODO: Write metadata, write index, update header, and close file.
        pass

    def __enter__(self):
        """Enable use with 'with' statements."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure file is closed properly."""
        self.close()

def convert_from_fasta(input_path: str, output_path: str, metadata: dict = None):
    """
    A high-level helper function to convert a FASTA file to .cseq format.

    Args:
        input_path (str): Path to the source .fasta file.
        output_path (str): Path to create the new .cseq file.
        metadata (dict, optional): A dictionary of metadata to include.
    """
    # TODO: Implement the FASTA parsing and conversion logic using CSEQWriter.
    print(f"Converting {input_path} to {output_path}...")
    # with CSEQWriter(output_path) as writer:
    #     if metadata:
    #         writer.add_metadata(metadata)
    #     for seq_id, sequence in FastaParser(input_path):
    #         writer.add_sequence(seq_id, sequence)
    print("Conversion complete.")

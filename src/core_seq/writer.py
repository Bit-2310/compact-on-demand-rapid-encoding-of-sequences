"""
coreWrite: The CSEQ File Writer Module

This is the architect of the CORE-seq project. It contains the tools
for building .cseq files from your sequence data.
"""
import json
import struct
from ._codec import encode_sequence, calculate_checksum
from tqdm import tqdm # Import the progress bar library

# --- Private Helper for FASTA Parsing ---

def _fasta_parser(fasta_path: str):
    """
    A simple, memory-efficient FASTA file parser.
    It reads the file sequence by sequence, yielding one at a time.
    """
    seq_id = None
    sequence_lines = []

    with open(fasta_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('>'):
                # If we have a sequence buffered, yield it before starting the next.
                if seq_id:
                    yield seq_id, "".join(sequence_lines)
                
                # Start a new sequence
                seq_id = line[1:].split()[0] # Take the first part of the header as the ID
                sequence_lines = []
            else:
                sequence_lines.append(line)
    
    # After the loop, yield the very last sequence in the file
    if seq_id:
        yield seq_id, "".join(sequence_lines)


# --- The Main Writer Class ---

class CSEQWriter:
    """
    Builds a .cseq file programmatically, sequence by sequence.
    
    This is perfect for when your data isn't in a FASTA file, but comes
    from another program, a database, or a simulation.
    
    Example:
        with CSEQWriter("output.cseq") as writer:
            writer.add_sequence("seq1", "GATTACA")
            writer.add_sequence("seq2", "CATCAT")
    """
    def __init__(self, output_path: str, encoding_mode: str = 'lossless'):
        """Opens the output file and prepares it for writing."""
        if not isinstance(output_path, str):
            raise TypeError("Output path must be a string.")
            
        self._file = open(output_path, 'wb')
        self._index = {}
        self._metadata = None
        self._finalized = False
        
        # Write a temporary, empty header. We'll come back and fill this in at the end.
        # Header format: Magic (6s), Flags (H), Index Offset (Q) = 16 bytes total
        placeholder_header = struct.pack('>6sHQ', b'CSEQ\x01\x00', 1, 0)
        self._file.write(placeholder_header)

    def add_sequence(self, seq_id: str, sequence: str):
        """
        Encodes a single sequence and writes it to the file.

        Args:
            seq_id (str): The unique identifier for the sequence.
            sequence (str): The DNA sequence string.
        """
        if self._finalized:
            raise IOError("Cannot add sequences after the file has been finalized.")
        if not isinstance(seq_id, str) or not seq_id:
            raise TypeError("Sequence ID must be a non-empty string.")
        if seq_id in self._index:
            raise ValueError(f"Duplicate sequence ID found: {seq_id}")

        offset = self._file.tell() # Remember where this sequence starts
        
        encoded_data, original_length = encode_sequence(sequence)
        checksum = calculate_checksum(encoded_data)

        # Write the actual sequence data and its checksum
        self._file.write(encoded_data)
        self._file.write(struct.pack('>I', checksum)) # 'I' is for a 4-byte unsigned int

        compressed_length = len(encoded_data) + 4 # Data length + 4 bytes for the checksum
        
        # Add an entry to our "table of contents"
        self._index[seq_id] = [offset, compressed_length, original_length]

    def add_metadata(self, metadata: dict):
        """
        Stores a dictionary of metadata to be written to the file.
        
        This can be anything you want: sample info, project name, etc.
        """
        if not isinstance(metadata, dict):
            raise TypeError("Metadata must be a dictionary.")
        self._metadata = metadata

    def close(self):
        """
        Finalizes the .cseq file. This writes the metadata and index,
        then updates the header with the correct pointers.
        """
        if self._finalized:
            return # Already closed

        metadata_offset = 0
        if self._metadata:
            metadata_offset = self._file.tell()
            metadata_bytes = json.dumps(self._metadata, indent=None).encode('utf-8')
            self._file.write(metadata_bytes)
        
        # --- Write the Index Block ---
        index_offset = self._file.tell()
        final_index_obj = {"index": self._index}
        if metadata_offset > 0:
            final_index_obj["metadata_offset"] = metadata_offset

        index_bytes = json.dumps(final_index_obj, indent=None).encode('utf-8')
        self._file.write(index_bytes)
        
        # --- Go back to the start and write the final header ---
        self._file.seek(8) # Seek to the Index Offset field (after Magic and Flags)
        self._file.write(struct.pack('>Q', index_offset))

        self._file.close()
        self._finalized = True

    # These methods allow the class to be used in a `with` block
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# --- The High-Level Helper Function ---

def convert_from_fasta(input_path: str, output_path: str, metadata: dict = None):
    """
    The simplest way to create a .cseq file.
    
    This function handles everything: parsing the FASTA, creating the
    .cseq file, and adding any optional metadata.

    Args:
        input_path (str): Path to the source .fasta file.
        output_path (str): Path where the new .cseq file will be created.
        metadata (dict, optional): A dictionary of metadata to include.
    """
    print(f"Starting conversion: {input_path} -> {output_path}")
    try:
        # For a user-friendly progress bar, we first do a quick scan
        # to count the total number of sequences in the file.
        print("  Scanning file to count sequences...")
        total_sequences = sum(1 for line in open(input_path) if line.startswith('>'))

        with CSEQWriter(output_path) as writer:
            if metadata:
                writer.add_metadata(metadata)

            # Wrap our FASTA parser with tqdm for a nice progress bar
            parser = _fasta_parser(input_path)
            progress_bar = tqdm(parser, total=total_sequences, unit=" seq", desc="  Converting")

            for seq_id, sequence in progress_bar:
                writer.add_sequence(seq_id, sequence)
        
        print(f"\nConversion complete. Processed {total_sequences} sequences.")
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"\nAn error occurred during conversion: {e}")


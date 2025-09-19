"""
End-to-End Integration Test for the CORE-seq library.

This single test function simulates the entire user workflow:
1. Defines a set of test sequences and metadata.
2. Writes them to a temporary FASTA file.
3. Uses the coreWrite module to convert the FASTA to a .cseq file.
4. Uses the coreRead module to open the .cseq file.
5. Rigorously verifies that all data (sequences, metadata, index info)
   is retrieved perfectly and losslessly.
"""

import pytest
# CORRECTED IMPORT: We now import directly from the installed 'core_seq' package.
from core_seq import convert_from_fasta, CSEQReader

# --- Test Data ---
# We define a dictionary of test sequences.
# This includes:
#   - A standard DNA sequence ('seq1')
#   - A sequence with an odd length ('seq2')
#   - A sequence containing all IUPAC ambiguity codes ('seq3')
#   - A short sequence to test boundaries ('seq4')
TEST_SEQUENCES = {
    "seq1_human_regular": "GATTACAGATTACAGATTACAGATTACAGATTACA",
    "seq2_mouse_odd_length": "GATTACAGATTACAGATTACAGATTACAGATTAC",
    "seq3_ambiguous_codes": "ACGTMRWSYKVHDBN",
    "seq4_short": "A",
}

TEST_METADATA = {
    "author": "Pranava Upparlapalli",
    "project": "CORE-seq Test Suite",
    "version": 1.0,
    "notes": "This is a test to ensure data integrity."
}


def test_full_write_read_cycle(tmp_path):
    """
    Tests the entire CORE-seq pipeline from start to finish.

    Args:
        tmp_path: A special pytest fixture that provides a temporary
                  directory for test files, which is automatically cleaned up.
    """
    # 1. SETUP: Define file paths in the temporary directory
    fasta_path = tmp_path / "test.fasta"
    cseq_path = tmp_path / "test.cseq"

    # 2. CREATE TEST FASTA: Write our test data to a temporary FASTA file.
    #    This makes our test self-contained and reproducible.
    with open(fasta_path, "w") as f:
        for seq_id, sequence in TEST_SEQUENCES.items():
            f.write(f">{seq_id}\n")
            f.write(f"{sequence}\n")

    # 3. EXECUTE coreWrite: Convert the FASTA file to our .cseq format.
    #    This is the main action of the "writer" part of the test.
    print("\n--- Writing .cseq file ---")
    convert_from_fasta(str(fasta_path), str(cseq_path), metadata=TEST_METADATA)
    print("Write complete.")

    # 4. EXECUTE coreRead: Open the newly created .cseq file for verification.
    #    This is the main action of the "reader" part of the test.
    print("\n--- Reading .cseq file for verification ---")
    with CSEQReader(str(cseq_path)) as reader:

        # 5. VERIFY - The moment of truth.
        #    We now rigorously check if everything we wrote was read back perfectly.

        # 5a. Verify Metadata
        retrieved_metadata = reader.get_metadata()
        print(f"Retrieved Metadata: {retrieved_metadata}")
        assert retrieved_metadata == TEST_METADATA, "Metadata was not read back correctly."
        print("✅ Metadata verified.")

        # 5b. Verify Index and Counts
        assert len(reader) == len(TEST_SEQUENCES), "Incorrect number of sequences in the file."
        assert sorted(reader.list_ids()) == sorted(TEST_SEQUENCES.keys()), "Sequence IDs do not match."
        print(f"✅ Index and counts verified ({len(reader)} sequences).")

        # 5c. Verify Sequence Data (The most critical part)
        print("\n--- Verifying individual sequences ---")
        for seq_id, original_sequence in TEST_SEQUENCES.items():
            
            # Check the primary `get` method
            retrieved_sequence = reader.get(seq_id)
            
            print(f"Verifying '{seq_id}':")
            print(f"  Original:    {original_sequence}")

            # --- ADDED FOR VISUALIZATION ---
            # Manually read the raw, encoded bytes from the file to display them.
            # This demonstrates what's actually stored on disk.
            offset, compressed_len, _ = reader._index[seq_id]
            reader._file.seek(offset)
            # We subtract 4 bytes for the checksum at the end
            encoded_bytes = reader._file.read(compressed_len - 4)
            print(f"  Encoded (hex): {encoded_bytes.hex()}")
            # --- END OF ADDED CODE ---

            print(f"  Retrieved:   {retrieved_sequence}")
            
            assert retrieved_sequence == original_sequence, f"Sequence data for '{seq_id}' is corrupt."
            
            # Check the `get_length` method
            assert reader.get_length(seq_id) == len(original_sequence), f"Length for '{seq_id}' is incorrect."
            print(f"  ✅ OK")


        # 5d. Verify Pythonic Interface
        #    Check that dictionary-style access and 'in' operator work.
        assert reader["seq1_human_regular"] == TEST_SEQUENCES["seq1_human_regular"]
        assert "seq3_ambiguous_codes" in reader
        assert "non_existent_seq" not in reader
        print("\n✅ Pythonic interface verified.")

    print("\n--- End-to-end test successful: Data integrity is maintained. ---")


# To run this test:
# 1. Make sure you have pytest installed: `pip install pytest`
# 2. Make sure you have run `pip install -e .[dev]` from the project root.
# 3. Save this file as `tests/tests_initial_implementation.py`
# 4. Run pytest from your main project directory: `pytest -s`
#    (The -s flag is important to show the print statements)


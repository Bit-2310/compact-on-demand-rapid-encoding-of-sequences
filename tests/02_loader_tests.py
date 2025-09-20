"""
Unit and Integration Tests for the MLDataLoader.

This test file verifies that the parallel data loader works correctly,
handles batches as expected, and returns data in the correct format.
"""
import pytest
import numpy as np
from core_seq import CSEQWriter, MLDataLoader
# We need the internal FASTA parser to create our test file correctly.
from core_seq.writer import _fasta_parser

# --- Test Data ---
# A larger, more structured dataset to test batching and shuffling.
TEST_SEQUENCES = {f"seq_{i:02d}": "A" * (10 + i) for i in range(50)}
FASTA_CONTENT = ""
for seq_id, seq in TEST_SEQUENCES.items():
    FASTA_CONTENT += f">{seq_id}\n{seq}\n"

# --- A simple transformation function for testing ---
def basic_transform(sequence: str) -> np.ndarray:
    """A dummy transform that returns the length of the sequence as an array."""
    return np.array([len(sequence)])

@pytest.fixture
def cseq_file(tmp_path):
    """
    A pytest fixture that creates a temporary .cseq file for our tests.
    This runs once per test function that needs it.
    """
    fasta_path = tmp_path / "test.fasta"
    cseq_path = tmp_path / "test.cseq"
    
    with open(fasta_path, "w") as f:
        f.write(FASTA_CONTENT)
    
    # Use the robust CSEQWriter to create the file, ensuring it's correct.
    with CSEQWriter(str(cseq_path)) as writer:
        for seq_id, sequence in _fasta_parser(str(fasta_path)):
            writer.add_sequence(seq_id, sequence)
            
    return str(cseq_path)


def test_loader_initialization(cseq_file):
    """Tests if the MLDataLoader initializes correctly."""
    loader = MLDataLoader(cseq_file, transform_fn=basic_transform, batch_size=10)
    assert len(loader) == 5, "Loader should have 5 batches (50 items / 10 batch size)."
    assert loader.batch_size == 10
    assert loader.num_workers > 0

def test_loader_iteration_and_content(cseq_file):
    """
    Tests a full, non-shuffled iteration over the data.
    
    This is the corrected test. Instead of assuming a fixed order, it collects
    all results and verifies the complete dataset is correct.
    """
    loader = MLDataLoader(
        cseq_file,
        transform_fn=basic_transform,
        batch_size=16,
        shuffle=False,
        num_workers=2
    )
    
    print("\n--- Starting loader iteration ---")
    # Collect all results into a dictionary to verify content, regardless of batch order.
    results_dict = {}
    total_items = 0
    batch_num = 0
    for sequence_batch, ids_batch in loader:
        batch_num += 1
        print(f"\n[Batch #{batch_num}]")
        print(f"  Received batch of size: {len(ids_batch)}")
        print(f"  IDs in batch: {ids_batch}")
        print(f"  Transformed data (lengths): {sequence_batch.flatten()}")

        total_items += len(ids_batch)
        for i, seq_id in enumerate(ids_batch):
            # The transformed value is the length of the sequence.
            results_dict[seq_id] = sequence_batch[i][0]
            
    assert total_items == len(TEST_SEQUENCES), "The total number of loaded items is incorrect."
    print("\n--- Iteration complete ---")
    print("✅ Total number of items verified.")

    # Now, verify the content of the entire dataset.
    for seq_id, sequence in TEST_SEQUENCES.items():
        expected_length = len(sequence)
        assert results_dict[seq_id] == expected_length, f"Content for {seq_id} is incorrect."
    print("✅ Content of all items verified.")


def test_loader_shuffling(cseq_file):
    """Tests that the shuffle=True parameter changes the order of data."""
    loader = MLDataLoader(
        cseq_file,
        transform_fn=basic_transform,
        batch_size=50, # Get all data in one batch
        shuffle=True,
        num_workers=2
    )
    
    for _ in range(5):
        _, ids_batch = next(iter(loader))
        if ids_batch != loader.ordered_ids:
            assert True # Shuffle is working
            return
    
    assert False, "Data was not shuffled across multiple epochs."

def test_loader_last_batch(cseq_file):
    """
    Ensures the last batch is handled correctly, even if it's smaller.
    This test is robust against the non-deterministic order of parallel loading.
    """
    loader = MLDataLoader(cseq_file, transform_fn=basic_transform, batch_size=40, shuffle=False, num_workers=2)
    
    # Collect the sizes of all batches that are returned.
    batch_sizes = [batch_data.shape[0] for batch_data, _ in loader]
    
    assert len(batch_sizes) == 2, "Should be two batches in total."
    # The order isn't guaranteed, so we check if the sizes are correct.
    assert sorted(batch_sizes) == [10, 40], "The batch sizes are incorrect."


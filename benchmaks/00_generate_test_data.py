"""
Benchmark Data Generator for CORE-seq

This script creates a large, synthetic, and reproducible FASTA file
to be used for performance testing and benchmarking.
"""

import random
import os
from pathlib import Path

# --- Configuration ---
TARGET_FILE_SIZE_MB = 300
NUM_SEQUENCES = 5000
RANDOM_SEED = 42  # By setting a seed, we guarantee the exact same file is generated every time.

# Calculate average sequence length needed to hit the target file size
AVG_SEQ_LENGTH = (TARGET_FILE_SIZE_MB * 1024 * 1024) // NUM_SEQUENCES

# --- Path Configuration ---
# Get the directory where this script is located.
BENCHMARKS_DIR = Path(__file__).parent
# Define the output directory for data, creating it if it doesn't exist.
DATA_DIR = BENCHMARKS_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
# Define the final output path.
OUTPUT_FILE = DATA_DIR / "benchmark_data.fasta"


def generate_random_sequence(length: int) -> str:
    """Generates a random DNA sequence of a given length."""
    bases = ['A', 'C', 'G', 'T']
    return "".join(random.choice(bases) for _ in range(length))

def create_test_fasta():
    """Creates the benchmark FASTA file."""
    # Set the seed for reproducibility
    random.seed(RANDOM_SEED)

    print(f"--- Generating Test FASTA File ---")
    print(f"  Target size: ~{TARGET_FILE_SIZE_MB} MB")
    print(f"  Number of sequences: {NUM_SEQUENCES}")
    print(f"  Random seed: {RANDOM_SEED}")
    print(f"  Output file: {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w") as f:
        for i in range(NUM_SEQUENCES):
            length_variance = int(AVG_SEQ_LENGTH * 0.2)
            seq_len = random.randint(AVG_SEQ_LENGTH - length_variance, AVG_SEQ_LENGTH + length_variance)
            
            seq_id = f"seq_{i+1:05d}"
            sequence = generate_random_sequence(seq_len)
            
            f.write(f">{seq_id}\n")
            f.write(f"{sequence}\n")

    file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n--- Generation Complete ---")
    print(f"  Final file size: {file_size_mb:.2f} MB")
    
    # --- Verification Step ---
    print("\n--- Verifying File Content (First 5 lines) ---")
    with open(OUTPUT_FILE, "r") as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            print(f"  {line.strip()}")
    print("-------------------------------------------------")


if __name__ == "__main__":
    create_test_fasta()
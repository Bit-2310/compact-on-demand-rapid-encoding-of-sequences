"""
CORE-seq Performance Benchmark vs. FASTA Workflows (Accurate Version)

This script provides a rigorous and fair comparison of CORE-seq against
standard and optimized FASTA file handling techniques.

It now saves all results to a CSV file for tracking over time.
"""

import time
import random
import os
import gzip
import zstandard as zstd
from pathlib import Path
import csv
from datetime import datetime

# --- Import our library and the fair competitor ---
from core_seq import __version__ as core_seq_version
from core_seq import convert_from_fasta, CSEQReader
from pyfaidx import Fasta

# --- Path and Parameter Configuration ---
BENCHMARKS_DIR = Path(__file__).parent
DATA_DIR = BENCHMARKS_DIR / "data"
FASTA_FILE = DATA_DIR / "benchmark_data.fasta"
CSEQ_FILE = DATA_DIR / "benchmark_data.cseq"
GZIP_FILE = DATA_DIR / "benchmark_data.fasta.gz"
ZSTD_FILE = DATA_DIR / "benchmark_data.fasta.zst"
RESULTS_FILE = BENCHMARKS_DIR / "benchmark_results.csv"

NUM_SEQS_TO_FETCH = 1000

# --- Helper Functions ---
def get_file_size_mb(filepath):
    """Gets file size in megabytes."""
    return Path(filepath).stat().st_size / (1024 * 1024)

# --- Benchmark Phases ---

def run_phase_1_compression(results):
    """Create all compressed files and report on final sizes."""
    print("\n--- Phase 1: Compression and File Size Comparison ---")
    
    # 1a. Convert to .cseq
    print("  Creating .cseq file...")
    start_time = time.perf_counter()
    convert_from_fasta(str(FASTA_FILE), str(CSEQ_FILE))
    results['conversion_time_sec'] = time.perf_counter() - start_time
    
    # 1b. Compress with gzip
    print("  Compressing with gzip...")
    with open(FASTA_FILE, 'rb') as f_in, gzip.open(GZIP_FILE, 'wb') as f_out:
        f_out.writelines(f_in)
        
    # 1c. Compress with Zstandard (modern, fast compressor)
    print("  Compressing with Zstandard...")
    zstd_compressor = zstd.ZstdCompressor(level=3)
    with open(FASTA_FILE, 'rb') as f_in, open(ZSTD_FILE, 'wb') as f_out:
        f_out.write(zstd_compressor.compress(f_in.read()))

    # 1d. Report sizes and save to results
    print("\n  --- File Size Results ---")
    results['size_fasta_mb'] = get_file_size_mb(FASTA_FILE)
    results['size_cseq_mb'] = get_file_size_mb(CSEQ_FILE)
    results['size_gzip_mb'] = get_file_size_mb(GZIP_FILE)
    results['size_zstd_mb'] = get_file_size_mb(ZSTD_FILE)

    print(f"  FASTA (raw): {results['size_fasta_mb']:>6.2f} MB (100.0%)")
    print(f"  CORE-seq:    {results['size_cseq_mb']:>6.2f} MB ({(results['size_cseq_mb']/results['size_fasta_mb']*100):.1f}%)")
    print(f"  gzip:        {results['size_gzip_mb']:>6.2f} MB ({(results['size_gzip_mb']/results['size_fasta_mb']*100):.1f}%)")
    print(f"  zstandard:   {results['size_zstd_mb']:>6.2f} MB ({(results['size_zstd_mb']/results['size_fasta_mb']*100):.1f}%)")
    print(f"  Conversion Time: {results['conversion_time_sec']:.4f} seconds")


def run_phase_2_random_access(results):
    """Benchmark random access speed for full sequences."""
    print("\n--- Phase 2: Random Full Sequence Access (Fair Comparison) ---")
    
    with Fasta(str(FASTA_FILE)) as fa:
        all_ids = list(fa.keys())
    ids_to_fetch = random.sample(all_ids, NUM_SEQS_TO_FETCH)
    print(f"  (Fetching {NUM_SEQS_TO_FETCH} random sequences from {len(all_ids)} total)")

    # 2a. FASTA via pyfaidx (The fair competitor)
    start_time = time.perf_counter()
    with Fasta(str(FASTA_FILE)) as fa:
        for seq_id in ids_to_fetch:
            # By converting to a string, we force pyfaidx to read and load the sequence.
            _ = str(fa[seq_id])
    duration = time.perf_counter() - start_time
    results["access_time_pyfaidx_sec"] = duration
    print(f"  pyfaidx took:   {duration:.4f} seconds")

    # 2b. CORE-seq
    start_time = time.perf_counter()
    with CSEQReader(str(CSEQ_FILE)) as reader:
        for seq_id in ids_to_fetch:
            _ = reader.get(seq_id, validate_checksum=False)
    duration = time.perf_counter() - start_time
    results["access_time_coreseq_sec"] = duration
    print(f"  CORE-seq took:  {duration:.4f} seconds")

def save_results_to_csv(results):
    """Appends the results of this benchmark run to a CSV file."""
    # Define the headers for our CSV file
    headers = [
        'timestamp', 'core_seq_version', 'size_fasta_mb', 'size_cseq_mb',
        'size_gzip_mb', 'size_zstd_mb', 'conversion_time_sec',
        'access_time_pyfaidx_sec', 'access_time_coreseq_sec'
    ]
    
    # Check if the file exists to decide whether to write headers
    file_exists = RESULTS_FILE.exists()
    
    print(f"\n--- Saving results to {RESULTS_FILE} ---")
    with open(RESULTS_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(results)
    print("  Results saved.")

def main():
    """Main function that runs the whole show."""
    if not FASTA_FILE.exists():
        print(f"Error: Hey, I can't find '{FASTA_FILE}'.")
        print("You need to run 'python benchmarks/00_generate_test_data.py' first.")
        return
        
    random.seed(42)
    
    # Prepare the dictionary to hold all our results
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'core_seq_version': core_seq_version
    }

    run_phase_1_compression(results)
    run_phase_2_random_access(results)

    # Let's print a nice summary at the end.
    print("\n" + "="*40)
    print("--- BENCHMARK SUMMARY ---")
    cseq_time = results.get("access_time_coreseq_sec", -1)
    pyfaidx_time = results.get("access_time_pyfaidx_sec", -1)
    
    if cseq_time > 0 and pyfaidx_time > 0:
        speedup = pyfaidx_time / cseq_time
        print(f"Random Access Speedup (CORE-seq vs. pyfaidx): {speedup:.1f}x faster")
    else:
        print("Couldn't calculate the speedup.")
    print("="*40)
    
    save_results_to_csv(results)

if __name__ == "__main__":
    main()
    
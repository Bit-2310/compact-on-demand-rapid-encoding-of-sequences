<p align="center">
  <img src="assets/logo.png" alt="CORE-seq logo" width="600"/>
</p>

# CORE-seq : Compact On-demand Rapid Encoding of Sequences

[![Project Status](https://img.shields.io/badge/status-in_development-orange?style=for-the-badge)](https://github.com/pranavaupparlapalli/CORE-seq)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](./LICENSE.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen?style=for-the-badge&logo=pytest)](./tests)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-blueviolet?style=for-the-badge&logo=github)](https://github.com/pranavaupparlapalli/CORE-seq/issues)


Hi! I am Pranava Upparlapalli and this is my brain child at 1:00 AM. The reason as to why I wanted to build this project was mainly because I was pondering the question "is there a faster processing format than `*.fasta`?"

Of course, there are several, for example, the BAM format for alignments, CRAM for reference-based compression, UCSC's `.2bit` format and several others. But I wanted to work on this problem too, just because... why not? It's an interesting problem, at least in my mind.

---
## 📂 Directory Structure

```plaintext
CORE-seq/
├── src/
│   └── core_seq/
│       ├── __init__.py
│       ├── _codec.py
│       ├── loader.py
│       ├── reader.py
│       └── writer.py
│
├── tests/
│   └── 01_Initial_tests.py
│
├── .gitignore
├── LICENSE.md
├── README.md
└── pyproject.toml
```

## The CORE Concept

The big idea was to stop treating sequence files like text documents and start treating them like smart, high-performance databases. Instead of just reading a file from top to bottom every single time, I wanted to build something that lets you jump straight to the data you need, instantly.

Here's the breakdown of what I cooked up:

1.  **Stop Wasting Space (Compact):** A standard FASTA file uses a whole 8 bits to store a single base like 'A' or 'G'. That I feel is slightly less effecient when used for processing! CORE-seq uses a smarter 4-bit encoding, which means we can pack four bases into the space of one. This shrinks the sequence data by about 50% (assumption! since I still need to test this)

2.  **Instant Access (On-demand):** This is the secret sauce. Instead of having to read through 9 GB of a 10 GB file just to get to the end, CORE-seq creates an index—like a table of contents for your sequences. So when you ask for "chromosome Y," the program looks it up in the index, sees it starts at byte `5,432,100`, and jumps right there. It's the difference between scrolling through a giant PDF and clicking a bookmark.

3.  **Built for Speed (Rapid Encoding):** By working directly with this binary data, we can skip all the slow text-parsing steps. This also makes the format perfect for parallel processing, because you can have 16 different CPU cores all jumping to different parts of the file at the same time without tripping over each other.

4.  **Make it ML-Ready:** I wanted to build this with modern data science in mind. The format is designed with the idea of being a high-throughput engine for machine learning, with a data loader that can feed a continuous stream of ready-to-process data to a GPU, making sure it never sits idle.

## The `.cseq` Format Design

At its heart, a `.cseq` file is a smartly structured binary file. It's not just a stream of data; it's organized into three distinct parts to make it fast and flexible.

1.  **File Header:** A small section at the very top of the file that acts like a business card. It tells the program: "Hi, I'm a .cseq file, version 1.0, the data inside is DNA, and you can find the index way at the end at this specific byte location."

2.  **Data Blocks:** This is the main body of the file where all the sequence data lives. Each sequence is encoded (using 4-bit packing) and stored in its own independent block. This is key—it means we can grab just one sequence without having to touch or read any of the others.

3.  **Index Block:** This is the "table of contents" that makes everything so fast. It's a list, stored at the end of the file, that maps every sequence ID to its exact location (byte offset) in the file. When you want a sequence, the program reads this small index into memory and immediately knows where to find everything.

## What can this potentially do?

Here are a few simple ways CORE-seq could help:

* **Pangenome Analysis:** Instead of reading through whole FASTA files for each genome, a `.cseq` file lets you go straight to the part you need. This makes it easier to look up the same gene across many genomes.  

* **Machine Learning:** Training models often slows down because FASTA files are read line by line. CORE-seq stores data in blocks and can send them in batches, which helps keep training smoother.  

* **Genome Browsers:** Web tools usually have to load large FASTA files even when you only need a small region. CORE-seq can fetch just that region, so genome browsers can respond faster.  

## Project Roadmap

This project is currently in the planning and early development stage. Here's the plan:

-   [x] Define the core concept and file specification.
-   [x] Initial Skeleton
-   [x] Develop the core Python library for encoding/decoding sequences.
-   [ ] **Coming Next:** Build the tool for converting FASTA files to `.cseq`.
-   [ ] Implement the high-performance ML data loader.
-   [ ] Package the project for release on PyPI.
-   [ ] Write comprehensive documentation and tutorials.

---

This project is my attempt at building a more efficient foundation for the next generation of bioinformatics tools. Thanks for checking it out!

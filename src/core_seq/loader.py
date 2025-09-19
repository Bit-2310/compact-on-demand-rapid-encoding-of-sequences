"""
coreLoader: The CSEQ Data Pipeline Module

This is the ML Fuel Injector of the CORE-seq project. It's designed to
be a high-performance data pipeline that efficiently reads from a .cseq
file and prepares data in batches for machine learning models.
"""
import random
import numpy as np
from .reader import CSEQReader

class MLDataLoader:
    """
    An efficient data loader for feeding .cseq data to ML models.

    This class acts as an iterator that you can use in a `for` loop. On each
    iteration, it yields a "batch" of sequences and their corresponding labels,
    already transformed into numerical arrays (tensors) ready for a GPU.

    Example:
        # Define a function to turn a sequence into numbers
        def one_hot_encode(sequence):
            # (Your one-hot encoding logic here)
            return np.array(...)

        # Create the loader
        loader = MLDataLoader(
            cseq_path="my_data.cseq",
            batch_size=64,
            shuffle=True,
            transform_fn=one_hot_encode
        )

        # Loop over the data for model training
        for epoch in range(5):
            print(f"--- Epoch {epoch+1} ---")
            for sequence_batch, label_batch in loader:
                # model.train(sequence_batch, label_batch)
                pass
    """
    def __init__(self,
                 cseq_path: str,
                 transform_fn,
                 labels: dict = None,
                 batch_size: int = 32,
                 shuffle: bool = True):
        """
        Initializes the data loader.

        Args:
            cseq_path (str): Path to the .cseq file.
            transform_fn (callable): A function that takes a DNA string and
                                     returns a NumPy array.
            labels (dict, optional): A dictionary mapping sequence IDs to their
                                     labels (e.g., 0 or 1).
            batch_size (int): The number of sequences per batch.
            shuffle (bool): If True, shuffles the data at the start of each epoch.
        """
        if not callable(transform_fn):
            raise TypeError("The 'transform_fn' must be a callable function.")

        self.cseq_path = cseq_path
        self.transform_fn = transform_fn
        self.labels = labels if labels is not None else {}
        self.batch_size = batch_size
        self.shuffle = shuffle

        # We use our reader to get the list of all available IDs
        with CSEQReader(self.cseq_path) as reader:
            self._all_ids = reader.list_ids()
            
        self._current_index = 0

    def __len__(self) -> int:
        """Returns the total number of batches in one epoch."""
        # Use ceiling division to include the last, possibly smaller, batch
        return (len(self._all_ids) + self.batch_size - 1) // self.batch_size

    def __iter__(self):
        """
        Prepares the loader for a new epoch (a full pass over the data).
        This is where the shuffling happens.
        """
        self._current_index = 0
        if self.shuffle:
            random.shuffle(self._all_ids)
        return self

    def __next__(self):
        """
        Fetches, transforms, and returns the next batch of data.
        This is what gets called in a `for` loop.
        """
        if self._current_index >= len(self._all_ids):
            # We've gone through all the data
            raise StopIteration

        # Figure out which slice of IDs to get for this batch
        start = self._current_index
        end = start + self.batch_size
        batch_ids = self._all_ids[start:end]

        # Update the index for the next batch
        self._current_index = end

        # Here's the pipeline: read, transform, and collect
        # TODO: This part can be parallelized using multiple workers
        #       for a significant speedup on large datasets.
        
        # We need a CSEQReader to be open for the duration of this batch fetch.
        # It's opened here to be thread-safe in a future parallel version.
        with CSEQReader(self.cseq_path) as reader:
            sequences_batch = []
            labels_batch = []
            
            for seq_id in batch_ids:
                # 1. Read the sequence string from the .cseq file
                sequence_str = reader.get(seq_id, validate_checksum=False)
                
                # 2. Transform it into a numerical array (tensor)
                sequence_tensor = self.transform_fn(sequence_str)
                sequences_batch.append(sequence_tensor)

                # 3. Get the corresponding label, if it exists
                if self.labels:
                    labels_batch.append(self.labels.get(seq_id))

        # Stack the individual arrays into a single "batch" array
        sequences_batch = np.stack(sequences_batch)
        
        if self.labels:
            labels_batch = np.array(labels_batch)
            return sequences_batch, labels_batch
        else:
            return sequences_batch
"""
coreLoader: The CSEQ Data Pipeline Module

This is the ML Fuel Injector of the CORE-seq project. It's designed to
be a high-performance, parallel data pipeline that efficiently reads 
from a .cseq file and prepares sequence data in batches for ML models.
"""
import random
import numpy as np
import multiprocessing as mp
from .reader import CSEQReader
import time

def _worker_fn(cseq_path, transform_fn, id_queue, batch_queue):
    """
    This is the function that runs in the background on a separate CPU core.
    
    It acts as a "producer": it continuously pulls a batch of sequence IDs
    from the `id_queue`, fetches the data, transforms it, and puts the 
    finished `(data_batch, id_batch)` tuple into the `batch_queue`.
    """
    try:
        with CSEQReader(cseq_path) as reader:
            while True:
                batch_ids = id_queue.get()
                # A "sentinel" value of None tells the worker to shut down.
                if batch_ids is None:
                    break

                sequences_batch = []
                for seq_id in batch_ids:
                    sequence_str = reader.get(seq_id, validate_checksum=False)
                    sequence_tensor = transform_fn(sequence_str)
                    sequences_batch.append(sequence_tensor)
                
                # Package the data and IDs together and put them in the output queue
                batch_queue.put((np.stack(sequences_batch), batch_ids))

    except Exception as e:
        # It's important to catch errors in the worker and report them.
        print(f"Error in worker process: {e}")
        batch_queue.put(e) # Send the error to the main process

class MLDataLoader:
    """
    An efficient, parallel data loader for feeding .cseq sequence data to ML models.
    
    Uses multiple background processes to pre-fetch and prepare batches of
    sequence data, ensuring the main training loop doesn't have to wait for I/O.
    """
    def __init__(self,
                 cseq_path: str,
                 transform_fn,
                 batch_size: int = 32,
                 shuffle: bool = True,
                 num_workers: int = 4):
        """
        Initializes the parallel data loader.

        Args:
            cseq_path (str): Path to the .cseq file.
            transform_fn (callable): A function that takes a DNA string and
                                     returns a NumPy array.
            batch_size (int): The number of sequences per batch.
            shuffle (bool): If True, shuffles data at the start of each epoch.
            num_workers (int): The number of CPU cores to use for pre-fetching.
        """
        if not callable(transform_fn):
            raise TypeError("The 'transform_fn' must be a callable function.")

        self.cseq_path = cseq_path
        self.transform_fn = transform_fn
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.num_workers = max(1, num_workers) if num_workers is not None else mp.cpu_count()

        with CSEQReader(self.cseq_path) as reader:
            self._all_ids = reader.list_ids()
            self.ordered_ids = self._all_ids[:]
            
        self._workers = []
        self._id_queue = None
        self._batch_queue = None
        self._batch_count = 0

    def __len__(self) -> int:
        """Returns the total number of batches in one epoch."""
        return (len(self._all_ids) + self.batch_size - 1) // self.batch_size

    def _start_workers(self):
        """Creates and starts the background worker processes."""
        self._id_queue = mp.Queue()
        self._batch_queue = mp.Queue(maxsize=self.num_workers * 2)

        for _ in range(self.num_workers):
            worker = mp.Process(
                target=_worker_fn,
                args=(self.cseq_path, self.transform_fn, self._id_queue, self._batch_queue)
            )
            worker.daemon = True
            worker.start()
            self._workers.append(worker)

    def _shutdown_workers(self):
        """Sends a signal to all workers to terminate and then joins them."""
        if self._workers:
            # Send a shutdown signal for each worker
            for _ in self._workers:
                try: self._id_queue.put(None)
                except Exception: pass
            
            # Clear the output queue
            while not self._batch_queue.empty():
                try: self._batch_queue.get_nowait()
                except Exception: pass

            for worker in self._workers:
                worker.join(timeout=5)
                if worker.is_alive():
                    worker.terminate()
            self._workers = []

    def __iter__(self):
        """Prepares for a new epoch: starts workers and queues up the work."""
        self._shutdown_workers()
        self._start_workers()
        
        ids_to_process = self._all_ids[:]
        if self.shuffle:
            random.shuffle(ids_to_process)
        
        # This counter is our simple, robust way of tracking progress.
        self._batch_count = 0
        
        # Queue up all the batches of IDs for the workers to process
        for i in range(0, len(ids_to_process), self.batch_size):
            batch_ids = ids_to_process[i:i + self.batch_size]
            self._id_queue.put(batch_ids)
            
        return self

    def __next__(self):
        """Fetches the next pre-prepared batch from the output queue."""
        if self._batch_count >= len(self):
            self._shutdown_workers()
            raise StopIteration
            
        try:
            # This is the "consumer" step: get a finished (data, ids) package.
            next_batch = self._batch_queue.get(timeout=60)
            
            if isinstance(next_batch, Exception):
                self._shutdown_workers()
                raise next_batch
            
            self._batch_count += 1
            return next_batch

        except Exception: # Catches queue.Empty from timeout
            self._shutdown_workers()
            raise StopIteration("Timeout: Worker processes failed to produce a batch in time.")

    def __del__(self):
        """Ensures workers are cleaned up when the loader is garbage collected."""
        self._shutdown_workers()


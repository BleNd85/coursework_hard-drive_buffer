from typing import List, Optional
from models.buffer import Buffer


# FIFO (First In First Out)
class FIFOStrategy:
    # FIFO strategy: process requests in the order they arrive
    # Does not optimize the movement of the drive mechanism
    def __init__(self, disk, config=None):
        self.disk = disk
        self.queue: List[Buffer] = []  # Queue of requests
        self.active_buffer: Optional[Buffer] = None  # Current buffer in processing

    def add_request(self, buffer: Buffer, operation: str):
        # Adds a request to the queue
        # operation: 'READ' or 'WRITE'
        buffer.io_operation = operation
        self.queue.append(buffer)

    def get_next_buffer(self) -> Optional[Buffer]:
        # Returns the next buffer to process
        if not self.queue:
            return None

        # Take the first request
        next_buffer = self.queue.pop(0)
        self.active_buffer = next_buffer
        return next_buffer

    def complete_io(self):
        # Marks the current operation as completed
        if self.active_buffer:
            self.active_buffer.io_operation = None
        self.active_buffer = None

    def get_state_string(self) -> str:
        # Returns a string with the strategy status for output
        active_str = str(self.active_buffer) if self.active_buffer else "None"
        queue_str = ', '.join([str(b) for b in self.queue])

        return f"DRIVER: Device strategy FIFO:\n" + \
            f"    Active buffer {active_str}\n" + \
            f"    Schedule queue [{queue_str}]"

    def has_pending_requests(self) -> bool:
        return len(self.queue) > 0 or self.active_buffer is not None

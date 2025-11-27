from typing import List, Optional
from models.buffer import Buffer


# NLOOK strategy
# Has multiple request queues
# Processes oldest queue using simplified LOOK principle (always OUT direction)
# New requests are added to a new queue (if current one is full)
class NLOOKStrategy:

    def __init__(self, disk, config):
        self.disk = disk
        self.config = config

        # List of queues (every queue is list of buffers)
        self.queues: List[List[Buffer]] = [[]]  # Start with one queue
        self.active_buffer: Optional[Buffer] = None

        # Max length of one queue
        self.queue_max_length = config.NLOOK_QUEUE_MAX_LENGTH

    def add_request(self, buffer: Buffer, operation: str):
        # Adds request to the queue
        # If the last one is full creates new
        buffer.io_operation = operation

        # If no queues exist, creates one
        if not self.queues:
            self.queues.append([buffer])
            return

        last_queue = self.queues[-1]

        # If the last queue is full, creates new
        if len(last_queue) >= self.queue_max_length:
            self.queues.append([buffer])
        else:
            last_queue.append(buffer)
            # Sorts by sector number
            last_queue.sort(key=lambda b: b.sector_num)

    def get_next_buffer(self) -> Optional[Buffer]:
        # Gets next buffer from the oldest queue

        self.queues = [q for q in self.queues if len(q) > 0]

        if not self.queues:
            return None

        oldest_queue = self.queues[0]
        oldest_queue.sort(key=lambda b: b.sector_num)

        # Search for buffer >= current track (OUT direction)
        current_track = self.disk.current_track
        next_buffer = self._find_buffer_from_track(oldest_queue, current_track)

        if next_buffer:
            oldest_queue.remove(next_buffer)
            self.active_buffer = next_buffer
            return next_buffer
        else:
            # No buffers >= current track, start from beginning of queue
            if oldest_queue:
                next_buffer = oldest_queue.pop(0)
                self.active_buffer = next_buffer
                return next_buffer
            else:
                # Queue is empty, move to next queue
                self.queues.pop(0)
                return self.get_next_buffer()

    def _find_buffer_from_track(self, queue: List[Buffer], from_track: int) -> Optional[Buffer]:
        # Searches for a buffer in the queue on track >= from_track (OUT direction).
        for buffer in queue:
            buffer_track = self.disk.get_track_for_sector(buffer.sector_num)
            if buffer_track >= from_track:
                return buffer
        return None

    def complete_io(self):
        # Completes current operation
        if self.active_buffer:
            self.active_buffer.io_operation = None
        self.active_buffer = None

    def get_state_string(self) -> str:
        # Gets strategy state
        active_str = str(self.active_buffer) if self.active_buffer else "None"

        result = f"DRIVER: Device strategy NLOOK (num {self.queue_max_length}):\n"
        result += f"    Active buffer {active_str}\n"

        for i, queue in enumerate(self.queues, 1):
            queue_str = ', '.join([str(b) for b in queue])
            result += f"    Schedule queue {i} [{queue_str}]\n"

        return result.rstrip()

    def has_pending_requests(self) -> bool:
        # Checks for requests"
        return len(self.queues) > 0 or self.active_buffer is not None

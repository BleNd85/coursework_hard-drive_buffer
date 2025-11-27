from typing import Optional, List
from collections import deque
from models.buffer import Buffer


# LFU (Least Frequently Used) with 3 segments
class LFUCache:
    # LFU algorithm with 3 segments, left, middle, right
    # Left segment: recently added buffers
    # Middle segment: buffers that have been accessed multiple times
    # Right segment: frequently used buffers
    def __init__(self, config):
        self.config = config
        self.total_buffers = config.BUFFERS_NUM

        # Max segments sizes
        self.left_max = config.LFU_LEFT_SEGMENT_MAX
        self.middle_max = config.LFU_MIDDLE_SEGMENT_MAX

        # Three segments
        self.left_segment: deque[Buffer] = deque()
        self.middle_segment: deque[Buffer] = deque()
        self.right_segment: deque[Buffer] = deque()

        # List of free buffers
        self.free_buffers: List[Buffer] = [
            Buffer(i) for i in range(self.total_buffers)
        ]

        # Fast search: sector_num -> Buffer
        self.sector_to_buffer = {}

    def find_buffer(self, sector_num: int) -> Optional[Buffer]:
        # Searches for buffer with the specified sector
        return self.sector_to_buffer.get(sector_num)

    def get_free_buffer(self) -> Buffer:
        # Gets free buffer
        # If there are no free ones - displaces from the right segment
        if self.free_buffers:
            return self.free_buffers.pop()

        # Push out of the right segment
        # Select the buffer with the smallest counter
        return self._evict_from_right()

    def _evict_from_right(self) -> Buffer:
        # Displaces the buffer from the right segment
        if not self.right_segment:
            raise Exception("No buffers available for eviction")

        # Find the buffer with the minimum counter that can be evicted
        # Filter out buffers that are in I/O operation
        evictable_buffers = [b for b in self.right_segment if b.io_operation is None]

        if not evictable_buffers:
            raise Exception("No buffers available for eviction")

        min_buffer = min(evictable_buffers, key=lambda b: b.access_counter)
        self.right_segment.remove(min_buffer)

        # Remove from the map
        if min_buffer.sector_num in self.sector_to_buffer:
            del self.sector_to_buffer[min_buffer.sector_num]

        return min_buffer

    def access_buffer(self, sector_num: int, track_num: int) -> Buffer:
        # Buffer access
        # If it is in the cache: move it according to the algorithm
        # If it is not: add a new one
        buffer = self.find_buffer(sector_num)

        if buffer:
            # Buffer was found: move
            self._move_on_access(buffer)
            return buffer
        else:
            # Buffer not found: add new one
            return self._add_new_buffer(sector_num, track_num)

    def _move_on_access(self, buffer: Buffer):
        # Moves the buffer on access according to the LFU algorithm
        # Determine in which segment the buffer is
        if buffer in self.left_segment:
            # Buffer in left segment: increment counter and move to beginning
            self.left_segment.remove(buffer)
            buffer.increment_access()
            self._add_to_left(buffer)
        elif buffer in self.middle_segment:
            # Buffer in middle segment: increment counter and move to left
            self.middle_segment.remove(buffer)
            buffer.increment_access()
            self._add_to_left(buffer)
        elif buffer in self.right_segment:
            # Buffer in right segment: increment counter and move to left
            self.right_segment.remove(buffer)
            buffer.increment_access()
            self._add_to_left(buffer)

    def _add_new_buffer(self, sector_num: int, track_num: int) -> Buffer:
        # Adds a new buffer to the left segment
        buffer = self.get_free_buffer()
        buffer.load_sector(sector_num, track_num)
        self._add_to_left(buffer)
        self.sector_to_buffer[sector_num] = buffer
        return buffer

    def _add_to_left(self, buffer: Buffer):
        # Adds a buffer to the beginning of the left segment
        self.left_segment.appendleft(buffer)

        # If the left one is full, move it to the middle one
        if len(self.left_segment) > self.left_max:
            moved_buffer = self.left_segment.pop()
            self._add_to_middle(moved_buffer)

    def _add_to_middle(self, buffer: Buffer):
        # Adds a buffer to the beginning of the middle segment
        self.middle_segment.appendleft(buffer)

        # If the middle one is full, move it to the right one
        if len(self.middle_segment) > self.middle_max:
            moved_buffer = self.middle_segment.pop()
            self._add_to_right(moved_buffer)

    def _add_to_right(self, buffer: Buffer):
        # Adds a buffer to the beginning of the right segment
        self.right_segment.appendleft(buffer)

    def add_buffer_to_cache(self, buffer: Buffer):
        # Adds a buffer to the cache after I/O completes
        if buffer.sector_num not in self.sector_to_buffer:
            self.sector_to_buffer[buffer.sector_num] = buffer
            self._add_to_left(buffer)

    def get_state_string(self) -> str:
        # Returns a string with the cache status for output
        left_str = ', '.join([str(b) for b in self.left_segment])
        middle_str = ', '.join([str(b) for b in self.middle_segment])
        right_str = ', '.join([str(b) for b in self.right_segment])

        return f"CACHE: Buffer cache LFU (left_max {self.left_max}, middle_max {self.middle_max}):\n" + \
            f"    List 1 (Left)   [{left_str}]\n" + \
            f"    List 2 (Middle) [{middle_str}]\n" + \
            f"    List 3 (Right)  [{right_str}]"

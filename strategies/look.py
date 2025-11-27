from distutils.dep_util import newer
from typing import List, Optional
from models.buffer import Buffer


# LOOK
class LOOKStrategy:
    # Sorts requests by sector number
    # Moves in one direction (OUT or IN)
    # Limits number of requests to one track
    # When there are no requests in the current direction - changes direction
    def __init__(self, disk, config):
        self.disk = disk
        self.config = config
        self.queue: List[Buffer] = []
        self.active_buffer: Optional[Buffer] = None

        # Direction of movement: 'OUT' (towards larger numbers) or 'IN' (towards smaller numbers)
        self.direction = 'OUT'

        # Current track access counter
        self.current_track_accesses = 0
        self.current_track_num = None

        # Max number of consecutive accesses to one track
        self.track_read_max = config.LOOK_TRACK_READ_MAX

    def add_request(self, buffer: Buffer, operation: str):
        # Adds request and sorts queue
        buffer.io_operation = operation
        self.queue.append(buffer)

        # Sort queue by number of a sector
        self.queue.sort(key=lambda b: b.sector_num)

    def get_next_buffer(self) -> Optional[Buffer]:
        # Chooses next buffer according to LOOK algorithm
        if not self.queue:
            return None

        current_track = self.disk.current_track

        # Search for buffer for current
        next_buffer = self._find_buffer_for_direction(current_track)

        if next_buffer:
            self.queue.remove(next_buffer)
            self.active_buffer = next_buffer

            # Update track counter
            buffer_track = self.disk.get_track_for_sector(next_buffer.sector_num)
            if buffer_track == self.current_track_num:
                self.current_track_accesses += 1
            else:
                self.current_track_num = buffer_track
                self.current_track_accesses = 1

            return next_buffer
        else:
            # No requests for current direction: change direction
            return self._change_direction_and_get_next()

    def _find_buffer_for_direction(self, current_track: int) -> Optional[Buffer]:
        # Finds a buffer for the current direction of travel
        # #Takes into account the limit on the number of accesses to one track
        for buffer in self.queue:
            buffer_track = self.disk.get_track_for_sector(buffer.sector_num)

            # Chek limit on track
            if buffer_track == self.current_track_num:
                if self.current_track_accesses >= self.track_read_max:
                    continue  # Skip this track

            # Check direction conformity
            if self.direction == 'OUT':
                if buffer_track >= current_track:
                    return buffer
            else:  # direction == 'IN'
                if buffer_track <= current_track:
                    return buffer
        return None

    def _change_direction_and_get_next(self) -> Optional[Buffer]:
        # Changes direction and selects first/last buffer
        # Calculates fastest transition (direct or via rewind)
        if not self.queue:
            return None

        # Change direction
        self.direction = 'IN' if self.direction == 'OUT' else 'OUT'

        # Reset track counter
        self.current_track_accesses = 0
        self.current_track_num = None

        # Choose first or last buffer in queue
        if self.direction == 'OUT':
            next_buffer = self.queue[0]
        else:
            next_buffer = self.queue[-1]

        self.queue.remove(next_buffer)
        self.active_buffer = next_buffer

        # Update counter
        buffer_track = self.disk.get_track_for_sector(next_buffer.sector_num)
        self.current_track_num = buffer_track
        self.current_track_accesses = 1

        return next_buffer

    def complete_io(self):
        # Marks the current operation as completed
        if self.active_buffer:
            self.active_buffer.io_operation = None
        self.active_buffer = None

    def get_state_string(self) -> str:
        # Returns strategy status
        active_str = str(self.active_buffer) if self.active_buffer else None
        queue_str = ', '.join([str(b) for b in self.queue])

        return f"DRIVER: Device strategy LOOK (track_read_max {self.track_read_max}):\n" + \
            f"    Direction {self.direction}\n" + \
            f"    Active buffer {active_str}\n" + \
            f"    Schedule queue [{queue_str}]"

    def has_pending_requests(self) -> bool:
        # If has requests
        return len(self.queue) > 0 or self.active_buffer is not None

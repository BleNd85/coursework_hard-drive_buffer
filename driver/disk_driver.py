from typing import Optional
from models.buffer import Buffer
from models.disk import HardDisk


# Hard disk driver
class DiskDriver:
    # The driver manages the request queue and interacts with the disk controller.
    # Uses one of the I/O scheduling strategies
    def __init__(self, disk: HardDisk, strategy):
        self.disk = disk
        self.strategy = strategy  # FIFO, LOOK, or NLOOK

        # Current active operation
        self.current_operation = None  # ('READ'/'WRITE', buffer, start_time)

        # Buffers that are currently being processed
        self.buffers_in_io = {}

    def schedule_io(self, buffer: Buffer, operation: str) -> None:
        # Adds I/O request to the drive queue, operation 'READ' or 'WRITE'
        print(f"DRIVER: Buffer {buffer} scheduled for I/O ({operation})")

        # Marks the buffer is being processed
        if buffer.sector_num not in self.buffers_in_io:
            self.buffers_in_io[buffer.sector_num] = (operation, [])

        # Adds to the strategy
        self.strategy.add_request(buffer, operation)

        # Outputs strategy state
        print(self.strategy.get_state_string())

    def start_next_io(self, current_time: float) -> Optional[tuple]:
        # Starts next I/O (operation, returns buffer, operation, completion_time) or None
        if self.current_operation:
            return None

        # Get the next buffer from the strategy
        next_buffer = self.strategy.get_next_buffer()

        if not next_buffer:
            print("DRIVER: Device strategy has nothing to do")
            return None

        operation = next_buffer.io_operation

        # Calculates the best mechanism move decision
        self._print_best_move_decision(next_buffer)

        # Calculates operation completion time
        completion_time = self._calculate_io_time(next_buffer, operation, current_time)

        # Saves current operation
        self.current_operation = (next_buffer, operation, completion_time)

        return (next_buffer, operation, completion_time)

    def _calculate_io_time(self, buffer: Buffer, operation: str, current_time: float) -> float:
        # Calculates I/O completion time
        # Travel time to the track
        target_track = self.disk.get_track_for_sector(buffer.sector_num)
        seek_time = self.disk.seek_to_track(target_track)

        # Updates current track
        self.disk.current_track = target_track

        rotational_delay = self.disk.config.ROTATION_DELAY_TIME
        transfer_time = self.disk.config.SECTOR_ACCESS_TIME

        # Total time (convert ms to µs)
        total_time_ms = seek_time + rotational_delay + transfer_time
        total_time_us = total_time_ms * 1000

        completion_time = current_time + total_time_us

        return completion_time

    def _print_best_move_decision(self, buffer: Buffer):
        # Displays information about the best way to move the mechanism
        target_track = self.disk.get_track_for_sector(buffer.sector_num)
        current_track = self.disk.current_track

        # Calculates direct distance
        direct_distance = abs(target_track - current_track)
        direct_time = direct_distance * self.disk.config.TRACK_SEEK_TIME

        rewind_time = self.disk.config.REWIND_SEEK_TIME + \
                      target_track * self.disk.config.TRACK_SEEK_TIME

        context = "next buffer in queue"

        print(f"DRIVER: Best move decision for tracks {current_track} => {buffer} ({context})")

        if direct_time == 0:
            print(f"    not to move, that is 0 us")
        else:
            print(f"    direct move time {int(direct_time * 1000)} us, " +
                  f"move time with rewind {int(rewind_time * 1000)} us")

    def complete_io(self, buffer: Buffer, operation: str):
        # Ends I/O operation
        print(f"DRIVER: Interrupt from disk")
        print(f"DRIVER: Completed I/O ({operation}) for buffer {buffer}")

        # Removes from buffers in processing
        if buffer.sector_num in self.buffers_in_io:
            del self.buffers_in_io[buffer.sector_num]

        # Informs the strategy
        self.strategy.complete_io()

        # Cleans current operation
        self.current_operation = None

        # Prints strategy state
        print(self.strategy.get_state_string())

    def is_buffer_in_io(self, sector_num: int) -> bool:
        # Checks if I/O currently in progress for this sector
        return sector_num in self.buffers_in_io

    def has_active_io(self) -> bool:
        # Has active I/O
        return self.current_operation is not None

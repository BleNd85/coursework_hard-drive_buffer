from models.buffer import Buffer
from models.process import Process


# System read and write calls
class SystemCalls:
    # Implementing system calls for working with the disk

    def __init__(self, config, cache, driver, scheduler):
        self.config = config
        self.cache = cache
        self.driver = driver
        self.scheduler = scheduler

    def sys_read(self, process: Process, sector_num: int, current_time: float) -> tuple:
        # System read call
        # Returns (success: bool, time_spent: float, blocked: bool)
        print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")

        syscall_time = self.config.SYSCALL_READ_TIME
        time_spent = syscall_time

        print(f"... worked for {int(syscall_time)} us in system call, request buffer cache")

        buffer = self.cache.find_buffer(sector_num)

        if buffer:
            print(f"CACHE: Buffer {buffer} found in cache")

            self.cache.access_buffer(sector_num,
                                     self.driver.disk.get_track_for_sector(sector_num))

            print(self.cache.get_state_string())

            return (True, time_spent, False)

        else:
            # Checks if I/O is already in progress for this sector
            if self.driver.is_buffer_in_io(sector_num):
                print(f"CACHE: Buffer for sector {sector_num} not found in cache")
                print(f"SCHEDULER: But this buffer is scheduled for I/O (READ)")
                return (False, time_spent, True)  # Блокуємо процес

            print(f"CACHE: Buffer for sector {sector_num} not found in cache")

            free_buffer = self._get_or_evict_buffer(sector_num, current_time + time_spent)

            if free_buffer is None:
                return (False, time_spent, True)

            track_num = self.driver.disk.get_track_for_sector(sector_num)
            free_buffer.load_sector(sector_num, track_num)

            self.driver.schedule_io(free_buffer, 'READ')

            return (False, time_spent, True)

    def sys_write(self, process: Process, sector_num: int, current_time: float) -> tuple:
        # System write call
        # Returns (success: bool, time_spent: float, blocked: bool)
        print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")

        syscall_time = self.config.SYSCALL_WRITE_TIME
        time_spent = syscall_time

        print(f"... worked for {int(syscall_time)} us in system call, request buffer cache")

        buffer = self.cache.find_buffer(sector_num)

        if buffer:
            print(f"CACHE: Buffer {buffer} found in cache")

            self.cache.access_buffer(sector_num,
                                     self.driver.disk.get_track_for_sector(sector_num))

            print(self.cache.get_state_string())

            buffer.mark_modified()
            print(f"SCHEDULER: Process `{process.name}` modified buffer {buffer}")

            return (True, time_spent, False)

        else:
            # Checks if I/O is already in progress for this sector
            if self.driver.is_buffer_in_io(sector_num):
                print(f"CACHE: Buffer for sector {sector_num} not found in cache")
                print(f"SCHEDULER: But this buffer is scheduled for I/O (READ)")
                return (False, time_spent, True)

            print(f"CACHE: Buffer for sector {sector_num} not found in cache")

            free_buffer = self._get_or_evict_buffer(sector_num, current_time + time_spent)

            if free_buffer is None:
                return (False, time_spent, True)

            track_num = self.driver.disk.get_track_for_sector(sector_num)
            free_buffer.load_sector(sector_num, track_num)

            self.driver.schedule_io(free_buffer, 'READ')

            return (False, time_spent, True)

    def _get_or_evict_buffer(self, sector_num: int, current_time: float) -> Buffer:
        # Gets a free buffer or replaces an existing one
        # If the replaced buffer is modified - starts writing to disk
        print("CACHE: Get free buffer")

        evicted_buffer = self.cache.get_free_buffer()

        # Checks whether the displaced buffer needs to be written
        if evicted_buffer.modified and evicted_buffer.sector_num is not None:
            print(f"CACHE: Buffer {evicted_buffer} removed from cache")
            print(self.cache.get_state_string())
            print("SCHEDULER: This buffer was modified, will write it")

            # Sends WRITE
            self.driver.schedule_io(evicted_buffer, 'WRITE')

            # Return None - the process have to be blocked
            return None

        # Deletes from cache if it was there
        if evicted_buffer.sector_num is not None:
            print(f"CACHE: Buffer {evicted_buffer} removed from cache")
            print(self.cache.get_state_string())
            print("SCHEDULER: This buffer was not modified, will reuse it")

        return evicted_buffer

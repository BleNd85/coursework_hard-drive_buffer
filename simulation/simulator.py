from models.process import Process
from models.disk import HardDisk
from cache.lfu_cache import LFUCache
from driver.disk_driver import DiskDriver
from scheduler.process_scheduler import ProcessScheduler
from kernel.syscalls import SystemCalls


class Simulator:
    # Event-driven OS simulator

    def __init__(self, config, strategy_class):
        self.config = config
        self.current_time = 0.0

        # System components
        self.disk = HardDisk(config)
        self.cache = LFUCache(config)
        self.strategy = strategy_class(self.disk, config)  # Передаємо обидва
        self.driver = DiskDriver(self.disk, self.strategy)
        self.process_scheduler = ProcessScheduler(config)
        self.syscalls = SystemCalls(config, self.cache, self.driver, self.process_scheduler)

        self.next_disk_interrupt_time = None

        # Process status tracking
        self.waiting_for_write_completion = {}  # process -> sector after write

    def add_process(self, process: Process):
        # Adds process
        self.process_scheduler.add_process(process)

    def run(self):
        # Main cycle
        print()
        print("Settings:")
        self._print_settings()
        print()

        iteration = 0

        while True:
            iteration += 1
            if iteration > 1000:
                print("ERROR: Too many iterations")
                break

            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")

            # Disk interruption
            if self._check_disk_interrupt():
                continue

            # Chooses process
            if not self.process_scheduler.current_process:
                if self.process_scheduler.has_ready_processes():
                    next_proc = self.process_scheduler.schedule_next()
                    self.process_scheduler.switch_context(next_proc)
                elif self.process_scheduler.all_processes_completed():
                    print("SCHEDULER: RunQ is empty")
                    print("SCHEDULER: All processes completed")
                    self._flush_cache()
                    break
                else:
                    print("SCHEDULER: RunQ is empty")
                    self._idle_until_interrupt()
                    continue

            # Runs the current process
            current = self.process_scheduler.current_process
            operation = current.get_next_operation()

            if operation is None:
                self.process_scheduler.terminate_current_process()
                continue

            op_type, sector_num = operation

            if op_type == 'r':
                self._execute_read(current, sector_num)
            elif op_type == 'w':
                self._execute_write(current, sector_num)

        print()
        print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
        print("SCHEDULER: Scheduler has nothing to do, exit")

    def _execute_read(self, process: Process, sector_num: int):
        # Execute read
        print(f"SCHEDULER: User mode for process `{process.name}`")
        print(f"SCHEDULER: Process `{process.name}` invoked read() for sector {sector_num}")

        success, time_spent, blocked = self.syscalls.sys_read(
            process, sector_num, self.current_time
        )

        self.current_time += time_spent
        self.process_scheduler.consume_time(time_spent)

        if blocked:
            process.blocked_on_sector = sector_num
            self.process_scheduler.block_current_process()
            self._start_next_io()
        else:
            # Cache hit - processes data
            print()
            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
            print(f"SCHEDULER: User mode for process `{process.name}`")

            time_after = self.config.AFTER_READING_TIME
            print(f"... worked for {int(time_after)} us in user mode (completed)")

            self.current_time += time_after
            self.process_scheduler.consume_time(time_after)

            process.advance_operation()

    def _execute_write(self, process: Process, sector_num: int):
        # Execute write
        print(f"SCHEDULER: User mode for process `{process.name}`")

        # Forms data
        time_before = self.config.BEFORE_WRITING_TIME
        print(f"... worked for {int(time_before)} us in user mode (completed)")

        self.current_time += time_before
        self.process_scheduler.consume_time(time_before)

        print(f"SCHEDULER: Process `{process.name}` invoked write() for sector {sector_num}")

        success, time_spent, blocked = self.syscalls.sys_write(
            process, sector_num, self.current_time
        )

        self.current_time += time_spent
        self.process_scheduler.consume_time(time_spent)

        if blocked:
            process.blocked_on_sector = sector_num
            self.process_scheduler.block_current_process()
            self._start_next_io()
        else:
            print()
            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
            print(f"SCHEDULER: User mode for process `{process.name}`")
            process.advance_operation()

    def _start_next_io(self):
        # Starts next I/O
        if not self.driver.has_active_io():
            io_info = self.driver.start_next_io(self.current_time)

            if io_info:
                buffer, operation, completion_time = io_info
                self.next_disk_interrupt_time = completion_time
                print(f"SCHEDULER: Next interrupt from disk will be at {int(completion_time)} us")

    def _check_disk_interrupt(self) -> bool:
        # Checks interruption
        if self.next_disk_interrupt_time and self.current_time >= self.next_disk_interrupt_time:
            print("SCHEDULER: Disk interrupt handler was invoked")

            buffer, operation, _ = self.driver.current_operation
            self.driver.complete_io(buffer, operation)

            self.next_disk_interrupt_time = None

            if operation == 'READ':
                self.cache.add_buffer_to_cache(buffer)
                print(f"CACHE: Buffer {buffer} added to cache")
                print(self.cache.get_state_string())

                # Unblocks processes waiting for this sector
                self._wakeup_waiting_processes(buffer.sector_num)
            elif operation == 'WRITE':
                buffer.reset()
                self.cache.free_buffers.append(buffer)
                print("CACHE: Put free buffer")

                # Unblocks alls processes, because a free buffer appeared
                self._wakeup_all_blocked_processes()

            intr_time = self.config.DISK_INTR_TIME
            print(f"... worked for {int(intr_time)} us in disk interrupt handler")

            self.current_time += intr_time
            self.process_scheduler.consume_time(intr_time)

            self._start_next_io()

            return True

        return False

    def _wakeup_waiting_processes(self, sector_num: int):
        # Unblocks processes waiting for a specific sector
        for process in self.process_scheduler.blocked_processes[:]:
            if process.blocked_on_sector == sector_num:
                self.process_scheduler.unblock_process(process)
                process.blocked_on_sector = None

    def _wakeup_all_blocked_processes(self):
        # Unblocks all blocked processes (after WRITE of the evicted buffer)"""
        for process in self.process_scheduler.blocked_processes[:]:
            self.process_scheduler.unblock_process(process)
            process.blocked_on_sector = None

    def _idle_until_interrupt(self):
        # Waits for interruption
        if self.next_disk_interrupt_time:
            idle_time = self.next_disk_interrupt_time - self.current_time
            print()
            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
            print(f"SCHEDULER: Scheduler has nothing to do for {int(idle_time)} us ")
            self.current_time = self.next_disk_interrupt_time
        else:
            print("ERROR: No pending interrupts")

    def _flush_cache(self):
        # Writes modified buffers
        print("SCHEDULER: Flushing buffer cache")

        all_buffers = (self.cache.left_segment +
                       self.cache.middle_segment +
                       self.cache.right_segment)

        for buffer in all_buffers:
            print(f"CACHE: Buffer {buffer} removed from cache")

            if buffer.modified:
                self.driver.schedule_io(buffer, 'WRITE')

        # Cleans caches
        self.cache.left_segment = []
        self.cache.middle_segment = []
        self.cache.right_segment = []
        self.cache.sector_to_buffer = {}

        # Execute recordings
        while self.strategy.has_pending_requests() or self.driver.has_active_io():
            self._start_next_io()

            if self.next_disk_interrupt_time:
                idle_time = self.next_disk_interrupt_time - self.current_time
                print()
                print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
                print(f"SCHEDULER: Scheduler has nothing to do for {int(idle_time)} us ")
                self.current_time = self.next_disk_interrupt_time

                # Interrupt handling for flush
                if self.driver.current_operation:
                    buffer, operation, _ = self.driver.current_operation
                    print("SCHEDULER: Disk interrupt handler was invoked")
                    self.driver.complete_io(buffer, operation)
                    self.next_disk_interrupt_time = None

                    buffer.reset()
                    self.cache.free_buffers.append(buffer)
                    print("CACHE: Put free buffer")

                    intr_time = self.config.DISK_INTR_TIME
                    print(f"... worked for {int(intr_time)} us in disk interrupt handler")
                    self.current_time += intr_time

    def _print_settings(self):
        # Prints configuration
        c = self.config
        print(f"    syscall_read_time   {int(c.SYSCALL_READ_TIME)}")
        print(f"    syscall_write_time  {int(c.SYSCALL_WRITE_TIME)}")
        print(f"    disk_intr_time      {int(c.DISK_INTR_TIME)}")
        print(f"    quantum_time        {int(c.QUANTUM_TIME):,}".replace(',', "'"))
        print(f"    before_writing_time {int(c.BEFORE_WRITING_TIME):,}".replace(',', "'"))
        print(f"    after_reading_time  {int(c.AFTER_READING_TIME):,}".replace(',', "'"))
        print()
        print(f"    buffers_num         {c.BUFFERS_NUM}")
        print()
        print(f"    tracks_num          {c.TRACKS_NUM}")
        print(f"    sectors_per_track   {c.SECTORS_PER_TRACK}")
        print(f"    track_seek_time     {int(c.TRACK_SEEK_TIME * 1000)}")
        print(f"    rewind_seek_time    {int(c.REWIND_SEEK_TIME)}")
        print()
        print(f"    rotation_delay_time {int(c.ROTATION_DELAY_TIME * 1000):,}".replace(',', "'"))
        print(f"    sector_access_time  {int(c.SECTOR_ACCESS_TIME * 1000)}")

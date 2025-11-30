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
        self.strategy = strategy_class(self.disk, config)
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

            if self._check_and_handle_interrupt():
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
        # Execute read operation
        if process.after_read_remaining_time > 0:
            return self._continue_after_read_processing(process)

        if process.syscall_in_progress == ('read', sector_num):
            return self._continue_syscall_read(process, sector_num)

        print(f"SCHEDULER: User mode for process `{process.name}`")
        print(f"SCHEDULER: Process `{process.name}` invoked read() for sector {sector_num}")

        return self._start_syscall_read(process, sector_num)

    def _start_syscall_read(self, process: Process, sector_num: int):
        syscall_time = self.config.SYSCALL_READ_TIME

        if self._will_interrupt_during(syscall_time):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
            print(f"... worked for {int(time_until_interrupt)} us in system call (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.syscall_remaining_time = syscall_time - time_until_interrupt
            process.syscall_in_progress = ('read', sector_num)
            return

        success, time_spent, blocked = self.syscalls.sys_read(
            process, sector_num, self.current_time
        )

        self.current_time += time_spent
        self.process_scheduler.consume_time(time_spent)

        if blocked:
            process.blocked_on_sector = sector_num
            process.syscall_in_progress = None
            self.process_scheduler.block_current_process()
            self._start_next_io()
        else:
            process.syscall_in_progress = None
            self._start_after_read_processing(process)

    def _continue_syscall_read(self, process: Process, sector_num: int):
        remaining_time = process.syscall_remaining_time

        if self._will_interrupt_during(remaining_time):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
            print(f"... worked for {int(time_until_interrupt)} us in system call (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.syscall_remaining_time = remaining_time - time_until_interrupt
            return

        print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
        print(f"... worked for {int(remaining_time)} us in system call, request buffer cache")

        self.current_time += remaining_time
        self.process_scheduler.consume_time(remaining_time)

        process.syscall_remaining_time = 0

        buffer = self.cache.find_buffer(sector_num)

        if buffer:
            print(f"CACHE: Buffer {buffer} found in cache")
            self.cache.access_buffer(sector_num, self.driver.disk.get_track_for_sector(sector_num))
            print(self.cache.get_state_string())

            process.syscall_in_progress = None
            self._start_after_read_processing(process)
        else:
            print(f"CACHE: Buffer for sector {sector_num} not found in cache")

            if self.driver.is_buffer_in_io(sector_num):
                print(f"SCHEDULER: But this buffer is scheduled for I/O (READ)")
                process.blocked_on_sector = sector_num
                process.syscall_in_progress = None
                self.process_scheduler.block_current_process()
                return

            free_buffer = self._get_free_buffer_for_read(sector_num)
            if free_buffer is None:
                process.blocked_on_sector = sector_num
                process.syscall_in_progress = None
                self.process_scheduler.block_current_process()
                self._start_next_io()
                return

            track_num = self.driver.disk.get_track_for_sector(sector_num)
            free_buffer.load_sector(sector_num, track_num)
            self.driver.schedule_io(free_buffer, 'READ')

            process.blocked_on_sector = sector_num
            process.syscall_in_progress = None
            self.process_scheduler.block_current_process()
            self._start_next_io()

    def _start_after_read_processing(self, process: Process):
        print()
        print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
        print(f"SCHEDULER: User mode for process `{process.name}`")

        time_after = self.config.AFTER_READING_TIME

        if self._will_interrupt_during(time_after):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"... worked for {int(time_until_interrupt)} us in user mode (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.after_read_remaining_time = time_after - time_until_interrupt
            return

        print(f"... worked for {int(time_after)} us in user mode (completed)")

        self.current_time += time_after
        self.process_scheduler.consume_time(time_after)

        process.advance_operation()

    def _continue_after_read_processing(self, process: Process):
        remaining_time = process.after_read_remaining_time

        print(f"SCHEDULER: User mode for process `{process.name}`")

        if self._will_interrupt_during(remaining_time):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"... worked for {int(time_until_interrupt)} us in user mode (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.after_read_remaining_time = remaining_time - time_until_interrupt
            return

        print(f"... worked for {int(remaining_time)} us in user mode (completed)")

        self.current_time += remaining_time
        self.process_scheduler.consume_time(remaining_time)

        process.after_read_remaining_time = 0
        process.advance_operation()

    def _execute_write(self, process: Process, sector_num: int):
        if process.syscall_in_progress == ('write', sector_num):
            return self._continue_syscall_write(process, sector_num)

        if process.before_write_remaining_time > 0:
            return self._continue_before_write_processing(process, sector_num)

        print(f"SCHEDULER: User mode for process `{process.name}`")

        time_before = self.config.BEFORE_WRITING_TIME

        if self._will_interrupt_during(time_before):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"... worked for {int(time_until_interrupt)} us in user mode (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.before_write_remaining_time = time_before - time_until_interrupt
            return

        print(f"... worked for {int(time_before)} us in user mode (completed)")

        self.current_time += time_before
        self.process_scheduler.consume_time(time_before)

        self._start_syscall_write(process, sector_num)

    def _continue_before_write_processing(self, process: Process, sector_num: int):
        remaining_time = process.before_write_remaining_time

        print(f"SCHEDULER: User mode for process `{process.name}`")

        if self._will_interrupt_during(remaining_time):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"... worked for {int(time_until_interrupt)} us in user mode (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.before_write_remaining_time = remaining_time - time_until_interrupt
            return

        print(f"... worked for {int(remaining_time)} us in user mode (completed)")

        self.current_time += remaining_time
        self.process_scheduler.consume_time(remaining_time)

        process.before_write_remaining_time = 0

        self._start_syscall_write(process, sector_num)

    def _start_syscall_write(self, process: Process, sector_num: int):
        print(f"SCHEDULER: Process `{process.name}` invoked write() for sector {sector_num}")

        syscall_time = self.config.SYSCALL_WRITE_TIME

        if self._will_interrupt_during(syscall_time):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
            print(f"... worked for {int(time_until_interrupt)} us in system call (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.syscall_remaining_time = syscall_time - time_until_interrupt
            process.syscall_in_progress = ('write', sector_num)
            return

        success, time_spent, blocked = self.syscalls.sys_write(
            process, sector_num, self.current_time
        )

        self.current_time += time_spent
        self.process_scheduler.consume_time(time_spent)

        if blocked:
            process.blocked_on_sector = sector_num
            process.syscall_in_progress = None
            self.process_scheduler.block_current_process()
            self._start_next_io()
        else:
            process.syscall_in_progress = None
            print()
            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
            print(f"SCHEDULER: User mode for process `{process.name}`")
            process.advance_operation()

    def _continue_syscall_write(self, process: Process, sector_num: int):
        remaining_time = process.syscall_remaining_time

        if self._will_interrupt_during(remaining_time):
            time_until_interrupt = self.next_disk_interrupt_time - self.current_time

            print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
            print(f"... worked for {int(time_until_interrupt)} us in system call (interrupted)")

            self.current_time = self.next_disk_interrupt_time
            self.process_scheduler.consume_time(time_until_interrupt)

            process.syscall_remaining_time = remaining_time - time_until_interrupt
            return

        print(f"SCHEDULER: Kernel mode (syscall) for process `{process.name}`")
        print(f"... worked for {int(remaining_time)} us in system call, request buffer cache")

        self.current_time += remaining_time
        self.process_scheduler.consume_time(remaining_time)

        process.syscall_remaining_time = 0

        buffer = self.cache.find_buffer(sector_num)

        if buffer:
            print(f"CACHE: Buffer {buffer} found in cache")
            self.cache.access_buffer(sector_num, self.driver.disk.get_track_for_sector(sector_num))
            print(self.cache.get_state_string())

            buffer.mark_modified()
            print(f"SCHEDULER: Process `{process.name}` modified buffer {buffer}")

            process.syscall_in_progress = None
            print()
            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
            print(f"SCHEDULER: User mode for process `{process.name}`")
            process.advance_operation()
        else:
            print(f"CACHE: Buffer for sector {sector_num} not found in cache")

            if self.driver.is_buffer_in_io(sector_num):
                print(f"SCHEDULER: But this buffer is scheduled for I/O (READ)")
                process.blocked_on_sector = sector_num
                process.syscall_in_progress = None
                self.process_scheduler.block_current_process()
                return

            free_buffer = self._get_free_buffer_for_write(sector_num)
            if free_buffer is None:
                process.blocked_on_sector = sector_num
                process.syscall_in_progress = None
                self.process_scheduler.block_current_process()
                self._start_next_io()
                return

            track_num = self.driver.disk.get_track_for_sector(sector_num)
            free_buffer.load_sector(sector_num, track_num)
            self.driver.schedule_io(free_buffer, 'READ')

            process.blocked_on_sector = sector_num
            process.syscall_in_progress = None
            self.process_scheduler.block_current_process()
            self._start_next_io()

    def _will_interrupt_during(self, time_duration: float) -> bool:
        if self.next_disk_interrupt_time is None:
            return False

        return self.current_time < self.next_disk_interrupt_time < self.current_time + time_duration

    def _get_free_buffer_for_read(self, sector_num: int):
        print("CACHE: Get free buffer")

        evicted_buffer = self.cache.get_free_buffer()

        if evicted_buffer.modified and evicted_buffer.sector_num is not None:
            print(f"CACHE: Buffer {evicted_buffer} removed from cache")
            print(self.cache.get_state_string())
            print("SCHEDULER: This buffer was modified, will write it")

            self.driver.schedule_io(evicted_buffer, 'WRITE')
            return None

        if evicted_buffer.sector_num is not None:
            print(f"CACHE: Buffer {evicted_buffer} removed from cache")
            print(self.cache.get_state_string())
            print("SCHEDULER: This buffer was not modified, will reuse it")

        return evicted_buffer

    def _get_free_buffer_for_write(self, sector_num: int):
        return self._get_free_buffer_for_read(sector_num)

    def _check_and_handle_interrupt(self) -> bool:
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

                # Unblocks all processes because a free buffer appeared
                self._wakeup_all_blocked_processes()

            intr_time = self.config.DISK_INTR_TIME
            print(f"... worked for {int(intr_time)} us in disk interrupt handler")

            self.current_time += intr_time
            self.process_scheduler.consume_time(intr_time)

            self._start_next_io()

            return True

        return False

    def _start_next_io(self):
        # Starts next I/O
        if not self.driver.has_active_io():
            io_info = self.driver.start_next_io(self.current_time)

            if io_info:
                buffer, operation, completion_time = io_info
                self.next_disk_interrupt_time = completion_time
                print(f"SCHEDULER: Next interrupt from disk will be at {int(completion_time)} us")

    def _idle_until_interrupt(self):
        # Waits for interruption
        if self.next_disk_interrupt_time:
            idle_time = self.next_disk_interrupt_time - self.current_time
            print()
            print(f"SCHEDULER: {int(self.current_time)} us (NEXT ITERATION)")
            print(f"SCHEDULER: Scheduler has nothing to do for {int(idle_time)} us")

            self.current_time = self.next_disk_interrupt_time
        else:
            print("ERROR: No pending interrupts and no ready processes")

    def _wakeup_waiting_processes(self, sector_num: int):
        # Unblocks processes waiting for a specific sector
        for process in self.process_scheduler.blocked_processes[:]:
            if process.blocked_on_sector == sector_num:
                self.process_scheduler.unblock_process(process)
                process.blocked_on_sector = None

    def _wakeup_all_blocked_processes(self):
        # Unblocks all blocked processes (after WRITE of the evicted buffer)
        for process in self.process_scheduler.blocked_processes[:]:
            self.process_scheduler.unblock_process(process)
            process.blocked_on_sector = None

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
        print(f"    syscall_read_time   {int(c.SYSCALL_READ_TIME):,}".replace(',', "'"))
        print(f"    syscall_write_time  {int(c.SYSCALL_WRITE_TIME):,}".replace(',', "'"))
        print(f"    disk_intr_time      {int(c.DISK_INTR_TIME)}")
        print(f"    quantum_time        {int(c.QUANTUM_TIME):,}".replace(',', "'"))
        print(f"    before_writing_time {int(c.BEFORE_WRITING_TIME):,}".replace(',', "'"))
        print(f"    after_reading_time  {int(c.AFTER_READING_TIME):,}".replace(',', "'"))
        print()
        print(f"    buffers_num         {c.BUFFERS_NUM}")
        print()
        print(f"    sectors_per_track   {c.SECTORS_PER_TRACK}")
        print(f"    track_seek_time     {int(c.TRACK_SEEK_TIME * 1000):,}".replace(',', "'"))
        print(f"    rewind_seek_time    {int(c.REWIND_SEEK_TIME):,}".replace(',', "'"))
        print()
        print(f"    rotation_delay_time {int(c.ROTATION_DELAY_TIME * 1000):,}".replace(',', "'"))
        print(f"    sector_access_time  {int(c.SECTOR_ACCESS_TIME * 1000)}")

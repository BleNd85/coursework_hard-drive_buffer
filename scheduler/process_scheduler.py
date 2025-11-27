from typing import List, Optional
from collections import deque
from models.process import Process


# Process scheduler
class ProcessScheduler:

    # Process scheduler
    # All processes have the same priority
    # Each process executes its own time quantum

    def __init__(self, config):
        self.config = config
        self.quantum_time = config.QUANTUM_TIME  # us

        # Queue of ready processes (READY)
        self.ready_queue: deque[Process] = deque()

        # Current process
        self.current_process: Optional[Process] = None

        # Remaining quantum for current process
        self.remaining_quantum = 0

        # Blocked processes
        self.blocked_processes: List[Process] = []

        # Completed processes
        self.terminated_processes: List[Process] = []

    def add_process(self, process: Process):
        # Adds new process
        print(f"SCHEDULER: Process `{process.name}` was added")
        print(f"    {process}")
        process.state = 'READY'
        self.ready_queue.append(process)

    def schedule_next(self) -> Optional[Process]:
        # Chooses next process from the queue (the first one)
        if not self.ready_queue:
            return None

        next_process = self.ready_queue.popleft()
        next_process.state = 'RUNNING'
        self.current_process = next_process

        self.remaining_quantum = self.quantum_time

        return next_process

    def switch_context(self, new_process: Process):
        # Switches context on another process
        if self.current_process:
            print(f"SCHEDULER: Switch context from process `{self.current_process.name}` " +
                  f"to process `{new_process.name}`")
        else:
            print(f"SCHEDULER: Switch context to process `{new_process.name}`")

        self.current_process = new_process
        new_process.state = 'RUNNING'

    def consume_time(self, time_us: float):
        # Consumes time for the current process
        if self.current_process:
            self.remaining_quantum -= time_us

            # If quantum is up returns to the queue
            if self.remaining_quantum <= 0:
                self._preempt_current_process()

    def _preempt_current_process(self):
        # Terminates the current process (quantum is over)
        # Returns it to the queue
        if self.current_process and self.current_process.state == 'RUNNING':
            self.current_process.state = 'READY'
            self.ready_queue.append(self.current_process)
            self.current_process = None

    def block_current_process(self, reason: str = ""):
        # Blocks current process (waits for I/O)
        if self.current_process:
            print(f"SCHEDULER: Block process `{self.current_process.name}`")
            self.current_process.state = 'BLOCKED'
            self.blocked_processes.append(self.current_process)
            self.current_process = None

    def unblock_process(self, process: Process):
        # Unlocks current process (I/O is completed)
        if process in self.blocked_processes:
            print(f"SCHEDULER: Wake up process `{process.name}`")
            self.blocked_processes.remove(process)
            process.state = 'READY'
            self.ready_queue.append(process)

    def terminate_current_process(self):
        # Terminates current process
        if self.current_process:
            print(f"SCHEDULER: Process `{self.current_process.name}` exited")
            self.current_process.state = 'TERMINATED'
            self.terminated_processes.append(self.current_process)
            self.current_process = None

    def has_ready_processes(self) -> bool:
        # Checks if there are any READY processes
        return len(self.ready_queue) > 0

    def has_any_processes(self) -> bool:
        # Checks if there are any active processes (READY OR BLOCKED)
        return len(self.ready_queue) > 0 or \
            len(self.blocked_processes) > 0 or \
            self.current_process is not None

    def all_processes_completed(self) -> bool:
        # Checks if all processes are complete
        return not self.has_any_processes()

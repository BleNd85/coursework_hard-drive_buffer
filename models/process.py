from typing import List, Tuple


# User process
class Process:
    # User process
    # Performs a sequence of sector read/write operations
    def __init__(self, name: str, operations: List[Tuple[str, int]]):
        # operations: list ('r', sector) or ('w', sector)
        self.name = name
        self.operations = operations
        self.current_op_index = 0

        # Process state
        self.state = 'READY'  # READY, RUNNING, BLOCKED, TERMINATED
        self.remaining_quantum = 0
        self.blocked_on_sector = None

    def get_next_operation(self) -> tuple[str, int] | None:
        # Returns next operation
        if self.current_op_index < len(self.operations):
            return self.operations[self.current_op_index]
        return None

    def advance_operation(self):
        # Goes to the next operation
        self.current_op_index += 1

    def is_finished(self) -> bool:
        # Checks if the process ended all operations
        return self.current_op_index >= len(self.operations)

    def __repr__(self):
        ops_str = ', '.join([f"{{'{op}',{sec}}}" for op, sec in self.operations])
        return f"{{{ops_str}}}"

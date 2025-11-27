# Buffer for storing the contents of the sector in RAM
class Buffer:
    # Buffer cache buffer
    # Stores the contents of one sector of the hard drive
    def __init__(self, buffer_id: int):
        self.buffer_id = buffer_id
        self.sector_num = None
        self.track_num = None
        self.modified = None
        self.data = None

        # For LFU algorithm
        self.access_counter = 0
        self.last_access_time = 0

        # For I/O operation
        self.io_operation = None # READ or WRITE

    def load_sector(self, sector_num: int, track_num: int, data=None):
        # Loads sector into buffer
        self.sector_num = sector_num
        self.track_num = track_num
        self.data = data
        self.modified = False
        self.access_counter = 1

    def mark_modified(self):
        # Marks buffer as modified
        self.modified = True

    def increment_access(self):
        # Increments hit counter (for LFU)
        self.access_counter += 1

    def reset(self):
        # Cleans buffer
        self.sector_num = None
        self.track_num = None
        self.modified = False
        self.data = None
        self.access_counter = 0

    def __repr__(self):
        return f"({self.track_num}:{self.sector_num})"

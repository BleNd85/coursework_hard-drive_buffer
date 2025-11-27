class SystemConfig:
    # System and drive config

    def __init__(self):
        # Hard disk parameters
        self.TRACKS_NUM = 10000
        self.SECTORS_PER_TRACK = 500
        self.TRACK_SEEK_TIME = 0.5  # ms
        self.REWIND_SEEK_TIME = 10.0  # ms
        self.ROTATION_SPEED = 7500  # rpm

        # Buffer cache parameters
        self.BUFFERS_NUM = 10

        # System calls parameters us
        self.SYSCALL_READ_TIME = 150
        self.SYSCALL_WRITE_TIME = 150
        self.DISK_INTR_TIME = 50

        # Process scheduler parameters
        self.QUANTUM_TIME = 20000
        self.BEFORE_WRITING_TIME = 7000
        self.AFTER_READING_TIME = 7000

        # LFU parameters
        self.LFU_LEFT_SEGMENT_MAX = 3
        self.LFU_MIDDLE_SEGMENT_MAX = 2

        # LOOK parameters
        self.LOOK_TRACK_READ_MAX = 1

        # NLOOK parameters
        self.NLOOK_QUEUE_MAX_LENGTH = 10

    @property
    def ROTATION_DELAY_TIME(self):
        # Average rotation delay
        return ((60 * 1000) / self.ROTATION_SPEED) / 2

    @property
    def SECTOR_ACCESS_TIME(self):
        # Sector access time ms
        return ((60 * 1000) / self.ROTATION_SPEED) / self.SECTORS_PER_TRACK

class SystemConfig:
    # Hard drive properties
    TRACKS_NUM = 10000  # Number of tracks
    SECTORS_PER_TRACK = 500  # Sectors per track
    TRACK_SEEK_TIME = 0.5  # Time to move one track (ms)
    REWIND_SEEK_TIME = 10.0  # Time to first/outer track (ms)
    ROTATION_SPEED = 7500  # Rotation speed (rpm)

    @property
    def ROTATION_DELAY_TIME(self):
        # Average rotation delay (ms)
        return ((60 * 1000) / self.ROTATION_SPEED) / 2

    @property
    def SECTOR_ACCESS_TIME(self):
        # Read/write time per sector (ms)
        return ((60 * 1000) / self.ROTATION_SPEED) / self.SECTORS_PER_TRACK

    # Buffer cache params
    BUFFERS_NUM = 10  # Overall amount of buffers

    # Process planner params
    SYSCAL_READ_TIME = 150  # (us)
    SYSCAL_WRITE_TIME = 150  # (us)
    DISK_INTR_TIME = 50  # Interrupt processing time (us)

    QUANTUM_TIME = 20000
    BEFORE_WRITING_TIME = 7000
    AFTER_READING_TIME = 7000

    # Algorithms params
    # LFU with 3 segments
    LFU_LEFT_SEGMENT_MAX = 3  # Max buffers in left segment
    LFU_MIDDLE_SEGMENT_MAX = 2  # Max buffers in middle segment

    # LOOK
    LOOK_TRACK_READ_MAX = 1  # Max number of hits to one track

    # NLOOK
    NLOOK_QUEUE_MAX_LENGTH = 10  # Max queue length

from functools import total_ordering


class Sector:
    # Sector
    def __init__(self, track_num: int, sector_num: int):
        self.track_num = track_num  # Track number
        self.sector_num = sector_num  # Absolute sector number
        self.data = None  # Sector data

    def __repr__(self):
        return f"({self.track_num}:{self.sector_num})"


class HardDisk:
    # Hard drive with logical block addressing
    def __init__(self, config):
        self.config = config
        self.tracks_num = config.TRACKS_NUM
        self.sectors_per_track = config.SECTORS_PER_TRACK
        self.total_sectors = self.tracks_num * self.sectors_per_track

        # Current position of the drive mechanism
        self.current_track = 0
        self.current_sector_position = 0

        # Statistics
        self.total_seeks = 0
        self.total_seek_time = 0

    def get_track_for_sector(self, sector_num: int) -> int:
        # Specifies the track number for the logical sector number
        return sector_num // self.sectors_per_track

    def calculate_seek_time(self, from_track: int, to_track: int) -> float:
        # Calculates seek time. Can be direct or rewind
        # Direct
        direct_distance = abs(to_track - from_track)
        direct_time = direct_distance * self.config.TRACK_SEEK_TIME

        # Rewind
        rewind_time = self.config.REWIND_SEEK_TIME + to_track * self.config.TRACK_SEEK_TIME

        # Choose the shortest
        return min(direct_time, rewind_time)

    def seek_to_track(self, track_num: int) -> float:
        # Moves the drive mechanism to the specified track
        seek_time = self.calculate_seek_time(self.current_track, track_num)
        self.current_track = track_num
        self.total_seeks += 1
        self.total_seek_time += seek_time
        return seek_time

    def access_sector(self, sector_num: int, operation: str) -> float:
        # Performs a sector read/write operation
        # Returns the total operation time (seek + rotational delay + transfer)
        track = self.get_track_for_sector(sector_num)
        seek_time = self.seek_to_track(track)
        rotational_delay = self.config.ROTATION_DELAY_TIME
        transfer_time = self.config.SECTOR_ACCESS_TIME

        total_time = seek_time + rotational_delay + transfer_time
        return total_time

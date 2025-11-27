from abc import ABC, abstractmethod
from typing import Optional
from models.buffer import Buffer


# Base class for buffer cache management algorithms
class BaseCache(ABC):
    # Abstract base class for buffer cache
    @abstractmethod
    def find_buffer(self, sector_unm: int) -> Optional[Buffer]:
        # Searches for a buffer with the specified sector
        pass

    @abstractmethod
    def get_free_buffer(self) -> Buffer:
        # Gets a free buffer (possibly with overflow)
        pass

    @abstractmethod
    def access_buffer(self, sector_num: int, track_num: int) -> Buffer:
        # Accessing the buffer (to update metadata)
        pass

    @abstractmethod
    def get_state_string(self) -> str:
        # Returns a string with the cache status
        pass

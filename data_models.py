# data_models.py

from dataclasses import dataclass
from typing import Tuple

@dataclass
class Station:
    id: int
    x: float
    y: float
    capacity: int
    bikes: int
    neighbourhood: str

    def has_bike(self) -> bool:
        return self.bikes > 0

    def has_space(self) -> bool:
        return self.bikes < self.capacity

    def take_bike(self) -> bool:
        """
        Takes a bike if available. Returns True on success, False on failure.
        """
        if self.has_bike():
            self.bikes -= 1
            return True
        return False

    def return_bike(self) -> bool:
        """
        Returns a bike if space is available. Returns True on success, False on failure.
        """
        if self.has_space():
            self.bikes += 1
            return True
        return False

@dataclass
class User:
    id: int
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    origin_type: str
    destination_type: str
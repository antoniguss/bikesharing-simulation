# data_models.py
from dataclasses import dataclass
from typing import Tuple

@dataclass
class Station:
    """Represents a bike station with its properties and state."""
    id: int
    x: float
    y: float
    capacity: int
    bikes: int
    neighbourhood: str

    def has_bike(self) -> bool:
        """Checks if there is at least one bike available."""
        return self.bikes > 0

    def has_space(self) -> bool:
        """Checks if there is at least one empty dock."""
        return self.bikes < self.capacity

    def take_bike(self) -> bool:
        """Removes a bike from the station if available. Returns True on success."""
        if self.has_bike():
            self.bikes -= 1
            return True
        return False

    def return_bike(self) -> bool:
        """Adds a bike to the station if space is available. Returns True on success."""
        if self.has_space():
            self.bikes += 1
            return True
        return False

@dataclass
class User:
    """Represents a user wanting to make a trip."""
    id: int
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    origin_type: str
    destination_type: str
# data_models.py
# Description: Data classes for the simulation (Station, User).

from dataclasses import dataclass
from typing import Tuple

@dataclass
class Station:
    id: int
    x: float  # longitude
    y: float  # latitude
    capacity: int
    bikes: int
    neighbourhood: str

    def has_bike(self) -> bool:
        return self.bikes > 0

    def has_space(self) -> bool:
        return self.bikes < self.capacity

    def take_bike(self):
        self.bikes -= 1

    def return_bike(self):
        self.bikes += 1

@dataclass
class User:
    id: int
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    origin_type: str
    destination_type: str
    origin_neighbourhood: str
    destination_neighbourhood: str
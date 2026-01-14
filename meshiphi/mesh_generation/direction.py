class Direction:
    north_east: int = 1
    east: int = 2
    south_east: int = 3
    south: int = 4
    south_west: int = -1
    west: int = -2
    north_west: int = -3
    north: int = -4

    def __init__(self) -> None:
        self.north_east = 1
        self.east = 2
        self.south_east = 3
        self.south = 4
        self.south_west = -1
        self.west = -2
        self.north_west = -3
        self.north = -4

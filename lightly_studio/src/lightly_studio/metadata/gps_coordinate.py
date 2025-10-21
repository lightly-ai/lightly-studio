"""GPS coordinate representation for complex metadata."""

from typing import Dict


class GPSCoordinate:
    """Represents a GPS coordinate."""

    def __init__(self, lat: float, lon: float):
        """Initialize GPS coordinate.

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.
        """
        self.lat = lat
        self.lon = lon

    def __repr__(self) -> str:
        """String representation of the GPS coordinate."""
        return f"GPSCoordinate(lat={self.lat}, lon={self.lon})"

    def as_dict(self) -> Dict[str, float]:
        """Convert the GPSCoordinate to a dictionary.

        Returns:
            Dictionary with 'lat' and 'lon' keys.
        """
        return {"lat": self.lat, "lon": self.lon}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "GPSCoordinate":
        """Create a GPSCoordinate from a dictionary.

        Args:
            data: Dictionary with 'lat' and 'lon' keys.

        Returns:
            A GPSCoordinate instance.
        """
        return cls(lat=data["lat"], lon=data["lon"])

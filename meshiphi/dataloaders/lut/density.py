from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
from shapely import wkt

from meshiphi.dataloaders.lut.abstract_lut import LutDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class DensityDataLoader(LutDataLoader):  # type: ignore[misc]
    def import_data(self, bounds: Boundary) -> pd.DataFrame:
        """
        Creates a simulated dataset of sea ice density based on
        scientific literature.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            density_df (pd.DataFrame):
                Sea Ice Density dataset within limits of bounds.
                DataFrame has coordinates 'date', 'shape',
                and variable 'density'
        """

        # Look up table parameters hardcoded
        northern_hemisphere = wkt.loads("POLYGON((-180 0, -180 90, 180 90, 180 0, -180 0))")
        southern_hemisphere = wkt.loads("POLYGON((-180 -90, -180 0, 180 0, 180 -90, -180 -90))")

        # su = summer, au = autumn, wi = winter, sp = spring
        northern_seasons = {
            1: "wi",
            2: "wi",
            12: "wi",
            3: "sp",
            4: "sp",
            5: "sp",
            6: "su",
            7: "su",
            8: "su",
            9: "au",
            10: "au",
            11: "au",
        }
        southern_seasons = {
            1: "su",
            2: "su",
            12: "su",
            3: "au",
            4: "au",
            5: "au",
            6: "wi",
            7: "wi",
            8: "wi",
            9: "sp",
            10: "sp",
            11: "sp",
        }

        densities = {"su": 875.0, "sp": 900.0, "au": 900.0, "wi": 920.0}

        # Create shape to intersect regions with
        bounds_polygon = bounds.to_polygon()

        # For every date in range, create a new shape and value pair
        dates = pd.date_range(start=bounds.get_time_min(), end=bounds.get_time_max())

        density_df = pd.concat(
            [
                pd.DataFrame(
                    {
                        "time": dates,
                        "geometry": northern_hemisphere & bounds_polygon,  # Intersect shapes
                        "density": [densities[northern_seasons[month]] for month in dates.month],
                    }
                ),
                pd.DataFrame(
                    {
                        "time": dates,
                        "geometry": southern_hemisphere & bounds_polygon,  # Intersect shapes
                        "density": [densities[southern_seasons[month]] for month in dates.month],
                    }
                ),
            ]
        ).reset_index()
        # Remove empty geometry rows from df
        drop_idxs = []
        for idx, row in density_df.iterrows():
            if row["geometry"].is_empty or row["geometry"].geom_type not in [
                "Polygon",
                "MultiPolygon",
            ]:
                drop_idxs += [idx]

        density_df.drop(index=drop_idxs, inplace=True)
        density_df.drop(columns=["index"], inplace=True)

        density_df = density_df.drop_duplicates()
        return density_df.set_index("time").sort_index()

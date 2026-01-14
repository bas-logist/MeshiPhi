import pandas as pd
from shapely import Polygon

from meshiphi.dataloaders.lut.abstract_lut import LutDataLoader
from meshiphi.mesh_generation.boundary import Boundary

# Mapping of month number to season per hemisphere
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


class ThicknessDataLoader(LutDataLoader):
    class Region:
        """
        Data storage object with region boundary as polygon, seasonal
        sea ice densities, and a dict mapping from integer month to season
        """

        def __init__(self, name, geometry, value_dict, seasons=southern_seasons):
            self.name = name
            self.geometry = geometry
            self.value_dict = value_dict
            self.month_to_season = seasons

        def get_value(self, month):
            """
            Returns the sea ice density for a given month, taking into account
            seasons per hemisphere

            Args:
                month (int): Month as an integer (1 = Jan ... 12 = Dec)

            Returns:
                float: Sea Ice Density in the specified season
            """
            return self.value_dict[self.month_to_season[month]]

    def import_data(self, bounds):
        """
        Creates a simulated dataset of sea ice thickness based on
        scientific literature.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            thickness_df (pd.DataFrame):
                Sea Ice thickness dataset within limits of bounds.
                DataFrame has coordinates 'date', 'geometry',
                and variable 'thickness'
        """
        regions = [
            self.Region(
                "Ross E",
                Boundary([-90, 0], [-180, -130]).to_polygon(),
                {"wi": 0.72, "sp": 0.67, "su": 1.32, "au": 0.82, "y": 1.07},
            ),
            self.Region(
                "Bellinghausen",
                Boundary([-90, 0], [-130, -60]).to_polygon(),
                {"wi": 0.65, "sp": 0.79, "su": 2.14, "au": 0.79, "y": 0.90},
            ),
            self.Region(
                "Weddell W",
                Boundary([-90, 0], [-60, -45]).to_polygon(),
                {"wi": 1.33, "sp": 1.33, "su": 1.20, "au": 1.38, "y": 1.33},
            ),
            self.Region(
                "Weddell E",
                Boundary([-90, 0], [-45, 20]).to_polygon(),
                {"wi": 0.54, "sp": 0.89, "su": 0.87, "au": 0.44, "y": 0.73},
            ),
            self.Region(
                "Indian",
                Boundary([-90, 0], [20, 90]).to_polygon(),
                {"wi": 0.59, "sp": 0.78, "su": 1.05, "au": 0.45, "y": 0.68},
            ),
            self.Region(
                "West Pacific",
                Boundary([-90, 0], [90, 160]).to_polygon(),
                {"wi": 0.72, "sp": 0.68, "su": 1.17, "au": 0.75, "y": 0.79},
            ),
            self.Region(
                "Ross W",
                Boundary([-90, 0], [160, 180]).to_polygon(),
                {"wi": 0.72, "sp": 0.67, "su": 1.32, "au": 0.82, "y": 1.07},
            ),
            # Baltic thickness to match example from arxiv paper
            self.Region(
                "Baltic",
                Boundary([54, 66], [12, 32]).to_polygon(),
                {"wi": 0.3, "sp": 0.3, "su": 0.3, "au": 0.3, "y": 0.3},
                seasons=northern_seasons,
            ),
            # Keep previous defaults everywhere else
            self.Region(
                "None",
                Polygon(
                    [(-180, 0), (180, 0), (180, 90), (-180, 90)],
                    holes=[[(12, 54), (32, 54), (32, 66), (12, 66)]],
                ),
                {"wi": 0.72, "sp": 0.67, "su": 1.32, "au": 0.82, "y": 1.07},
                seasons=northern_seasons,
            ),
        ]

        # Create shape to intersect regions with
        bounds_polygon = bounds.to_polygon()

        # For every date in range, create a new shape and value pair
        dates = pd.date_range(start=bounds.get_time_min(), end=bounds.get_time_max())

        thickness_df = pd.DataFrame()

        for region in regions:
            intersection = region.geometry & bounds_polygon
            if intersection.geom_type in ["Polygon", "MultiPolygon"] and intersection != Polygon():
                region_df = pd.concat(
                    [
                        pd.DataFrame(
                            {
                                "time": dates,
                                "geometry": region.geometry & bounds_polygon,
                                "thickness": region.get_value(month),
                            }
                        )
                        for month in dates.month
                    ]
                )

                thickness_df = pd.concat([thickness_df, region_df])

        thickness_df = thickness_df.drop_duplicates()
        return thickness_df.set_index("time").sort_index()

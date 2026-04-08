from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import cartopy.crs as ccrs
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import shapely

if TYPE_CHECKING:
    from cartopy.mpl.geoaxes import GeoAxes


class MeshPlotter:
    """
    Object for plotting mesh json files using matplotlib and cartopy.
    """

    def __init__(self, mesh_json: dict[str, Any], figscale: int = 10) -> None:
        self.mesh_json = mesh_json
        self.mesh_df = pd.DataFrame(self.mesh_json["cellboxes"])

        self.lat_min = mesh_json["config"]["mesh_info"]["region"]["lat_min"]
        self.lat_max = mesh_json["config"]["mesh_info"]["region"]["lat_max"]
        self.long_min = mesh_json["config"]["mesh_info"]["region"]["long_min"]
        self.long_max = mesh_json["config"]["mesh_info"]["region"]["long_max"]

        self.figscale = figscale

        self.aspect_ratio = (self.long_max - self.long_min) / (self.lat_max - self.lat_min)

        self.fig = plt.figure(figsize=(self.figscale * self.aspect_ratio, self.figscale))

        self.plot = cast("GeoAxes", plt.axes(projection=ccrs.PlateCarree()))
        self.plot.set_extent([self.long_min, self.long_max, self.lat_min, self.lat_max])

    def plot_bool(self, value_name: str, colour: str) -> None:
        """
        Plots boolean values from the mesh json file.
        Args:
            value_name (str): The name of the boolean value to plot.
            colour (str): The colour to plot the value in.
        """
        for cellbox in self.mesh_json["cellboxes"]:
            polygon = shapely.wkt.loads(cellbox["geometry"])
            if cellbox[value_name] is True:
                self.plot.add_geometries(
                    [polygon],
                    ccrs.PlateCarree(),
                    facecolor=colour,
                    alpha=1.0,
                    edgecolor="darkslategrey",
                )

    def plot_cmap(self, value_name: str, colourmap: str) -> None:
        """
        Plots colourmap values from the mesh json file.
        Args:
            value_name (str): The name of the colourmap value to plot.
            colourmap (str): The colourmap to plot the value in.
        """

        # get min and max values for normalisation
        value_min = self.mesh_df[value_name].min()
        value_max = self.mesh_df[value_name].max()
        value_diff = value_max - value_min

        # get Colourmap from matplotlib
        cmap = matplotlib.colormaps[colourmap]
        for cellbox in self.mesh_json["cellboxes"]:
            # normalise value
            normalized_value = (cellbox[value_name] - value_min) / value_diff
            polygon = shapely.wkt.loads(cellbox["geometry"])
            self.plot.add_geometries(
                [polygon],
                ccrs.PlateCarree(),
                facecolor=cmap(normalized_value),
                alpha=1.0,
                edgecolor="darkslategrey",
            )

    def save(self, filename: str) -> None:
        """
        Saves the plot to a file.
        Args:
            filename (str): The name of the file to save the plot to.
        """
        plt.savefig(filename)

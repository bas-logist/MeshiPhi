from meshiphi.dataloaders.lut.abstract_lut import LutDataLoader
from meshiphi.mesh_generation.boundary import Boundary

import logging

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
from shapely.ops import split, transform, unary_union
import numpy as np

logger = logging.getLogger(__name__)


class LutShapefileArcNet(LutDataLoader):
    """
    LUT dataloader for ArcNet shapefiles.

    The ArcNet polygons may cross the antimeridian and may be delivered in
    project coordinates. This loader normalises the source CRS to EPSG:4326,
    unwraps longitudes around the dateline, splits crossing geometries at
    +/-180 degrees, and then re-wraps the output into the canonical
    [-180, 180] longitude range.
    """

    @staticmethod
    def _unwrap_longitudes(geom):
        def unwrap_coords(x, y, z=None):
            x = np.asarray(x, dtype=float)
            for i in range(1, len(x)):
                if x[i] - x[i - 1] > 180:
                    x[i:] -= 360
                elif x[i] - x[i - 1] < -180:
                    x[i:] += 360
            if z is not None:
                return x, y, z
            return x, y

        return transform(unwrap_coords, geom)

    @staticmethod
    def _wrap_longitudes(geom):
        def wrap_coords(x, y, z=None):
            x = np.asarray(x, dtype=float)
            x = ((x + 180) % 360) - 180
            if z is not None:
                return x, y, z
            return x, y

        return transform(wrap_coords, geom)

    @staticmethod
    def _split_if_required(geom):
        candidates = [geom]

        for _ in range(3):
            next_candidates = []
            split_happened = False

            for candidate in candidates:
                minx, _, maxx, _ = candidate.bounds
                if maxx <= 180 and minx >= -180:
                    next_candidates.append(candidate)
                    continue

                split_happened = True
                for split_x in (180, -180):
                    split_line = LineString([(split_x, -90), (split_x, 90)])
                    try:
                        pieces = list(split(candidate, split_line).geoms)
                    except Exception:
                        pieces = [candidate]

                    if len(pieces) > 1:
                        next_candidates.extend(pieces)
                        break
                    next_candidates.extend(pieces)

            if not split_happened:
                return candidates

            candidates = next_candidates

        return candidates

    @staticmethod
    def normalize_geometries(gdf):
        """
        Normalise shapefile geometries for use in MeshiPhi's 4326 longitude
        domain. This handles projected inputs, missing CRS metadata, and the
        antimeridian.
        """
        if gdf is None or gdf.empty:
            return gdf

        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        elif gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        gdf = gdf[gdf.geometry.notna()].copy()
        gdf = gdf.set_geometry(gdf.geometry.make_valid())

        normalized = []
        for geom in gdf.geometry:
            if geom is None or geom.is_empty:
                continue

            pieces = [geom]
            if geom.geom_type == "MultiPolygon":
                pieces = list(geom.geoms)

            for piece in pieces:
                if piece is None or piece.is_empty:
                    continue

                raw_span = piece.bounds[2] - piece.bounds[0]
                unwrapped = LutShapefileArcNet._unwrap_longitudes(piece)
                candidates = LutShapefileArcNet._split_if_required(unwrapped)

                if raw_span > 180 and len(candidates) <= 1:
                    continue

                for candidate in candidates:
                    candidate = LutShapefileArcNet._wrap_longitudes(candidate)
                    if candidate.is_empty or not candidate.is_valid:
                        continue

                    if candidate.bounds[2] - candidate.bounds[0] > 180:
                        continue

                    normalized.append(candidate)

        if not normalized:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

        out = gpd.GeoDataFrame(geometry=normalized, crs="EPSG:4326")
        out = out.explode(index_parts=False).reset_index(drop=True)
        out = out[out.geometry.notna() & ~out.geometry.is_empty].copy()
        return out

    def add_default_params(self, params):
        params = super().add_default_params(params)

        if "data_name" not in params:
            params["data_name"] = "dummy_data"

        # The ArcNet value (e.g. a speed limit) only applies inside the
        # polygons. The default "parent" fill would copy it into every
        # descendant of a boundary cell, including sub-cells that do not touch
        # any polygon, so the restriction would spread well beyond the area.
        fill = params.get("value_fill_types", "parent")
        if fill == "parent":
            if "value_fill_types" in params:
                logger.warning(
                    "\tvalue_fill_types='parent' would extend ArcNet values to "
                    "cells outside the polygons; using 'Nan' instead."
                )
            params["value_fill_types"] = "Nan"

        return params

    def import_data(self, bounds):
        gdf_list = []
        for file in self.files:
            gdf = gpd.read_file(file)
            gdf = self.normalize_geometries(gdf)
            if not gdf.empty:
                gdf_list.append(gdf)

        if not gdf_list:
            raise ValueError(f"No valid ArcNet geometries were found in {self.files}")

        shape_df = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True))
        shape_df[self.data_name] = self.value
        shape_df = gpd.GeoDataFrame(
            pd.concat(gdf_list, ignore_index=True),
            geometry="geometry",
            crs="EPSG:4326",
        )
        shape_df[self.data_name] = self.value

        world_polygon = Boundary([-90, 90], [-180, 180]).to_polygon()
        defined_polygon = unary_union(shape_df.geometry)
        undefined_polygon = world_polygon - defined_polygon

        if self.value is True:
            alt_val = False
        elif self.value is False:
            alt_val = True
        else:
            alt_val = np.nan

        # Keep only valid, real protected-area polygons.
        # The world complement is not a valid routeable cell.
        valid = (
            shape_df.geometry.notna()
            & ~shape_df.geometry.is_empty
            & shape_df.geometry.is_valid
            & shape_df[self.data_name].notna()
        )

        shape_df = shape_df.loc[valid].copy()
        shape_df = self.trim_datapoints(bounds, data=shape_df)

        return shape_df
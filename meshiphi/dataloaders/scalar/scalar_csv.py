from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class ScalarCSVDataLoader(ScalarDataLoader):  # type: ignore[misc]
    def import_data(self, bounds: Boundary) -> pd.DataFrame:
        """
        Reads in data from a CSV file.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            pd.DataFrame:
                Scalar dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', potentially 'time',
                and variable defined by column heading in csv file
        """
        # Read in data
        if self.files is None:
            raise ValueError("files parameter is required for ScalarCSVDataLoader")
        df_list = []
        # NOTE: All csv files must have same columns for this to work
        for file in self.files:
            df_list += [pd.read_csv(file)]
        data = pd.concat(df_list)
        # Trim to initial datapoints
        return self.trim_datapoints(bounds, data=data)

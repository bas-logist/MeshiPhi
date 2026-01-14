import pandas as pd

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader


class ScalarCSVDataLoader(ScalarDataLoader):
    def import_data(self, bounds):
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

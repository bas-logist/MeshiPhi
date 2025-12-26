from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

import logging
import xarray as xr

logger = logging.getLogger(__name__)


class VisualIcedDataLoader(ScalarDataLoader):
    def import_data(self, bounds):
        """
        Reads in data from Visual_Ice NetCDF files. Renames coordinates to
        'lat' and 'long'.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                visual_ice dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        """
        # Import data from files defined in config
        if len(self.files) == 1:
            visual_ice = xr.open_dataset(self.files[0])
            # If the file is a tiff, use the import_from_tiff method
            if self.files[0].split(".")[-1] == "tiff":
                visual_ice = self.import_from_tiff(visual_ice)
            elif self.files[0].split(".")[-1] == "nc":
                visual_ice = self.import_from_nc(visual_ice)
            else:
                logger.error("File type not supported")
                return None
        else:
            logger.error(
                "Multiple tiff files not supported. Only single tiff file supported"
            )
            raise ValueError(
                "Multiple tiff files not supported. Only single tiff file supported"
            )

        return visual_ice

    def import_from_nc(self, xarray_dataset):
        """
        applys transformations need to import a netcdf file

        Args:
            xarray_dataset (xr.Dataset): dataset to be transformed

        Returns:
            xr.Dataset: transformed dataset
        """
        # drop unnecessary variables
        xarray_dataset = xarray_dataset.drop_vars("polar_stereographic")

        # rename variables
        xarray_dataset = xarray_dataset.rename({"Band1": "SIC"})

        # convert SIC to percentage
        xarray_dataset = xarray_dataset.assign(SIC=lambda x: x.SIC * 100)

        return xarray_dataset

    def import_from_tiff(self, xarray_dataset):
        """
        applys transformations need to import a tiff file

        Args:
            xarray_dataset (xr.Dataset): dataset to be transformed

        Returns:
            xr.Dataset: transformed dataset
        """
        vi_dataframe = xarray_dataset.to_dataframe().reset_index()
        # drop unnecessary columns
        vi_dataframe = vi_dataframe.drop(columns=["band", "spatial_ref"])

        # rename columns
        vi_dataframe = vi_dataframe.rename(columns={"band_data": "SIC"})

        # convert SIC to percentage
        vi_dataframe["SIC"] = vi_dataframe["SIC"] * 100

        # convert back to xarray
        vi_dataframe = vi_dataframe.set_index(["x", "y"])
        vi_dataset = vi_dataframe.to_xarray()

        return vi_dataset

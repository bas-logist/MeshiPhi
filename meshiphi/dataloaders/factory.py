from meshiphi.dataloaders.scalar.amsr import AMSRDataLoader
from meshiphi.dataloaders.scalar.bsose_depth import BSOSEDepthDataLoader
from meshiphi.dataloaders.scalar.bsose_sea_ice import BSOSESeaIceDataLoader
from meshiphi.dataloaders.scalar.baltic_sea_ice import BalticSeaIceDataLoader
from meshiphi.dataloaders.scalar.gebco import GEBCODataLoader
from meshiphi.dataloaders.scalar.icenet import IceNetDataLoader
from meshiphi.dataloaders.scalar.modis import MODISDataLoader
from meshiphi.dataloaders.scalar.scalar_csv import ScalarCSVDataLoader
from meshiphi.dataloaders.scalar.scalar_grf import ScalarGRFDataLoader
from meshiphi.dataloaders.scalar.shape import ShapeDataLoader
from meshiphi.dataloaders.scalar.era5_sig_wave_height import ERA5SigWaveHeightDataLoader
from meshiphi.dataloaders.scalar.era5_max_wave_height import ERA5MaxWaveHeightDataLoader
from meshiphi.dataloaders.scalar.era5_wave_period import ERA5WavePeriodDataLoader
from meshiphi.dataloaders.scalar.era5_mean_wave_direction import (
    ERA5MeanWaveDirDataLoader,
)
from meshiphi.dataloaders.scalar.era5_wind_mag import ERA5WindMagDataLoader
from meshiphi.dataloaders.scalar.era5_wind_dir import ERA5WindDirDataLoader
from meshiphi.dataloaders.scalar.visual_iced import VisualIcedDataLoader
from meshiphi.dataloaders.scalar.ecmwf_sig_wave_height import (
    ECMWFSigWaveHeightDataLoader,
)

from meshiphi.dataloaders.vector.baltic_current import BalticCurrentDataLoader
from meshiphi.dataloaders.vector.era5_wind import ERA5WindDataLoader
from meshiphi.dataloaders.vector.north_sea_current import NorthSeaCurrentDataLoader
from meshiphi.dataloaders.vector.oras5_current import ORAS5CurrentDataLoader
from meshiphi.dataloaders.vector.sose import SOSEDataLoader
from meshiphi.dataloaders.vector.vector_csv import VectorCSVDataLoader
from meshiphi.dataloaders.vector.vector_grf import VectorGRFDataLoader
from meshiphi.dataloaders.vector.duacs_current import DuacsCurrentDataLoader
from meshiphi.dataloaders.vector.era5_wave_direction_vector import (
    ERA5WaveDirectionLoader,
)
from meshiphi.dataloaders.vector.vector_shape import VectorShapeDataLoader

from meshiphi.dataloaders.lut.density import DensityDataLoader
from meshiphi.dataloaders.lut.thickness import ThicknessDataLoader
from meshiphi.dataloaders.lut.scotland_ncmpa import ScotlandNCMPA
from meshiphi.dataloaders.lut.lut_csv import LutCSV
from meshiphi.dataloaders.lut.lut_geojson import LutGeoJSON
from meshiphi.dataloaders.lut.lut_shapefile import LutShapefile

from glob import glob
import os


class DataLoaderFactory:
    """
    Produces initialised DataLoader objects that can be used by the mesh to
    quickly retrieve values within a boundary.
    """

    @staticmethod
    def get_dataloader(name, bounds, params, min_dp=5):
        """
        Creates appropriate dataloader object based on name

        Args:
            name (str):
                Name of data source/type. Must be one of following -
                'scalar_csv', 'scalar_grf', 'binary_grf', 'amsr', 'bsose_sic',
                'bsose_depth', 'baltic_sic', 'gebco', 'icenet', 'modis',
                'thickness', 'density', 'circle', 'square', 'gradient',
                'checkerboard', 'vector_csv', 'vector_grf', 'baltic_currents',
                'era5_wind', 'northsea_currents', 'oras5_currents', 'sose',
                'duacs_currents', 'era5_wave_height', 'era5_wave_direction'
            bounds (Boundary):
                Boundary object with initial mesh space&time limits
            params (dict):
                Dictionary of parameters required by each dataloader
            min_dp (int):
                Minimum datapoints required to get homogeneity condition

        Returns:
            (Scalar/Vector/LUT DataLoader):
                DataLoader object of correct type, with required params set
        """
        # Cast name to lowercase to make case insensitive
        name = name.lower()
        # Translate 'file' or 'folder' into 'files' key
        params = DataLoaderFactory.translate_file_input(params)

        # Add loader name to params
        params["dataloader_name"] = name
        params["min_dp"] = min_dp

        dataloader_requirements = {
            # Scalar
            "scalar_csv": (ScalarCSVDataLoader, ["files"]),
            "scalar_grf": (ScalarGRFDataLoader, ["binary"]),
            "binary_grf": (ScalarGRFDataLoader, ["binary"]),
            "amsr": (AMSRDataLoader, ["files", "hemisphere"]),
            "bsose_sic": (BSOSESeaIceDataLoader, ["files"]),
            "bsose_depth": (BSOSEDepthDataLoader, ["files"]),
            "baltic_sic": (BalticSeaIceDataLoader, ["files"]),
            "gebco": (GEBCODataLoader, ["files"]),
            "icenet": (IceNetDataLoader, ["files"]),
            "modis": (MODISDataLoader, ["files"]),
            "visual_iced": (VisualIcedDataLoader, ["files"]),
            "era5_sig_wave_height": (ERA5SigWaveHeightDataLoader, ["files"]),
            "era5_max_wave_height": (ERA5MaxWaveHeightDataLoader, ["files"]),
            "era5_wave_dir": (ERA5MeanWaveDirDataLoader, ["files"]),
            "era5_wave_period": (ERA5WavePeriodDataLoader, ["files"]),
            "era5_wind_mag": (ERA5WindMagDataLoader, ["files"]),
            "era5_wind_dir": (ERA5WindDirDataLoader, ["files"]),
            "ecmwf_sig_wave_height": (ECMWFSigWaveHeightDataLoader, ["files"]),
            # Scalar - Abstract shapes
            "circle": (ShapeDataLoader, []),
            "rectangle": (ShapeDataLoader, []),
            "gradient": (ShapeDataLoader, []),
            "checkerboard": (ShapeDataLoader, []),
            # Vector
            "vector_csv": (VectorCSVDataLoader, ["files"]),
            "vector_grf": (VectorGRFDataLoader, []),
            "baltic_currents": (BalticCurrentDataLoader, ["files"]),
            "era5_wind": (ERA5WindDataLoader, ["files"]),
            "era5_wave_direction": (ERA5WaveDirectionLoader, ["files"]),
            "northsea_currents": (NorthSeaCurrentDataLoader, ["files"]),
            "duacs_currents": (DuacsCurrentDataLoader, ["files"]),
            "oras5_currents": (ORAS5CurrentDataLoader, ["files"]),
            "sose": (SOSEDataLoader, ["files"]),
            # Vector - Abstract shapes
            "vector_circle": (VectorShapeDataLoader, []),
            "vector_gradient": (VectorShapeDataLoader, []),
            "vector_rectangle": (VectorShapeDataLoader, []),
            # LUT
            "thickness": (ThicknessDataLoader, []),
            "density": (DensityDataLoader, []),
            "scotland_ncmpa": (ScotlandNCMPA, ["files"]),
            "lut_csv": (LutCSV, ["files"]),
            "lut_geojson": (LutGeoJSON, ["files", "value"]),
            "lut_shapefile": (LutShapefile, ["files", "value"]),
        }
        # If name is recognised as a dataloader
        if name in dataloader_requirements:
            # Set data loader and params required for it to work
            data_loader = dataloader_requirements[name][0]
            required_params = dataloader_requirements[name][1]
        else:
            raise ValueError(f"{name} not in known list of DataLoaders")

        # Check dataloader will get all required params to work
        missing_params = [key for key in required_params if key not in params]
        if missing_params:
            raise KeyError(
                f"Dataloader {name} is missing required parameters: {missing_params}. "
                f"Required: {required_params}. Provided: {list(params.keys())}"
            )

        # Create instance of dataloader
        return data_loader(bounds, params)

    @staticmethod
    def translate_file_input(params):
        """
        Allows flexible file specification in params. Translates 'file' or
        'folder' into 'files'

        Args:
            params (dict):
                Dictionary of parameters written in config
        """
        if "file" in params:
            params["files"] = [params["file"]]
            del params["file"]
        elif "folder" in params:
            folder = os.path.join(
                params["folder"], ""
            )  # Adds trailing slash if non-existent
            params["files"] = sorted(glob(folder + "*"))
            del params["folder"]
        return params

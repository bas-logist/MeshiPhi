# Scalar Dataloaders

## Abstract Scalar Base Class

The Abstract Base Class of the scalar dataloaders holds most of the 
functionality that would be needed to manipulate the data to work 
with the mesh. When creating a new dataloader, the user must define
how to open the data files, and what methods are required to manipulate
the data into a standard format. 

Documentation for the abstract `ScalarDataLoader` is available in the [API documentation](../../autoapi/meshiphi/dataloaders/scalar/abstract_scalar).

## Scalar Dataloader Examples

Data must be imported and saved as an xarray.Dataset, or a pandas.DataFrame object.
Below is a simple example of how to load in a NetCDF file:

```py
from meshiphi.Dataloaders.Scalar.AbstractScalar import ScalarDataLoader
import xarray as xr
import logging

class MyDataLoader(ScalarDataLoader):
    
    def import_data(self, bounds):
        logging.debug("Importing my data...")
        # Open Dataset
        if len(self.files) == 1:    data = xr.open_dataset(self.files[0])
        else:                       data = xr.open_mfdataset(self.files)

        # Rename coordinate columns to 'lat', 'long', 'time' if they aren't already
        data = data.rename({'lon':'long'})

        # Limit to initial boundary
        data = self.trim_data(bounds, data=data)

        return data
```

Sometimes there are parameters that are constant for a data source, but are not 
constant for all data sources. Default values are defined in the dataloader `add_default_params()`.
Below is an example of setting default parameters for reprojection of a dataset:

```py
class MyDataLoader(ScalarDataLoader):
    def add_default_params(self, params):
        # Add all the regular default params that scalar dataloaders have
        params = super().add_default_params(params) # This line MUST be included

        # Define projection of dataset being imported
        params['in_proj'] = 'EPSG:3412'
        # Define projection required by output 
        params['out_proj'] = 'EPSG:4326' # default is EPSG:4326, so strictly
                                            # speaking this line is not necessary

        # Coordinates in dataset that will be reprojected into long/lat
        params['x_col'] = 'x' # Becomes 'long'
        params['y_col'] = 'y' # Becomes 'lat'

        return params
        
    def import_data(self, bounds):
        # Open Dataset
        data = xr.open_mfdataset(self.files)

        # Can't easily determine bounds of data in wrong projection, so skipping for now
        return data
```

## Included Scalar Dataloaders

The following scalar dataloaders are included in MeshiPhi.

See the package [API Reference](../../autoapi/meshiphi/dataloaders/scalar) section of the docs for details.

### AMSR

The AMSR (Advanced Microwave Scanning Radiometer) dataset is a publicly
available that provides Sea Ice Concentration scans of the earth's oceans.
It is produced by researchers at the University of Bremen.

The AMSR dataloader is currently the only 'standalone' dataloader, in that it
is defined independently of the abstract base class. This is due to issues
with `pandas` calculating mean values differently depending on how the 
data is loaded. This caused issues with the regression tests passing. 
This issue will be rectified soon by updating the regression tests.

Data can be downloaded from the [University of Bremen Sea Ice Data Archive](https://seaice.uni-bremen.de/data-archive/).

Name in config: `'amsr'`

Class documentation: [AMSRDataLoader](../../autoapi/meshiphi/dataloaders/scalar/amsr)

### Baltic Sea Ice 

Baltic sea ice concentration values are provided by the Finnish Meteorological Institute (FMI).
From their webpage:

   The operational sea ice service at FMI provides ice parameters over the Baltic Sea. 
   The parameters are based on ice chart produced on daily basis during the 
   Baltic Sea ice season and show the ice concentration in a 1 km grid.

Data can be downloaded from <https://data.marine.copernicus.eu/product/SEAICE_BAL_PHY_L4_MY_011_019/description>

Name in config: `'baltic_sic'`

Class documentation: [BalticSeaIceDataLoader](../../autoapi/meshiphi/dataloaders/scalar/baltic_sea_ice)

### Binary GRF 

The binary GRF dataloader is the same as the :ref:`Scalar GRF<scalar-grf>`
The only difference is that instead of returning a dataframe that consists
of values between the min/max set in the config, this dataframe will contain
only True/False. It is useful for generating land masks.

Default parameters for binary/mask GRF dataloader :

```json
{
    "loader": "binary_grf",
    "params":{
        "data_name": "data",    # - Name of the data column
        "seed":       None,     # - Seed for random number generator. Must
                                #   be int or None. None sets a random seed
        "size":       512,      # - Number of datapoints per lat/long axis
        "alpha":      3,        # - Power of the power-law momentum 
                                #   distribution used to generate GRF
        "min":        0,        # - Minimum value of GRF
        "max":        1,        # - Maximum value of GRF
        "binary":     True,     # - Flag specifying this GRF is a binary mask
        "threshold":  0.5       # - Value around which mask values are set.
                                #   Below this, values are set to False 
                                #   Above this, values are set to True
    }
}
```

Name in config: `'binary_grf'`

See the :ref:`Scalar GRF page<scalar-grf>` for documentation on the dataloader



### BSOSE Depth 

B-SOSE (Biogeochemical Southern Ocean State Estimate solution) provide a publicly available dataset that
hosts (amongst other products) sea ice concentration (SIC) of the southern ocean. Their SIC product provides 
a 'depth' value, which this dataloader ingests.
BSOSE is an extension of the SOSE project led by Mazloff at the Scripps Institution of Oceanography.

From their website:
>   The Southern Ocean State Estimate (SOSE) is a model-generated best fit to Southern Ocean 
>   observations. As such, it provides a quantitatively useful climatology of the mean-state 
>   of the Southern Ocean. 

Name in config: `'bsose_depth'`

Data can be downloaded from <http://sose.ucsd.edu/BSOSE_iter105_solution.html>

Class documentation: [BSOSEDepthDataLoader](../../autoapi/meshiphi/dataloaders/scalar/bsose_depth)

**Note**: This dataloader may not work "as is" for new data downloaded, it has been internally collated into
a more easily ingestable format.

### BSOSE Sea Ice 

B-SOSE (Biogeochemical Southern Ocean State Estimate solution) provide a publicly available dataset that
hosts (amongst other products) sea ice concentration of the southern ocean. It is an extension of the 
SOSE project led by Mazloff at the Scripps Institution of Oceanography.

From their website:
>   The Southern Ocean State Estimate (SOSE) is a model-generated best fit to Southern Ocean 
>   observations. As such, it provides a quantitatively useful climatology of the mean-state 
>   of the Southern Ocean.

Data can be downloaded from <http://sose.ucsd.edu/BSOSE_iter105_solution.html>

Name in config: `'bsose_sic'`

Class documentation: [BSOSESeaIceDataLoader](../../autoapi/meshiphi/dataloaders/scalar/bsose_sea_ice)

**Note**: This dataloader may not work as is for new data downloaded, it has been internally collated into 
a more easily ingestable format.


### ECMWFSigWaveHeight 

The ECMWF (European Centre for Medium-Range Weather Forecasts) are both a 
research institute and a 24/7 operational service, producing global numerical 
weather predictions and other data for their Member and Co-operating States 
and the broader community. The Centre has one of the largest supercomputer 
facilities and meteorological data archives in the world. Other strategic 
activities include delivering advanced training and assisting the WMO in 
implementing its programmes.
(description taken from <https://www.ecmwf.int/en/about>)

**Note**: This dataloader is for the grib2 files.

Data can be downloaded from <https://data.ecmwf.int/forecasts/>

Name in config: `'ecmwf_sig_wave_height'`

Class documentation: [ECMWFSigWaveHeightDataLoader](../../autoapi/meshiphi/dataloaders/scalar/ecmwf_sig_wave_height)

### ERA5 Dataloaders

ERA5 is a family of data products produced by the European Centre for Medium-Range Weather Forecasts (ECMWF).
It is the fifth generation ECMWF atmospheric reanalysis of the global climate covering the period from January 1950 to present.

From their website:

>   ERA5 provides hourly estimates of a large number of atmospheric,
>   land and oceanic climate variables. The data cover the Earth on a
>   30km grid and resolve the atmosphere using 137 levels from the
>   surface up to a height of 80km. ERA5 includes information about
>   uncertainties for all variables at reduced spatial and temporal resolutions.

Instructions for how to download their data products are
available from <https://confluence.ecmwf.int/display/CKB/How+to+download+ERA5>

Variables, their names in config and class documentation:

* Maximum Wave Height: `'era5_max_wave_height'` - [ERA5MaxWaveHeightDataLoader](../../autoapi/meshiphi/dataloaders/scalar/era5_max_wave_height)
* Significant Wave Height: `'era5_sig_wave_height'` - [ERA5SigWaveHeightDataLoader](../../autoapi/meshiphi/dataloaders/scalar/era5_sig_wave_height)
* Mean Wave Direction Dataloader: `'era5_wave_dir'` - [ERA5MeanWaveDirDataLoader](../../autoapi/meshiphi/dataloaders/scalar/era5_wave_dir)
* Mean Wave Period: `'era5_wave_period'` - [ERA5WavePeriodDataLoader](../../autoapi/meshiphi/dataloaders/scalar/era5_wave_period)
* Wind Direction: `'era5_wind_dir'` - [ERA5WindDirDataLoader](../../autoapi/meshiphi/dataloaders/scalar/era5_wind_dir)
* Wind Magnitude: `'era5_wind_mag'` - [ERA5WindMagDataLoader](../../autoapi/meshiphi/dataloaders/scalar/era5_wind_mag)

### GEBCO

The General Bathymetric Chart of the Oceans (GEBCO) is a publicly available
bathymetric chart of the Earth's oceans. It is a common resource used by
ocean scientists, amongst others.

Data can be downloaded from <https://download.gebco.net/>

Name in config: `'gebco'`

Class documentation: [GEBCODataLoader](../../autoapi/meshiphi/dataloaders/scalar/gebco)

### IceNet

IceNet is a seasonal sea ice forecasting tool being developed by researchers
at the British Antarctic Survey. From the website:

>   IceNet is a probabilistic, deep learning sea ice forecasting system 
>   developed by an international team and led by British Antarctic Survey 
>   and The Alan Turing Institute [Andersson et al., 2021]. IceNet has been 
>   trained on climate simulations and observational data to forecast the 
>   next 6 months of monthly-averaged sea ice concentration maps.

Data for IceNet V1 is available from <https://ramadda.data.bas.ac.uk/repository/entry/show>
Data for IceNet V2 is not publicly available.

Name in config: `'icenet'`

Class documentation: [IceNetDataLoader](../../autoapi/meshiphi/dataloaders/scalar/icenet)


### MODIS

Moderate Resolution Imaging Spectroradiometer (MODIS) is a satellite-borne 
instrument developed by NASA.

From their website:
>   MODIS are viewing the entire Earth's surface every 1 to 2 days, 
>   acquiring data in 36 spectral bands, or groups of wavelengths.

Information on where to download their data products can be found at <https://modis.gsfc.nasa.gov/data/dataprod/mod29.php>

Name in config: `'modis'`

Class documentation: [MODISDataLoader](../../autoapi/meshiphi/dataloaders/scalar/modis)


### Scalar CSV

The scalar CSV dataloader is designed to take any `.csv` file and cast
it into a data source for mesh construction. It was primarily used in testing 
for loading dummy data to test performance. As such, there is no data source 
for this dataloader.

Name in config: `'scalar_csv'`

Class documentation: [ScalarCSVDataLoader](../../autoapi/meshiphi/dataloaders/scalar/scalar_csv)

### Scalar GRF

Produces a gaussian random field of scalar values, useful for producing 
artificial, yet somewhat realistic values for real-world variables.

Name in config: `'scalar_grf'`

Can be used to generate :ref:`binary masks<binary-grf>`.

For vector fields, see  the :ref:`Vector GRF page<vector-grf>`.

Class documentation: [ScalarGRFDataLoader](../../autoapi/meshiphi/dataloaders/scalar/scalar_grf)

Default parameters for scalar GRF dataloader. 

```json
{
    "loader": "scalar_grf",
    "params":{
        "data_name": "data",    # - Name of the data column
        "seed":       None,     # - Seed for random number generator. Must
                                #   be int or None. None sets a random seed
        "size":       512,      # - Number of datapoints per lat/long axis
        "alpha":      3,        # - Power of the power-law momentum 
                                #   distribution used to generate GRF
        "binary":     False,    # - Flag specifying this GRF isn't a binary mask
        "threshold":  [0, 1],   # - Caps of min/max values to ensure normalising 
                                #   not skewed by outlier in randomised GRF
        "min":        -10,      # - Minimum value of GRF
        "max":        10,       # - Maximum value of GRF
        "multiplier": 1,        # - Multiplier for entire dataset
        "offset":     0         # - Offset for entire dataset
    }
}
```

**NOTE**: min/max are set BEFORE multiplier and offset are used. The actual values for
the min and max are 

* `actual_min = multiplier * min + offset`
* `actual_max = multiplier * max + offset` 

### Shape Dataloader

The shape dataloader is designed to create abstract shapes with well known 
boundaries, and cast it into a data source for mesh construction. It was primarily 
used in testing to debug cellbox generation. As such, there is no data source 
for this dataloader.

Class documentation: [ShapeDataLoader](../../autoapi/meshiphi/dataloaders/scalar/shape)

### Visual_iced 

Visual_iced is a dataloader for .tiff images, which are outputs from the visual_iced library
developed by Martin Rogers at the British Antarctic Survey's AI Lab. These visual_iced
images are ice/water binary files, generated from a combination of MODIS and SAR
satellite imagery. 

In the source data, 0s are representative of open water, and 1s are representative of
ice. In the dataloader, we map these values to sea ice concentration, in the range of 0 to 100.
Values between 0 and 100 are generated by the aggregation of the 0s and 1s within each cell.

**Note**: The visual_iced dataloader only supports loading in single files, as the visual_iced datasets are not temporally continuous within a given boundary.

Name in config: `'visual_iced'`

Class documentation: [VisualIcedDataLoader](../../autoapi/meshiphi/dataloaders/scalar/visual_iced)

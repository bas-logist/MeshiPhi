# Vector Dataloaders

## Abstract Vector Base Class

The Abstract Base Class of the vector dataloaders holds most of the 
functionality that would be needed to manipulate the data to work 
with the mesh. When creating a new dataloader, the user must define
how to open the data files, and what methods are required to manipulate
the data into a standard format. 

Documentation for the abstract `VectorDataLoader` is available in the [API documentation](../../autoapi/meshiphi/dataloaders/vector/abstract_vector).


## Examples

Creating a vector dataloader is almost identical to creating a 
:ref:`scalar dataloader<abstract-scalar-dataloader>`. The key differences 
are that the `VectorDataLoader` abstract base class must be used, and that
the `data_name` is a comma separated string of the vector component names.
e.g. a dataloader storing a vector with column names `uC` and 
`vC` will have an attribute `self.data_name = 'uC,vC'`
Data must be imported and saved as an `xarray.Dataset`, or a 
`pandas.DataFrame` object. Below is a simple example of how to load in a 
NetCDF file:

```py
from meshiphi.Dataloaders.Scalar.AbstractScalar import VectorDataLoader
import xarray as xr
import logging

class MyDataLoader(VectorDataLoader):
    def import_data(self, bounds):
        logging.debug("Importing my data...")
        # Open Dataset
        logging.debug(f"- Opening file {self.file}")
        data = xr.open_dataset(self.file)

        # Rename coordinate columns to 'lat', 'long', 'time' if they aren't already
        data = data.rename({'lon':'long'})

        # Limit to initial boundary
        data = self.trim_data(bounds, data=data)

        return data
```

Similar to scalar data loaders, sometimes there are parameters that are constant 
for a data source, but are not constant for all data sources. Default values may 
be defined either in the dataloader factory, or within the dataloader itself. 
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
        
    def import_data(self, bounds):
        # Open Dataset
        data = xr.open_mfdataset(self.file)

        # Can't easily determine bounds of data in wrong projection, so skipping for now
        return data
```

## Included Vector Dataloaders

The following vector dataloaders are included in MeshiPhi.

### Baltic Currents

Baltic current values are provided by the Finnish Meteorological Institute (FMI).
From their webpage:

>   This CMEMS Baltic Sea Physical Reanalysis product provides a physical reanalysis 
>   for the whole Baltic Sea area, inclusive the Transition Area to the North Sea. 
>   The surface variables are available every hour and include sea surface height, 
>   ice concentration and total ice thickness. The other variables, available as daily 
>   and monthly means, are salinity, temperature, horizontal current components, 
>   mixed layer depth, bottom salinity and bottom temperature.

Data can be downloaded from <https://data.marine.copernicus.eu/product/BALTICSEA_REANALYSIS_PHY_003_011/description>

Name in config: `'baltic_currents'`

Class documentation: [BalticCurrentDataLoader](../../autoapi/meshiphi/dataloaders/vector/baltic_current)

### DUACS Currents

DUACS  is a European operational multi-mission production system of altimeter data that provides (amongst other products)
global ocean current vectors. The system was developed by CNES/CLS and data is available from the copernicus marine data
service.

From their website:
>   Altimeter satellite gridded Sea Level Anomalies (SLA) computed with respect to a twenty-year 1993, 2012 mean. The SLA
>   is estimated by Optimal Interpolation, merging the L3 along-track measurement from the different altimeter missions
>   available. Part of the processing is fitted to the Global Ocean. The product gives additional variables (i.e.
>   Absolute Dynamic Topography and geostrophic currents).

Near real-time data can be downloaded from `here <https://data.marine.copernicus.eu/product/SEALEVEL_GLO_PHY_L4_NRT_008_046/description>`_.

Reanalysis data can be downloaded from `here. <https://data.marine.copernicus.eu/product/SEALEVEL_GLO_PHY_L4_MY_008_047/description>`_

Name in config: `'duacs_currents'`

Class documentation: [DuacsCurrentDataLoader](../../autoapi/meshiphi/dataloaders/vector/duacs_current)

### ERA5 Wave Direction

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

This dataloader takes the mean wave direction variable, which gives the direction the waves are coming from as an angle
from north in degrees, and converts it to a unit vector with u and v components.

Name in config: `'era5_wave_direction'`

Class documentation: [ERA5WaveDirectionLoader](../../autoapi/meshiphi/dataloaders/vector/era5_wave_direction_vector)

### ERA5 Wind 

See above for information about ERA5.

Name in config: `'era5_wind'`

Class documentation: [ERA5WindDataLoader](../../autoapi/meshiphi/dataloaders/vector/era5_wind)

### North Sea Currents 

North Atlantic Ocean currents are provided by the Proudman Oceanographic Laboratory 
Coastal-Ocean Modelling System (POLCOMS). Their dataset was generated by the UK National 
Oceanography Centre, Liverpool.

More information on where to download the data is 
available <https://www.bodc.ac.uk/resources/inventories/edmed/report/6364/>

Name in config: `'northsea_currents'`

Class documentation: [NorthSeaCurrentDataLoader](../../autoapi/meshiphi/dataloaders/vector/north_sea_current)

### ORAS5 Currents

Ocean Reanalysis System 5 (ORAS5) is a publicly available dataset providing
estimated values for many different ocean parameters, including ocean currents.

From their website:

>   This dataset provides global ocean and sea-ice reanalysis 
>   (ORAS5: Ocean Reanalysis System 5) monthly mean data prepared by 
>   the European Centre for Medium-Range Weather Forecasts (ECMWF) 
>   OCEAN5 ocean analysis-reanalysis system. This system comprises 5 ensemble 
>   members from which one member is published in this catalogue entry.

Data can be downloaded from <https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-oras5?tab=form>

Name in config: `'oras5_currents'`

Class documentation: [ORAS5CurrentDataLoader](../../autoapi/meshiphi/dataloaders/vector/oras5_current)

### SOSE Currents

Southern Ocean State Estimate (SOSE) is a publicly available dataset that provides (amongst other products)
ocean current vectors of the southern ocean. It is a project led by Mazloff at the Scripps Institution of Oceanography.

From their website:
>   The Southern Ocean State Estimate (SOSE) is a model-generated best fit to Southern Ocean 
>   observations. As such, it provides a quantitatively useful climatology of the mean-state 
>   of the Southern Ocean.

Data can be downloaded from `here <http://sose.ucsd.edu/sose_stateestimation_data_05to10.html>`_

Name in config: `'sose'`

Class documentation: [SOSEDataLoader](../../autoapi/meshiphi/dataloaders/vector/sose)

!!! note
    This dataloader may not work as is for new data downloaded, it has been internally collated into  a more easily ingestable format.

### Vector CSV 

The vector CSV dataloader is designed to take any `.csv` file and cast
it into a data source for mesh construction. It was primarily used in testing 
for loading dummy data to test performance. As such, there is no data source 
for this dataloader.

Name in config: `'vector_csv'`

Class documentation: [VectorCSVDataLoader](../../autoapi/meshiphi/dataloaders/vector/vector_csv)

### Vector GRF

Produces a gaussian random field of vector values, useful for producing 
artificial, yet somewhat realistic values for real-world variables. 
Values are broken down into `x` and `y` components, and saved in two
columns in the final dataframe.

Name in config: `'vector_grf'`

Class documentation: [VectorGRFDataLoader](../../autoapi/meshiphi/dataloaders/vector/vector_grf)

Can be used to generate :ref:`binary masks<binary-grf>`.

For scalar fields, see  the :ref:`Vector GRF page<scalar-grf>`.

.. code-block::
    :caption: Default parameters for vector GRF dataloader 

    {
        "loader": "vector_grf",
        "params":{
            "vec_x":     "uC",      # - Name of the first data column
            "vec_y":     "vC",      # - Name of the second data column
            "seed":       None,     # - Seed for random number generator. Must
                                    #   be int or None. None sets a random seed
            "size":       512,      # - Number of datapoints per lat/long axis
            "alpha":      3,        # - Power of the power-law momentum 
                                    #   distribution used to generate GRF
            "min":        0,        # - Minimum value of vector magnitude
            "max":        10        # - Maximum value of vector magnitude
        }
    }
# Look Up Table Dataloaders

## Abstract LUT Base Class

The Abstract Base Class of the Look Up Table dataloaders holds most of the 
functionality that would be needed to manipulate the data to work 
with the mesh. When creating a new dataloader, the user must define
how to open the data files, and what methods are required to manipulate
the data into a standard format.

Documentation for the abstract `LutDataLoader` is available in the [API documentation](../../autoapi/meshiphi/dataloaders/lut/abstract_lut).

## LUT Dataloader Examples

Creating a LUT dataloader is almost identical to creating a 
:ref:`scalar dataloader<abstract-scalar-dataloader>`. The key differences 
are that the `LUTDataLoader` abstract base class must be used, and 
regions are defined by Shapely polygons. Data is imported and saved as 
GeoPandas dataframes, holding a polygon and an associated value.

## Included LUT Dataloaders

### Density 

Density values were taken from the paper 'Thickness distribution of Antarctic sea ice' Worby, A.P. _et al._ (2008) <https://doi.org/10.1029/2007JC004254>. This paper took a density model from the paper 'Structure, principal properties and strength of Antarctic sea ice' (Buynitskiy, V.K.). 

Name in config: `'density'`

Class documentation: [BalticCurrentDataLoader](../../autoapi/meshiphi/dataloaders/lut/DensityDataLoader)

### LUT CSV 

The scalar CSV dataloader is designed to take any `.csv` file and cast
it into a data source for mesh construction. It was primarily used in testing 
for loading dummy data to test performance. As such, there is no data source 
for this dataloader. The CSV must have two columns: 'geometry' and 'data_name'.
'geometry' must have that title, and is a shapely wkt string. data_name can have 
any name, and is just the value that is associated with the polygon.

Name in config: `'lut_csv'`

Class documentation: [LutCSV](../../autoapi/meshiphi/dataloaders/lut/lut_csv)

### LUT GeoJSON

The scalar CSV dataloader is designed to take any geojson file and cast
it into a data source for mesh construction. It was primarily used in testing 
for loading dummy data to test performance. When using this dataloader, a value
should be provided in the mesh config file that specifies the value and data_name 
that the polygons save. The keyword in the config params is 'value'.

Name in config: `'lut_geojson'`

Class documentation: [LutGeoJSON](../../autoapi/meshiphi/dataloaders/lut/lut_geojson)

### Scotland NCMPA

GeoJSON files are provided by the Scottish government for Nature Conservation Marine Protected Areas.

Data can be downloaded from <https://www.data.gov.uk/dataset/67572936-18dc-4180-af74-39b088b6fb19/nature-conservation-marine-protected-areas-mpa>

Name in config: `'scotland_ncmpa'`

Class documentation: [ScotlandNCMPA](../../autoapi/meshiphi/dataloaders/lut/scotland_ncmpa)

### Thickness Dataloader

Thickness values were taken from the paper 'Thickness distribution of Antarctic sea ice' Worby, A.P. _et al._ (2008) <https://doi.org/10.1029/2007JC004254>

Data is generated using the values from this paper, and so no data file is available for download.

Name in config: `'thickness'`

Class documentation: [ThicknessDataLoader](../../autoapi/meshiphi/dataloaders/lut/thickness)

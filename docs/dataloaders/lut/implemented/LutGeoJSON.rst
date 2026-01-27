**********************
LUT GeoJSON Dataloader
**********************

The scalar CSV dataloader is designed to take any geojson file and cast
it into a data source for mesh construction. It was primarily used in testing 
for loading dummy data to test performance. When using this dataloader, a value
should be provided in the mesh config file that specifies the value and data_name 
that the polygons save. The keyword in the config params is 'value'.

Name in config: :code:`'lut_geojson'`

.. automodule:: meshiphi.dataloaders.lut.lut_geojson
   :special-members: __init__
   :members:
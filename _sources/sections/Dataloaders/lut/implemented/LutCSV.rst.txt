******************
LUT CSV Dataloader
******************

The scalar CSV dataloader is designed to take any `.csv` file and cast
it into a data source for mesh construction. It was primarily used in testing 
for loading dummy data to test performance. As such, there is no data source 
for this dataloader. The CSV must have two columns: 'geometry' and 'data_name'.
'geometry' must have that title, and is a shapely wkt string. data_name can have 
any name, and is just the value that is associated with the polygon.

Name in config: :code:`'lut_csv'`

.. automodule:: meshiphi.dataloaders.lut.lut_csv
   :special-members: __init__
   :members:
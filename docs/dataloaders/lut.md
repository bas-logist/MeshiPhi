.. _abstract-lut-dataloader-index:

***************
LUT Dataloaders
***************


^^^^^^^^^^^^^^^^^^^^^^^
Abstract LUT Base Class
^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 1
   :glob:

   ./abstractLUT

The Abstract Base Class of the Look Up Table dataloaders holds most of the 
functionality that would be needed to manipulate the data to work 
with the mesh. When creating a new dataloader, the user must define
how to open the data files, and what methods are required to manipulate
the data into a standard format. More details are provided on the 
:ref:`abstractVector doc page<abstract-lut-dataloader>`


^^^^^^^^^^^^^^^^^^^^^^^
LUT Dataloader Examples
^^^^^^^^^^^^^^^^^^^^^^^
Creating a LUT dataloader is almost identical to creating a 
:ref:`scalar dataloader<abstract-scalar-dataloader>`. The key differences 
are that the `LUTDataLoader` abstract base class must be used, and 
regions are defined by Shapely polygons. Data is imported and saved as 
GeoPandas dataframes, holding a polygon and an associated value.

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Implemented LUT Dataloaders
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. toctree::
   :maxdepth: 1
   :glob:

   ./implemented/*
Welcome to the MeshiPhi Manual Pages
======================================

MeshiPhi is a tool for the discretisation of environmental data with a non uniform resolution based on the variance of
the data. This software package has been developed by the **British Antarctic Survey** (BAS). It was initially designed
as part of a `route planning tool <https://github.com/bas-amop/PolarRoute>`_ for the BAS research vessel RRS Sir David
Attenborough, although it can be applied to any geospatial data. The software is written in Python and is open source.

The package contains limited plotting functionality, which is described in the :ref:`Mesh Plotting` section. For 
extended plotting functionality, we recommend using the GeoPlot package, which was also developed at BAS. This is
available from the following GitHub repository: `GeoPlot <https://github.com/bas-amop/GeoPlot>`_

For more information on the project, please visit the `AMOP website <https://www.bas.ac.uk/project/autonomous-marine-operations-planning/>`_
and follow our `GitHub repository <https://github.com/bas-amop/meshiphi>`_.


.. note:: The development of this codebase is ongoing and not yet complete. 
          Please contact the developers for more information.

Contents:

.. toctree::
   :maxdepth: 2
   :numbered:

   ./sections/Installation
   ./sections/Examples
   ./sections/Command_line_interface
   ./sections/Code_overview
   ./sections/Configuration/Configuration_overview
   ./sections/Outputs
   ./sections/Dataloaders/overview
   ./sections/Mesh_Construction/Mesh_construction_overview
   ./sections/Plotting/mesh_plotting
   ./sections/testing_strategy

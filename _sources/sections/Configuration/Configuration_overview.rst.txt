######################################
Configuration Overview
######################################

In this section we outline the standard structure for the configuration file used as the starting point for generating
an environmental mesh using the MeshiPhi software package. These configuration files are written in JSON, can be passed
to MeshiPhi as command-line arguments or through a Python interpreter.

Example configuration files are provided in the :code:`examples/environment_config/` directory on GitHub.

Descriptions of the configuration options for the Mesh Construction can be found in 
the :ref:`Configuration - Mesh Construction` section of the documentation.


.. toctree::
   :maxdepth: 1

   ./Mesh_construction_config


Config Validation
^^^^^^^^^^^^^^^^^

The configs supplied by the user are validated using a template JSON Schema. This schema checks that the correct
keywords and datatypes are provided in the config JSON file. They also perform rudimentary checks on the values within
the config to ensure that they make sense (e.g. start_time is before end_time).

.. automodule:: meshiphi.config_validation.config_validator
   :members:
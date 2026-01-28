.. _outputs:

********************
Outputs - Data Types
********************

######################
The Mesh.json file
######################

Once a mesh has been constructed using MeshiPhi, it can then be exported as a json object and saved to a file. An example
of mesh construction and json object generation are as follows:

::

    from meshiphi.mesh import Mesh

    with open('config.json', 'r') as f:
        config = json.load(f)

    mesh = Mesh(config)
    mesh_json = mesh.to_json()

.. note:: 
    Examples and a description of the configuration files can be found in
    the :ref:`configuration - mesh construction` section of this document.


The json object outputted by the Mesh consists of 3 sections: **config**,
**cellboxes** and **neighbour_graph**.

::

    {
        "config": {
            ...
        },
        "cellboxes": [
            {...},
            ...
            {...}
        ],
        "neighbour_graph": [
            "<id_1>": {
                ...
            },
            ...
            "id_n": {
                ...
            }
        ]
    }

where the parts of the json object can be understood as follows:

* **config** : The configuration file used to generate the Mesh.
* **cellboxes** : A list of json representations of CellBox objects that form the Mesh.
* **neighbour_graph** : A graphical representation of the adjacency of CellBoxes within the Mesh.

=========
cellboxes
=========

Each CellBox object within **cellboxes** in the outputted json object is of
the following form:

::

    {
        "id" (string): ...,
        "geometry" (string): ...,
        "cx" (float): ...,
        "cy" (float): ...,
        "dcx" (float): ...,
        "dcy" (float): ...,
        "<value_1>" (float): ...,
        ...
        "<value_n>" (float): ...
    }

Where the values within the CellBox represent the following:

* **id** : The index of the CellBox within the Mesh.
* **geometry** : The spatial boundaries of the CellBox.
* **cx** : The x-position of the centroid of the CellBox, given in degrees latitude.
* **cy** : The y-position of the centroid of the CellBox, given in degrees longitude.
* **dcx** : The x-distance from the edge of the CellBox to the centroid of the CellBox. Given in degrees longitude.
* **dxy** : the y-distance from the edge of the CellBox to the centroid of the CellBox. Given in degrees latitude.

.. figure:: ./Figures/cellbox_json.png
   :align: center
   :width: 700


===============
neighbour_graph
===============

For each CellBox in the **cellboxes** section of the json object, there will be a
corresponding entry in the **neighbour_graph**.

.. note::
    Once the vehicle accessibility conditions have been applied to the json object, this may no longer be true
    as inaccessible CellBoxes will be removed from *neighbour_graph* but will remain in *cellboxes*

Each entry in the **neighbour_graph** is of the following form:

:: 

    "<id>": {
        "1": [...],
        "2": [...],
        "3": [...],
        "4": [...],
        "-1": [...],
        "-2": [...],
        "-3": [...],
        "-4": [...]
    }

where each of the values represent the following: 

* **<id>** : The id of a CellBox within *cellboxes*
    * **1**  : A list of id's of CellBoxes within *cellboxes* to the North-East of the CellBox specified by 'id'.
    * **2**  : A list of id's of CellBoxes within *cellboxes* to the East of the CellBox specified by 'id'.
    * **3**  : A list of id's of CellBoxes within *cellboxes* to the South-East of the CellBox specified by 'id'.
    * **4**  : A list of id's of CellBoxes within *cellboxes* to the South-West of the CellBox specified by 'id'.
    * **-1** : A list of id's of CellBoxes within *cellboxes* to the South of the CellBox specified by 'id'.
    * **-2** : A list of id's of CellBoxes within *cellboxes* to the South-West of the CellBox specified by 'id'.
    * **-3** : A list of id's of CellBoxes within *cellboxes* to the North-West of the CellBox specified by 'id'.
    * **-4** : A list of id's of CellBoxes within *cellboxes* to the South of the CellBox specified by 'id'.

.. figure:: ./Figures/neighbour_graph_json.png
   :align: center
   :width: 700

# Mesh Construction - Classes

This section describes the main classes of the Mesh Construction module in detail. 
For an overview of the abstractions behind the Mesh Construction module, see the 
[Mesh Construction - Overview](index.md) section of the documentation.

## MeshBuilder

The `MeshBuilder` object is the main class of the Mesh Construction module. It is used to build the 
`EnvironmentalMesh` object from a collection geospatial data. Features of the created `EnvironmentalMesh` 
as be set using a configuration file passed to the `MeshBuilder` object. For more information on the format
of the configuration file, see the [configuration - mesh construction](../config/mesh_construction.md) section of the documentation.

::: meshiphi.mesh_generation.mesh_builder.MeshBuilder
    options:
      merge_init_into_class: true                 
      members:
      - build_environmental_mesh
      - split_and_replace
      - split_to_depth
      - add_dataloader

## EnvironmentMesh

The `EnvironmentMesh` object is a collection of geospatial boundaries containing an aggregated representation 
of the data contained within the boundaries (`AggregatedCellBox` objects). The `EnvironmentMesh` object is 
created by the `MeshBuilder` object, though the object is mutable and can be updated after construction.

::: meshiphi.mesh_generation.environment_mesh.EnvironmentMesh
    options:
      merge_init_into_class: true                 
      members:
      - load_from_json
      - update_cellbox
      - to_json
      - to_geojson
      - to_tif
      - save
      - merge_mesh
      - split_and_replace

## NeighbourGraph

The `NeighbourGraph` object is used to store the connectivity information between the cells of the `EnvironmentMesh`.
The `NeighbourGraph` object is created by the `MeshBuilder` object and is encoded into the `EnvironmentalMesh`.

::: meshiphi.mesh_generation.neighbour_graph.NeighbourGraph
    options:
      members:
      - initialise_neighbour_graph
      - get_neighbour_case
      - update_neighbours

## CellBox

The `CellBox` object is used to store the data contained within a geospatial boundary in the `MeshBuilder`. 
The `CellBox` object is created by the `MeshBuilder` object and transformed into an `AggregatedCellBox` object 
when the `MeshBuilder` returns the ``EnvironmentalMesh`` object.

::: meshiphi.mesh_generation.cellbox.CellBox
    options:
      merge_init_into_class: true                 
      members:
      - set_data_source
      - should_split
      - split
      - set_parent
      - aggregate

## MetaData

The `Metadata` object is used to store the metadata associated with a `CellBox` object within the `MeshBuilder`. This includes 
associated DataLoaders, the depth of the ``CellBox`` within the `MeshBuilder`, and the parent `CellBox` of the `CellBox` among others.

::: meshiphi.mesh_generation.metadata.Metadata
    options:
      merge_init_into_class: true                 

## AggregatedCellBox

An aggregated representation of the data contained within a geospatial boundary. The `AggregatedCellBox` object is created 
by the `CellBox` object when the `MeshBuilder` returns the `EnvironmentalMesh`. 

::: meshiphi.mesh_generation.aggregated_cellbox.AggregatedCellBox
    options:
      merge_init_into_class: true                 
      members:
      - contains_point
      - to_json

  







# Dataloader Interface

Shows how the mesh generation code may interact with the dataloaders. In operation,
only `get_hom_condition()` and `get_value()` are needed realistically. Other methods are
implemented in the [abstractScalar](scalar.md#abstract-scalar-base-class) and [abstractVector](vector.md#abstract-vector-base-class) dataloaders.

::: meshiphi.dataloaders.dataloader_interface

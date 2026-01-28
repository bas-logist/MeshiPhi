# Background


## Code Structure

The aim of this manual is to provide the user with all the tools that they need to run the software for a set of
examples. We also hope that the background information supplied for each section allows the user to understand the
methods used throughout this package.

The separate stages of the codebase can be broken down into:

1. [Dataloaders](dataloaders/overview.md) - Reading in different datasets of differing types. Throughout this section
we will outline the form that the input datasets should take and useful tips for pre-processing your data.

2. [Mesh Construction](mesh_construction/index.md) - Generating a non-uniform mesh representation of the
environmental conditions. In this section we outline the different Python classes that are used to construct a
discretised representation of the user-defined datasets, giving a coding background to the dynamic splitting of the mesh
to finer resolution in regions of spatially varying data.

Each stage of this process makes use of a configuration file, found in the [Configuration Overview](config/overview.md) section of the
documentation and produces an output file, the form of which can be found in the [outputs](output.md) section.

In addition to the core functionality of the package we have also developed a set of plotting classes that allow the user
to generate both interactive maps and static figures of the Mesh outputs. These can be found in the [Mesh Plotting](plotting.md)
section later in the manual.
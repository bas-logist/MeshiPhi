# Meshiφ (MeshiPhi)

![](logo.jpg)

![Dev Status](https://img.shields.io/badge/Status-Active-green)
[![Documentation](https://img.shields.io/badge/Manual%20-github.io%2FMeshiPhi%2F-red)](https://bas-amop.github.io/MeshiPhi/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/meshiphi)
[![PyPi](https://img.shields.io/pypi/v/meshiphi)](https://pypi.org/project/meshiphi/)
[![Release Tag](https://img.shields.io/github/v/tag/bas-amop/MeshiPhi)](https://github.com/bas-amop/meshiphi/tags)
[![Issues](https://img.shields.io/github/issues/bas-amop/MeshiPhi)](https://github.com/bas-amop/MeshiPhi/issues)
[![License](https://img.shields.io/github/license/bas-amop/MeshiPhi)](https://github.com/bas-amop/MeshiPhi/blob/main/LICENSE)
[![Test Status](https://github.com/bas-amop/MeshiPhi/actions/workflows/test.yml/badge.svg)](https://github.com/bas-amop/MeshiPhi/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/badge/coverage-report-blue)](https://github.com/bas-amop/MeshiPhi/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-0C3A5C?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)


Introducing Meshiφ, a versatile software package designed for comprehensive earth modeling and navigation planning. Meshiφ works by discretizing the Earth's surface into a non-uniform grid, allocating higher resolution in regions of geographic diversity, and conserving lower resolution in more uniform regions. These mesh objects can be output in standard formats, such as GeoJSON and GeoTIFF, enabling data-visualisation via GIS software such as ArcGIS. The default end products are designed to work with <a href="https://github.com/bas-amop/PolarRoute/">PolarRoute</a>.

## Installation
Meshiφ can be installed via pip or by cloning the repository from GitHub.

 Pip:
```
pip install meshiphi
```

Github: (for local development)
```
git clone https://github.com/bas-amop/MeshiPhi
cd MeshiPhi
pip install -e .
```

The Meshiφ package has an optional dependency on GDAL, which is required to produce outputs in GeoJSON or GeoTIFF formats. More information on setting up GDAL can be found in the manual pages linked above.

## Usage

Meshiφ provides CLI commands. For example, to create a mesh:

```
create_mesh --config path/to/config.json --output path/to/output.geojson
```

Example configs are provided in `examples/environment_config/`.

To export a mesh:
```
export_mesh --input path/to/meshfile --format geojson --output path/to/output.geojson
```

For a full list of commands and options, run:
```
create_mesh --help
```

See the [documentation](https://bas-amop.github.io/MeshiPhi/) for more details and advanced usage.

## Documentation
Sphinx is used to generate documentation for this project. The dependencies can be installed through pip:
```
pip install sphinx sphinx_markdown_builder sphinx_rtd_theme rinohtype
```
When updating the docs, run the following command within the MeshiPhi directory to recompile.
```
sphinx-build -b html ./docs/source ./docs/html
```
Sometimes the cache needs to be cleared for internal links to update. If facing this problem, run this from the MeshiPhi directory.
```
rm -r docs/build/.doctrees/
```

## Required Data sources
Meshiφ has been built to work with a variety of open-source atmospheric and oceanographic data sources.
A list of supported data sources and their associated data-loaders is given in the
'Data Loaders' section of the manual


## Developers
Samuel Hall, Harrison Abbot, Ayat Fekry, George Coombs, David Wyld, Thomas Zwagerman, Jonathan Smith, Maria Fox, and James Byrne

## Contributing
For more details on contributing, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License
This software is licensed under a MIT license, but request users cite our publication.

Jonathan D. Smith, Samuel Hall, George Coombs, James Byrne, Michael A. S. Thorne,  J. Alexander Brearley, Derek Long, Michael Meredith, Maria Fox,  (2022), Autonomous Passage Planning for a Polar Vessel, arXiv, https://arxiv.org/abs/2209.02389

For more information please see the attached ``LICENSE`` file.

## How to Cite

If you use Meshiφ in your research, please cite our software and publication:

- See the [CITATION.cff](./CITATION.cff) file for citation metadata.

You can also use the "Cite this repository" button on GitHub for formatted citations.

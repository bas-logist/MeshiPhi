# Installation

In this section we outline the necessary steps for installing the MeshiPhi software package. MeshiPhi requires a
pre-existing installation of Python 3.8 or higher.


## Installing MeshiPhi

MeshiPhi can be installed from one of the following two sources:

from PyPI: `pip install MeshiPhi`

from Github: 

```sh
git clone https://github.com/bas-amop/MeshiPhi.git
cd MeshiPhi
pip install .
```

## Installing GDAL (Optional)

MeshiPhi has GDAL as an optional requirement. It is only used when exporting TIFF images, so if this is not useful to
you, we would recommend steering clear. It is not trivial and is a common source of problems.
With that said, below are instructions for various operating systems.

### Windows

**Note**: We assume a version of Windows 10 or higher, with a working version of Python 3.9 including pip installed. 

**Note**: We recommend installing MeshiPhi into a virtual environment.


```sh
pip install pipwin # pipwin is a package that allows for easy installation of windows binaries
pipwin install gdal
pipwin install fiona
```

### Linux/MacOS

Ubuntu/Debian:

```sh
sudo add-apt-repository ppa:ubuntugis/ppa
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal
pip install GDAL==$(gdal-config --version)
```

Fedora:

```sh
sudo dnf update
sudo dnf install gdal gdal-devel
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal
pip install GDAL==$(gdal-config --version)
```

MacOS (with HomeBrew):

```sh
brew install gdal --HEAD
brew install gdal
pip install GDAL==$(gdal-config --version)
```
# Mesh Manipulation Using Shapefiles - ArcNet Example

Sometimes we might want our mesh to be manipulated based on some spatial data. For example, lets say we want to limit maximum travel speeds for ecologically sensitive areas like [WWF's ArcNet Priority Areas for Conservation](https://www.arcticwwf.org/our-priorities/arcnet/). We can load these shapefiles using a custom `DataLoader` and generate a mesh which accounts for these constraints. 

## ArcNet Shapefile Download

First, download the ArcNet shapefiles to a suitable location on your machine: 

```bash
wget https://admin.arcticwwf.org/app/uploads/2026/06/ArcNet-shapefiles.zip
unzip ArcNet-shapefiles.zip
```

## Generate a Mesh Config File Using the ArcNet Shapefiles

A minimal working example of such a config may look like the following:

```json
{
    "region": {
        "lat_min": 45,
        "lat_max": 90,
        "long_min": -180,
        "long_max": -180,
        "start_time": "2026-08-31",
        "end_time": "2026-09-03",
        "cell_width": 5,
        "cell_height": 2.5
    },
    "data_sources": [
        {
            "loader": "lut_shapefile_arcnet",
            "params": {
                "data_name": "protected_area_speed_limit",
                "value": 15.00, 
                "value_fill_types": "Nan",
                "aggregate_type": "MIN",
                "files": [
                    "/path/to/ArcNet_PACs_uncurved.shp"
                ],
                "splitting_conditions": [
                    {
                        "protected_area_speed_limit": {
                            "boundary": true,
                            "split_lock": false
                        }
                    }
                ]
            }
        }
    ],
    "splitting": {
        "split_depth": 4,
        "minimum_datapoints": 5
    }
}
```

This config will load the ArcNet shapefiles using MeshiPhi's ArcNet DataLoader (`meshiphi/dataloaders/lut/lut_shapefile_arcnet.py`) and set a `protected_area_speed_limit` value of 15.00 for any mesh cells that overlap with the shapefile, effectively setting a speed limit of 15km/h for those areas. 

We tell the mesh generator to split any cells that overlap with the shapefile boundaries, so that the speed limit does not apply beyond the shapefile's boundaries. 

We set the `aggregate_type` to `MIN`, so that if multiple data sources want to influence the speed of a cell split by the DataLoader, the minimum value will be used. This ensures that the speed limit provided by the ArcNet DataLoader is always enforced, even if others apply a higher speed to the cell (e.g., low sea ice concentration means the vessel could travel >15km/h). 

It is highly likely you will want to add additional data sources to the config. 

Save the config to a suitable location as a JSON.

## Generate a mesh

We can then generate a mesh in Python using the config file we created.

```python
# Load ArcNet config
config_path = '/path/to/arcnet.config.json'
with open(config_path, 'r') as f:
    config = json.load(f)
    
# Build environmental mesh
cg = MeshBuilder(config).build_environmental_mesh()
mesh = cg.to_json()

# Save mesh to file
with open('arcnet_mesh.json', 'w') as f:
    json.dump(mesh, f)
```

We can then use this mesh for whatever we want, for example by passing it to [PolarRoute](https://github.com/bas-logist/PolarRoute) to generate a vessel path that respects the speed limits imposed in the ArcNet areas. To see how this can be achieved, please see the [PolarRoute example documentation](https://bas-logist.github.io/PolarRoute/examples/).


## Acknowledgements

The ArcNet Priority Areas for Conservation shapefiles were provided by WWF:

James, T.D., Sommerkorn, M., Solovyev, B. et al. Whole-ocean network design and implementation pathway for Arctic marine conservation. npj Ocean Sustain 3, 25 (2024). [https://doi.org/10.1038/s44183-024-00047-9](https://doi.org/10.1038/s44183-024-00047-9).
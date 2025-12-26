region_schema = {
    "type": "object",
    "required": [
        "lat_min",
        "lat_max",
        "long_min",
        "long_max",
        "start_time",
        "end_time",
        "cell_width",
        "cell_height",
    ],
    "additionalProperties": False,
    "properties": {
        "lat_min": {"type": "number"},
        "lat_max": {"type": "number"},
        "long_min": {"type": "number"},
        "long_max": {"type": "number"},
        "start_time": {"type": "string"},
        "end_time": {"type": "string"},
        "cell_width": {"type": "number"},
        "cell_height": {"type": "number"},
    },
}

dataloader_schema = {
    "type": "object",
    "required": ["loader", "params"],
    "additionalProperties": False,
    "properties": {"loader": {"type": "string"}, "params": {"type": "object"}},
}

splitting_schema = {
    "type": "object",
    "required": ["split_depth", "minimum_datapoints"],
    "additionalProperties": False,
    "properties": {
        "split_depth": {"type": "integer"},
        "minimum_datapoints": {"type": "integer"},
    },
}

mesh_schema = {
    "type": "object",
    "required": ["region", "data_sources", "splitting"],
    "properties": {
        "region": {"$ref": "#/region_schema"},
        "data_sources": {
            "type": "array",
            "items": {"$ref": "#/dataloader_schema"},
        },
        "splitting": {"$ref": "#/splitting_schema"},
    },
    "region_schema": region_schema,
    "dataloader_schema": dataloader_schema,
    "splitting_schema": splitting_schema,
}

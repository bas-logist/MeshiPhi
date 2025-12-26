from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
import pandas as pd


class FullMeshValidator:
    """
    A class that validates a constructed mesh against its actual sourced geo-spatial data.
    Validation takes place by comparing the aggregated data value of mesh's cellbox against the
    actual data contained within cellbox's bounds.

    This object compares all source data contained within the mesh to the mesh data, where as the
    MeshValidator object only compares a sample of the source data to the mesh data.
    """

    def __init__(self, mesh, source_data):
        """
        Args:
            mesh: json file containing mesh data
            source_data: DataFrame containing source data. Must contain columns 'lat' and 'long'
        """
        self.mesh = EnvironmentMesh.load_from_json(mesh)
        self.source_data = source_data

        # Validate that the source data contains the required columns
        if "lat" not in self.source_data.columns:
            raise ValueError("Source data must contain column 'lat'")
        if "long" not in self.source_data.columns:
            raise ValueError("Source data must contain column 'long'")

        # Validate that the source data is within the require bounds

    def validate_vector(self, sd_name, md_name):
        """
        Validate the mesh by comparing the vector field in the mesh to the source data
        Args:
            sd_name: name of source data vector field
            md_name: name of mesh vector field

        Returns:
            validation_results: dictionary containing validation results
        """

        full_raw_processed = pd.DataFrame()
        for cell_count in range(len(self.mesh.agg_cellboxes)):
            # Get slice of data within cellbox
            bounds = self.mesh.agg_cellboxes[cell_count].get_bounds()
            raw_slice = self.slice_data(bounds)

            # Get vector value from cellbox
            cell_vector_0 = "cell_" + md_name[0]
            cell_vector_1 = "cell_" + md_name[1]
            raw_slice[cell_vector_0] = self.mesh.agg_cellboxes[
                cell_count
            ].get_agg_data()[md_name[0]]
            raw_slice[cell_vector_1] = self.mesh.agg_cellboxes[
                cell_count
            ].get_agg_data()[md_name[1]]

            # Calculate difference vector

            raw_slice["d_vector_0"] = raw_slice[sd_name[0]] - raw_slice[cell_vector_0]
            raw_slice["d_vector_1"] = raw_slice[sd_name[1]] - raw_slice[cell_vector_1]

            # Calculate magnitude of difference vector (used as error metric)
            raw_slice["d_vector_mag"] = (
                raw_slice["d_vector_0"] ** 2 + raw_slice["d_vector_1"] ** 2
            ) ** 0.5
            raw_slice["d_vector_mag^2"] = raw_slice["d_vector_mag"] ** 2

            full_raw_processed = pd.concat([full_raw_processed, raw_slice])

        # Calculate mean magnitude of difference vector
        mean_d_vector_mag = full_raw_processed["d_vector_mag"].mean()
        rms_d_vector_mag = (full_raw_processed["d_vector_mag^2"].mean()) ** 0.5

        validation_results = {
            "cellbox_count": len(self.mesh.agg_cellboxes),
            "mean_d_vector_mag": mean_d_vector_mag,
            "root_mean_squared_d_vector_mag": rms_d_vector_mag,
        }

        return validation_results

    def validate_scalar(self, sd_name, md_name):
        """
        Validate the mesh by comparing the scalar field in the mesh to the source data
        Args:
            sd_name: name of source data scalar field
            md_name: name of mesh scalar field

        Returns:
            validation_results: dictionary containing validation results
        """
        full_raw_processed = pd.DataFrame()

        for cell_count in range(len(self.mesh.agg_cellboxes)):
            # Get slice of data within cellbox
            bounds = self.mesh.agg_cellboxes[cell_count].get_bounds()
            raw_slice = self.slice_data(bounds)

            # Get scalar value from cellbox
            cell_scalar = "cell_" + md_name
            raw_slice[cell_scalar] = self.mesh.agg_cellboxes[cell_count].get_agg_data()[
                md_name
            ]

            # Calculate difference scalar
            raw_slice["d_scalar"] = abs(raw_slice[sd_name] - raw_slice[cell_scalar])
            raw_slice["d_scalar^2"] = raw_slice["d_scalar"] ** 2

            full_raw_processed = pd.concat([full_raw_processed, raw_slice])

        mean_err = full_raw_processed["d_scalar"].mean()
        rmse = (full_raw_processed["d_scalar^2"].mean()) ** 0.5

        validation_results = {
            "cellbox_count": len(self.mesh.agg_cellboxes),
            "mean_err": mean_err,
            "root_mean_squared_err": rmse,
        }

        return validation_results

    def slice_data(self, bounds):
        """
        return a slice of the source data within the bounds
        Args:
        bounds: Bounds object containing bounds to slice data with

        Returns:
        raw_slice: DataFrame containing slice of data
        """

        raw_slice = self.source_data[
            self.source_data["lat"].between(bounds.lat_range[0], bounds.lat_range[1])
        ]
        raw_slice = raw_slice[
            raw_slice["long"].between(bounds.long_range[0], bounds.long_range[1])
        ]

        return raw_slice

import pandas as pd

from meshiphi.utils import round_to_sigfig


class MeshComparator:
    SIG_FIG_TOLERANCE = 4

    @staticmethod
    def _return_as(df, return_type):
        """
        Allows for flexibility in how to return differences to user. Sets a
        return type for each method.

        Args:
            df (pd.DataFrame): Dataframe with all the discovered differences
            return_type (str): Flag determining the type of output the user wants

        Returns:
            <various>: Output depends on what return_type is specified in args
        """

        # Set default return_type to entire dataframe
        if return_type is None:
            return_type = "df"
        # Parse return_type to provide correct output
        if return_type in ["cellboxes", "cb"]:
            return df["cellboxes"]
        if return_type in ["id"]:
            return df["id"]
        if return_type in ["dataframe", "df"]:
            return df
        return None

    def compare_cellbox_boundaries(self, mesh1, mesh2, return_type=None):
        """
        Compare the boundaries of the cellboxes in the two meshes

        Args:
            mesh1 (json): the first mesh to compare
            mesh2 (json): the second mesh to compare
            return_type (str, optional): Type of output user wants. Defaults to pd.DataFrame.

        Returns:
            <various>:
                Output in format specified by return_type argument.
                See _return_as() docstring for more info
        """

        cellboxes1 = pd.DataFrame(mesh1["cellboxes"]).set_index("geometry")
        cellboxes2 = pd.DataFrame(mesh2["cellboxes"]).set_index("geometry")

        # Get list of cellboxes that are in mesh2 but not mesh1
        mismatched_rows = []
        for idx, row in cellboxes2.iterrows():
            if idx not in cellboxes1.index:
                mismatched_rows += [row]

        # If there were mismatched rows
        if mismatched_rows:
            mismatched_df = pd.concat(mismatched_rows, axis=1).T
            mismatched_df.index.name = "geometry"
        # Otherise, create an empty dataframe
        else:
            mismatched_df = pd.DataFrame()

        # TODO update to check if there are cells that are common but split in diff

        return self._return_as(mismatched_df, return_type)

    def compare_cellbox_values(self, mesh1, mesh2, return_type=None):
        """
        Compare the values of the cellboxes in the two meshes in cellboxes
        that both meshes have in common

        Args:
            mesh1 (json): the first mesh to compare
            mesh2 (json): the second mesh to compare
            return_type (str, optional): Type of output user wants. Defaults to pd.DataFrame.

        Returns:
            <various>:
                Output in format specified by return_type argument.
                See _return_as() docstring for more info
        """

        cellboxes1 = pd.DataFrame(mesh1["cellboxes"]).set_index("geometry")
        cellboxes2 = pd.DataFrame(mesh2["cellboxes"]).set_index("geometry")

        # Only compare values in cellboxes common between both meshes
        common_cbs = cellboxes1.index.intersection(cellboxes2.index)
        cellboxes1 = cellboxes1.loc[common_cbs]
        cellboxes2 = cellboxes2.loc[common_cbs]

        # Drop columns with different names between the two
        col1 = cellboxes1.columns.to_list()
        col2 = cellboxes2.columns.to_list()

        common_cols = list(set(col1).intersection(col2))
        cellboxes1 = cellboxes1[common_cols]
        cellboxes2 = cellboxes2[common_cols]

        for df in [cellboxes1, cellboxes2]:
            # Round float values to significant figure
            float_cols = df.select_dtypes(include=float).columns
            for col in float_cols:
                df[col] = round_to_sigfig(df[col].to_numpy(), self.SIG_FIG_TOLERANCE)

            # Round all float values in lists to significant figure
            list_cols = df.select_dtypes(include=list).columns
            for col in list_cols:
                round_col = []
                for val in df[col]:
                    if isinstance(val, list) and all(isinstance(x, float) for x in val):
                        round_col.append(round_to_sigfig(val, self.SIG_FIG_TOLERANCE))
                    else:
                        round_col.append(val)
                df[col] = round_col

        # Compare the two dataframes
        # Note: Only the diff lines are kept
        diff = cellboxes1.compare(cellboxes2)
        # Return list of common cellboxes with different values
        diff_df = cellboxes2.loc[diff.index]

        return self._return_as(diff_df, return_type)

    def compare_cellbox_attributes(self, mesh1, mesh2, return_type=None):
        """
        Compare the attributes of the cellboxes in the two meshes if the meshes
        have cellboxes in common

        Args:
            mesh1 (json): the first mesh to compare
            mesh2 (json): the second mesh to compare
            return_type (str, optional): Type of output user wants. Defaults to pd.DataFrame.

        Returns:
            <various>:
                Output in format specified by return_type argument.
                See _return_as() docstring for more info
        """

        # Load as a dict of pd Series
        # Can't load as a df as columns would be generated for every attribute in the mesh
        # so can't compare cellbox by cellbox
        cellboxes1 = {i["geometry"]: pd.Series(i) for i in mesh1["cellboxes"]}
        cellboxes2 = {i["geometry"]: pd.Series(i) for i in mesh2["cellboxes"]}

        mismatched_rows = []

        for cb1_geom, cb1_series in cellboxes1.items():
            # If not matching geometries, skip
            if cb1_geom not in cellboxes2:
                continue
            # Otherwise, extract other cellbox to compare
            cb2_series = cellboxes2[cb1_geom]

            # If attributes not the same between the two cellboxes with similar boundary
            if not cb1_series.index.equals(cb2_series.index):
                mismatched_rows += [cb2_series]

        # If there were mismatched rows
        if mismatched_rows:
            mismatched_df = pd.concat(mismatched_rows, axis=1).T
            mismatched_df = mismatched_df.set_index("geometry")
        # Otherise, create an empty dataframe
        else:
            mismatched_df = pd.DataFrame()
        return self._return_as(mismatched_df, return_type)

    def compare_neighbour_graph_values(self, mesh1, mesh2, return_type=None):
        """
        Compare the values of the neighbour graph in the two meshes

        Args:
            mesh1 (json): the first mesh to compare
            mesh2 (json): the second mesh to compare
            return_type (str, optional): Type of output user wants. Defaults to pd.DataFrame.

        Returns:
            <various>:
                Output in format specified by return_type argument.
                See _return_as() docstring for more info
        """

        cellboxes2 = pd.DataFrame(mesh2["cellboxes"]).set_index("geometry")

        ng_1 = mesh1["neighbour_graph"]
        ng_2 = mesh2["neighbour_graph"]

        mismatched_rows = []

        for node in ng_2:
            if node in ng_1:
                neighbours_1 = ng_1[node]
                neighbours_2 = ng_2[node]

                sorted_neighbours_1 = {k: sorted(neighbours_1[k]) for k in neighbours_1}
                sorted_neighbours_2 = {k: sorted(neighbours_2[k]) for k in neighbours_2}

                if sorted_neighbours_1 != sorted_neighbours_2:
                    cellbox_row = cellboxes2.loc[cellboxes2["id"] == node]
                    mismatched_rows += [cellbox_row]
        # If there were mismatched rows
        if mismatched_rows:
            mismatched_df = pd.concat(mismatched_rows, axis=1)
            mismatched_df.index.name = "geometry"
        # Otherise, create an empty dataframe
        else:
            mismatched_df = pd.DataFrame()
        return self._return_as(mismatched_df, return_type)

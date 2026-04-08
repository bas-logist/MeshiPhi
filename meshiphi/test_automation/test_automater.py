from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess as sp
import tempfile
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch
from shapely import wkt

from meshiphi import REGRESSION_TESTS_BY_FILE, UNIT_TESTS_BY_FILE
from meshiphi.mesh_validation.mesh_comparator import MeshComparator

logger = logging.getLogger(__name__)


class TestAutomater:
    def __init__(
        self,
        from_branch: str | None = None,
        into_branch: str = "main",
        regression: bool = True,
        unit: bool = True,
        save: bool = False,
        plot: bool = False,
    ) -> None:
        """
        Runs through test suite only taking into account relevant tests for the
        modified files

        Args:
            from_branch (str):
                Git branch that you want to test.
                Defaults to currently active branch.
            into_branch (str):
                Git branch that 'from_branch' is being compared to.
                Defaults to main.
            regression (bool, optional):
                Flag for running regression tests.
                Defaults to True.
            unit (bool, optional):
                Flag for running unit tests.
                Defaults to True.
        """
        # Get directory of this package, so can reference test files individually
        self.repo_dir = self.get_base_dir()
        # Save current directory for output files
        self.cwd = os.getcwd()
        # Set base folder to repo directory to run git command later
        os.chdir(self.repo_dir)
        # Create a temporary directory to write mesh fixtures to
        temp_dir = tempfile.mkdtemp()
        # Create a seperator, 32 = length of logging prefix
        remaining_terminal_width = os.get_terminal_size().columns - 32
        self._double_separator = "=" * remaining_terminal_width
        self._single_separator = "-" * remaining_terminal_width
        # Initialise arrays with each test, organise by status
        self.passes: list[TestInfo] = []
        self.fails: list[TestInfo] = []
        self.errors: list[TestInfo] = []

        # Get files that are different between branches
        diff_files = self.get_diff_filenames(from_branch=from_branch, into_branch=into_branch)

        # Run relevant tests
        logger.info(self._double_separator)
        if regression:
            self.run_regression_tests(diff_files, save_to=temp_dir, plot=plot)
        if unit:
            self.run_unit_tests(diff_files, save_to=temp_dir)

        # Write status for all tests to terminal
        logger.info(self._double_separator)
        for test_info in self.passes:
            logger.debug(str(test_info))
        for test_info in self.fails:
            logger.info(str(test_info))
        for test_info in self.errors:
            logger.info(str(test_info))

        # Write out stats about each test suite run
        logger.info(self._double_separator)
        self.summarise_test_stats()

        # Save output if requested
        logger.info(self._single_separator)
        if save:
            output_folder = self._setup_output_folder()
            # Save failing test output to current working directory
            self.save_tests(temp_dir, output_folder, fails=True, errors=True)

        # Finally, remove temp folder
        shutil.rmtree(temp_dir)

    def _run_tests(
        self,
        diff_files: list[str],
        test_dir: str,
        test_dict: dict[str, list[str]],
        save_to: str | None = None,
    ) -> None:
        """
        Runs relevant regression or unit tests within 'test_dir'

        Args:
            diff_files (list):
                List of files that are different from comparison branch
            test_dir (str):
                Directory where relevant tests are located
            test_dict (dict):
                Mapping between diff file and relevant test
        """
        if save_to is None:
            save_to = os.devnull

        relevant_tests = []
        # Change to reg/unit test folder
        os.chdir(test_dir)

        # For each file with a diff
        for file in diff_files:
            # Get relevant regression tests
            relevant_tests += self.get_relevant_tests(file, test_dict)
        # Get list of unique reg tests to run
        relevant_tests = list(set(relevant_tests))

        # If there are tests to run
        if relevant_tests:
            logger.info("Running the following tests:")
            # Run each test
            for test in relevant_tests:
                test_file_path = os.path.join(test_dir, test)
                logger.info(f"\t- {test_file_path}")

                command = ["pytest", test_file_path, "-rA", "--basetemp", save_to]
                pytest_output = sp.run(command, stdout=sp.PIPE)
                pytest_stdout = pytest_output.stdout.decode("utf-8")
                passes, fails, errors = self.parse_pytest_stdout(pytest_stdout)
                self.passes += passes
                self.fails += fails
                self.errors += errors

        # Otherwise provide a message
        else:
            logger.info(" --- No relevant tests found --- ")

        # Change back to repo base directory
        os.chdir(self.repo_dir)

    def run_regression_tests(
        self, diff_files: list[str], save_to: str | None = None, plot: bool = False
    ) -> None:
        """
        Runs relevant regression tests for files within 'diff_files'

        Args:
            diff_files (list):
                List of files that are different from comparison branch
        """
        # Get base directory for regression tests
        reg_test_dir = os.path.join(self.repo_dir, "tests", "regression_tests")
        logger.info("Attempting regression tests...")
        self._run_tests(diff_files, reg_test_dir, REGRESSION_TESTS_BY_FILE, save_to=save_to)

        # Summarise mesh stats of regression tests
        if save_to:
            # For each test file saved
            for test_output_file in os.listdir(save_to):
                test_output_path = os.path.join(save_to, test_output_file)
                # Skip over any non-json files that might be leftover in folder
                # e.g. Saved plots that are generated in this loop
                if not test_output_file.endswith(".json"):
                    continue

                # Save plot if requested
                if plot:
                    self.plot_test(test_output_path, save_to=save_to)

                # Write summary to CLI
                logger.info(f"Analysing {test_output_file}")
                self.summarise_reg_tests(test_output_path)
                logger.info(self._single_separator)

    def run_unit_tests(self, diff_files: list[str], save_to: str | None = None) -> None:
        """
        Runs relevant unit tests for files within 'diff_files'

        Args:
            diff_files (list):
                List of files that are different from comparison branch
        """
        # Get base directory for unit tests
        unit_test_dir = os.path.join(self.repo_dir, "tests", "unit_tests")
        logger.info("Attempting unit tests...")
        self._run_tests(diff_files, unit_test_dir, UNIT_TESTS_BY_FILE, save_to=save_to)

    def _setup_output_folder(self) -> str:
        """
        Creates a 'pytest_meshiphi' folder at the user's current working directory

        Returns:
            str: Path to folder output is being saved to
        """
        # Define output folder as current location
        output_folder = os.path.join(self.cwd, "pytest_meshiphi")
        # Remove folder if it exists
        try:
            shutil.rmtree(output_folder)
            logger.warning(f"Overwriting {output_folder}")
        except FileNotFoundError:
            logger.debug(f"{output_folder} doesn't exist, nothing to remove")
        # Recreate folder
        os.makedirs(output_folder, exist_ok=True)

        return output_folder

    @staticmethod
    def parse_pytest_stdout(
        stdout: str,
    ) -> tuple[list[TestInfo], list[TestInfo], list[TestInfo]]:
        """
        Turns stdout of Pytest into TestInfo objects

        Args:
            stdout (str): Minimal output of Pytest

        Returns:
            tuple: lists of TestInfo objects, organised into pass, fail, and error
        """
        # Split into three categories
        passes = []
        fails = []
        errors = []
        # Get index of line in stdout that contains short summary info
        stdout_lines = stdout.split("\n")
        summary_idx = next(
            (idx for idx, s in enumerate(stdout_lines) if "short test summary info" in s), 0
        )
        # Iterate through pytest summary output
        for line in stdout_lines[summary_idx:]:
            # Only read the lines with all necessary info
            if "::" in line:
                # Split into pertinent parts
                split_line_str = line.replace("::", " ").replace("[", " ").replace("]", " ")
                split_line: list[str] = split_line_str.split()
                status = split_line[0]
                test_file = split_line[1]
                test_method = os.path.basename(split_line[2])
                reference_file = split_line[3]
                # Store as object
                test_info = TestInfo(test_file, test_method, reference_file, status)
                # Append to correct list
                if status == "PASSED":
                    passes += [test_info]
                elif status == "FAILED":
                    fails += [test_info]
                elif status == "ERROR":
                    errors += [test_info]
                else:
                    raise ValueError(
                        f"Unexpected test status {status}. Expected PASSED, FAILED, or ERROR"
                    )

        return passes, fails, errors

    @staticmethod
    def get_base_dir() -> str:
        """
        Get base folder for repo.
        """
        # Get grandparent directory of this file, and change to it to run git diff
        dir_path = os.path.dirname(os.path.realpath(__file__))
        par_path = os.path.join(dir_path, os.pardir)
        repo_path = os.path.join(par_path, os.pardir)

        return os.path.abspath(repo_path)

    @staticmethod
    def get_diff_filenames(
        from_branch: str | None = None, into_branch: str | None = None
    ) -> list[str]:
        """
        Gets a list of files that have changed between 'from_branch' and 'into_branch'

        Args:
            from_branch (str, optional):
                Test branch to compare.
                Defaults to current working branch.
            into_branch (str, optional):
                'Ground truth' branch to compare from_branch to.
                Defaults to main.

        Returns:
            list(str):
                List of files that are different between
                from_branch and into_branch
        """
        # Make sure that at least branch merging into is defined
        if into_branch is None:
            into_branch = "main"

        # Base command to run as arg list
        command = ["git", "--no-pager", "diff", "--name-only"]

        # Append branch(es) to diff
        if not from_branch:
            command += [into_branch]
        else:
            command += ["--merge-base", from_branch, into_branch]

        # Run git diff
        git_diff_result = sp.run(command, stdout=sp.PIPE, check=False)
        git_diff = git_diff_result.stdout.decode("utf-8")
        # Extract list of files that have been modified
        raw_filenames = git_diff.split("\n")

        # Sanitise raw list to avoid empty lines
        diff_files = []
        if from_branch:
            logger.info(
                "Following files different between " + f'"{from_branch}" and "{into_branch}"'
            )
        else:
            logger.info(
                "Following files different between " + f'current branch and "{into_branch}"'
            )

        for filename in raw_filenames:
            if filename != "":
                logger.info(f"\t- {filename}")
                diff_files += [filename]

        return diff_files

    def get_relevant_tests(self, diff_file: str, test_dict: dict[str, list[str]]) -> list[str]:
        """
        Determines the relevant tests to run from filename

        Args:
            diff_file (str): File that is modified from into_branch
            test_dict (dict): Mapping of modified file to relevant tests

        Returns:
            list(str):
                List of tests that need to be run due to diff_file being
                modified from ground truth
        """
        relevant_tests = []
        # Strip path from filename
        diff_file = os.path.basename(diff_file)
        # For each available mapping of files to tests
        for package_file, package_tests in test_dict.items():
            # If found a match
            if package_file == diff_file:
                relevant_tests += package_tests

        return relevant_tests

    @staticmethod
    def extract_test_meshes(test_output_file: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Reads test output file and extracts out two meshes;
        the old 'ground truth' mesh, and the newly generated mesh

        Args:
            test_output_file (str):
                Filename of json file holding both meshes

        Returns:
            dict: Ground truth 'old' json mesh
            dict: Updated 'new' json mesh
        """
        with open(test_output_file) as fp:
            test_json = json.load(fp)
        old_json = test_json["old_mesh"]
        new_json = test_json["new_mesh"]

        return old_json, new_json

    def compare_meshes(
        self, old_json: dict[str, Any], new_json: dict[str, Any]
    ) -> dict[str, pd.DataFrame]:
        """
        Runs mesh comparator on old and new mesh stored within
        test_output_file

        Args:
            old_json (dict):
                Mesh with old 'ground truth' values
            new_json (dict):
                Newly generated mesh to compare against old_mesh

        Returns:
            dict: Mesh comparison dataframes indexed by human readable labels
        """

        mc = MeshComparator()

        return {
            "new_mesh": pd.DataFrame(new_json["cellboxes"]).set_index("geometry"),
            "bounds": mc.compare_cellbox_boundaries(old_json, new_json),
            "values": mc.compare_cellbox_values(old_json, new_json),
            "attributes": mc.compare_cellbox_attributes(old_json, new_json),
            "neighbour_graph": mc.compare_neighbour_graph_values(old_json, new_json),
        }

    def save_tests(
        self,
        tmp_dir: str,
        output_folder: str,
        passes: bool = False,
        fails: bool = True,
        errors: bool = True,
    ) -> None:
        """
        Saves copy of newly generated test meshes to 'pytest_meshiphi' folder
        in current working directory. Meshes will be saved as
        './pytest_meshiphi/<test_name>.json'

        Args:
            passes (bool, optional):
                Choice to save tests that pass. Defaults to False.
            fails (bool, optional):
                Choice to save tests that fail. Defaults to True.
            errors (bool, optional):
                Choice to save tests that error. Defaults to True.
        """
        # Get list of files to copy
        reference_files = []
        if passes:
            reference_files += [test_info.reference for test_info in self.passes]
        if fails:
            reference_files += [test_info.reference for test_info in self.fails]
        if errors:
            reference_files += [test_info.reference for test_info in self.errors]
        # Keep unique entries
        reference_files = list(set(reference_files))
        reference_files = [os.path.basename(file) for file in reference_files]

        # For each computed mesh
        for pytest_output_file in os.listdir(tmp_dir):
            # Do a quick comparison
            basename, extension = os.path.splitext(pytest_output_file)
            pytest_output_basename = os.path.join(tmp_dir, basename)
            # Skip over non-json files (i.e. plots if generated, pytest subdirectories)
            if extension != ".json":
                continue
            old_json, new_json = self.extract_test_meshes(pytest_output_basename + ".json")
            comparison = self.compare_meshes(old_json, new_json)
            # Remove full new mesh from comparison dict
            del comparison["new_mesh"]
            # Determine which meshes have no differences
            identical_meshes = [df.empty for df in comparison.values()]
            # If no difference in meshes, remove the file
            if all(identical_meshes):
                os.remove(pytest_output_basename + ".json")
                # Remove plot if it exists
                if os.path.isfile(pytest_output_basename + ".svg"):
                    os.remove(pytest_output_basename + ".svg")
            # If there is a difference, move the file to current directory
            else:
                save_filename = os.path.join(output_folder, basename + ".json")
                plot_filename = os.path.join(output_folder, basename + ".svg")
                logger.info(save_filename)
                shutil.copyfile(pytest_output_basename + ".json", save_filename)
                # Try / Except in case plotting not done
                try:
                    shutil.copyfile(pytest_output_basename + ".svg", plot_filename)
                except OSError as e:
                    logger.debug(e)

    def plot_test(self, test_output: str, save_to: str | None = None) -> None:
        """
        Creates a plot of the differences between the newly generated mesh and
        the ground truth mesh. The mesh displayed will be the new mesh, with
        cellboxes different to the ground truth mesh being highlighted in a unique
        colour depending on the difference.

        Saves image to current working directory under
        './pytest_meshiphi/<test_name>.svg'
        """

        def add_df_to_ax(
            df: gpd.GeoDataFrame,
            ax: Any,
            c: str = "black",
            ids: bool = False,
            label: str | None = None,
            a: float = 0.2,
        ) -> tuple[Any, Patch | None]:
            """
            Converts dataframe output from the MeshComparator into a plotable
            feature

            Args:
                df (pd.DataFrame):
                    Output of MeshComparator. Rows relate to each cellbox that
                    is different between old and new meshes.
                ax (mpl.Axes):
                    Matplotlib axes object to plot onto
                c (str, optional):
                    Colour to plot cellbox. Defaults to 'black'.
                a (float, optional):
                    Alpha value of cellboxes being plotted. Defaults to 0.2.
                ids (bool, optional):
                    Flag indicating whether cellbox ID should be added to cellboxes.
                    Defaults to False.
                label (str, optional):
                    Label to add to legend entry. Defaults to None.

            Returns:
                mpl.Axes: Axes object after being plotted ontop of
                mpl.Patch: Custom legend entry for plotted cellboxes
            """
            # Only attempt plotting if there's something to plot
            if df.empty:
                logger.debug("Nothing to plot, skipping")
                return ax, None
            # Turn geometry wkt to shapely polygons
            df = df.reset_index()
            df["geometry"] = df["geometry"].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(df, crs="EPSG:4326", geometry="geometry")

            # Plot polygons
            gdf.plot(ax=ax, color=c, alpha=a, edgecolor=c)

            # Create a patch for the legend to plot
            legend_entry = Patch(facecolor=to_rgba(c, a), edgecolor=c, label=label)

            # Set a column to have roughly the centrepoint of each cellbox
            gdf["coords"] = gdf["geometry"].apply(lambda x: x.representative_point().coords[:][0])
            if ids:
                # Print cellbox id within the cellbox
                for _idx, row in gdf.iterrows():
                    # Scale cell ID label to fit nicely within cellbox
                    fontsize = 2 * row["dcx"] * (2 ** row["dcx"])
                    ax.annotate(
                        row["id"],
                        xy=(row["cx"], row["cy"]),
                        ha="center",
                        va="center",
                        fontsize=fontsize,
                    )

            return ax, legend_entry

        # Read in test output file and compare meshes in it
        old_json, new_json = self.extract_test_meshes(test_output)
        mesh_comparison = self.compare_meshes(old_json, new_json)

        # Create a plotting window
        _, ax = plt.subplots()

        # Add empty background with cellbox boundaries
        ax, _ = add_df_to_ax(mesh_comparison["new_mesh"], ax, c="darkgrey")
        # Add cellboxes with different boundaries to original
        ax, legend_1 = add_df_to_ax(
            mesh_comparison["bounds"], ax, c="red", ids=True, label="Boundary"
        )
        # Add cellboxes with different values to original
        ax, legend_2 = add_df_to_ax(
            mesh_comparison["values"], ax, c="green", ids=True, label="Values"
        )
        # Add cellboxes with different attributes to original
        ax, legend_3 = add_df_to_ax(
            mesh_comparison["attributes"], ax, c="blue", ids=True, label="Attributes"
        )
        # Add cellboxes with different neighbour graph to original
        ax, legend_4 = add_df_to_ax(
            mesh_comparison["neighbour_graph"],
            ax,
            c="purple",
            ids=True,
            label="Neighbour graph",
        )
        # Save legend entries to handle later, remove None entries
        legend_boxes = [legend_1, legend_2, legend_3, legend_4]
        legend_boxes = [x for x in legend_boxes if x is not None]
        # Draw legend
        ax.legend(
            handles=legend_boxes,
            title="Mismatched\n",
            title_fontsize="large",
            loc="center left",
            bbox_to_anchor=(1, 0.5),
        )
        # Remove whitespace between polygons and axes
        ax.margins(0)

        test_name = os.path.basename(test_output)[:-5]
        ax.set_title(f"Differences in {test_name}")

        if save_to:
            # Save as vector image so can zoom in to see ID per diff cellbox
            plot_output = test_name + ".svg"
            save_output = os.path.join(save_to, plot_output)
            plt.savefig(save_output, bbox_inches="tight")
        else:
            plt.show()
        plt.close()

    def summarise_reg_tests(self, test_output: str) -> None:
        """
        Write out a summary of the difference in cellboxes in the terminal

        Args:
            test_output (str): Filename of saved test mesh
        """

        def print_summary(comparison: dict[str, pd.DataFrame], summary_key: str) -> None:
            """
            Prints out a summary of the number of different values
            in the old mesh compared to the new mesh
            """

            logger.info(f"Comparing {summary_key}:")
            # Extract out the relevant dfs
            new_df = comparison["new_mesh"]
            diff_df = comparison[summary_key]

            if diff_df.empty:
                logger.info("\tNo differences found!")
            else:
                # Get length of dfs to get fractional values
                num_new_cbs = len(new_df.index)
                num_diff_cbs = len(diff_df.index)
                # Write to terminal
                logger.info(
                    f"\t{num_diff_cbs}/{num_new_cbs} are different in the newly generated mesh"
                )
                logger.debug(
                    "\tDifferent cellboxes have the following id's in the "
                    f"new mesh: \n{diff_df['id'].to_list()}"
                )

        # Read in test output file and compare meshes in it
        old_json, new_json = self.extract_test_meshes(test_output)
        mesh_comparison = self.compare_meshes(old_json, new_json)

        print_summary(mesh_comparison, "bounds")
        print_summary(mesh_comparison, "values")
        print_summary(mesh_comparison, "attributes")
        print_summary(mesh_comparison, "neighbour_graph")

    def summarise_test_stats(self) -> None:
        """
        Summarise statistics about the tests and print to terminal
        Example: 10 / 12 tests passed for test_boundary.py
        """
        # Out of every test run
        all_tests = self.passes + self.fails + self.errors
        # Get list of unique files (i.e. unique test sets)
        diff_test_files = {ti.file for ti in all_tests}
        # Set up empty array to store status for calculating stats
        status_by_file: dict[str, list[str]] = {test: [] for test in diff_test_files}
        # Append status to each unique test set
        for test in all_tests:
            status_by_file[test.file] += [test.status]
        for test_file, statuses in status_by_file.items():
            num_passes = statuses.count("PASSED")
            num_tests = len(statuses)
            logger.info(f"{num_passes}/{num_tests} tests passed for {test_file}")


class TestInfo:
    def __init__(self, file: str, test: str, reference: str, status: str) -> None:
        self.file = file
        self.test = test
        self.reference = reference
        self.status = status

    def __str__(self) -> str:
        return f"{self.status} - {self.file} > {self.test} > {self.reference}"

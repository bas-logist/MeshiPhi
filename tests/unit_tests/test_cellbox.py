import unittest
import warnings
from meshiphi.mesh_generation.metadata import Metadata
from meshiphi.dataloaders.factory import DataLoaderFactory
from meshiphi.mesh_generation.cellbox import CellBox

from meshiphi.mesh_generation.boundary import Boundary


def create_cellbox(
    bounds, id=0, parent=None, params=None, splitting_conds=None, min_dp=5
):
    """
    Helper function that simplifies creation of test cases

    Args:
        bounds (Boundary): Boundary of cellbox
        id (int, optional): Cellbox ID to initialise. Defaults to 0.
        parent (CellBox, optional): Cellbox to link as a parent. Defaults to None.

    Returns:
        CellBox: Cellbox with completed attributes
    """
    dataloader = create_dataloader(bounds, params, min_dp=min_dp)
    metadata = create_metadata(bounds, dataloader, splitting_conds=splitting_conds)

    new_cellbox = CellBox(bounds, id)
    new_cellbox.data_source = [metadata]
    new_cellbox.parent = parent

    return new_cellbox


def create_dataloader(bounds, params=None, min_dp=5):
    if params is None:
        params = {
            "dataloader_name": "rectangle",
            "data_name": "dummy_data",
            "width": bounds.get_width() / 4,
            "height": bounds.get_height() / 4,
            "centre": (bounds.getcx(), bounds.getcy()),
            "nx": 15,
            "ny": 15,
            "aggregate_type": "MEAN",
            "value_fill_type": "parent",
        }
    dataloader = DataLoaderFactory().get_dataloader(
        params["dataloader_name"], bounds, params, min_dp=min_dp
    )
    return dataloader


def create_metadata(bounds, dataloader, splitting_conds=None):
    if splitting_conds is None:
        splitting_conds = [{"threshold": 0.5, "upper_bound": 0.75, "lower_bound": 0.25}]
    data_source = Metadata(
        dataloader,
        splitting_conditions=splitting_conds,
        value_fill_type="parent",
        data_subset=dataloader.trim_datapoints(bounds),
    )
    return data_source


def compare_cellbox_lists(s, t):
    t = list(t)  # make a mutable copy
    try:
        for elem in s:
            t.remove(elem)
    except ValueError:
        return False
    return not t


class TestCellBox(unittest.TestCase):
    def setUp(self):
        # Cellbox to modify on the fly
        self.dummy_cellbox = create_cellbox(Boundary([10, 20], [30, 40]))
        # Cellboxes to test splitting conditions
        arbitrary_bounds = Boundary([-10, 10], [-10, 10])

        het_splitting_conds = {"threshold": 0.5, "upper_bound": 1, "lower_bound": 0}
        hom_splitting_conds = {"threshold": 0.5, "upper_bound": 0.5, "lower_bound": 0.5}

        clr_splitting_conds = {"threshold": 1, "upper_bound": 1, "lower_bound": 1}

        self.het_cellbox = create_cellbox(
            arbitrary_bounds, splitting_conds=[het_splitting_conds]
        )
        self.hom_cellbox = create_cellbox(
            arbitrary_bounds, splitting_conds=[hom_splitting_conds]
        )
        self.clr_cellbox = create_cellbox(
            arbitrary_bounds, splitting_conds=[clr_splitting_conds]
        )
        self.min_cellbox = create_cellbox(
            arbitrary_bounds, splitting_conds=[het_splitting_conds], min_dp=99999999
        )

    def test_set_minimum_datapoints(self):
        self.assertRaises(ValueError, self.dummy_cellbox.set_minimum_datapoints, -1)

        self.dummy_cellbox.set_minimum_datapoints(5)
        self.assertEqual(self.dummy_cellbox.minimum_datapoints, 5)

    def test_get_minimum_datapoints(self):
        self.dummy_cellbox.minimum_datapoints = 10
        self.assertEqual(self.dummy_cellbox.get_minimum_datapoints(), 10)

    def test_set_data_source(self):
        arbitrary_bounds = Boundary([-50, -40], [-30, -20])
        arbitrary_params = {
            "dataloader_name": "gradient",
            "data_name": "dummy_data",
            "vertcal": True,
        }
        arbitrary_dataloader = create_dataloader(arbitrary_bounds, arbitrary_params)
        arbitrary_data_source = create_metadata(arbitrary_bounds, arbitrary_dataloader)

        self.dummy_cellbox.set_data_source([arbitrary_data_source])
        self.assertEqual(self.dummy_cellbox.data_source, [arbitrary_data_source])

    def test_get_data_source(self):
        arbitrary_bounds = Boundary([-40, -20], [-20, 0])
        arbitrary_params = {
            "dataloader_name": "gradient",
            "data_name": "dummy_data",
            "vertcal": False,
        }
        arbitrary_dataloader = create_dataloader(arbitrary_bounds, arbitrary_params)
        arbitrary_data_source = create_metadata(arbitrary_bounds, arbitrary_dataloader)

        self.dummy_cellbox.data_source = arbitrary_data_source
        self.assertEqual(self.dummy_cellbox.get_data_source(), arbitrary_data_source)

    def test_set_parent(self):
        arbitrary_cellbox = create_cellbox(Boundary([10, 30], [30, 50]))
        self.dummy_cellbox.set_parent(arbitrary_cellbox)
        self.assertEqual(self.dummy_cellbox.parent, arbitrary_cellbox)

    def test_get_parent(self):
        # Make sure to set bounds values different to test_set_parent() method
        # to ensure that the value being checked isn't leftover from a previous test
        arbitrary_cellbox = create_cellbox(Boundary([0, 20], [20, 40]))
        self.dummy_cellbox.parent = arbitrary_cellbox
        self.assertEqual(self.dummy_cellbox.get_parent(), arbitrary_cellbox)

    def test_set_split_depth(self):
        self.assertRaises(ValueError, self.dummy_cellbox.set_split_depth, -1)

        self.dummy_cellbox.set_split_depth(5)
        self.assertEqual(self.dummy_cellbox.split_depth, 5)

    def test_get_split_depth(self):
        # Make sure to set split_depth values different to test_set_split_depth() method
        # to ensure that the value being checked isn't leftover from a previous test
        self.dummy_cellbox.split_depth = 3
        self.assertEqual(self.dummy_cellbox.get_split_depth(), 3)

    def test_set_id(self):
        self.dummy_cellbox.set_id(123)
        self.assertEqual(self.dummy_cellbox.id, 123)

    def test_get_id(self):
        self.dummy_cellbox.id = 321
        self.assertEqual(self.dummy_cellbox.get_id(), 321)

    def test_set_bounds(self):
        arbitrary_bounds = Boundary([30, 50], [50, 70])
        self.dummy_cellbox.set_bounds(arbitrary_bounds)
        self.assertEqual(self.dummy_cellbox.bounds, arbitrary_bounds)

    def test_get_bounds(self):
        # Make sure to set bounds values different to test_set_bounds() method
        # to ensure that the value being checked isn't leftover from a previous test
        arbitrary_bounds = Boundary([20, 40], [40, 60])
        self.dummy_cellbox.bounds = arbitrary_bounds
        self.assertEqual(self.dummy_cellbox.get_bounds(), arbitrary_bounds)

    def test_should_split(self):
        self.assertTrue(self.het_cellbox.should_split(1))
        self.assertFalse(self.hom_cellbox.should_split(1))
        self.assertFalse(self.clr_cellbox.should_split(1))
        self.assertFalse(self.min_cellbox.should_split(1))

    def test_should_split_breadth_first(self):
        self.assertTrue(self.het_cellbox.should_split_breadth_first())
        self.assertFalse(self.hom_cellbox.should_split_breadth_first())
        self.assertFalse(self.clr_cellbox.should_split_breadth_first())
        self.assertFalse(self.min_cellbox.should_split_breadth_first())

    def test_split(self):
        parent_cellbox = create_cellbox(
            Boundary([-10, 10], [-10, 10]), id=0, parent=None
        )
        children_cellboxes = parent_cellbox.create_splitted_cell_boxes(0)

        for child in children_cellboxes:
            parent_metadata = parent_cellbox.get_data_source()[0]
            child_data_subset = parent_metadata.data_loader.trim_datapoints(
                child.bounds, data=parent_metadata.data_subset
            )
            child_metadata = Metadata(
                parent_metadata.get_data_loader(),
                parent_metadata.get_splitting_conditions(),
                parent_metadata.get_value_fill_type(),
                child_data_subset,
            )
            child.set_data_source([child_metadata])
            child.set_parent(parent_cellbox)
            child.set_split_depth(parent_cellbox.get_split_depth() + 1)

        cb_pairs = zip(parent_cellbox.split(0), children_cellboxes)
        for cb_pair in cb_pairs:
            self.assertEqual(cb_pair[0].bounds, cb_pair[1].bounds)
            self.assertEqual(cb_pair[0].parent, cb_pair[1].parent)
            self.assertEqual(
                cb_pair[0].minimum_datapoints, cb_pair[1].minimum_datapoints
            )
            self.assertEqual(cb_pair[0].split_depth, cb_pair[1].split_depth)
            self.assertEqual(cb_pair[0].data_source, cb_pair[1].data_source)
            self.assertEqual(cb_pair[0].id, cb_pair[1].id)

    def test_create_splitted_cell_boxes(self):
        parent_cellbox = create_cellbox(
            Boundary([-10, 10], [-10, 10]), id=1, parent=None
        )
        nw_child = CellBox(Boundary([0, 10], [-10, 0]), "0")
        ne_child = CellBox(Boundary([0, 10], [0, 10]), "1")
        sw_child = CellBox(Boundary([-10, 0], [-10, 0]), "2")
        se_child = CellBox(Boundary([-10, 0], [0, 10]), "3")

        children_cellboxes = [nw_child, ne_child, sw_child, se_child]

        split_cbs = parent_cellbox.create_splitted_cell_boxes(0)

        cb_pairs = zip(split_cbs, children_cellboxes)
        for cb_pair in cb_pairs:
            self.assertEqual(cb_pair[0].bounds, cb_pair[1].bounds)
            self.assertEqual(cb_pair[0].parent, cb_pair[1].parent)
            self.assertEqual(
                cb_pair[0].minimum_datapoints, cb_pair[1].minimum_datapoints
            )
            self.assertEqual(cb_pair[0].split_depth, cb_pair[1].split_depth)
            self.assertEqual(cb_pair[0].data_source, cb_pair[1].data_source)
            self.assertEqual(cb_pair[0].id, cb_pair[1].id)

    def test_aggregate(self):
        parent_cellbox = create_cellbox(
            Boundary([-10, 10], [-10, 10]), id=1, parent=None
        )
        parent_agg_cb = parent_cellbox.aggregate()
        self.assertAlmostEqual(parent_agg_cb.agg_data["dummy_data"], 0.25, 3)

        # Create a child, set values to NaN, and test that it inherits parent value
        # intead of aggregating to NaN
        child_cellbox = parent_cellbox.split(1)[0]
        child_data = (
            child_cellbox.get_data_source()[0].get_data_loader().data.dummy_data
        )
        nan_data = child_data.where(child_data == float("nan"), other=float("nan"))
        child_cellbox.get_data_source()[0].get_data_loader().data["dummy_data"] = (
            nan_data
        )
        child_agg_cb = child_cellbox.aggregate()

        self.assertAlmostEqual(child_agg_cb.agg_data["dummy_data"], 0.245, 3)

    def test_check_vector_data(self):
        vector_bounds = Boundary([-10, 10], [-10, 10])
        vector_params = {
            "dataloader_name": "vector_rectangle",
            "data_name": "dummy_data_u,dummy_data_v",
            "width": vector_bounds.get_width(),
            "height": vector_bounds.get_height() / 2,
            "centre": (vector_bounds.getcx(), vector_bounds.getcy()),
            "nx": 15,
            "ny": 15,
            "aggregate_type": "MEAN",
            "multiplier_u": 3,
            "multiplier_v": 1,
        }

        vector_parent_cb = create_cellbox(
            vector_bounds, params=vector_params, id=1, parent=None
        )
        vector_child_cb = vector_parent_cb.split(1)[0]

        arbitrary_cb = create_cellbox(
            vector_bounds, params=vector_params, id=1, parent=vector_parent_cb
        )

        parent_agg_val = {"dummy_data_u": float("3"), "dummy_data_v": float("1")}
        child_agg_val = {"dummy_data_u": float("nan"), "dummy_data_v": float("nan")}

        self.assertEqual(
            vector_parent_cb.check_vector_data(
                vector_parent_cb.data_source[0],
                vector_parent_cb.data_source[0].get_data_loader(),
                dict(parent_agg_val),
                vector_params["data_name"],
            ),
            parent_agg_val,
        )

        self.assertEqual(
            vector_child_cb.check_vector_data(
                vector_child_cb.data_source[0],
                vector_child_cb.data_source[0].get_data_loader(),
                dict(child_agg_val),
                vector_params["data_name"],
            ),
            parent_agg_val,
        )

        self.assertRaises(
            ValueError,
            arbitrary_cb.check_vector_data,
            arbitrary_cb.data_source[0],
            vector_child_cb.data_source[0].get_data_loader(),
            dict(child_agg_val),
            vector_params["data_name"],
        )

    def test_deallocate_cellbox(self):
        ### Test code commented in case method is fixed rather than deprecated
        # parent_cellbox   = create_cellbox(Boundary([-10, 10], [-10, 10]),
        #                                   id=1,
        #                                   parent=None)
        # child_cellbox = parent_cellbox.split(1)[0]
        # try:
        #     child_cellbox.deallocate_cellbox()
        #     # Try to force a NameError by calling any CellBox method
        #     x = child_cellbox.get_parent()
        # except NameError:
        #     pass
        # else:
        #     self.fail(f'Cellbox still exists after running deallocate_cellbox()')

        warnings.warn("Method doesn't work as intended, avoiding tests for now")

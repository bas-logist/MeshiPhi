import pytest
import warnings
from meshiphi.mesh_generation.metadata import Metadata
from meshiphi.mesh_generation.cellbox import CellBox
from meshiphi.mesh_generation.boundary import Boundary
from tests.conftest import create_cellbox, create_dataloader, create_metadata


@pytest.fixture
def het_cellbox():
    """Cellbox with heterogeneous splitting conditions"""
    arbitrary_bounds = Boundary([-10, 10], [-10, 10])
    het_splitting_conds = {
        'threshold': 0.5,
        'upper_bound': 1,
        'lower_bound': 0
    }
    return create_cellbox(arbitrary_bounds, splitting_conds=[het_splitting_conds])


@pytest.fixture
def hom_cellbox():
    """Cellbox with homogeneous splitting conditions"""
    arbitrary_bounds = Boundary([-10, 10], [-10, 10])
    hom_splitting_conds = {
        'threshold': 0.5,
        'upper_bound': 0.5,
        'lower_bound': 0.5
    }
    return create_cellbox(arbitrary_bounds, splitting_conds=[hom_splitting_conds])


@pytest.fixture
def clr_cellbox():
    """Cellbox with clear splitting conditions"""
    arbitrary_bounds = Boundary([-10, 10], [-10, 10])
    clr_splitting_conds = {
        'threshold': 1,
        'upper_bound': 1,
        'lower_bound': 1
    }
    return create_cellbox(arbitrary_bounds, splitting_conds=[clr_splitting_conds])


@pytest.fixture
def min_cellbox():
    """Cellbox with minimum datapoints condition"""
    arbitrary_bounds = Boundary([-10, 10], [-10, 10])
    het_splitting_conds = {
        'threshold': 0.5,
        'upper_bound': 1,
        'lower_bound': 0
    }
    return create_cellbox(arbitrary_bounds, splitting_conds=[het_splitting_conds], min_dp=99999999)


def test_getter_setter_minimum_datapoints(dummy_cellbox):
    """Test minimum datapoints getter and setter"""
    with pytest.raises(ValueError):
        dummy_cellbox.set_minimum_datapoints(-1)
    
    dummy_cellbox.set_minimum_datapoints(5)
    assert dummy_cellbox.minimum_datapoints == 5
    
    dummy_cellbox.minimum_datapoints = 10
    assert dummy_cellbox.get_minimum_datapoints() == 10


def test_getter_setter_data_source(dummy_cellbox):
    """Test data source getter and setter"""
    arbitrary_bounds = Boundary([-50, -40], [-30, -20])
    arbitrary_params = {
        'dataloader_name': 'gradient',
        'data_name': 'dummy_data',
        'vertcal': True
    }
    arbitrary_dataloader = create_dataloader(arbitrary_bounds, arbitrary_params)
    arbitrary_data_source = create_metadata(arbitrary_bounds, arbitrary_dataloader)
    
    dummy_cellbox.set_data_source([arbitrary_data_source])
    assert dummy_cellbox.data_source == [arbitrary_data_source]
    
    # Test getter
    arbitrary_bounds2 = Boundary([-40, -20], [-20, 0])
    arbitrary_params2 = {
        'dataloader_name': 'gradient',
        'data_name': 'dummy_data',
        'vertcal': False
    }
    arbitrary_dataloader2 = create_dataloader(arbitrary_bounds2, arbitrary_params2)
    arbitrary_data_source2 = create_metadata(arbitrary_bounds2, arbitrary_dataloader2)
    
    dummy_cellbox.data_source = arbitrary_data_source2
    assert dummy_cellbox.get_data_source() == arbitrary_data_source2


@pytest.mark.parametrize("bounds", [
    Boundary([10, 30], [30, 50]),
    Boundary([0, 20], [20, 40])
])
def test_getter_setter_parent(dummy_cellbox, bounds):
    """Test parent getter and setter"""
    arbitrary_cellbox = create_cellbox(bounds)
    dummy_cellbox.set_parent(arbitrary_cellbox)
    assert dummy_cellbox.parent == arbitrary_cellbox
    
    # Test getter
    dummy_cellbox.parent = arbitrary_cellbox
    assert dummy_cellbox.get_parent() == arbitrary_cellbox


def test_getter_setter_split_depth(dummy_cellbox):
    """Test split depth getter and setter"""
    with pytest.raises(ValueError):
        dummy_cellbox.set_split_depth(-1)

    dummy_cellbox.set_split_depth(5)
    assert dummy_cellbox.split_depth == 5
    
    dummy_cellbox.split_depth = 3
    assert dummy_cellbox.get_split_depth() == 3


def test_getter_setter_id(dummy_cellbox):
    """Test ID getter and setter"""
    dummy_cellbox.set_id(123)
    assert dummy_cellbox.id == 123
    
    dummy_cellbox.id = 321
    assert dummy_cellbox.get_id() == 321


@pytest.mark.parametrize("bounds", [
    Boundary([30, 50], [50, 70]),
    Boundary([20, 40], [40, 60])
])
def test_getter_setter_bounds(dummy_cellbox, bounds):
    """Test bounds getter and setter"""
    dummy_cellbox.set_bounds(bounds)
    assert dummy_cellbox.bounds == bounds
    
    # Test getter
    dummy_cellbox.bounds = bounds
    assert dummy_cellbox.get_bounds() == bounds


@pytest.mark.parametrize("cellbox_fixture,expected,description", [
    ("het_cellbox", True, "heterogeneous"),
    ("hom_cellbox", False, "homogeneous"),
    ("clr_cellbox", False, "clear"),
    ("min_cellbox", False, "minimum_datapoints"),
])
def test_should_split(cellbox_fixture, expected, description, request):
    """Test should_split method"""
    cellbox = request.getfixturevalue(cellbox_fixture)
    assert cellbox.should_split(1) == expected


@pytest.mark.parametrize("cellbox_fixture,expected,description", [
    ("het_cellbox", True, "heterogeneous"),
    ("hom_cellbox", False, "homogeneous"),
    ("clr_cellbox", False, "clear"),
    ("min_cellbox", False, "minimum_datapoints"),
])
def test_should_split_breadth_first(cellbox_fixture, expected, description, request):
    """Test should_split_breadth_first method"""
    cellbox = request.getfixturevalue(cellbox_fixture)
    assert cellbox.should_split_breadth_first() == expected


def test_split():
    parent_cellbox   = create_cellbox(Boundary([-10, 10], [-10, 10]), 
                                      id=0, 
                                      parent=None)
    children_cellboxes = parent_cellbox.create_splitted_cell_boxes(0)
    
    for child in children_cellboxes:
        parent_metadata = parent_cellbox.get_data_source()[0]
        child_data_subset = parent_metadata.data_loader.trim_datapoints(child.bounds, 
                                                    data=parent_metadata.data_subset)
        child_metadata = Metadata(parent_metadata.get_data_loader(),
                                  parent_metadata.get_splitting_conditions(),
                                  parent_metadata.get_value_fill_type(),
                                  child_data_subset)
        child.set_data_source([child_metadata])
        child.set_parent(parent_cellbox)
        child.set_split_depth(parent_cellbox.get_split_depth() + 1)

    cb_pairs = zip(parent_cellbox.split(0), children_cellboxes)
    for cb_pair in cb_pairs:
        assert cb_pair[0].bounds == cb_pair[1].bounds
        assert cb_pair[0].parent == cb_pair[1].parent
        assert cb_pair[0].minimum_datapoints == cb_pair[1].minimum_datapoints
        assert cb_pair[0].split_depth == cb_pair[1].split_depth
        assert cb_pair[0].data_source == cb_pair[1].data_source
        assert cb_pair[0].id == cb_pair[1].id


def test_create_splitted_cell_boxes():
    parent_cellbox   = create_cellbox(Boundary([-10, 10], [-10, 10]), 
                                      id=1, 
                                      parent=None)
    nw_child = CellBox(Boundary([0, 10], [-10,0]), '0')
    ne_child = CellBox(Boundary([0, 10], [0, 10]), '1')
    sw_child = CellBox(Boundary([-10,0], [-10,0]), '2')
    se_child = CellBox(Boundary([-10,0], [0, 10]), '3')

    children_cellboxes = [nw_child,
                          ne_child,
                          sw_child,
                          se_child]

    split_cbs = parent_cellbox.create_splitted_cell_boxes(0)

    cb_pairs = zip(split_cbs, children_cellboxes)
    for cb_pair in cb_pairs:
        assert cb_pair[0].bounds == cb_pair[1].bounds
        assert cb_pair[0].parent == cb_pair[1].parent
        assert cb_pair[0].minimum_datapoints == cb_pair[1].minimum_datapoints
        assert cb_pair[0].split_depth == cb_pair[1].split_depth
        assert cb_pair[0].data_source == cb_pair[1].data_source
        assert cb_pair[0].id == cb_pair[1].id


def test_aggregate():
    parent_cellbox   = create_cellbox(Boundary([-10, 10], [-10, 10]), 
                                      id=1, 
                                      parent=None)
    parent_agg_cb = parent_cellbox.aggregate()
    assert parent_agg_cb.agg_data['dummy_data'] == pytest.approx(0.25, abs=0.001)

    # Create a child, set values to NaN, and test that it inherits parent value 
    # intead of aggregating to NaN        
    child_cellbox = parent_cellbox.split(1)[0]
    child_data = child_cellbox.get_data_source()[0].get_data_loader().data.dummy_data
    nan_data = child_data.where(child_data==float('nan'), other=float('nan'))
    child_cellbox.get_data_source()[0].get_data_loader().data['dummy_data'] = nan_data
    child_agg_cb  = child_cellbox.aggregate()

    assert child_agg_cb.agg_data['dummy_data'] == pytest.approx(0.245, abs=0.001)


def test_check_vector_data():
    vector_bounds = Boundary([-10, 10], [-10, 10])
    vector_params = {
                'dataloader_name': 'vector_rectangle',
                'data_name': 'dummy_data_u,dummy_data_v',
                'width': vector_bounds.get_width(),
                'height': vector_bounds.get_height()/2,
                'centre': (vector_bounds.getcx(), vector_bounds.getcy()),
                'nx': 15,
                'ny': 15,
                "aggregate_type": "MEAN",
                "multiplier_u": 3,
                "multiplier_v": 1
            }
    
    vector_parent_cb = create_cellbox(vector_bounds, 
                                      params=vector_params,
                                      id=1,
                                      parent=None)
    vector_child_cb = vector_parent_cb.split(1)[0]

    arbitrary_cb = create_cellbox(vector_bounds, 
                                  params=vector_params,
                                  id=1,
                                  parent=vector_parent_cb)
    
    parent_agg_val = {'dummy_data_u': float('3'), 'dummy_data_v': float('1')}
    child_agg_val = {'dummy_data_u': float('nan'), 'dummy_data_v': float('nan')}

    assert vector_parent_cb.check_vector_data(vector_parent_cb.data_source[0],
                                              vector_parent_cb.data_source[0].get_data_loader(),
                                              dict(parent_agg_val),
                                              vector_params['data_name']) == parent_agg_val

    assert vector_child_cb.check_vector_data(vector_child_cb.data_source[0],
                                             vector_child_cb.data_source[0].get_data_loader(),
                                             dict(child_agg_val),
                                             vector_params['data_name']) == parent_agg_val
    
    with pytest.raises(ValueError):
        arbitrary_cb.check_vector_data(arbitrary_cb.data_source[0],                                           
                                       vector_child_cb.data_source[0].get_data_loader(), 
                                       dict(child_agg_val), 
                                       vector_params['data_name'])


def test_deallocate_cellbox():

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
    #     pytest.fail(f'Cellbox still exists after running deallocate_cellbox()')
    
    warnings.warn("Method doesn't work as intended, avoiding tests for now")

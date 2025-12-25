"""
MeshValidator class tests.
"""
import pytest
from meshiphi.mesh_validation.sampler import Sampler
from meshiphi.mesh_validation.mesh_validator import MeshValidator
from tests.conftest import REGRESSION_TESTS_DIR


@pytest.fixture
def mesh_validator():
    """Create a mesh validator instance for testing."""
    mesh_file = REGRESSION_TESTS_DIR / "example_meshes/abstract_env_meshes/hgrad.json"
    return MeshValidator(str(mesh_file))


def test_sampler():
    """Test sampler generates valid samples within ranges"""
    sampler = Sampler(2, 20)
    ranges = [[10, 20], [100, 200]]
    mapped_samples = sampler.generate_samples(ranges)
    
    for sample in mapped_samples:
        assert sample[0] <= ranges[0][1]
        assert sample[0] >= ranges[0][0]
        assert sample[1] <= ranges[1][1]
        assert sample[1] >= ranges[1][0]


def test_validate_mesh(mesh_validator):
    """Test mesh validation distance"""
    distance = mesh_validator.validate_mesh()
    print(f"Validation distance: {distance}")
    assert distance < 0.1

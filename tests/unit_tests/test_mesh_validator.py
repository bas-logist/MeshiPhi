import unittest
from pathlib import Path
from meshiphi.mesh_validation.sampler import Sampler
from meshiphi.mesh_validation.mesh_validator import MeshValidator


class TestMeshValidator(unittest.TestCase):
    """Tests for MeshValidator class"""

    def setUp(self):
        """Set up test mesh validator"""
        test_dir = Path(__file__).parent.parent
        mesh_file = test_dir / "regression_tests/example_meshes/abstract_env_meshes/hgrad.json"
        self.mesh_validator = MeshValidator(str(mesh_file))

    def test_sampler(self):
        """Test sampler generates valid samples within ranges"""
        sampler = Sampler(2, 20)
        ranges = [[10, 20], [100, 200]]
        mapped_samples = sampler.generate_samples(ranges)
        
        for sample in mapped_samples:
            with self.subTest(sample=sample):
                self.assertLessEqual(sample[0], ranges[0][1])
                self.assertGreaterEqual(sample[0], ranges[0][0])
                self.assertLessEqual(sample[1], ranges[1][1])
                self.assertGreaterEqual(sample[1], ranges[1][0])

    def test_validate_mesh(self):
        """Test mesh validation distance"""
        distance = self.mesh_validator.validate_mesh()
        print(f"Validation distance: {distance}")
        self.assertLess(distance, 0.1)


if __name__ == '__main__':
    unittest.main()



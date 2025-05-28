__version__ = "2.1.16"
__description__ = "MeshiPhi: Earth's digital twin mapped on a non-uniform mesh"
__license__ = "MIT"
__author__ = "Autonomous Marine Operations Planning (AMOP) Team, AI Lab, British Antarctic Survey"
__email__ = "amop@bas.ac.uk"
__copyright__ = "2021-, BAS AI Lab"

# Wrapped in try-except so that setup.py can import meshiphi without crashing due to dependency errors
try:
    from meshiphi.mesh_generation.mesh_builder import MeshBuilder as MeshBuilder
    from meshiphi.dataloaders.factory import DataLoaderFactory as DataLoaderFactory
    from meshiphi.mesh_generation.boundary import Boundary as Boundary

except ModuleNotFoundError as err:
    print(f'{err}\n Is meshiphi installed correctly?')

# Map modified files to relevant tests
REGRESSION_TESTS_BY_FILE = {
    'mesh_builder.py':      ['test_mesh.py'],
    'mesh.py':              ['test_mesh.py'],
    'neighbour_graph.py':   ['test_mesh.py'],
    'metadata.py':          ['test_mesh.py'],
    'aggregated_cellbox.py':['test_mesh.py'],
    'boundary.py':          ['test_mesh.py'],
    'cellbox.py':           ['test_mesh.py'],
    'direction.py':         ['test_mesh.py'],
    'environment_mesh.py':  ['test_mesh.py']
}

UNIT_TESTS_BY_FILE = {
    'mesh_builder.py':      ['test_mesh_builder.py'],
    'mesh.py':              [],
    'neighbour_graph.py':   ['test_neighbour_graph.py'],
    'metadata.py':          [],
    'aggregated_cellbox.py':['test_aggregated_cellbox.py'],
    'boundary.py':          ['test_boundary.py'],
    'cellbox.py':           ['test_cellbox.py'],
    'direction.py':         [],
    'environment_mesh.py':  ['test_env_mesh.py'],
    'cli.py':               ['test_cli.py']
}

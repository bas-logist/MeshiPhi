from shapely.geometry import Polygon, Point
from meshiphi.mesh_generation.boundary import Boundary
import shapely.wkt


class AggregatedCellBox:
    """
    a class represnts an aggrgated information within a geo-spatial/temporal boundary. 


    Attributes:
      

    Note:
        All geospatial boundaries of a CellBox are given in a 'EPSG:4326' projection
    """
    @classmethod
    def from_json(cls, cellbox_json):
        """

            Args:
                cellbox_json(Json): json object that encapsulates boundary, agg_data and id of the CellBox
        """
        cellbox_id = cellbox_json ['id']
        def load_bounds(cellbox_json):
            shape = shapely.wkt.loads (cellbox_json ["geometry"])
            # Take case where crossing antimeridian
            if shape.geom_type == 'MultiPolygon':
                shapes = list(shape.geoms)
                assert (len(shapes) == 2), 'Too many polygons in MultiPolygon boundary!'
                bounds_a = shapes[0].bounds
                bounds_b = shapes[1].bounds

                # Bottom left should be origin from which all polygons are defined
                # They should have the same lat range
                lat_range = [bounds_a[1] , bounds_a[3]]
                # Left most boundary and right most boundary are from two different polygons
                # Right boundary of bounds_a should be 180, 
                # and left boundary of bounds_b should be -180
                long_range = [bounds_a [0], bounds_b [2]]

            # Otherwise it's just a normal cellbox
            elif shape.geom_type == 'Polygon':
                bounds = shape.bounds
                lat_range = [bounds[1] , bounds[3]]
                long_range = [bounds [0], bounds [2]]
            # Or something is wrong with the mesh
            else:
                raise TypeError(f'Expected Polygon or MultiPolygon, instead got {shape.geom_type}')
            
            return Boundary (lat_range , long_range)

        def load_agg_data (cellbox_json):
            dict_obj = {}
            for key in cellbox_json:
                if key  not in [  "geometry","cx", "cy", "dcx", "dcy", "id"]:
                    dict_obj[key] = cellbox_json[key]

            return dict_obj
        
        boundary = load_bounds( cellbox_json)
        agg_data = load_agg_data( cellbox_json)
        obj = AggregatedCellBox(boundary , agg_data ,cellbox_id )
        return obj




    def __init__(self, boundary , agg_data , id):
        """

            Args:
                boundary(Boundary): encapsulates latitude, longtitude and time range of the CellBox
                agg_data (dict): a dictionary that contains data_names and agg values
                id (string): a string represents cellbox id
        """
        # Box information relative to bottom left
        self.boundary = boundary
        self.agg_data = agg_data
        self.id = id
        
######## setters and getters ########
    def set_bounds(self, boundary):
        """
            set the boundary of the CellBox
        """
        self.boundary = boundary

    def set_agg_data (self, agg_data):
        """
        sets the agg_data
        """
        self.agg_data = agg_data
    
    def set_id (self, id):
        """
        sets the cellbox id
        """
        self.id = id
    
    def get_bounds(self):
        """
            get the boundary of the CellBox
        """
        return self.boundary 

    def get_agg_data (self):
        """
        returns the agg_data
        """
        return self.agg_data

    def get_id (self):
        """
        returns the id
        """
        return self.id


    def to_json(self):
        '''
            convert cellbox to JSON

            The returned object is of the form -

                {\n
                    "geometry" (String): POLYGON(...),\n
                    "cx" (float): ...,\n
                    "cy" (float): ...,\n
                    "dcx" (float): ...,\n
                    "dcy" (float): ..., \n
                    \n
                    "agg_value_1" (float): ...,\n
                    ...,\n
                    "agg_value_n" (float): ...\n
                }\n
            Returns:
                cell_json (dict): A JSON parsable dictionary representation of this AggregatedCellBox
        '''
        cell_json = {
            "geometry": str(self.get_bounds().to_poly_string()),
            'cx': float(self.get_bounds().getcx()),
            'cy': float(self.get_bounds().getcy()),
            'dcx': float(self.get_bounds().getdcx()),
            'dcy': float(self.get_bounds().getdcy()),
           
        }

        cell_json.update(self.get_agg_data())
        cell_json['id'] = self.get_id()
        
        return cell_json



    def contains_point(self, lat, long):
        """
            Returns true if a given lat/long coordinate is contained within this cellbox.

            Args:
                lat (float): latitude of a given point
                long (float): longitude of a given point

            Returns:
                contains_points (bool): True if this CellBox contains a point given by
                    parameters (lat, long)
        """
        shapely_boundary = self.boundary.to_polygon()
        point = Point(long, lat)
        point_within_bounds = shapely_boundary.contains(point)
        point_on_bounds     = shapely_boundary.boundary.contains(point)
        point_on_north_edge = shapely_boundary.bounds[2] == point.x
        point_on_east_edge  = shapely_boundary.bounds[3] == point.y
        
        return (point_within_bounds or \
                (point_on_bounds and (point_on_north_edge or point_on_east_edge)))
    
    def __eq__(self, other):

        if isinstance(other, AggregatedCellBox):

            eq_checks = []

            eq_checks += [self.get_id() == other.get_id()]
            eq_checks += [self.get_agg_data() == other.get_agg_data()]
            eq_checks += [self.get_bounds() == other.get_bounds()]

            if all(eq_checks):
                return True
            
        return False
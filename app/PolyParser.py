import geoplot.crs as gcrs
import geopandas as gpd

import geoplot as gplt
import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.geometry import Point

class PolyParser:
    def __init__(self):
        pass

    @staticmethod
    def poly_to_polygon(file_name):
        with open(file_name) as f:
            content = f.readlines()
        return PolyParser.parse_poly(content)

    def parse_poly(lines):
        """ Parse an Osmosis polygon filter file.
            Accept a sequence of lines from a polygon file, return a shapely.geometry.MultiPolygon object.
            http://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Format
        """
        ring = None
        in_ring = False
        coords = []

        for (index, line) in enumerate(lines):
            if index == 0:
                # first line is junk.
                continue

            elif index == 1:
                # second line is the first polygon ring.
                coords.append([[], []])
                ring = coords[-1][0]
                in_ring = True

            elif in_ring and line.strip() == 'END':
                # we are at the end of a ring, perhaps with more to come.
                in_ring = False

            elif in_ring:
                #ADDED "list()" for python 3 
                # we are in a ring and picking up new coordinates.
                ring.append(list(map(float, line.split())))

            elif not in_ring and line.strip() == 'END':
                # we are at the end of the whole polygon.
                break

            elif not in_ring and line.startswith('!'):
                # we are at the start of a polygon part hole.
                coords[-1][1].append([])
                ring = coords[-1][1][-1]
                in_ring = True

            elif not in_ring:
                # we are at the start of a polygon part.
                coords.append([[], []])
                ring = coords[-1][0]
                in_ring = True
        fig, ax = plt.subplots(figsize=(12, 10))
        world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        pp=gplt.polyplot(world,ax=ax,zorder=1)
        
        poly =MultiPolygon(coords)
        shape=gpd.GeoDataFrame({'geometry':poly},crs='epsg:3857')
        pp2=gplt.polyplot(shape,zorder=0,ax=ax)


        # plt.plot(*poly.exterior.xy)
        plt.show()

        return MultiPolygon(coords)

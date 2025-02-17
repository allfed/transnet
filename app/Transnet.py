import json
import logging
import sys
import urllib
from datetime import datetime
from optparse import OptionParser
from os import makedirs, remove
from os import walk
from os.path import dirname, getsize
from os.path import exists
from os.path import join
from subprocess import call

import psycopg2
import pyproj
from shapely import wkb, wkt, geometry
from shapely.geometry import MultiPoint, LinearRing

from CSVWriter import CSVWriter
from CimWriter import CimWriter
from Circuit import Circuit
from InferenceValidator import InferenceValidator
from Line import Line
from LoadEstimator import LoadEstimator
from Plotter import Plotter
from PolyParser import PolyParser
from Station import Station

root = logging.getLogger()
root.setLevel(logging.DEBUG)
# importing the sys module
import sys
  
# the setrecursionlimit function is
# used to modify the default recursion
# limit set by python. Using this, 
# we can increase the recursion limit
# to satisfy our needs
  
sys.setrecursionlimit(10**6)

class Transnet:
    def __init__(self, _database, _user, _host, _port, _password, _ssid, _poly, _bpoly, _verbose, _validate,
                 _topology, _voltage_levels, _load_estimation, _destdir, _continent, _whole_planet, _find_missing_data,
                 _close_nodes, _overpass):
        self.length_all = 0
        self.all_lines = dict()
        self.all_stations = dict()
        self.all_power_planet = dict()

        self.db_name = _database
        self.ssid = _ssid
        self.poly = _poly
        self.bpoly = _bpoly
        self.verbose = _verbose
        self.validate = _validate
        self.topology = _topology
        self.voltage_levels = _voltage_levels
        self.load_estimation = _load_estimation
        self.destdir = _destdir
        print(self.destdir)
        self.chose_continent = _continent
        self.whole_planet = _whole_planet
        self.find_missing_data = _find_missing_data
        self.close_nodes = _close_nodes
        self.overpass = _overpass

        self.connection = {'database': _database, 'user': _user, 'host': _host, 'port': _port}
        print(self.connection)
        print('pass')
        print(_password)
        print('db')
        print(_database)
        print('host')
        print(_host)
        print('port')
        print(_port)
        print('user')
        print(_user)
        #this would be "psql -p 5432 -h 127.0.0.1 -d austria -U postgres -W" on the command line, for me
        self.conn = psycopg2.connect(password=_password, **self.connection)
        self.cur = self.conn.cursor()

        print('self.close_nodes')
        print(self.close_nodes)

        self.covered_nodes = None
        self.geod = pyproj.Geod(ellps='WGS84')

    # noinspection PyMethodMayBeStatic
    def prepare_poly_country(self, continent_name, country):
        if not exists('../data/{0}/{1}/'.format(continent_name, country)):
            makedirs('../data/{0}/{1}/'.format(continent_name, country))
        root.info('Downloading poly for {0}'.format(country))
        if continent_name == 'usa':
            download_string = 'http://download.geofabrik.de/north-america/us/{0}.poly'.format(country)
            root.info(download_string)
        elif continent_name == 'germany':
            download_string = 'http://download.geofabrik.de/europe/germany/{0}.poly'.format(country)
            root.info(download_string)
        else:
            download_string = 'http://download.geofabrik.de/{0}/{1}.poly'.format(continent_name, country)
        urllib.URLopener().retrieve(download_string, '../data/{0}/{1}/pfile.poly'.format(continent_name, country))
        


    # noinspection PyMethodMayBeStatic
    def prepare_poly_continent(self, continent_name):
        if not exists('../data/planet/{0}/'.format(continent_name)):
            makedirs('../data/planet/{0}/'.format(continent_name))
        root.info('Downloading poly for {0}'.format(continent_name))
        if continent_name == 'usa':
            download_string = 'http://svn.openstreetmap.org/applications/utils/' \
                              'osm-extract/polygons/united_states_inc_ak_and_hi.poly'
        elif continent_name == 'germany':
            download_string = 'http://download.geofabrik.de/europe/germany.poly'
        else:
            download_string = 'http://download.geofabrik.de/{0}.poly'.format(continent_name)
        urllib.URLopener().retrieve(download_string, '../data/planet/{0}/pfile.poly'.format(continent_name))

    def reset_params(self):
        self.covered_nodes = None

    def create_relations(self, stations, lines, _ssid, voltage):
        # root.info('\nStart inference for Substation %s', str(ssid))
        relations = []
        # print('stations[_ssid]')
        # print(stations[_ssid])
        inferred_relations=self.infer_relations(stations, lines, stations[_ssid])
        # print('inferred_relations')
        # print(inferred_relations)
        # print('inferred_relations')
        # print(inferred_relations)
        relations.extend(inferred_relations)

        circuits = []
        for relation in relations:
            # at least two end points + one line
            if self.num_subs_in_relation(relation) == 2 and len(relation) >= 3:
                first_line = relation[1]
                station1 = relation[0]
                station2 = relation[-1]
                station1.add_connected_station(station2.id, voltage)
                station2.add_connected_station(station1.id, voltage)
                # print('creating from relation')
                circuit = Circuit(relation, voltage, first_line.name, first_line.ref)
                circuits.append(circuit)

        return circuits

    # inferences circuits around a given station
    # station - represents the station to infer circuits for
    # stations - dict of all possibly connected stations
    # lines - list of all lines that could connect stations
    def infer_relations(self, stations, lines, station):
        # find lines that cross the station's area - note that
        #  the end point of the line has to be within the substation for valid crossing
        # self.close_nodes=True
        relations = []
        for line in lines.values():
            # if(station.serialize()['name']=='Viljandi alajaam'):
            #     print('station 3')
            #     quit()
            node_to_continue_id = None
            # here it checks to find the intersecting lines and station, if no intersecting found then looks for line
            # nodes with distance less than 50 meters
            # print('station')
            # print(station)
            # print('line')
            # print(line)
            # print('line.end_point_dict[line.first_node()], [station]')
            # print(line.end_point_dict[line.first_node()], [station])
            # print(station.serialize()['name'])
            # if(station.serialize()['id']):
            # if(station.serialize()['id']==100009331):

            #     name=line.serialize()['name']
            #     print(name)
            #     quit()
            #     if(name):
            #         if(name.find('National Grid Taunton-Alverdiscott')>-1):
            #             # print(name)
            #             print('station considered')
            #             print(station.serialize()['name'])

            #             print(self.node_intersect_with_any_station(line.end_point_dict[line.first_node()], [station]))
            #             print(self.node_intersect_with_any_station(line.end_point_dict[line.first_node()], [station]))
            #             print(self.node_within_distance_any_station(line.end_point_dict[line.first_node()], [station]))
            #             print(self.node_within_distance_any_station(line.end_point_dict[line.last_node()], [station]))
            #             print(self.close_nodes)
                        # quit()

            # printstuff=False
            # if(line.serialize()['name']=='Balti — Tartu 330 kV'):
            #     # print('line1')
            #     if(station.serialize()['name']=='Balti EJ alajaam'):
            #         print('station 1 and line 1')
            #         printstuff=True

            #     if(station.serialize()['name']=='Tartu alajaam'):
            #         print('station 0 and line 1')
            #         printstuff=True


            # if(line.serialize()['name']=='Tartu — Sindi 330 kV & Puhja JP — Viljandi 110 kV'):
            #     # print('line2')
            #     if(station.serialize()['name']=='Kilingi-Nõmme 330 kV alajaam'):
            #         print('station 2 and line 2')
            #         printstuff=True

            #     if(station.serialize()['name']=='Tartu alajaam'):
            #         print('station 0 and line 2')
            #         printstuff=True

            int2=False
            int3=False
            int4=False
            int1=self.node_intersect_with_any_station(line.end_point_dict[line.first_node()], [station])
            if(not int1):
                int2=self.node_intersect_with_any_station(line.end_point_dict[line.last_node()], [station])
            int3=self.node_within_distance_any_station(line.end_point_dict[line.first_node()],[station])
            if(not int3):
                int4=self.node_within_distance_any_station(line.end_point_dict[line.last_node()],[station])
            # if(printstuff):
            #     print([int1,int2,int3,int4])
            #     print('first node')
            #     print(line.first_node())
            #     print('line:'+str(line.end_point_dict[line.first_node()]))
            #     print('station: POINT: ('+station.serialize()['lon']+' '+station.serialize()['lat']+')')
            #     print('last node')
            #     print(line.last_node())
            #     print('line:'+str(line.end_point_dict[line.last_node()]))
            #     print('station: POINT: ('+station.serialize()['lon']+' '+station.serialize()['lat']+')')
            #     print('')
            #     print('')
            if int1:
                node_to_continue_id = line.last_node()
                # print('node_to_continue_id1') 
                # print(node_to_continue_id) 
                # print(int2)
            elif int2:
                node_to_continue_id = line.first_node()
                # print('node_to_continue_id2')
                # print(node_to_continue_id) 
                # if self.close_nodes and self.node_within_distance_any_station(line.end_point_dict[line.first_node()],
            # if self.close_nodes and self.node_within_distance_any_station(line.end_point_dict[line.first_node()],
            # print(int3)
            if int3:
                # print('node_to_continue_id3')
                # print(node_to_continue_id)
                node_to_continue_id = line.last_node()
                # print('node_to_continue_id3')
            elif int4:
                # print('node_to_continue_id')
                node_to_continue_id = line.first_node()
                # print(node_to_continue_id)
                # quit()

            if node_to_continue_id:
                # name=line.serialize()['name']
                # if(name):
                #     if(name.find('Queen')>-1):
                #         print(name)
                #         if(name.find('National Grid Indian Queens-Alverdiscott')>-1):
                #             print('GOT EM!1')
                #             print('station')
                #             print(station.serialize()['name'])
                self.covered_nodes = set(line.nodes)
                self.covered_nodes.remove(node_to_continue_id)
                if line.id in station.covered_line_ids:
                    root.debug('Relation with %s at %s already covered', str(line), str(station))
                    continue
                root.debug('%s', str(station))
                root.debug('%s', str(line))
                station.covered_line_ids.append(line.id)
                # init new circuit
                # here we have the beginning of the relation which is one station with one line connected to it
                relation = [station, line]
                relations.extend(
                    self.infer_relation(stations, lines, relation, node_to_continue_id, line))
        return relations

    # recursive function that infers electricity circuits
    # circuit - sorted member array
    # line - line of circuit
    # stations - all known stations
    def infer_relation(self, stations, lines, relation, node_to_continue_id, from_line):
        relation = list(relation)  # make a copy
        start_station = relation[0]
        # here also check for intersection
        station_id = self.node_intersect_with_any_station(
            from_line.end_point_dict[node_to_continue_id], stations.values())
        if not station_id and self.close_nodes:
            self.node_within_distance_any_station(
                from_line.end_point_dict[node_to_continue_id], stations.values())
        # if(from_line.end_point_dict[node_to_continue_id].x>-5 and from_line.end_point_dict[node_to_continue_id].x<-4.8 and from_line.end_point_dict[node_to_continue_id].y <50.5 and from_line.end_point_dict[node_to_continue_id].y >50.2):
        #     print('from_line.end_point_dict[node_to_continue_id]')
        #     print(from_line.end_point_dict[node_to_continue_id].x)
        #     print(from_line.end_point_dict[node_to_continue_id].y)
        if station_id and station_id == start_station.id:  # if node to continue is at the starting station --> LOOP
            root.debug('Encountered loop: %s', self.to_overpass_string(relation))
            return []
        elif station_id and station_id != start_station.id:
            # if a node is within another station --> FOUND THE 2nd ENDPOINT
            station = stations[station_id]
            root.debug('%s', str(station))
            if from_line.id in station.covered_line_ids:
                root.debug('Relation with %s at %s already covered', str(from_line), str(station))
                return []
            station.covered_line_ids.append(from_line.id)
            relation.append(station)
            root.debug('Could obtain relation')
            return [list(relation)]

        # no endpoints encountered - handle line subsection
        # at first find all lines that cover the node to continue
        relations = []
        for line in lines.values():
            if from_line.end_point_dict[node_to_continue_id].intersects(line.geom):
                if line.id == from_line.id:
                    continue
                root.debug('%s', str(line))
                if from_line.end_point_dict[node_to_continue_id].intersects(line.end_point_dict[line.first_node()]):
                    new_node_to_continue_id = line.last_node()
                else:
                    new_node_to_continue_id = line.first_node()
                if new_node_to_continue_id in self.covered_nodes:
                    relation.append(line)
                    root.debug('Encountered loop - stopping inference at line (%s): %s', str(line.id),
                               self.to_overpass_string(relation))
                    relation.remove(line)
                    self.covered_nodes.update(line.nodes)
                    continue
                relation_copy = list(relation)
                relation_copy.append(line)
                self.covered_nodes.update(line.nodes)
                self.covered_nodes.remove(new_node_to_continue_id)
                relations.extend(self.infer_relation(stations, lines, relation_copy, new_node_to_continue_id, line))

        # if not relations:
        #     root.debug('Could not obtain circuit')
        return relations

    # noinspection PyMethodMayBeStatic
    def to_overpass_string(self, relation):
        overpass = ''
        for member in relation:
            overpass += 'way(' + str(member.id) + ');(._;>;);out;'
        return overpass

    # noinspection PyMethodMayBeStatic
    def circuit_to_overpass_string(self, circuit):
        overpass = ''
        for member in circuit.members:
            overpass += 'way(' + str(member.id) + ');(._;>;);out;'
        return overpass

    # returns if node is in station
    # noinspection PyMethodMayBeStatic
    def node_intersect_with_any_station(self, node, stations):
        # print('node')
        # print(node) 
        # print('stations')
        # print(stations)
        for station in stations:
            # print(station.geom)
            if node.intersects(station.geom):
                # print('success')
                return station.id

        # print('return NONE')
        return None

    # returns if node is within curtain distance
    def node_within_distance_any_station(self, node, stations):
        for station in stations:

            distance = self.get_node_station_ditance(node, station)
            # if distance and distance < 1000:
            #     print('distance')
            #     print(distance)
            #     print(node)
            if(self.close_nodes):
                if distance and distance < 1000:
                    return station.id
            else:
                if distance and distance < 300:
                    return station.id
        return None

    def get_node_station_ditance(self, node, station):
        pol_ext = LinearRing(station.geom.exterior.coords)
        touch_node = pol_ext.interpolate(pol_ext.project(node))
        angle1, angle2, distance = self.geod.inv(touch_node.coords.xy[0], touch_node.coords.xy[1],
                                                 node.coords.xy[0], node.coords.xy[1])
        if distance and len(distance):
            return distance[0]
        return None

    # noinspection PyMethodMayBeStatic
    def num_subs_in_relation(self, relation):
        num_stations = 0
        for way in relation:
            if isinstance(way, Station):
                num_stations += 1
        return num_stations

    # noinspection PyMethodMayBeStatic
    def get_close_components(self, components, center_component):
        close_components = dict()
        for component in components:
            distance = center_component.geom.centroid.distance(component.geom.centroid)
            if distance <= 300000:
                close_components[component.id] = component
        return close_components

    # noinspection PyMethodMayBeStatic
    def parse_power(self, power_string):
        if not power_string:
            return None
        power_string = power_string.replace(',', '.').replace('W', '')
        try:
            if 'k' in power_string:
                tokens = power_string.split('k')
                return float(tokens[0].strip()) * 1000
            elif 'K' in power_string:
                tokens = power_string.split('K')
                return float(tokens[0].strip()) * 1000
            elif 'm' in power_string:
                tokens = power_string.split('m')
                return float(tokens[0].strip()) * 1000000
            elif 'M' in power_string:
                tokens = power_string.split('M')
                return float(tokens[0].strip()) * 1000000
            elif 'g' in power_string:
                tokens = power_string.split('g')
                return float(tokens[0].strip()) * 1000000000
            elif 'G' in power_string:
                tokens = power_string.split('G')
                return float(tokens[0].strip()) * 1000000000
            else:
                return float(power_string.strip())
        except ValueError:
            root.debug('Could not extract power from string %s', power_string)
            return None

    def create_relations_of_region(self, substations, generators, lines, voltage):
        stations = substations.copy()
        stations.update(generators)
        # for gi in substations.keys():
        #     val=substations[gi]
        #     if(val.serialize()['name'].find('Alverdiscott')>-1):
        #         print(val.serialize()['name'])
        #         print(val.serialize()['lat'])
        #         print(val.serialize()['lon'])
        #         print(gi)
        #         print('TRUE QUEEN')
        #         # quit()
        #         break
        circuits = []

        for substation_id in substations.keys():
            # print(substations[substation_id].serialize()['name'])
            # print(substations[gi].serialize()['name'])
            # # quit()

            # isqueen=False

            # if(substations[substation_id].serialize()['name'].find('Queen')>-1):
                # print('Queen!!')
                # print('Queen!!')
                # print('Queen!!')
                # print('Queen!!')
                # print('Queen!!')
                # isqueen=True
                # quit()
            close_stations_dict = self.get_close_components(stations.values(), stations[substation_id])
            # for g in close_stations_dict.values():
            #     if(g.serialize()['name'].find('Queen')>-1):
            #         print(g.serialize()['name'])
            #         break
            close_lines_dict = self.get_close_components(lines.values(), stations[substation_id])
            # print(close_lines_dict)
            # print('generators')
            # print(generators)
            # print('close_stations_dict')
            # for s in close_stations_dict.values():
            #     print(s.serialize()['name'])
            #     if(s):
            #         if(s.serialize()['name'].find('Queen')>-1):
            #             break
            # print('close_lines_dict')
            # print(close_lines_dict)
            # print('substation_id')
            # print(substation_id)
            relations=self.create_relations(close_stations_dict, close_lines_dict, substation_id, voltage)
            # if(substation_id==gi):
            #     print('relations')
            #     for r in relations:
            #         r.print_circuit()
            #        # print(relations)
                
            #     quit()
            # if(isqueen):

                # quit()
            # print('relations')
            # print(relations)
            circuits.extend(relations)
            
        return circuits

    # noinspection PyMethodMayBeStatic
    def remove_duplicates(self, circuits):

        root.info('Remove duplicates from %s circuits', str(len(circuits)))
        covered_connections = []
        filtered_circuits = []
        total_line_length = 0
        for circuit in circuits:
            station1 = circuit.members[0]
            station2 = circuit.members[-1]
            for line in circuit.members[1:-1]:
                total_line_length += line.length
            if str(station1.id) + str(station2.id) + str(circuit.voltage) in covered_connections \
                    or str(station2.id) + str(station1.id) + str(circuit.voltage) in covered_connections:
                continue
            covered_connections.append(str(station1.id) + str(station2.id) + str(circuit.voltage))
            filtered_circuits.append(circuit)
        root.info('%s circuits remain', str(len(filtered_circuits)))
        root.info('Line length with duplicates is %s meters', str(total_line_length))
        return filtered_circuits

    @staticmethod
    def run_matlab_for_continent(matlab_command, continent_folder, root_log):
        matlab_dir = join(dirname(__file__), '../matlab')
        try:
            log_dir = join(dirname(__file__), '../logs/planet/{0}'.format(continent_folder))
            if not exists(log_dir):
                makedirs(log_dir)

            command = 'cd {0} && {1} -r "transform planet/{2};quit;"| tee ../logs/planet/{2}/transnet_matlab.log' \
                .format(matlab_dir, matlab_command, continent)
            root_log.info('running MATLAB modeling for {0}'.format(continent_folder))
            return_code = call(command, shell=True)
            root_log.info('MATLAB return code {0}'.format(return_code))
        except Exception as ex:
            root_log.error(ex.message)

    @staticmethod
    def run_matlab_for_countries(matlab_command, continent_folder, root_log):
        dirs = [x[0] for x in walk(join(dirname(__file__), '../../transnet-models/{0}/'.format(continent_folder)))]
        matlab_dir = join(dirname(__file__), '../matlab')
        for DIR in dirs[1:]:
            try:
                country = DIR.split('/')[-1]
                log_dir = join(dirname(__file__), '../logs/{0}/{1}'.format(continent_folder, country))
                if not exists(log_dir):
                    makedirs(log_dir)

                command = 'cd {0} && {1} -r "transform {2}/{3};quit;"| tee ../logs/{2}/{3}/transnet_matlab.log' \
                    .format(matlab_dir, matlab_command, continent, country)
                root_log.info('running MATLAB modeling for {0}'.format(country))
                return_code = call(command, shell=True)
                root_log.info('MATLAB return code {0}'.format(return_code))
            except Exception as ex:
                root_log.error(ex.message)

    # noinspection PyMethodMayBeStatic
    def try_parse_int(self, string):
        try:
            return int(string)
        except ValueError:
            return 0

    # noinspection PyMethodMayBeStatic
    def convert_size_mega_byte(self, size):
        return size / 1048576.0

    def prepare_continent_json(self, continent_name):
        with open('meta/{0}.json'.format(continent_name), 'r+') as continent_file:
            continent_json = json.load(continent_file)
            for country in continent_json:
                self.prepare_poly_country(continent_name, country)
                boundary = PolyParser.poly_to_polygon('../data/{0}/{1}/pfile.poly'.format(continent_name, country))
                where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
                query = '''SELECT DISTINCT(voltage) AS voltage, count(*)
                            AS num FROM planet_osm_line  l WHERE %s
                            GROUP BY voltage ORDER BY num DESC''' % where_clause
                continent_json[country]['voltages'] = self.get_voltages_from_query(query=query)
            continent_file.seek(0)
            continent_file.write(json.dumps(continent_json, indent=4))
            continent_file.truncate()

    def prepare_planet_json(self, continent_name):
        with open('meta/planet.json'.format(continent_name), 'r+') as continent_file:
            continent_json = json.load(continent_file)
            self.prepare_poly_continent(continent_name)
            query = '''SELECT DISTINCT(voltage) AS voltage, count(*) AS num
                        FROM planet_osm_line  l
                        GROUP BY voltage ORDER BY num DESC'''
            continent_json[continent_name]['voltages'] = self.get_voltages_from_query(query=query)
            continent_file.seek(0)
            continent_file.write(json.dumps(continent_json, indent=4))
            continent_file.truncate()

    def get_voltages_from_query(self, query):
        voltages = set()
        voltages_string = ''
        first_round = True
        self.cur.execute(query)
        result = self.cur.fetchall()
        # np.save(str(voltage)+)

        for (voltage, num) in result:
            if num > 30 and voltage:
                raw_voltages = [self.try_parse_int(x) for x in str(voltage).strip().split(';')]
                voltages = voltages.union(set(raw_voltages))
        for voltage in sorted(voltages):
            if voltage > 199999:
                if first_round:
                    voltages_string += str(voltage)
                    first_round = False
                else:
                    voltages_string += '|' + str(voltage)
        return voltages_string

    def export_to_json(self, all_circuits):
        try:
            with open('{0}/relations.json'.format(self.destdir), 'w') as outfile:
                json.dump([c.serialize() for c in all_circuits], outfile, indent=4)
            file_size = self.convert_size_mega_byte(getsize('{0}/relations.json'.format(self.destdir)))

            if file_size >= 100:
                command = 'split --bytes=50M {0}/relations.json {0}/_relations'.format(self.destdir)
                return_code = call(command, shell=True)
                root.info('Relation file split return {0}'.format(return_code))
                remove('{0}/relations.json'.format(self.destdir))
        except Exception as ex:
            root.error(ex.message)

    def inference_for_voltage(self, voltage_level, where_clause, length_found_lines, equipment_points, all_substations,
                              all_generators, boundary):
        root.info('Infer net for voltage level %sV', voltage_level)

        substations = dict()
        generators = dict()
        lines = dict()
        # create lines dictionary
        sql = '''SELECT l.osm_id AS id,
                -- st_transform(create_line(l.osm_id), 4326) AS geom,
                create_line(l.osm_id) AS geom,
                l.way AS srs_geom, 
                l.power AS type,
                l.name,
                l.ref, 
                l.voltage, 
                l.cables, 
                w.nodes, 
                w.tags,
                -- st_transform(create_point(w.nodes[1]), 4326) AS first_node_geom,
                create_point(w.nodes[1]) AS first_node_geom,
                -- st_transform(create_point(w.nodes[array_length(w.nodes, 1)]), 4326) AS last_node_geom,
                create_point(w.nodes[array_length(w.nodes, 1)]) AS last_node_geom,
                ST_Y(ST_Transform(ST_Centroid(l.way),4326)) AS lat,
                ST_X(ST_Transform(ST_Centroid(l.way),4326)) AS lon,
                st_length(st_transform(l.way, 4326), TRUE) AS spheric_length
                FROM planet_osm_line l, planet_osm_ways w
                -- WHERE l.osm_id >= 0 
                -- AND l.power ~ 'line|cable|minor_line'
                WHERE l.power ~ 'line|cable|minor_line'
                AND l.voltage ~ '%s' 
                AND l.osm_id = w.id AND %s
                LIMIT 100''' % (voltage_level, where_clause)
        self.cur.execute(sql)

        result = self.cur.fetchall()
        # noinspection PyShadowingBuiltins,PyShadowingBuiltins
        for (id, geom, srs_geom, type, name, ref, voltage, cables, nodes, tags, first_node_geom, last_node_geom,
             lat, lon, length) in result:
            # if(name):
            #     if(name.find('Queen')>-1):
            #         print(name)
            #         if(name.find('National Grid Indian Queens-Alverdiscott')>-1):
            #             print('GOT EM!')
            line_raw = wkb.loads(geom, hex=True)
            raw_geom = geom

            srs_line = wkb.loads(srs_geom, hex=True)
            # print('srs_line')
            # print(srs_line)
            length_found_lines += length
            last_node_raw = wkb.loads(last_node_geom, hex=True)
            first_node_raw = wkb.loads(first_node_geom, hex=True)

            #convert to lat/long from integer OSM lat/long format
            first_node=geometry.Point(first_node_raw.x/100000,first_node_raw.y/100000)
            # print('first_node')
            # print(first_node)
            #convert to lat/long from integer OSM lat/long format
            last_node=geometry.Point(last_node_raw.x/100000,last_node_raw.y/100000)
            # print('last_node')
            # print(last_node)

            # if(name):
                # if(name.find('National Grid Indian Queens-Alverdiscott')>-1):
                
                # print('first_node')
                # print(first_node)
                # print('last_node')
                # print(last_node)
            end_points_geom_dict = dict()
            end_points_geom_dict[nodes[0]] = first_node
            end_points_geom_dict[nodes[-1]] = last_node
            # print('line raw')
            # print(line_raw)
            # print('srs_line')
            # print(srs_line)
            line_array=[[]]*len(line_raw.coords)
            for i in range(0,len(line_raw.coords)):
                # print(i)
                x=line_raw.coords[i][0]/100000
                y=line_raw.coords[i][1]/100000
                line_array[i]=[x,y]

            line=geometry.LineString(line_array)
            # print('done')
            # print(line)

            # for i in range(0,len(line.coords.xy)):
            #     line[i]=geometry.Point(line.coords.xy[0][i]/100000,line.coords.xy[1][i]/100000)
            lines[id] = Line(id, line, srs_line, type, name.replace(',', ';') if name else None,
                             ref.replace(',', ';') if ref is not None else None,
                             voltage.replace(',', ';').replace('/', ';') if voltage else None, cables,
                             nodes, tags, lat, lon,
                             end_points_geom_dict, length, raw_geom)
            # if(name):
            #     if(name=='Balti — Tartu 330 kV'):
            #         print('')
            #         print('line.first_node()')
            #         print(lines[id].first_node())
            #         print('line.last_node()')
            #         print(lines[id].last_node())
            #         print('end_points_geom_dict')
            #         print(end_points_geom_dict[nodes[0]].xy)
            #         print(end_points_geom_dict[nodes[-1]].xy)
            # print('lines[id]')
            # print(lines[id])
            # print('lat')
            # print(lat)
            # print('long')
            # print(lon)
            # print('long')
            # print(lon)
            # print('line.end_point_dict[line.first_node()], [station]')
            # print('lines[id].first_node()')
            # print(lines[id].first_node())
            # print(lines[id].end_point_dict[lines[id].first_node()])
            equipment_points.append((lat, lon))
        root.info('Found %s lines', str(len(result)))

        # create station dictionary by quering only ways
        sql = '''SELECT DISTINCT(p.osm_id) AS id,
                  st_transform(p.way, 4326) AS geom,
                  p.power AS type, 
                  p.name, 
                  p.ref, 
                  p.voltage, 
                  p.tags,
                  ST_Y(ST_Transform(ST_Centroid(p.way),4326)) AS lat,
                  ST_X(ST_Transform(ST_Centroid(p.way),4326)) AS lon
                  FROM planet_osm_line l, planet_osm_polygon p
                  -- WHERE l.osm_id >= 0 
                  -- AND p.osm_id >= 0
                  -- AND p.power ~ 'substation|station|sub_station' 
                  WHERE p.power ~ 'substation|station|sub_station'
                  -- AND (p.voltage ~ '%s' OR (p.voltage = '') IS NOT FALSE)                   
                  AND l.power ~ 'line|cable|minor_line' 
                  AND l.voltage ~ '%s' AND %s''' % (self.voltage_levels, voltage_level, where_clause)

        if self.close_nodes:
        #if True:
            sql += ''' AND (st_intersects(l.way, p.way) OR st_distance(l.way, p.way) < 1500)'''
            #sql += ''' AND (st_intersects(l.way, p.way) OR st_distance(l.way, p.way) < 300)'''
        else:
            sql += ''' AND st_intersects(l.way, p.way)'''
        # print('sql')
        # print(sql)
        # quit()
        self.cur.execute(sql)
        result = self.cur.fetchall()
        # noinspection PyShadowingBuiltins,PyShadowingBuiltins
        for (id, geom, type, name, ref, voltage, tags, lat, lon) in result:
            # if(name=='Viljandi alajaam'):
            #     print('success')
            #     # quit()
            # if(name=='Sopi alajaam'):
            #     print('Sopi')
            if id not in all_substations:
                polygon = wkb.loads(geom, hex=True)
                raw_geom = geom
                substations[id] = Station(id, polygon, type, name, ref,
                                          voltage.replace(',', ';').replace('/', ';') if voltage else None,
                                          None, tags, lat, lon, raw_geom)
                equipment_points.append((lat, lon))
            else:
                substations[id] = all_substations[id]

        root.info('Found %s stations', str(len(equipment_points)))

        # add power plants with area
        sql = '''SELECT DISTINCT(p.osm_id) AS id,
                st_transform(p.way, 4326) AS geom,
                p.power AS type,
                p.name, 
                p.ref, 
                p.voltage, 
                p.\"plant:output:electricity\" AS output1,
                p.\"generator:output:electricity\" AS output2,
                p.tags, 
                ST_Y(ST_Transform(ST_Centroid(p.way),4326)) AS lat,
                ST_X(ST_Transform(ST_Centroid(p.way),4326)) AS lon
                FROM planet_osm_line l, planet_osm_polygon p
                -- WHERE l.osm_id >= 0 
                -- AND p.osm_id >= 0 
                WHERE p.power ~ 'plant|generator'               
                AND l.power ~ 'line|cable|minor_line'
                AND l.voltage ~ '%s' AND %s''' % (voltage_level, where_clause)

        if self.close_nodes:
        # if True:
            # sql += ''' AND (st_intersects(l.way, p.way) OR st_distance(l.way, p.way) < 1000)'''
            sql += ''' AND (st_intersects(l.way, p.way) OR st_distance(l.way, p.way) < 300)'''
        else:
            sql += ''' AND st_intersects(l.way, p.way)'''

        self.cur.execute(sql)
        result = self.cur.fetchall()
        # noinspection PyShadowingBuiltins,PyShadowingBuiltins
        for (id, geom, type, name, ref, voltage, output1, output2, tags, lat, lon) in result:
            if id not in all_generators:
                polygon = wkb.loads(geom, hex=True)
                raw_geom = geom
                generators[id] = Station(id, polygon, type, name, ref,
                                         voltage.replace(',', ';').replace('/', ';') if voltage else None,
                                         None, tags, lat, lon, raw_geom)
                generators[id].nominal_power = self.parse_power(
                    output1) if output1 is not None else self.parse_power(output2)
                equipment_points.append((lat, lon))
            else:
                generators[id] = all_generators[id] 
        root.info('Found %s generators', str(len(generators)))
        # for g in generators.values():
        #     print(g.serialize()['name'])
        # print(boundary)
        print('before heavy lifting')
        if boundary:
            circuits = self.create_relations_of_region(substations, generators, lines, voltage_level)
            # print('circuits!')
            # print(circuits)
            # stations.update(generators)
        else:
            # print('no boundary')
            stations = substations.copy()
            stations.update(generators)
            # print('voltage_level')
            # print(voltage_level)
            # print('stations')
            # print(stations)

            circuits = self.create_relations(stations, lines, self.ssid, voltage_level)

        return length_found_lines, equipment_points, generators, substations, circuits

    def find_missing_data_for_country(self):
        root.info('Finding missing data')

        if not exists(self.destdir):
            makedirs(self.destdir)

        if self.poly:
            boundary = PolyParser.poly_to_polygon(self.poly)
            where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
            where_clause_station = "st_intersects(p.way, st_transform(st_geomfromtext('" + \
                                   boundary.wkt + "',4269),3857))"
        elif self.bpoly:
            boundary = wkt.loads(self.bpoly)
            where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
            where_clause_station = "st_intersects(p.way, st_transform(st_geomfromtext('" + \
                                   boundary.wkt + "',4269),3857))"
        else:
            where_clause = "st_distance(l.way, (select way from planet_osm_polygon where osm_id = " + str(
                self.ssid) + ")) <= 300000"
            where_clause_station = "st_distance(p.way, (select way from planet_osm_polygon where osm_id = " + str(
                self.ssid) + ")) <= 300000"

        voltages_line = set()
        voltages_cable = set()
        voltages_minor_line = set()
        line_voltage_query = '''SELECT DISTINCT(voltage) AS voltage, power as power_type, count(*) AS num
                                          FROM planet_osm_line  l WHERE %s
                                          GROUP BY power, voltage''' % where_clause
        self.cur.execute(line_voltage_query)
        result_voltages = self.cur.fetchall()
        for (voltage, power_type, num) in result_voltages:
            if num > 30 and voltage:
                raw_voltages = [self.try_parse_int(x) for x in str(voltage).strip().split(';')]
                if power_type == 'line':
                    voltages_line = voltages_line.union(set(raw_voltages))
                elif power_type == 'cable':
                    voltages_cable = voltages_cable.union(set(raw_voltages))
                elif power_type == 'minor_line':
                    voltages_minor_line = voltages_minor_line.union(set(raw_voltages))

        cables_line = set()
        cables_cable = set()
        cables_minor_line = set()
        line_cables_query = '''SELECT DISTINCT(cables) AS cables, power as power_type, count(*) AS num
                                                  FROM planet_osm_line  l WHERE %s
                                                  GROUP BY power, cables''' % where_clause
        self.cur.execute(line_cables_query)
        result_cables = self.cur.fetchall()
        for (cables, power_type, num) in result_cables:
            if num > 30 and cables:
                raw_cables = [self.try_parse_int(x) for x in str(cables).strip().split(';')]
                if power_type == 'line':
                    cables_line = cables_line.union(set(raw_cables))
                elif power_type == 'cable':
                    cables_cable = cables_cable.union(set(raw_cables))
                elif power_type == 'minor_line':
                    cables_minor_line = cables_minor_line.union(set(raw_cables))

        voltages_line_str = ';'.join([str(x) for x in voltages_line])
        cables_line_str = ';'.join([str(x) for x in cables_line])
        voltages_cable_str = ';'.join([str(x) for x in voltages_cable])
        cables_cable_str = ';'.join([str(x) for x in cables_cable])
        voltages_minor_line_str = ';'.join([str(x) for x in voltages_minor_line])
        cables_minor_line_str = ';'.join([str(x) for x in cables_minor_line])

        lines = dict()

        lines_sql = '''SELECT l.osm_id AS osm_id,
                        st_transform(create_line(l.osm_id), 4326) AS geom,
                        l.way AS srs_geom, l.power AS power_type,
                        l.name, l.ref, l.voltage, l.cables, w.nodes, w.tags,
                        st_transform(create_point(w.nodes[1]), 4326) AS first_node_geom,
                        st_transform(create_point(w.nodes[array_length(w.nodes, 1)]), 4326) AS last_node_geom,
                        ST_Y(ST_Transform(ST_Centroid(l.way),4326)) AS lat,
                        ST_X(ST_Transform(ST_Centroid(l.way),4326)) AS lon,
                        st_length(st_transform(l.way, 4326), TRUE) AS spheric_length
                        FROM planet_osm_line l, planet_osm_ways w
                        -- WHERE l.osm_id >= 0 AND l.power ~ 'line|cable|minor_line'
                        WHERE l.power ~ 'line|cable|minor_line'
                        AND (l.voltage IS NULL OR l.cables IS NULL) AND l.osm_id = w.id AND %s''' % where_clause

        self.cur.execute(lines_sql)
        lines_result = self.cur.fetchall()
        for (osm_id, geom, srs_geom, power_type, name, ref, voltage, cables, nodes, tags, first_node_geom,
             last_node_geom, lat, lon, length) in lines_result:
            line = wkb.loads(geom, hex=True)
            raw_geom = geom
            srs_line = wkb.loads(srs_geom, hex=True)
            first_node = wkb.loads(first_node_geom, hex=True)
            last_node = wkb.loads(last_node_geom, hex=True)
            end_points_geom_dict = dict()
            end_points_geom_dict[nodes[0]] = first_node
            end_points_geom_dict[nodes[-1]] = last_node
            temp_line = Line(osm_id, line, srs_line, power_type, name.replace(',', ';') if name else None,
                             ref.replace(',', ';') if ref is not None else None,
                             voltage.replace(',', ';').replace('/', ';') if voltage else None, cables,
                             nodes, tags, lat, lon,
                             end_points_geom_dict, length, raw_geom)
            if power_type == 'line':
                temp_line.add_missing_data_estimation(voltage=voltages_line_str, cables=cables_line_str)
            elif power_type == 'cable':
                temp_line.add_missing_data_estimation(voltage=voltages_cable_str, cables=cables_cable_str)
            elif power_type == 'minor_line':
                temp_line.add_missing_data_estimation(voltage=voltages_minor_line_str, cables=cables_minor_line_str)

            if power_type in ['line', 'cable', 'minor_line']:
                lines[osm_id] = temp_line
        with open('{0}/lines_missing_data.json'.format(self.destdir), 'w') as outfile:
            json.dump([l.serialize() for osm_id, l in lines.items()], outfile, indent=4)

        file_size = self.convert_size_mega_byte(getsize('{0}/lines_missing_data.json'.format(self.destdir)))

        if file_size >= 100:
            command = 'split --bytes=50M {0}/lines_missing_data.json {0}/_lines_missing_data'.format(self.destdir)
            return_code = call(command, shell=True)
            root.info('Lines Missing Data file split return {0}'.format(return_code))
            remove('{0}/lines_missing_data.json'.format(self.destdir))

        stations_missing_connections_sql = '''SELECT DISTINCT
                                              p.osm_id                                     AS osm_id,
                                              st_transform(p.way, 4326)                    AS geom,
                                              p.power                                      AS power_type,
                                              p.name,
                                              p.ref,
                                              p.voltage,
                                              p.tags,
                                              ST_Y(ST_Transform(ST_Centroid(p.way), 4326)) AS lat,
                                              ST_X(ST_Transform(ST_Centroid(p.way), 4326)) AS lon
                                            FROM planet_osm_polygon p
                                            WHERE %s
                                            EXCEPT
                                            SELECT DISTINCT
                                              p.osm_id                                     AS osm_id,
                                              st_transform(p.way, 4326)                    AS geom,
                                              p.power                                      AS power_type,
                                              p.name,
                                              p.ref,
                                              p.voltage,
                                              p.tags,
                                              ST_Y(ST_Transform(ST_Centroid(p.way), 4326)) AS lat,
                                              ST_X(ST_Transform(ST_Centroid(p.way), 4326)) AS lon
                                            FROM planet_osm_line l, planet_osm_polygon p
                                            WHERE %s
                                                  -- AND l.osm_id >= 0
                                                  -- AND p.osm_id >= 0
                                                  AND p.power ~ 'substation|station|sub_station|plant|generator'
                                                  AND l.power ~ 'line|cable|minor_line'
                                                  AND st_intersects(l.way, p.way);''' % \
                                           (where_clause_station, where_clause)

        stations_missing_voltage = '''SELECT DISTINCT
                                      p.osm_id                                     AS osm_id,
                                      st_transform(p.way, 4326)                    AS geom,
                                      p.power                                      AS power_type,
                                      p.name,
                                      p.ref,
                                      p.voltage,
                                      p.tags,
                                      ST_Y(ST_Transform(ST_Centroid(p.way), 4326)) AS lat,
                                      ST_X(ST_Transform(ST_Centroid(p.way), 4326)) AS lon
                                    FROM planet_osm_polygon p
                                    WHERE %s
                                    AND p.voltage IS NULL;''' % where_clause_station

        stations_voltages = '''SELECT
                              p.voltage AS voltage,
                              p.power AS power_type,
                              count(*) AS num
                            FROM planet_osm_polygon p
                            WHERE %s
                            GROUP BY power, voltage;''' % where_clause_station

        voltages_substations = set()
        voltages_stations = set()
        voltages_plant = set()
        self.cur.execute(stations_voltages)
        result_station_voltages = self.cur.fetchall()
        for (voltage, power_type, num) in result_station_voltages:
            if num > 30 and voltage:
                raw_voltages = [self.try_parse_int(x) for x in str(voltage).strip().split(';')]
                if power_type in ['substation', 'sub_station']:
                    voltages_substations = voltages_substations.union(set(raw_voltages))
                elif power_type == 'station':
                    voltages_stations = voltages_stations.union(set(raw_voltages))
                elif power_type in ['plant', 'generator']:
                    voltages_plant = voltages_plant.union(set(raw_voltages))

        voltages_substations_str = ';'.join([str(x) for x in voltages_substations])
        voltages_stations_str = ';'.join([str(x) for x in voltages_stations])
        voltages_plant_str = ';'.join([str(x) for x in voltages_plant])

        stations_missing_data = dict()

        self.cur.execute(stations_missing_connections_sql)
        result_stations_missing_connection = self.cur.fetchall()
        for (osm_id, geom, power_type, name, ref, voltage, tags, lat, lon) in result_stations_missing_connection:
            if osm_id not in stations_missing_data:
                polygon = wkb.loads(geom, hex=True)
                raw_geom = geom
                temp_station = Station(osm_id, polygon, power_type, name, ref,
                                       voltage.replace(',', ';').replace('/', ';') if voltage else None,
                                       None, tags, lat, lon, raw_geom)
                temp_station.add_missing_connection()
                if power_type in ['substation', 'sub_station']:
                    temp_station.add_missing_data_estimation(voltage=voltages_substations_str)
                elif power_type == 'station':
                    temp_station.add_missing_data_estimation(voltage=voltages_stations_str)
                elif power_type in ['plant', 'generator']:
                    temp_station.add_missing_data_estimation(voltage=voltages_plant_str)

                if power_type in ['substation', 'sub_station', 'station', 'plant', 'generator']:
                    stations_missing_data[osm_id] = temp_station

        self.cur.execute(stations_missing_voltage)
        result_stations_missing_voltage = self.cur.fetchall()
        for (osm_id, geom, power_type, name, ref, voltage, tags, lat, lon) in result_stations_missing_voltage:
            if osm_id not in stations_missing_data:
                polygon = wkb.loads(geom, hex=True)
                raw_geom = geom
                temp_station = Station(osm_id, polygon, power_type, name, ref,
                                       voltage.replace(',', ';').replace('/', ';') if voltage else None,
                                       None, tags, lat, lon, raw_geom)
                if power_type in ['substation', 'sub_station']:
                    temp_station.add_missing_data_estimation(voltage=voltages_substations_str)
                elif power_type == 'station':
                    temp_station.add_missing_data_estimation(voltage=voltages_stations_str)
                elif power_type in ['plant', 'generator']:
                    temp_station.add_missing_data_estimation(voltage=voltages_plant_str)

                if power_type in ['substation', 'sub_station', 'station', 'plant', 'generator']:
                    stations_missing_data[osm_id] = temp_station

        with open('{0}/stations_missing_data.json'.format(self.destdir), 'w') as outfile:
            json.dump([s.serialize() for osm_id, s in stations_missing_data.items()], outfile, indent=4)

        file_size = self.convert_size_mega_byte(getsize('{0}/stations_missing_data.json'.format(self.destdir)))

        if file_size >= 100:
            command = 'split --bytes=50M {0}/stations_missing_data.json {0}/_stations_missing_data'.format(self.destdir)
            return_code = call(command, shell=True)
            root.info('Stations Missing Data file split return {0}'.format(return_code))
            remove('{0}/stations_missing_data.json'.format(self.destdir))

    def run(self):
        if self.whole_planet and self.chose_continent:
            with open('meta/planet.json'.format(continent)) as continent_file:
                continent_json = json.load(continent_file)
                try:
                    self.voltage_levels = continent_json[self.chose_continent]['voltages']
                    self.poly = '../data/planet/{0}/pfile.poly'.format(continent)
                    self.destdir = '../../transnet-models/planet/{0}/'.format(continent)
                    if self.voltage_levels:
                        self.reset_params()
                        self.modeling(continent)
                    if self.find_missing_data:
                        self.find_missing_data_for_country()
                except Exception as ex:
                    root.error(ex.message)
        elif self.chose_continent:
            with open('meta/{0}.json'.format(continent)) as continent_file:
                continent_json = json.load(continent_file)
                for country in continent_json:
                    try:
                        self.voltage_levels = continent_json[country]['voltages']
                        self.poly = '../data/{0}/{1}/pfile.poly'.format(continent, country)
                        self.destdir = '../../transnet-models/{0}/{1}/'.format(continent, country)
                        if self.voltage_levels:
                            self.reset_params()
                            self.modeling(country)
                        if self.find_missing_data:
                            self.find_missing_data_for_country()
                    except Exception as ex:
                        root.error(ex.message)
        else:
            self.modeling(self.db_name)
            if self.find_missing_data:
                self.find_missing_data_for_country()


    def modeling(self, country_name):
        # create dest dir
        if not exists(self.destdir):
            makedirs(self.destdir)
        print('country name')
        print(country_name)
        root.info('Infer for %s', country_name)

        time = datetime.now()

        # build location where clause for succeeding queries
        boundary = None
        if self.poly:
            boundary = PolyParser.poly_to_polygon(self.poly)
            where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        elif self.bpoly:
            boundary = wkt.loads(self.bpoly)
            where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        else:
            where_clause = "st_distance(l.way, (select way from planet_osm_polygon where osm_id = " + str(
                self.ssid) + ")) <= 300000"

        # do inference for each voltage level
        all_circuits = []
        all_substations = dict()
        all_generators = dict()
        equipment_points = []
        length_found_lines = 0

        for voltage_level in self.voltage_levels.split('|'):
            (length_found_lines, equipment_points, generators, substations, circuits) = self.inference_for_voltage(
                voltage_level, where_clause, length_found_lines, equipment_points,
                all_substations, all_generators, boundary)
            # print('circuits')
            # print(circuits[0])
            # print('v')
            # print(voltage_level)
            all_generators.update(generators)
            all_substations.update(substations)
            all_circuits.extend(circuits)

        root.info('Total length of all found lines is %s meters', str(length_found_lines))
        equipments_multipoint = MultiPoint(equipment_points)
        map_centroid = equipments_multipoint.centroid
        # logging.debug('Centroid lat:%lf, lon:%lf', map_centroid.x, map_centroid.y)
        # all_circuits = self.remove_duplicates(all_circuits)
        root.info('Inference took %s millies', str(datetime.now() - time))

        transnet_instance.export_to_json(all_circuits)

        partition_by_station_dict = None
        population_by_station_dict = None
        cities = None
        if self.load_estimation:
            root.info('Start partitioning into Voronoi-portions')
            load_estimator = LoadEstimator(all_substations, boundary)
            partition_by_station_dict, population_by_station_dict = load_estimator.partition()
            cities = load_estimator.cities
        print(self.topology)
        print(self.destdir)
        if self.topology:
            root.info('Plot inferred transmission system topology')
            plotter = Plotter(self.voltage_levels)
            plotter.plot_topology(all_circuits, equipments_multipoint, partition_by_station_dict, cities, self.destdir)

        try:
            #root.info('CSV generation started ...')
            root.info('Skipping CSV generation')
            # print('all_circuits')
            # print(all_circuits)
            #csv_writer = CSVWriter(all_circuits, root)
            #csv_writer.publish(self.destdir + '/csv')
        except Exception as ex:
            root.error(ex.message)
        try:
            root.info('CIM model generation started ...')
            cim_writer = CimWriter(all_circuits, map_centroid, population_by_station_dict, self.voltage_levels,
                                   country_name, len(all_substations))
            cim_writer.publish(self.destdir + '/cim')
        except Exception as ex:
            root.error(ex.message)

        ###########################################################
        if self.overpass:
            for circuit in all_circuits:
                root.info(self.circuit_to_overpass_string(circuit))

        for circuit in all_circuits:
            for line in circuit.members[1:-1]:
                if line.id not in self.all_lines:
                    self.length_all += line.length
                    self.all_lines[line.id] = line.id

        root.info('All lines length without duplicates %d', round(self.length_all / 1000))

        self.length_all = 0
        for circuit in all_circuits:
            for line in circuit.members[1:-1]:
                self.length_all += line.length

        root.info('All lines length with duplicates %d', round(self.length_all / 1000))

        for circuit in all_circuits:
            sts = [circuit.members[0], circuit.members[-1]]
            for st in sts:
                if st.id not in self.all_stations:
                    self.all_stations[st.id] = 1
                else:
                    self.all_stations[st.id] += 1

        root.info('All Stations count %d', len(self.all_stations))

        for circuit in all_circuits:
            for gen in [circuit.members[0], circuit.members[-1]]:

                if gen.type in ['plant', 'generator']:
                    if gen.id not in self.all_power_planet:
                        self.all_power_planet[gen.id] = '%s_%s' % (gen.lat, gen.lon)

        root.info('All power Planets count %s', len(self.all_power_planet))
        #####################################################
        if self.validate:
            validator = InferenceValidator(self.cur)
            if boundary:
                all_stations = all_substations.copy()
                all_stations.update(all_generators)
                validator.validate2(all_circuits, all_stations, boundary, self.voltage_levels)
            else:
                validator.validate(self.ssid, all_circuits, None, self.voltage_levels)

        root.info('Took %s in total', str(datetime.now() - time))


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-D", "--dbname", action="store", dest="dbname",
                      help="database name of the topology network")
    parser.add_option("-H", "--dbhost", action="store", dest="dbhost",
                      help="database host address of the topology network")
    parser.add_option("-P", "--dbport", action="store", dest="dbport",
                      help="database port of the topology network")
    parser.add_option("-U", "--dbuser", action="store", dest="dbuser",
                      help="database user name of the topology network")
    parser.add_option("-X", "--dbpwrd", action="store", dest="dbpwrd",
                      help="database user password of the topology network")
    parser.add_option("-s", "--ssid", action="store", dest="ssid",
                      help="substation id to start the inference from")
    parser.add_option("-p", "--poly", action="store", dest="poly",
                      help="poly file that defines the region to perform the nce for")
    parser.add_option("-b", "--bpoly", action="store", dest="bounding_polygon",
                      help="defines the region to perform the inference for within the specified polygon in WKT, e.g."
                           "'POLYGON((128.74 41.68, 142.69 41.68, 142.69 30.84, 128.74 30.84, 128.74 41.68))'")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="enable verbose logging")
    parser.add_option("-e", "--evaluate", action="store_true", dest="evaluate",
                      help="enable inference-to-existing-relation evaluation")
    parser.add_option("-t", "--topology", action="store_true", dest="topology",
                      help="enable plotting topology graph")
    parser.add_option("-V", "--voltage", action="store", dest="voltage_levels",
                      help="voltage levels in format 'level 1|...|level n', e.g. '220000|380000'")
    parser.add_option("-l", "--loadestimation", action="store_true", dest="load_estimation",
                      help="enable load estimation based on Voronoi partitions")
    parser.add_option("-d", "--destdir", action="store", dest="destdir",
                      help="destination of the inference results; "
                           "results will be stored in directory transnet/models/<destdir>")
    parser.add_option("-c", "--continent", action="store", dest="continent",
                      help="name of continent, options: 'africa', 'antarctica', 'asia', "
                           "'australia-oceania', 'central-america', 'europe', 'north-america', 'south-america' ")
    parser.add_option("-m", "--matlab", action="store", dest="matlab",
                      help="run matlab for all countries in continent modeling")
    parser.add_option("-j", "--preparejson", action="store_true", dest="prepare_json",
                      help="prepare json files of planet")
    parser.add_option("-g", "--globe", action="store_true", dest="whole_planet",
                      help="run global commmands")
    parser.add_option("-f", "--findmissing", action="store_true", dest="find_missing",
                      help="find missing data from OSM")
    parser.add_option("-n", "--closenodes", action="store_true", dest="close_nodes",
                      help="Include nodes close to station")
    parser.add_option("-o", "--overpass", action="store_true", dest="overpass",
                      help="Print overpass string")

    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser
    dbpwrd = options.dbpwrd
    ssid = options.ssid if options.ssid else '23025610'
    poly = options.poly
    bpoly = options.bounding_polygon
    verbose = options.verbose if options.verbose else False
    validate = options.evaluate if options.evaluate else False
    topology = options.topology if options.topology else False
    voltage_levels = options.voltage_levels
    load_estimation = options.load_estimation if options.load_estimation else False
    destdir = '../../transnet-models/' + options.destdir if options.destdir else '../results'
    continent = options.continent
    matlab = options.matlab

    # configure logging
    ch = logging.StreamHandler(sys.stdout)
    if verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    root.addHandler(ch)

    if matlab and continent:
        if options.whole_planet:
            Transnet.run_matlab_for_continent(matlab, continent, root)
        else:
            Transnet.run_matlab_for_countries(matlab, continent, root)
        exit()

    try:
        logging.info("Running for %s " % destdir)
        logging.info("Running for %s " % dbname)

        transnet_instance = Transnet(_database=dbname, _host=dbhost, _port=dbport,
                                     _user=dbuser, _password=dbpwrd, _ssid=ssid,
                                     _poly=poly, _bpoly=bpoly, _verbose=verbose,
                                     _validate=validate, _topology=topology, _voltage_levels=voltage_levels,
                                     _load_estimation=load_estimation, _destdir=destdir, _continent=continent,
                                     _whole_planet=options.whole_planet, _find_missing_data=options.find_missing,
                                     _close_nodes=options.close_nodes, _overpass=options.overpass)
        if options.prepare_json and continent:
            transnet_instance.prepare_continent_json(continent)
            if options.whole_planet:
                transnet_instance.prepare_planet_json(continent)
        else:
            transnet_instance.run()
        logging.info("#################################################")
    except Exception as e:
        root.error(e.message)
        parser.print_help()
        exit()

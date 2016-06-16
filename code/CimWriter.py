
from CIM14.ENTSOE.Equipment.Core import BaseVoltage, GeographicalRegion, SubGeographicalRegion, ConnectivityNode, Terminal
from CIM14.ENTSOE.Equipment.Wires import PowerTransformer, SynchronousMachine, TransformerWinding
from CIM14.ENTSOE.Equipment.LoadModel import LoadResponseCharacteristic
from CIM14.IEC61968.Common import Location, PositionPoint
from CIM14.IEC61970.Core import Substation
from CIM14.IEC61970.Generation.Production import GeneratingUnit
from CIM14.IEC61970.Wires import ACLineSegment, EnergyConsumer

from PyCIM import cimwrite
from LoadEstimator import LoadEstimator

import uuid
from xml.dom.minidom import parse
from string import maketrans
from collections import OrderedDict
from shapely.ops import linemerge
import ogr
import osr
import logging
import re
import io

root = logging.getLogger()


class CimWriter:
    circuits = None
    centroid = None
    population_by_station_dict = ()
    id = 0
    winding_types = ['primary', 'secondary', 'tertiary']

    base_voltages_dict = dict()

    region = SubGeographicalRegion(Region=GeographicalRegion(name='DE'))

    # osm id -> cim uuid
    uuid_by_osmid_dict = dict()
    # cim uuid -> cim object
    cimobject_by_uuid_dict = OrderedDict()
    # cim uuid -> cim connectivity node object
    connectivity_by_uuid_dict = dict()

    def __init__(self, circuits, centroid, population_by_station_dict):
        self.circuits = circuits
        self.centroid = centroid
        self.population_by_station_dict = population_by_station_dict

    def publish(self, file_name):
        self.region.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[self.region.UUID] = self.region

        self.add_location(self.centroid.x, self.centroid.y, is_center=True)

        covered_connections = []
        for circuit in self.circuits:
            station1 = circuit.members[0]
            station2 = circuit.members[len(circuit.members) - 1]
            if str(station1.id) + str(station2.id) + str(circuit.voltage) in covered_connections or str(station2.id) + str(station1.id) + str(circuit.voltage) in covered_connections:
                continue

            if 'station' in station1.type:
                connectivity_node1 = self.substation_to_cim(station1, circuit.voltage)
            elif 'plant' in station1.type or 'generator' in station1.type:
                connectivity_node1 = self.generator_to_cim(station1, circuit.voltage)
            else:
                root.error('Invalid circuit! - Skip circuit')
                circuit.print_circuit()
                continue

            if 'station' in station2.type:
                connectivity_node2 = self.substation_to_cim(station2, circuit.voltage)
            elif 'plant' in station2.type or 'generator' in station2.type:
                connectivity_node2 = self.generator_to_cim(station2, circuit.voltage)
            else:
                root.error('Invalid circuit! - Skip circuit')
                circuit.print_circuit()
                continue

            lines_wsg84 = []
            lines_srs = []
            for line_wsg84 in circuit.members[1:-1]:
                lines_wsg84.append(line_wsg84.geom)
                lines_srs.append(line_wsg84.srs_geom)
            line_wsg84 = linemerge(lines_wsg84)
            line_srs = linemerge(lines_srs)
            root.debug('Map line from (%lf,%lf) to (%lf,%lf) with length %s meters', station1.geom.centroid.y, station1.geom.centroid.x, station2.geom.centroid.y, station2.geom.centroid.x, str(line_srs.length))
            self.line_to_cim(connectivity_node1, connectivity_node2, line_srs.length, circuit.name, circuit.voltage, line_wsg84.centroid.y, line_wsg84.centroid.x)
            covered_connections.append(str(station1.id) + str(station2.id) + str(circuit.voltage))

        self.attach_loads()

        cimwrite(self.cimobject_by_uuid_dict, file_name + '.xml', encoding='utf-8')
        cimwrite(self.cimobject_by_uuid_dict, file_name + '.rdf', encoding='utf-8')

        # pretty print cim file
        xml = parse(file_name + '.xml')
        pretty_xml_as_string = xml.toprettyxml(encoding='utf-8')
        matches = re.findall('#x[0-9a-f]{4}', pretty_xml_as_string)
        for match in matches:
            pretty_xml_as_string = pretty_xml_as_string.replace(match, unichr(int(match[2:len(match)], 16)))
        pretty_file = io.open(file_name + '_pretty.xml', 'w', encoding='utf8')
        pretty_file.write(pretty_xml_as_string)
        pretty_file.close()

    def substation_to_cim(self, osm_substation, circuit_voltage):
        transformer_winding = None
        if self.uuid_by_osmid_dict.has_key(osm_substation.id):
            root.debug('Substation with OSMID %s already covered', str(osm_substation.id))
            cim_substation = self.cimobject_by_uuid_dict[self.uuid_by_osmid_dict[osm_substation.id]]
            transformer = cim_substation.getEquipments()[0] # TODO check if there is actually one equipment
            for winding in transformer.getTransformerWindings():
                if int(circuit_voltage) == winding.ratedU:
                    root.debug('Transformer of Substation with OSMID %s already has winding for voltage %s', str(osm_substation.id), circuit_voltage)
                    transformer_winding = winding
                    break
        else:
            root.debug('Create CIM Substation for OSMID %s', str(osm_substation.id))
            cim_substation = Substation(name='SS_' + str(osm_substation.id), Region=self.region, Location=self.add_location(osm_substation.lat, osm_substation.lon))
            transformer = PowerTransformer(name='T_' + str(osm_substation.id) + '_' + str(osm_substation.voltage) + '_' + CimWriter.escape_string(osm_substation.name), EquipmentContainer=cim_substation)
            cim_substation.UUID = str(self.uuid())
            transformer.UUID = str(self.uuid())
            self.cimobject_by_uuid_dict[cim_substation.UUID] = cim_substation
            self.cimobject_by_uuid_dict[transformer.UUID] = transformer
            self.uuid_by_osmid_dict[osm_substation.id] = cim_substation.UUID
        if transformer_winding is None:
            transformer_winding = self.add_transformer_winding(osm_substation.id, osm_substation.voltage, circuit_voltage, transformer)
        return self.connectivity_by_uuid_dict[transformer_winding.UUID]

    def generator_to_cim(self, generator, circuit_voltage):
        if self.uuid_by_osmid_dict.has_key(generator.id):
            root.debug('Generator with OSMID %s already covered', str(generator.id))
            generating_unit = self.cimobject_by_uuid_dict[self.uuid_by_osmid_dict[generator.id]]
        else:
            root.debug('Create CIM Generator for OSMID %s', str(generator.id))
            generating_unit = GeneratingUnit(name='G_' + str(generator.id), maxOperatingP=generator.nominal_power, minOperatingP=0,
                                             nominalP='' if generator.nominal_power is None else generator.nominal_power, Location=self.add_location(generator.lat, generator.lon))
            synchronous_machine = SynchronousMachine(name='G_' + str(generator.id) + '_' + CimWriter.escape_string(generator.name), operatingMode='generator', qPercent=0, x=0.01,
                                                     r=0.01, ratedS='' if generator.nominal_power is None else generator.nominal_power, type='generator',
                                                     GeneratingUnit=generating_unit, BaseVoltage=self.base_voltage(int(circuit_voltage)))
            generating_unit.UUID = str(self.uuid())
            synchronous_machine.UUID = str(self.uuid())
            self.cimobject_by_uuid_dict[generating_unit.UUID] = generating_unit
            self.cimobject_by_uuid_dict[synchronous_machine.UUID] = synchronous_machine
            self.uuid_by_osmid_dict[generator.id] = generating_unit.UUID
            connectivity_node = ConnectivityNode(name='CN' + str(generator.id))
            connectivity_node.UUID = str(self.uuid())
            self.cimobject_by_uuid_dict[connectivity_node.UUID] = connectivity_node
            terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=synchronous_machine,
                                sequenceNumber=1)
            terminal.UUID = str(self.uuid())
            self.cimobject_by_uuid_dict[terminal.UUID] = terminal
            self.connectivity_by_uuid_dict[generating_unit.UUID] = connectivity_node
        return self.connectivity_by_uuid_dict[generating_unit.UUID]

    def line_to_cim(self, connectivity_node1, connectivity_node2, length, name, circuit_voltage, lat, lon):
        line = ACLineSegment(name=CimWriter.escape_string(name) + '_' + connectivity_node1.name + '_' + connectivity_node2.name, bch=0, r=0.3257, x=0.3153, r0=0.5336,
                             x0=0.88025, length=length, BaseVoltage=self.base_voltage(int(circuit_voltage)), Location=self.add_location(lat, lon))
        line.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[line.UUID] = line
        terminal1 = Terminal(ConnectivityNode=connectivity_node1, ConductingEquipment=line, sequenceNumber=1)
        terminal1.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[terminal1.UUID] = terminal1
        terminal2 = Terminal(ConnectivityNode=connectivity_node2, ConductingEquipment=line, sequenceNumber=2)
        terminal2.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[terminal2.UUID] = terminal2

    def get_winding_type(self, substation_voltage, circuit_voltage, transformer):
        # is substation a winding station (only one voltage level)?
        if ';' not in substation_voltage:
            return self.winding_types[len(transformer.getTransformerWindings())]

        # if substation has more voltage levels
        i = 0
        for station_voltage in substation_voltage.split(';'):
            if station_voltage == circuit_voltage:
                return self.winding_types[i]
            i += 1
        return None

    def uuid(self):
        return uuid.uuid1()

    def add_transformer_winding(self, osm_substation_id, osm_substation_voltage, winding_voltage, transformer):
        transformer_winding = TransformerWinding(name='TW_' + str(osm_substation_id) + '_' + str(winding_voltage),
                                                 b=0, x=1.0, r=1.0, connectionType='Yn',
                                                 windingType=self.get_winding_type(osm_substation_voltage, winding_voltage, transformer),
                                                 ratedU=int(winding_voltage), ratedS=5000000,
                                                 PowerTransformer=transformer,
                                                 BaseVoltage=self.base_voltage(int(winding_voltage)))
        transformer_winding.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[transformer_winding.UUID] = transformer_winding
        connectivity_node = ConnectivityNode(name='CN_' + str(osm_substation_id) + '_' + winding_voltage)
        connectivity_node.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[connectivity_node.UUID] = connectivity_node
        terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=transformer_winding,
                            sequenceNumber=1)
        terminal.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[terminal.UUID] = terminal
        self.connectivity_by_uuid_dict[transformer_winding.UUID] = connectivity_node
        return transformer_winding

    def attach_loads(self):
        for object in self.cimobject_by_uuid_dict.values():
            if isinstance(object, PowerTransformer):
                transformer = object
                osm_substation_id = transformer.name.split('_')[1]
                transformer_voltage = transformer.name.split('_')[2]
                transformer_voltage_levels = transformer_voltage.split(';')
                if len(transformer_voltage_levels) >= 2 and int(transformer_voltage_levels[1]) > 0:
                    transformer_lower_voltage = transformer_voltage_levels[1]
                else:
                    transformer_lower_voltage = transformer_voltage_levels[0]
                self.attach_load(osm_substation_id, transformer_voltage, transformer_lower_voltage, transformer)

    def attach_load(self, osm_substation_id, transformer_voltage, winding_voltage, transformer):
        transformer_winding = None
        winding_voltages = []
        for winding in transformer.getTransformerWindings():
            winding_voltages.append(str(winding.ratedU))
            if int(winding_voltage) == winding.ratedU:
                transformer_winding = winding
        # add winding for lower voltage, if not already existing or
        # add winding if substaion is a switching station (only one voltage level)
        if transformer_winding is None or len(transformer_voltage.split(';')) == 1:
            transformer_winding = self.add_transformer_winding(osm_substation_id, transformer_voltage, winding_voltage, transformer)
        connectivity_node = self.connectivity_by_uuid_dict[transformer_winding.UUID]
        estimated_load = LoadEstimator.estimate_load(self.population_by_station_dict[str(osm_substation_id)]) if self.population_by_station_dict is not None else 100000
        load_response_characteristic = LoadResponseCharacteristic(exponentModel=False, pConstantPower=estimated_load)
        load_response_characteristic.UUID = str(self.uuid())
        energy_consumer = EnergyConsumer(name='L_' + osm_substation_id, LoadResponse=load_response_characteristic, BaseVoltage=self.base_voltage(int(winding_voltage)))
        energy_consumer.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[load_response_characteristic.UUID] = load_response_characteristic
        self.cimobject_by_uuid_dict[energy_consumer.UUID] = energy_consumer
        terminal = Terminal(ConnectivityNode=connectivity_node, ConductingEquipment=energy_consumer,
                            sequenceNumber=1)
        terminal.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[terminal.UUID] = terminal

    @staticmethod
    def escape_string(string):
        if string is not None:
            str = unicode(string.translate(maketrans('-]^$/. ', '_______')), 'utf-8')
            hexstr = ''
            for c in str:
                if ord(c) > 127:
                    hexstr += "#x%04x" % ord(c)
                else:
                    hexstr += c
            return hexstr
        return ''

    def add_location(self, lat, lon, is_center=False):
        pp = PositionPoint(yPosition=lat, xPosition=lon)
        if is_center:
            pp.zPosition = 1
        pp.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[pp.UUID] = pp
        location = Location(PositionPoints=[pp])
        location.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[location.UUID] = location
        return location


    @staticmethod
    def convert_mercator_to_wgs84(mercLat, mercLon):
        # Spatial Reference System
        inputEPSG = 3857
        outputEPSG = 4326

        # create a geometry from coordinates
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(mercLon, mercLat)

        # create coordinate transformation
        inSpatialRef = osr.SpatialReference()
        inSpatialRef.ImportFromEPSG(inputEPSG)

        outSpatialRef = osr.SpatialReference()
        outSpatialRef.ImportFromEPSG(outputEPSG)

        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

        # transform point
        point.Transform(coordTransform)

        # return point in EPSG 4326
        return (point.GetY(), point.GetX())

    def base_voltage(self, voltage):
        if self.base_voltages_dict.has_key(voltage):
            return self.base_voltages_dict[voltage];
        base_voltage = BaseVoltage(nominalVoltage=voltage)
        base_voltage.UUID = str(self.uuid())
        self.cimobject_by_uuid_dict[base_voltage.UUID] = base_voltage
        self.base_voltages_dict[voltage] = base_voltage
        return base_voltage
#python:

from collections import namedtuple

import numpy as np
from scipy.constants import speed_of_light

import gprMax.input_cmd_funcs as gprmax_cmds

import rflib
from itur import p2040
from itur import p527


Point = namedtuple('Point', ['x', 'y', 'z'])

# ! Simulation model parameters begin

# * Naming parameters
simulation_name = 'Simple concrete pipe in homogeneous soil'
filename_base = 'straight_pipe'

geometry_mode = '2D'
output_geometry = True
output_snapshots = True
snapshots_count = 4

fund_freq = 2.45e9
max_harmonic = 5
runtime_multiplier = 3
pml_cells_number = 20

# * Pipe dimensions and properties, in base units
pipe_material = 'concrete'
pipe_diameter = 225e-3
pipe_wall_thickness = 35e-3
pipe_length = 1.5
pipe_burial_depth = 0.8

# * Soil dimensions and properties, in base units
soil_name = 'sand'
soil_temp = 15.0
soil_water_content = 1e-15
soil_depth = 0.5

air_depth = 0.5

# * Partially filled pipe parameters
include_water = False
fill_level = 0.5  # As a ratio, i.e. 0 - 1

# * Tx and Rx parameters
# * The X, Y, and Z offsets are from the centre points of the end
# * faces of the cylinder representing the pipe. They do not include the PML
# * cells distance in them, this is taken care of later in the script.
tx_power = 10.0
tx_offset = Point(10e-2, 0, 0)
rx_offset = Point(10e-2, 0, 0)

waveform_type = 'contsine'
waveform_identifier = 'tx_1'
dipole_polarisation = 'z'

# ! Simulation model parameters end

# * Frequency-derived parameters
fund_freq_GHz = fund_freq / 1e9
fund_wavelength = speed_of_light / fund_freq

# * Filenames
geometry_filename = '_'.join([filename_base, str(pipe_length), soil_name,
                              str(fund_freq_GHz), 'b', str(pipe_burial_depth),
                              's', str(soil_depth), 'a', str(air_depth),
                              waveform_type])
snapshot_filename = '_'.join([geometry_filename, 'snapshot_'])

# * Pipe material properties
pipe_material_er = p2040.material_permittivity(
    fund_freq_GHz, pipe_material
)
pipe_material_conductivity = p2040.material_conductivity(
    fund_freq_GHz, pipe_material
)

# * Soil properties
soil_constituents = p527.SOILS[soil_name]
soil_complex_er = p527.soil_permittivity(
    fund_freq_GHz,
    soil_temp,
    99.0,
    0.5,
    0.5,
    soil_water_content
)
soil_conductivity = rflib.dielectrics.imaginary_permittivity_to_conductivity(
    fund_freq_GHz, np.abs(soil_complex_er.imag)
)
soil_er = soil_complex_er.real

# * Partially filled pipe preliminary calculations, if used
if include_water:
    sw_complex_er = p527.salt_water_permittivity(fund_freq_GHz, soil_temp)
    sw_conductivity = rflib.dielectrics.imaginary_permittivity_to_conductivity(
        fund_freq_GHz, np.abs(sw_complex_er.imag)
    )
    sw_er = sw_complex_er.real

    fill_depth = pipe_diameter * fill_level
    chord_length = np.sqrt(
        8 * (pipe_diameter / 2) * fill_depth - 4 * np.power(fill_depth, 2)
    )
    central_angle = 2 * np.arcsin(chord_length / pipe_diameter)
    central_angle_deg = np.rad2deg(central_angle)
else:
    fill_depth = 0

# * Some preliminary calculations
if include_water:
    er_max = np.max([pipe_material_er, soil_er, sw_er])
else:
    er_max = np.max([pipe_material_er, soil_er])

lambda_min = speed_of_light / (max_harmonic * fund_freq)
lambda_min_eff = lambda_min / np.sqrt(er_max)

delta_d = lambda_min_eff / 10
round_digits = int(np.ceil(-np.log10(delta_d))) + 1
round_digits = np.power(10, round_digits)
delta_d = np.trunc(delta_d * round_digits) / round_digits

# * PML command
if geometry_mode == '2D':
    pml_command = '{0} {0} 0 {0} {0} 0'.format(pml_cells_number)
elif geometry_mode == '3D':
    pml_command = '{0} {0} {0} {0} {0} {0}'.format(pml_cells_number)

# * Model geometry
pml_x = pml_cells_number * delta_d
pml_y = pml_cells_number * delta_d
if geometry_mode == '2D':
    pml_z = 0
elif geometry_mode == '3D':
    pml_z = pml_cells_number * delta_d

model_x = pipe_length
model_y = pipe_diameter + 2 * pipe_wall_thickness + soil_depth + \
          pipe_burial_depth + air_depth
if geometry_mode == '2D':
    model_z = delta_d
elif geometry_mode == '3D':
    model_z = pipe_diameter + 2 * pipe_wall_thickness + 2 * soil_depth

domain_x = model_x + 2 * pml_x
domain_y = model_y + 2 * pml_y
domain_z = model_z + 2 * pml_z

longest_dimension = np.max([domain_x, domain_y, domain_z])
simulation_runtime = runtime_multiplier * (longest_dimension / speed_of_light)

if geometry_mode == '2D':
    pipe_start = Point(
        0,
        pml_y + soil_depth + pipe_wall_thickness + pipe_diameter / 2,
        0
    )
    pipe_end = Point(
        domain_x,
        pml_y + soil_depth + pipe_wall_thickness + pipe_diameter / 2,
        0
    )
elif geometry_mode == '3D':
    pipe_start = Point(
        0,
        pml_y + soil_depth + pipe_wall_thickness + pipe_diameter / 2,
        domain_z / 2
    )
    pipe_end = Point(
        domain_x,
        pml_y + soil_depth + pipe_wall_thickness + pipe_diameter / 2,
        domain_z / 2
    )

# * Calculate Hertzian dipole current from required power
waveform_amplitude = rflib.antennas.hertzian_dipole_current(
    fund_freq_GHz, tx_power, delta_d
)

transmitter_position = Point(
    pipe_start.x + (pml_x + tx_offset.x),
    pipe_start.y + tx_offset.y + fill_depth / 2.0,
    pipe_start.z + tx_offset.z
)

receiver_position = Point(
    pipe_end.x - (pml_x + rx_offset.x),
    pipe_end.y + rx_offset.y,
    pipe_end.z + rx_offset.z
)

observer_rx_1 = Point(
    transmitter_position.x,
    domain_y - (pml_y + air_depth / 2),
    transmitter_position.z
)

observer_rx_2 = Point(
    receiver_position.x,
    domain_y - (pml_y + air_depth / 2),
    receiver_position.z
)

# * gprMax simulation setup
gprmax_cmds.command('title', simulation_name)
gprmax_cmds.command('pml_cells', pml_command)

gprmax_cmds.domain(x=domain_x, y=domain_y, z=domain_z)

gprmax_cmds.dx_dy_dz(delta_d, delta_d, delta_d)

gprmax_cmds.time_window(simulation_runtime)

gprmax_cmds.material(permittivity=pipe_material_er,
                     conductivity=pipe_material_conductivity,
                     permeability=1,
                     magconductivity=0,
                     name='pipe_material')

gprmax_cmds.material(permittivity=soil_er,
                     conductivity=soil_conductivity,
                     permeability=1,
                     magconductivity=0,
                     name='soil_material')

if include_water:
    gprmax_cmds.material(permittivity=sw_er,
                         conductivity=sw_conductivity,
                         permeability=1,
                         magconductivity=0,
                         name='water_fill')

soil = gprmax_cmds.box(0, 0, 0,
                       domain_x, domain_y, domain_z,
                       'soil_material',
                       'y')

pipe_shell = gprmax_cmds.cylinder(pipe_start.x, pipe_start.y, pipe_start.z,
                                  pipe_end.x, pipe_end.y, pipe_end.z,
                                  pipe_diameter / 2 + pipe_wall_thickness,
                                  'pipe_material',
                                  'y')

pipe_inside = gprmax_cmds.cylinder(pipe_start.x, pipe_start.y, pipe_start.z,
                                   pipe_end.x, pipe_end.y, pipe_end.z,
                                   pipe_diameter / 2,
                                   'free_space',
                                   'y')

if include_water and geometry_mode == '2D':
    pipe_water_fill = gprmax_cmds.box(
        pipe_start.x,
        pipe_start.y - pipe_diameter / 2,
        0,
        pipe_end.x,
        pipe_end.y - pipe_diameter / 2 + fill_depth,
        delta_d,
        'water_fill',
        'y'
    )

if include_water and geometry_mode == '3D':
    gprmax_cmds.cylindrical_sector(
        'x',
        pipe_start.y, pipe_start.z,
        pipe_start.x, pipe_end.x,
        pipe_diameter / 2,
        180 - central_angle_deg / 2, central_angle_deg,
        'water_fill',
        'y'
    )

    pipe_refill_air = gprmax_cmds.triangle(
        pipe_start.x, pipe_start.y, pipe_start.z,
        pipe_start.x,
        pipe_start.y - pipe_diameter / 2 * np.cos(central_angle / 2),
        pipe_start.z - pipe_diameter / 2 * np.sin(central_angle / 2),
        pipe_start.x,
        pipe_start.y - pipe_diameter / 2 * np.cos(central_angle / 2),
        pipe_start.z + pipe_diameter / 2 * np.sin(central_angle / 2),
        domain_x,
        'free_space',
        'y'
    )

air_above = gprmax_cmds.box(0, domain_y - (pml_y + air_depth), 0,
                            domain_x, domain_y, domain_z,
                            'free_space',
                            'y')

pulse_excitation = gprmax_cmds.waveform(waveform_type,
                                        amplitude=waveform_amplitude,
                                        frequency=fund_freq,
                                        identifier=waveform_identifier)

transmitter = gprmax_cmds.hertzian_dipole(dipole_polarisation,
                                          transmitter_position.x,
                                          transmitter_position.y,
                                          transmitter_position.z,
                                          pulse_excitation)

receiver = gprmax_cmds.rx(receiver_position.x,
                          receiver_position.y,
                          receiver_position.z)

obsv_rx_1 = gprmax_cmds.rx(observer_rx_1.x,
                           observer_rx_1.y,
                           observer_rx_1.z)

obsv_rx_2 = gprmax_cmds.rx(observer_rx_2.x,
                           observer_rx_2.y,
                           observer_rx_2.z)

if output_geometry:
    gprmax_cmds.geometry_view(
        0,
        0,
#        pipe_start.y - (pipe_diameter / 2 + pipe_wall_thickness + 0.25),
        0,
        domain_x,
        domain_y,
#        pipe_start.y + (pipe_diameter / 2 + pipe_wall_thickness + 0.25),
        domain_z,
        delta_d, delta_d, delta_d,
        geometry_filename, 'n'
    )

if output_snapshots:
    for number in range(snapshots_count):
        gprmax_cmds.snapshot(
            0,
            0,
#            pipe_start.y - (pipe_diameter / 2 + pipe_wall_thickness + 0.25),
            0,
            domain_x,
            domain_y,
#            pipe_start.y + (pipe_diameter / 2 + pipe_wall_thickness + 0.25),
            domain_z,
            delta_d, delta_d, delta_d,
            ((number + 1) * (simulation_runtime / snapshots_count)),
            snapshot_filename + str(number)
        )

#end_python:

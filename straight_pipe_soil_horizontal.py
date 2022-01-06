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
output_snapshots = False
snapshots_count = 16

fund_freq = 2.45e9
max_harmonic = 5
runtime_multiplier = 3
pml_cells_number = 20

# * Pipe dimensions and properties, in base units
pipe_material = 'concrete'
pipe_diameter = 100e-3
pipe_wall_thickness = 60e-3
pipe_length = 2.70

# * Soil dimensions and properties, in base units
soil_name = 'sandy_clay_loam'
soil_temp = 10.0
soil_water_content = 0.9
soil_width = 1.0

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
                              str(fund_freq_GHz), waveform_type])
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
    soil_constituents.p_sand,
    soil_constituents.p_clay,
    soil_constituents.p_silt,
    soil_water_content
)
soil_conductivity = rflib.dielectrics.imaginary_permittivity_to_conductivity(
    fund_freq_GHz, np.abs(soil_complex_er.imag)
)
soil_er = soil_complex_er.real

# * Some preliminary calculations
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
model_y = pipe_diameter + 2 * pipe_wall_thickness + 2 * soil_width
if geometry_mode == '2D':
    model_z = delta_d
elif geometry_mode == '3D':
    model_z = pipe_diameter + 2 * pipe_wall_thickness + 2 * soil_width

domain_x = model_x + 2 * pml_x
domain_y = model_y + 2 * pml_y
domain_z = model_z + 2 * pml_z

longest_dimension = np.max([domain_x, domain_y, domain_z])
simulation_runtime = runtime_multiplier * (longest_dimension / speed_of_light)

if geometry_mode == '2D':
    pipe_start = Point(
        0, domain_y / 2, 0
    )
    pipe_end = Point(
        domain_x, domain_y / 2, 0
    )
elif geometry_mode == '3D':
    pipe_start = Point(
        0, domain_y / 2, domain_z / 2
    )
    pipe_end = Point(
        domain_x, domain_y / 2, domain_z / 2
    )

# * Calculate Hertzian dipole current from required power
waveform_amplitude = rflib.antennas.hertzian_dipole_current(
    fund_freq_GHz, tx_power, delta_d
)

transmitter_position = Point(
    pipe_start.x + (pml_x + tx_offset.x),
    pipe_start.y + tx_offset.y,
    pipe_start.z + tx_offset.z
)

receiver_position = Point(
    pipe_end.x - (pml_x + rx_offset.x),
    pipe_end.y + rx_offset.y,
    pipe_end.z + rx_offset.z
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

if output_geometry:
    gprmax_cmds.geometry_view(0, 0, 0,
                              domain_x, domain_y, domain_z,
                              delta_d, delta_d, delta_d,
                              geometry_filename, 'n')

if output_snapshots:
    for number in range(snapshots_count):
        gprmax_cmds.snapshot(0, 0, 0,
                             domain_x, domain_y, domain_z,
                             delta_d, delta_d, delta_d,
                             ((number + 1) *
                              (simulation_runtime / snapshots_count)),
                             snapshot_filename + str(number))

#end_python:

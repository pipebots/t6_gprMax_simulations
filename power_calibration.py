#python:

from collections import namedtuple

import numpy as np
from scipy.constants import speed_of_light

import gprMax.input_cmd_funcs as gprmax_cmds

import aux_funcs


Point = namedtuple('Point', ['x', 'y', 'z'])

# ! Simulation model parameters begin

# * Naming parameters
simulation_name = 'Antenna in free space'
geometry_filename = 'power_calibration_2.45ghz'
snapshot_filename = '_'.join([geometry_filename, 'snapshot'])

geometry_mode = '2D'

output_snapshots = True
snapshots_count = 64

fund_freq = 2.45e9
max_harmonic = 5
runtime_multiplier = 1.25
pml_cells_number = 20

# * Tx and Rx parameters
# * The X, Y, and Z offsets are from the middle points of the side
# * surfaces of the simulation domain. They do not include the PML
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

# * Some preliminary calculations
lambda_min = speed_of_light / (max_harmonic * fund_freq)
delta_d = lambda_min / 10

# ! Copied this from SO, to round down `delta_d` to a reasonable width
round_digits = int(np.ceil(-np.log10(delta_d))) + 1
round_digits = np.power(10, round_digits)

delta_d = np.trunc(delta_d * round_digits) / round_digits

# * PML command
if geometry_mode == '2D':
    pml_command = '{0} {0} 0 {0} {0} 0'.format(pml_cells_number)
elif geometry_mode == '3D':
    pml_command = '{0} {0} {0} {0} {0} {0}'.format(pml_cells_number)

# * Model geometry
far_field_distance = aux_funcs.far_field_distance(
    fund_freq_GHz, delta_d, 'hertzian'
)

pml_x = pml_cells_number * delta_d
pml_y = pml_cells_number * delta_d
if geometry_mode == '2D':
    pml_z = 0
elif geometry_mode == '3D':
    pml_z = pml_cells_number * delta_d

model_x = 3  # 5 * far_field_distance
model_y = 3  # 5 * far_field_distance
if geometry_mode == '2D':
    model_z = delta_d
elif geometry_mode == '3D':
    model_z = 1  # 2 * far_field_distance

domain_x = model_x + 2 * pml_x
domain_y = model_y + 2 * pml_y
domain_z = model_z + 2 * pml_z

longest_dimension = np.max([domain_x, domain_y, domain_z])
simulation_runtime = runtime_multiplier * (longest_dimension / speed_of_light)

# * Calculate Hertzian dipole current from required power
waveform_amplitude = aux_funcs.hertzian_dipole_current(
    fund_freq_GHz, tx_power, delta_d
)

if geometry_mode == '2D':
    transmitter_position = Point(
        0 + (pml_x + tx_offset.x),
        domain_y / 2 + tx_offset.y,
        0 + tx_offset.z
    )

    receiver_position = Point(
        domain_x - (pml_x + rx_offset.x),
        domain_y / 2 + rx_offset.y,
        0 + rx_offset.z
    )
elif geometry_mode == '3D':
    transmitter_position = Point(
        0 + (pml_x + tx_offset.x),
        domain_y / 2 + tx_offset.y,
        domain_z / 2 + tx_offset.z
    )

    receiver_position = Point(
        domain_x - (pml_x + rx_offset.x),
        domain_y / 2 + rx_offset.y,
        domain_z / 2 + rx_offset.z
    )

# * gprMax simulation setup
gprmax_cmds.command('title', simulation_name)
gprmax_cmds.command('pml_cells', pml_command)

gprmax_cmds.domain(x=domain_x, y=domain_y, z=domain_z)

gprmax_cmds.dx_dy_dz(delta_d, delta_d, delta_d)

gprmax_cmds.time_window(simulation_runtime)

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

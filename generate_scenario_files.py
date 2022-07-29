from collections import namedtuple
from itertools import product
from pathlib import Path

import yaml
import numpy as np
from scipy.constants import speed_of_light
from jinja2 import Environment, FileSystemLoader, StrictUndefined

import rflib
from itur import p2040
from itur import p527


Point = namedtuple('Point', ['x', 'y', 'z'])

# ! Read in lists of values for which to generate gprMax input files
parameters_values_filename = "scenarios_empty_pipe.yml"

with open(parameters_values_filename, "r") as input_file:
    all_params_values = yaml.safe_load(input_file)

all_params_values = product(*all_params_values.values())

# ! gprMax input file template and corresponding settings
jinja2_env = Environment(
    loader=FileSystemLoader('./'), undefined=StrictUndefined,
    trim_blocks=True, lstrip_blocks=True,
)

jinja2_template = jinja2_env.get_template('straight_pipe_soil_vertical.j2')

output_folder_name = "scenarios_empty"

# ! Simulation model parameters - constant across all scenarios

# * Naming parameters
simulation_name = 'Simple concrete pipe in homogeneous soil'
filename_base = 'straight_pipe'

geometry_mode = '2D'
output_geometry = True
output_snapshots = True
snapshots_count = 4

max_harmonic = 5
runtime_multiplier = 3
pml_cells_number = 20

# * Pipe dimensions and properties, in base units
pipe_material = 'concrete'
pipe_wall_thickness = 35e-3

# * Soil and air dimensions and properties, in base units
air_depth = 0.5
soil_temp = 15.0
soil_depth = 0.5

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

# * Set up output folder
output_folder = Path.cwd() / output_folder_name
output_folder.mkdir(exist_ok=True)

for params in all_params_values:
    (fund_freq, pipe_diameter, pipe_length,
     pipe_burial_depth, soil_name,
     soil_water_content) = params

    # * Frequency-derived parameters
    fund_freq_GHz = fund_freq / 1e9
    fund_wavelength = speed_of_light / fund_freq

    # * Filenames
    geometry_filename = '_'.join([
        filename_base, str(fund_freq_GHz), str(pipe_diameter),
        str(pipe_length), str(pipe_burial_depth), soil_name,
        str(soil_water_content)
    ])
    snapshot_filename = '_'.join([geometry_filename, 'snapshot'])
    simulation_filename = ".".join([geometry_filename, 'py'])

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
    soil_cond = rflib.dielectrics.imaginary_permittivity_to_conductivity(
        fund_freq_GHz, np.abs(soil_complex_er.imag)
    )
    soil_er = np.real(soil_complex_er)

    # * Partially filled pipe preliminary calculations, if used
    if include_water:
        sw_complex_er = p527.salt_water_permittivity(fund_freq_GHz, soil_temp)
        sw_cond = rflib.dielectrics.imaginary_permittivity_to_conductivity(
            fund_freq_GHz, np.abs(sw_complex_er.imag)
        )
        sw_er = np.real(sw_complex_er)

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
    model_y = (
        pipe_diameter + 2 * pipe_wall_thickness + soil_depth +
        pipe_burial_depth + air_depth
    )
    if geometry_mode == '2D':
        model_z = delta_d
    elif geometry_mode == '3D':
        model_z = pipe_diameter + 2 * pipe_wall_thickness + 2 * soil_depth

    domain_x = model_x + 2 * pml_x
    domain_y = model_y + 2 * pml_y
    domain_z = model_z + 2 * pml_z

    longest_dimension = np.max([domain_x, domain_y, domain_z])
    simulation_runtime = (
        runtime_multiplier * (longest_dimension / speed_of_light)
    )

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
#    waveform_amplitude = rflib.antennas.hertzian_dipole_current(
#        fund_freq_GHz, tx_power, delta_d
#    )

    # ! Use a fixed amplitude of 1 for all simulations
    waveform_amplitude = 1.0

    transmitter_position = Point(
        pipe_start.x + (pml_x + tx_offset.x),
        pipe_start.y + tx_offset.y + fill_depth / 2.0,
        pipe_start.z + tx_offset.z
    )

    receiver_position = Point(
        pipe_end.x - (pml_x + rx_offset.x),
        pipe_end.y + rx_offset.y + fill_depth / 2.0,
        pipe_end.z + rx_offset.z
    )

    observer_rx_1 = Point(
        transmitter_position.x +
        ((receiver_position.x - transmitter_position.x) / 3.0),
        receiver_position.y,
        receiver_position.z
    )

    observer_rx_2 = Point(
        transmitter_position.x +
        2 * ((receiver_position.x - transmitter_position.x) / 3.0),
        receiver_position.y,
        receiver_position.z
    )

    sim_params = {
        'simulation_name': simulation_name,
        'simulation_runtime': simulation_runtime,
        'geometry_filename': geometry_filename,
        'snapshots_count': snapshots_count,
        'snapshot_filename': snapshot_filename,

        'include_water': include_water,
        'output_snapshots': output_snapshots,
        'output_geometry': output_geometry,
        'geometry_mode': geometry_mode,

        'pml_command': pml_command,
        'pml_y': pml_y,

        'domain_x': domain_x,
        'domain_y': domain_y,
        'domain_z': domain_z,

        'delta_d': delta_d,

        'pipe_material_er': pipe_material_er,
        'pipe_material_conductivity': pipe_material_conductivity,
        'soil_er': soil_er,
        'soil_conductivity': soil_cond,

        'pipe_start': pipe_start._asdict(),
        'pipe_end': pipe_end._asdict(),
        'pipe_diameter': pipe_diameter,
        'pipe_wall_thickness': pipe_wall_thickness,

        'air_depth': air_depth,

        'waveform_type': waveform_type,
        'waveform_amplitude': waveform_amplitude,
        'waveform_identifier': waveform_identifier,

        'fund_freq': fund_freq,
        'dipole_polarisation': dipole_polarisation,

        'transmitter_position': transmitter_position._asdict(),
        'receiver_position': receiver_position._asdict(),
        'observer_rx_1': observer_rx_1._asdict(),
        'observer_rx_2': observer_rx_2._asdict()
    }

    if include_water:
        sim_params.update(
            {
                'sw_er': sw_er,
                'sw_conductivity': sw_cond,
                'fill_depth': fill_depth,
                'central_angle_deg': central_angle_deg,
                'central_angle': central_angle,
            }
        )

    template_output = jinja2_template.render(params=sim_params)

    simulation_file = output_folder / simulation_filename

    with simulation_file.open(mode='w') as out_file:
        out_file.write(template_output)

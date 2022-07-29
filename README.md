```
 __________.__             ___.     |__|  __
 \______   \__|_____   ____\_ |__   _||__/  |_  ______ (C) George Jackson-Mills 2020
  |     ___/  \____ \_/ __ \| __ \ /  _ \   __\/  ___/
  |    |   |  |  |_> >  ___/| \_\ (  O_O )  |  \___ \
  |____|   |__|   __/ \___  >___  /\____/|__| /____  >
              |__|        \/    \/                 \/
```

# gprMax simulations of sewer pipes

## Overview

[gprMax](http://www.gprmax.com/about.shtml) is an electromagnetic simulator working in the time domain. Originally developed for ground-penetrating radar (GPR) applications, it excels at simulating interactions of electromagnetic waves with soils and other dielectrics.

This makes it great for qualitatively investigating how radio waves would propagate inside buried sewer pipes. Since gprMax supports Python scripting, it is straightforward to automate the simulation of the effect of multiple parameters.

The only downside is that 3D simulations require too much RAM, on the order of 100s of GBs. However, using 2D cross-sections instead is sufficiently good and representative of the 3D case.

## Simulation workflow

The standard gprMax workflow is to provide an input file, which defines the geometry, materials, excitations, and receivers, which are to be simulated. Depending on what is specified in this input file, the simulator can output snapshots in time of the electromagnetic wave, the geometry setup that is being simulated, as well as the x, y, and z components of the electric and magnetic fields at certain points.

The input file itself can be a Python file with all sorts of preliminary calculations, such as pipe length, electromagnetic properties of a particular soil, and so on. In this case, the main input file is `straight_pipe_soil_vertical.py`. This can be used for individual simulations, where you manually change certain parameters and run gprMax.

The step up from this is the combination of `straight_pipe_soil_vertical.j2`, `scenarios_empty_pipe.yml`, `generate_scenario_files.py`, and `run_scenarios.py`. The logic here is to generate lots of input files, where only a single parameter is changed. The parameters to change, and their respective values, are specified in `scenarios_empty_pipe.yml`. This is used by `generate_scenario_files.py` together with the Jinja2 template `straight_pipe_soil_vertical.j2`. Once the input files are all ready, `run_scenarios.py` goes through them one at a time and invokes the gprMax simulator.

Please bear in mind that some of the scenarios, particularly those for 5.8 GHz, can easily generate 100s of GBs of output data.

There is also the `pipe_to_above_ground.py` input file, which is used to look at electromagnetic wave propagation from inside the pipe, through the soil, and to a receiver above ground.

## Requirements and Installation

The gprMax project comes with its own `conda` environment file, along with extensive [installation instructions](http://docs.gprmax.com/en/latest/include_readme.html#installation).

Asides from that, the scenario files use the `rflib` and `itur` packages, developed as part of Theme 6's work on Pipebots. These are available [here](https://github.com/pipebots/t6_rflib) and [here](https://github.com/pipebots/t6_itur).

## Contributing

Contributions are more than welcome and are in fact actively sought! Please contact Viktor at [v.doychinov@bradford.ac.uk](mailto:v.doychinov@bradford.ac.uk).

## Acknowledgements

This work is supported by the UK's Engineering and Physical Sciences Research Council (EPSRC) Programme Grant EP/S016813/1

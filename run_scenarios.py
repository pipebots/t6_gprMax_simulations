import time
import datetime
import logging
from pathlib import Path

import gprMax
from gprMax.exceptions import GeneralError


def setup_logger(filename_base: str, timestamp: str) -> logging.Logger:
    """Sets up a `Logger` object for diagnostic and debug

    A standard function to set up and configure a Python `Logger` object
    for recording diagnostic and debug data.

    Args:
        filename_base: A `str` containing a user-supplied filename to better
                      identify the logs.
        timestamp: A `str` with the date and time the logger was started
                   to differentiate between different runs

    Returns:
        A `Logger` object with appropriate configurations. All the messages
        are duplicated to the command prompt as well.

    Raises:
        Nothing
    """
    log_filename = "_".join([timestamp, filename_base])
    log_filename = ".".join([log_filename, "log"])

    logger = logging.getLogger(filename_base)

    logger_handler = logging.FileHandler(log_filename)
    logger_handler.setLevel(logging.DEBUG)

    fmt_string = "{asctime:s} {msecs:.3f} \t {levelname:^10s} \t {message:s}"
    datefmt_string = "%Y-%m-%d %H:%M:%S"
    logger_formatter = logging.Formatter(
        fmt=fmt_string, datefmt=datefmt_string, style="{"
    )

    # * This is to ensure consistent formatting of the miliseconds field
    logger_formatter.converter = time.gmtime

    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)

    # * This enables the streaming of messages to stdout
    logging.basicConfig(
        format=fmt_string,
        datefmt=datefmt_string,
        style="{",
        level=logging.DEBUG,
    )
    logger.info("Logger configuration done")

    return logger


global_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
gprmax_logger = setup_logger("gprMax_scenario_runner", global_timestamp)
gprmax_logger.info("Starting gprMax simulations")

# ! Modify this if individual simulation files are elsewhere
scenarios_folder = Path.cwd() / 'scenarios_empty'

gprmax_logger.info("Processing %s", scenarios_folder)

scenarios_files = list(scenarios_folder.glob("*.py"))

gprmax_logger.info("Found %d files", len(scenarios_files))

for scenario_file in scenarios_files:
    try:
        gprmax_logger.info("Running %s", scenario_file)
        gprMax.gprMax.api(str(scenario_file), write_processed=True)
    except GeneralError as e:
        gprmax_logger.exception("gprMax error during simulation")
    else:
        gprmax_logger.info("Simulation completed successfully")

gprmax_logger.info("All files processed")

logging.shutdown()

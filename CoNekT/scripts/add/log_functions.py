import argparse
import logging
import os
import sys


def setup_logger(log_dir="logs_populate", base_filename="default", DBverbose=False, PYverbose=True, overwrite_logs=True):
    """
    Sets up the application's logging system with support for both file and console output.

    Creates a logger with separate handlers for info and error messages, writing them to 
    distinct files and displaying them in the console. Also allows enabling or disabling 
    SQLAlchemy engine log propagation.

    :param log_dir: Directory where the log files will be saved (default: "logs_populate")
    :param base_filename: Base name for the generated log files (default: "functional data")
    :param DBverbose: If True, enables SQLAlchemy engine logs to propagate to the console (default: False)
    :return: Configured logger object
    """

    # Set SQLAlchemy logger level
    sqla_logger = logging.getLogger('sqlalchemy.engine')
    sqla_logger.setLevel(logging.INFO)
    sqla_logger.propagate = DBverbose 

    #creates log dir
    os.makedirs(log_dir, exist_ok=True)

    # defines openning type for log files
    openFileMode = 'w' if overwrite_logs else 'a'

    logger = logging.getLogger()
    level = logging.DEBUG if PYverbose else logging.INFO
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    log_file_base = os.path.join(log_dir, base_filename)
    stdout_log_path = f"{log_file_base}.o.log"
    stderr_log_path = f"{log_file_base}.e.log"

    # File handlers
    file_info_handler = logging.FileHandler(stdout_log_path, mode=openFileMode, encoding='utf-8')
    file_info_handler.setLevel(level)
    file_info_handler.setFormatter(formatter)

    file_error_handler = logging.FileHandler(stderr_log_path, mode=openFileMode, encoding='utf-8')
    file_error_handler.setLevel(logging.ERROR)
    file_error_handler.setFormatter(formatter)

    # Handlers para console
    console_info_handler = logging.StreamHandler(sys.stdout)
    console_info_handler.setLevel(level)
    console_info_handler.setFormatter(formatter)

    console_error_handler = logging.StreamHandler(sys.stderr)
    console_error_handler.setLevel(logging.ERROR)
    console_error_handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(file_info_handler)
        logger.addHandler(file_error_handler)
        logger.addHandler(console_info_handler)
        logger.addHandler(console_error_handler)

    return logger


def print_log_error(logger, message):
    """
    Logs an error message and a follow-up instruction to abort the operation.
    :param message: Error message to log
    """
    logger.error(f'❌ {message}')
    logger.error("OPERATION ABORTED. Fix the issue and run the script again.")


def str2bool(v):
    """
    Converts a string or value to a boolean.
    :param v: The input value to convert to boolean
    :return: Boolean value (True or False)
    """
    if isinstance(v, bool):
        return v
    val = str(v).strip().lower()
    if val in ('yes', 'true', 't', '1'):
        return True
    elif val in ('no', 'false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError(f'Boolean value expected, got "{v}"')

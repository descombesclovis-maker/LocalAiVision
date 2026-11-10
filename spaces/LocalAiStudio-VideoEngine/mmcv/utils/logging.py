import logging as _logging

logger_initialized = {}


def get_logger(name, log_file=None, log_level=_logging.INFO, file_mode="w"):
    logger = _logging.getLogger(name)
    if name in logger_initialized:
        return logger
    logger_initialized[name] = True
    return logger

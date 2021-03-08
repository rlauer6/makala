import boto3
import logging
import os
import json

logging.basicConfig()
logger = logging.getLogger()

LOG_HANDLER = logger.handlers[0]
LOG_HANDLER.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s:%(name)s:%(message)s", "%Y-%m-%d %H:%M:%S"))

if "LOG_LEVEL" in os.environ:
    log_level = os.environ["LOG_LEVEL"].upper()
    if log_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif log_level == "INFO":
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
else:
    logger.setLevel(logging.INFO)


def handler(event, context):
  logger.debug(json.dumps(event))

  logger.info("version: [{}]".format(os.environ.get("VERSION")))

  return True

#!/bin/env python
"""makala
"""

import argparse
import json
import os
import glob
import sys
import time

from datetime import datetime

import pkg_resources

import yaml
import logging

from jinja2 import Environment, FileSystemLoader

import makala.aws.utils as aws
from makala import MakalaConfig
from makala import LambdaConfig

def main():
    """makala - a Makefile based serverless framework for AWS Lambdas
    """

    logging.basicConfig()
    logger = logging.getLogger()

    if "LOG_LEVEL" in os.environ:
        if os.environ["LOG_LEVEL"] == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif os.environ["LOG_LEVEL"] == "INFO":
            logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    if os.path.exists('makala.cfg'):
        logger.info("using local makala.cfg for defaults")
        config_path = "makala.cfg"
    else:
        config_path = pkg_resources.resource_filename("makala", 'data/makala.cfg')

    makala_config = MakalaConfig(path=config_path)

    parser = argparse.ArgumentParser(description='A Makefile based serverless framework',
                                     allow_abbrev=True)
    parser.add_argument("lambda_name", type=str, help="name of the lambda function")
    parser.add_argument("-c", "--config", dest="config_file", type=str,
                        help="Configuration filename. default={lambda-name}.yaml")
    parser.add_argument('-o', '--overwrite',
                        dest="overwrite",
                        action="store_true", help="replace existing Makefile if it exists")

    parser.add_argument('-g', '--generate-config',
                        dest="generate",
                        action="store_true", help="generate a stub configuration file")

    args = parser.parse_args()
    lambda_name = args.lambda_name

    if args.generate:
        config_name = "{}.yaml".format(lambda_name)
        if os.path.exists(config_name) and not args.overwrite:
            logger.error("{} exists. Use -o (overwrite) option.".format(config_name))
            sys.exit(-1)

        lambda_config = LambdaConfig(lambda_name=lambda_name, makala_config=makala_config)
        with open(config_name, "w") as f:
            f.write(lambda_config.generate_stub())
        sys.exit(0)

    if os.path.exists("Makefile") and not args.overwrite:
        logger.error("Makefile exists. Use --overwrite.")
        sys.exit(-1)

    try:
        path = args.config_file or "{}.yaml".format(lambda_name)
        lambda_config = LambdaConfig(path=path,
                                     lambda_name=lambda_name,
                                     makala_config=makala_config)
    except Exception as e:
        logger.error("{}-{}".format(str(e), "could not read configuration file!"))
        sys.exit(-1)

    valid_config = lambda_config.validate()

    for a in lambda_config.warnings:
        logger.warning(a)
    for a in lambda_config.errors:
        logger.error(a)

    if valid_config:
        lambda_config.save()
    else:
        sys.exit(-1)

    if os.path.exists("Makefile.jinja2"):
        template_name = "Makefile.jinja2"
        tempdate_dir = os.getcwd()
        logger.info("using local Makefile template")
    else:
        template_name = pkg_resources.resource_filename("makala", 'data/Makefile.jinja2')
        template_dir = "/"

    # setup a few variables needed for jinja template
    validated_config = lambda_config.config

    if "vpc" in validated_config:
        logger.info("configuring to connect function to a VPC")
        validated_config["vpc_config"] = '$(VPC_CONFIG)'
        validated_config["vpc_config_option"] = '--vpc-config file://./$(VPC_CONFIG)'
    else:
        validated_config["vpc_config"] = ""
        validated_config["vpc_config_option"] = ""

    validated_config["cache_dir"] = makala_config.cache_dir

    makefile = render_makefile(templat_dir=template_dir, template=template_name, config=validated_config)
    with open("Makefile", "w") as f: # pylint: disable=C0103
        f.write(makefile)


def render_makefile(**kwargs):
    """Render the jinja2 template and create the Makefile.
    """
    file_loader = FileSystemLoader(kwargs.get("template_dir") or "/")
    config = kwargs["config"]

    env = Environment(loader=file_loader)

    template = env.get_template(kwargs["template"])

    package_files = []
    if "packages" in config:
        for p in config["packages"]:
            package_files += get_files(p)

    if len(package_files):
        text = "\\\n    {}".format(" \\\n    ".join(package_files))
        config["package_files"] = text

    for f in ["modules", "packages"]:
        text = ""
        if f in config:
            text_list = config[f]
            text = "\\\n    {}".format(" \\\n    ".join(text_list))

        config[f] = text

    config["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M%p')

    return template.render(config)

def get_files(path):
    all_files = []
    files = glob.iglob('{}/*'.format(path))
    for f in files:
        if os.path.isdir(f):
            all_files = all_files + get_files(f)
        else:
            if not ".pyc" in f:
                all_files.append(f)

    return all_files

def clean_cache(files, lambda_name, cache_dir):
    """Remove files defined in config whenever this script is
    executed. (Not currently called but may have some use in the
    future)

    """
    for file in files:
        if "{}" in file:
            name = file.format(lambda_name)
        else:
            name = file
        name = "{}/{}".format(cache_dir, name)
        if os.path.exists(name):
            os.remove(name)

if __name__ == "__main__":

    main()

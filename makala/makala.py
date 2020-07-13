#!/bin/env python
"""makala
"""

import argparse
import json
import os
import sys
import time

from datetime import datetime

import pkg_resources

import yaml

from jinja2 import Environment, FileSystemLoader

import makala.aws.utils as aws
from makala import MakalaConfig
from makala import LambdaConfig

def main():
    """makala - a Makefile based serverless framework for AWS Lambdas
    """

    makala_config = MakalaConfig(path=config_path)

    parser = argparse.ArgumentParser(description='A Makefile based serverless framework',
                                     allow_abbrev=True)
    parser.add_argument("lambda_name", type=str, help="name of the lambda function")
    parser.add_argument("-c", "--config", dest="config_file", type=str,
                        help="Configuration filename. default={lambda-name}.yaml")
    parser.add_argument('-o', '--overwrite',
                        dest="over_write",
                        action="store_true", help="replace existing Makefile if it exists")

    parser.add_argument('-g', '--generate-config',
                        dest="generate",
                        action="store_true", help="generate a stub configuration file")

    args = parser.parse_args()
    lambda_name = args.lambda_name

    if args.generate:
        print("..tbd...create_config_stub()")
        sys.exit(0)

    if os.path.exists("Makefile") and not args.over_write:
        print("Makefile exists. Use --overwrite.")
        sys.exit(-1)

    try:
        path = args.config_file or "{}.yaml".format(lambda_name)
        lambda_config = LambdaConfig(path=path,
                                     lambda_name=lambda_name,
                                     makala_config=makala_config)
    except Exception as e:
        print(str(e))
        print("ERROR: Could not read configuration file!")
        sys.exit(-1)

    valid_config = lambda_config.validate()

    for a in lambda_config.warnings:
        print("WARNING: {}".format(a))
    for a in lambda_config.errors:
        print("ERROR: {}".format(a))

    if valid_config:
        lambda_config.save()
    else:
        sys.exit(-1)

    if os.path.exists("Makefile.jinja2"):
        template_name = "Makefile.jinja2"
        tempdate_dir = os.getcwd()
    else:
        template_name = pkg_resources.resource_filename("makala", 'data/Makefile.jinja2')
        template_dir = "/"

    # setup a few variables needed for jinja template
    validated_config = lambda_config.config

    if "vpc" in validated_config:
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
    modules_text = ""
    if "modules" in config:
        modules = config["modules"]
        modules_text = "\\\n    {}".format(" \\\n    ".join(modules))

    config["modules"] = modules_text
    config["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M%p')

    return template.render(config)


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

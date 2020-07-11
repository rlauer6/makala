#!/bin/env python
"""makala
"""

import argparse
import json
import os
import sys
import configparser
import copy
import time
from datetime import datetime

import pkg_resources

import yaml

from jinja2 import Environment, FileSystemLoader

import makala.aws.utils as aws


class MakalaConfig(): # pylint: disable=R0902, disable=C0116
    """makal config object
    """
    @property
    def region(self):
        return self._region

    @property
    def memory(self):
        return self._memory

    @property
    def timeout(self):
        return self._timeout

    @property
    def runtime(self):
        return self._runtime

    @property
    def log_retention(self):
        return self._log_retention

    @property
    def cache_dir(self):
        return self._cache_dir

    @property
    def clean_files(self):
        return self._clean_files

    @property
    def create_role(self):
        return self._create_role

    def __init__(self, **kwargs): # pylint: disable=R0912
        name = kwargs.get("name") or "makala.cfg"

        config = configparser.ConfigParser()
        if os.path.exists(name):
            config.read(name)
        else:
            raise Exception("no {} file found.".format(name))

        defaults = config["DEFAULT"]

        self._region = defaults.get("region", "us-east-1")

        self._timeout = defaults.get("timeout", "120")

        self._memory = defaults.get("memory", "128")

        self._runtime = defaults.get("runtime", "python3.6")

        self._log_retention = defaults.get("log_retention", "7")

        self._cache_dir = defaults.get("cache_dir", "cache")

        if defaults.get("create_role"):
            self._create_role = defaults.get("create_role") == "true"
        else:
            self._create_role = True

        self._template = defaults.get("template", "")

        if defaults.get("clean_files"):
            try:
                self._clean_files = json.loads(config["DEFAULT"]["clean_files"])
            except:
                print("WARNING: clean files must be a JSON list.")
                self._clean_files = []
        else:
            self._clean_files = []

        if not os.path.exists(self._cache_dir):
            os.mkdir(self._cache_dir)

config_name = pkg_resources.resource_filename("makala", 'data/makala.cfg')
makala_config = MakalaConfig(name=config_name)

def main():
    """makala - a Makefile based serverless framework for AWS Lambdas
    """

    parser = argparse.ArgumentParser(description='A Makefile based serverless framework',
                                     allow_abbrev=True)
    parser.add_argument("lambda_name", type=str, help="name of the lambda function")
    parser.add_argument("-c", "--config", dest="config_file", type=argparse.FileType('r'),
                        help="Configuration filename. default={lambda-name}.yaml")
    parser.add_argument('-o', '--overwrite',
                        dest="over_write",
                        action="store_true", help="replace existing Makefile if it exists")

    args = parser.parse_args()
    lambda_name = args.lambda_name

    try:
        if args.config_file:
            config = yaml.safe_load(args.config_file)
        else:
            with open("{}.yaml".format(lambda_name), encoding='utf-8') as f: # pylint: disable=C0103
                config = yaml.safe_load(f)
    except FileNotFoundError:
        print("no {}.yaml found!".format(lambda_name))
        sys.exit(-1)

    if os.path.exists("Makefile") and not args.over_write:
        print("Makefile exists. Use --overwrite.")
        sys.exit(-1)

    # whenever we run makala, clean up files
    clean(makala_config.clean_files, lambda_name)

    validated_config = validate_config(config, lambda_name)
    write_lambda_config(validated_config, lambda_name)
    write_vpc_config(validated_config)
    write_env_vars(validated_config)

    template_name = pkg_resources.resource_filename("makala", 'data/Makefile.jinja2')
    if "vpc" in validated_config:
        validated_config["vpc_config"] = '$(VPC_CONFIG)'
        validated_config["vpc_config_option"] = '--vpc-config file://./$(VPC_CONFIG)'
    else:
        validated_config["vpc_config"] = ""
        validated_config["vpc_config_option"] = ""

    validated_config["cache_dir"] = makala_config.cache_dir

    makefile = render_makefile(template=template_name, config=validated_config)
    with open("Makefile", "w") as f: # pylint: disable=C0103
        f.write(makefile)


def validate_config(config, lambda_name):
    """Validate the configuration file.
    """
    validated_config = copy.deepcopy(config)

    if not "name" in config:
        validated_config["name"] = lambda_name

    required_vars = {
        "handler" : None,
        "description" : validated_config["name"],
        "role"    : None,
        "memory"  : makala_config.memory,
        "timeout" : makala_config.timeout,
        "runtime" : makala_config.runtime,
        "region"  : makala_config.region,
        "logs"    : {"retention": makala_config.log_retention, "level" : "info"}
    }

    # current valid values according to:
    #   https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutRetentionPolicy.html: pylint: disable=C0301
    valid_log_retention_in_days = [1, 3, 5, 7, 14, 30, 60, 90, 120,
                                   150, 180, 365, 400, 545, 731, 1827, 3653]

    for var in required_vars:  # pylint: disable=C0103
        if not var in config:
            if required_vars[var] is None:
                print("ERROR: no {} defined in config".format(var))
            else:
                validated_config[var] = required_vars[var]

    if ("logs" in config and
            "retention" in config["logs"] and not
            config["logs"]["retention"] in valid_log_retention_in_days):
        error_msg = "ERROR: invalid log retention value must be one of {}"
        print(error_msg.format(str(valid_log_retention_in_days)))

    if "vpc" in config:
        validate_vpc_config(validated_config)

    role_arn = None
    role_name = config.get("role")
    if role_name == "default" or not role_name:
        role_name = "{}-role".format(config["name"])

    role_arn = aws.validate_role(role_name)

    if not role_arn and makala_config.create_role:
        role_arn = aws.create_lambda_role(role_name=role_name, vpc=("vpc" in config))
        # ...may take some time to be ready for use by a Lambda...sleep(5)?
        time.sleep(5)

    if role_arn:
        write_role_arn(role_name, role_arn)

    return validated_config


def validate_vpc_config(config):
    """Validate the vpc object in the configuration.
    """
    vpc_config_valid = True

    if "vpc" in config:
        vpc_config = config["vpc"]
        if isinstance(vpc_config, dict) and "id" in vpc_config:
            vpc_id = vpc_config["id"]
            if vpc_id == "default":
                vpc_config = create_default_vpc_config()
                config["vpc"] = vpc_config
            elif vpc_config["id"]:
                if "security_group_ids" in vpc_config:
                    if (isinstance(vpc_config["security_group_ids"], list) and
                            len(vpc_config["security_group_ids"]) == 0):
                        default_sg = aws.get_default_security_group(vpc_id)
                        vpc_config["security_group_ids"] = [default_sg["GroupId"]]
                    elif not isinstance(vpc_config["security_group_ids"], list):
                        vpc_config_valid = False
                        print("ERROR: security_group_ids must be list")
                else:
                    default_sg = aws.get_default_security_group(vpc_id)
                    vpc_config["security_group_ids"] = [default_sg["GroupId"]]

                if "subnet_ids" in vpc_config:
                    if (isinstance(vpc_config["subnet_ids"], list) and
                            len(vpc_config["subnet_ids"]) == 0):
                        vpc_config["subnet_ids"] = aws.get_subnet_ids(vpc_id)
                    elif not isinstance(vpc_config["subnet_ids"], list):
                        print("ERROR: subnet_ids")
                        vpc_config_valid = False
                else:
                    vpc_config["subnet_ids"] = aws.get_subnet_ids(vpc_id)

        else:
            config["vpc"] = { "id" : "default"}
            validate_vpc_config(config)

    return vpc_config_valid


def create_default_vpc_config():
    """Returns the a default VPC configuration
    """
    vpc_config = {}

    default_vpc = aws.get_default_vpc()

    if default_vpc:
        default_vpc_id = default_vpc["VpcId"]
        if default_vpc_id:
            default_subnets = aws.get_subnet_ids(default_vpc_id)
            if default_subnets:
                default_security_group = aws.get_default_security_group(default_vpc_id)
                if default_security_group:
                    vpc_config = dict({"id": default_vpc_id,
                                       "security_group_ids": [default_security_group["GroupId"]],
                                       "subnet_ids": default_subnets})
    return vpc_config


def write_vpc_config(config):
    """Write the vpc configuration.
    """

    if "vpc" in config:
        vpc_config = {"SubnetIds": config["vpc"]["subnet_ids"],
                      "SecurityGroupIds": config["vpc"]["security_group_ids"]}

        with open("{}/vpc-config.json".format(makala_config.cache_dir), "w") as f:  #pylint: disable=C0103
            f.write(json.dumps(vpc_config))


def write_env_vars(config):
    """Write the environment variable configuration.
    """
    if "env" in config:
        with open("{}/{}-env.json".format(makala_config.cache_dir, config["name"]), "w") as f: # pylint: disable=C0103
            f.write(json.dumps(get_env_vars(config)))


def write_role_arn(role_name, role_arn):
    """Write the role arn to a file.
    """
    with open("{}/{}.arn".format(makala_config.cache_dir, role_name), "w") as f: # pylint: disable=C0103
        f.write(role_arn)

def write_lambda_config(config, lambda_name):
    """Write the lambda config to the config file.
    """
    with open("{}.yaml".format(lambda_name), "w", encoding='utf-8') as f: #pylint: disable=C0103
        f.write(yaml.dump(config))


def get_env_vars(config):
    """Creates a dict suitable for passing as the --environment option to
    the update-function-configuration or create-function aws CLI
    commands.

    """
    if "logs" in config:
        if "level" in config["logs"]:
            if "env" in config:
                config["env"]["log_level"] = config["logs"]["level"].upper()
            else:
                config["env"] = {"log_level" : config["logs"]["level"].upper()}

    if "env" in config:
        env_vars = dict()
        for name in config["env"].keys():
            env_vars[name.upper()] = config["env"][name]

    return dict({"Variables": env_vars})


def render_makefile(**kwargs):
    """Render the jinja2 template and create the Makefile.
    """
    file_loader = FileSystemLoader('/')
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


def clean(files, lambda_name):
    """Remove files defined in config whenever this script is
    executed. (Not currently called but may have some use in the
    future)

    """
    for file in files:
        if "{}" in file:
            name = file.format(lambda_name)
        else:
            name = file
        name = "{}/{}".format(makala_config.cache_dir, name)
        if os.path.exists(name):
            os.remove(name)

if __name__ == "__main__":

    main()

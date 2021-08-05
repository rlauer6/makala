import yaml
import os
import errno
import logging

import configparser
import copy
import json

import pkg_resources

from .aws.vpc_config import AWSVPCConfig
from .aws.lambda_role import AWSLambdaRole
from .aws.sqs_config import AWSSQSConfig

import makala.aws.utils as aws

class LambdaConfig():
    """Class to represent the .yaml configuration file
    """
    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, env):
        self._env = env

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        self._profile = profile

    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, region):
        self._region = region

    @property
    def sns_topic(self):
        return self._sns_topic

    @sns_topic.setter
    def sns_topic(self, sns_topic):
        self._sns_topic = sns_topic

    @property
    def vpc(self):
        return self._vpc

    @vpc.setter
    def vpc(self, vpc):
        self._vpc = vpc

    @property
    def bucket(self):
        return self._bucket

    @bucket.setter
    def bucket(self, bucket):
        self._bucket = bucket

    @property
    def source_arn(self):
        return self._source_arn

    @source_arn.setter
    def source_arn(self, source_arn):
        self._source_arn = source_arn

    @property
    def errors(self):
        return self._errors

    @errors.setter
    def errors(self, errors):
        self._errors = errors if isinstance(errors, list) else [ errors ]

    @property
    def warnings(self):
        return self._warnings

    @warnings.setter
    def warnings(self, warnings):
        self._warnings = warnings if isinstance(warnings, list) else [ warnings ]

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, role):
        self._role = role

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        if path:
            if not os.path.exists(path):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), path)

            if not os.path.getsize(path):
                raise Exception("{} is empty".format(path))

        self._path = path

    @property
    def lambda_name(self):
        return self._lambda_name

    @lambda_name.setter
    def lambda_name(self, lambda_name):
        self._lambda_name = lambda_name

    @property
    def makala_config(self):
        return self._makala_config

    @makala_config.setter
    def makala_config(self, makala_config):
        self._makala_config = makala_config
    @property

    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger

    def __init__(self, **kwargs):

        self.logger = logging.getLogger()

        self.role = None
        self.env = None
        self.vpc = None
        self.bucket = None
        self.sns_topic = None
        self.source_arn = None
        self.profile = None

        self.lambda_name = kwargs["lambda_name"]
        self.makala_config = kwargs["makala_config"]

        self.path = kwargs.get("path")
        if self.path:
            self.config = self._read_lambda_config()
            self.profile = self.config.get("profile")

            if "env" in self.config and isinstance(self.config["env"], dict):
                self.env = EnvironmentVars(self.config["env"])
            else:
                self.env = None

    def save(self):
        self._write_lambda_config()
        if self.vpc:
            self._write_vpc_config()
        if self.env:
            self._write_env_vars()
        if self.role:
            self._write_role_arn()

    def _write_lambda_config(self):
        """Write the lambda config to the config file.
        """
        with open(self.path, "w", encoding='utf-8') as f: #pylint: disable=C0103
            f.write(yaml.dump(self.config))

    def _read_lambda_config(self):
        with open(self.path, encoding='utf-8') as f: # pylint: disable=C0103
            return yaml.safe_load(f)

    def __str__(self):
        return yaml.dump(self._config)

    def validate(self):
        """Validate the configuration file.
        """
        validated_config = copy.deepcopy(self.config)
        self.errors = errors = []
        self.warnings = warnings = []

        validated_config["name"] = self.config.get("name", self.lambda_name)

        required_vars = {
            "handler" : None,
            "description" : validated_config["name"],
            "memory"  : self.makala_config.memory,
            "timeout" : self.makala_config.timeout,
            "runtime" : self.makala_config.runtime,
            "region"  : self.makala_config.region,
            "logs"    : {"retention": self.makala_config.log_retention, "level" : "info"}
            }

        valid_parameters = {
            "env" : None,
            "logs" : None,
            "name" : None,
            "role" : None,
            "role_arn" : None,
            "custom_role" : None,
            "service" : None,
            "bucket" : None,
            "vpc" : None,
            "source_account" : None,
            "sqs" : None
            }

        all_parameters = list(valid_parameters.keys()) + list(required_vars.keys())
        for p in self.config.keys():
            if p not in all_parameters:
                errors.append("{} is not a valid parameter".format(p))

        # current valid values according to:
        #   https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutRetentionPolicy.html: pylint: disable=C0301
        valid_log_retention_in_days = [1, 3, 5, 7, 14, 30, 60, 90, 120,
                                       150, 180, 365, 400, 545, 731, 1827, 3653]

        for var in required_vars:  # pylint: disable=C0103
            if not var in self.config:
                if required_vars[var] is None:
                    errors.append("no {} defined in config".format(var))
                else:
                    warnings.append("no required {} defined. Using default: {}".format(var, required_vars[var]))
                    validated_config[var] = required_vars[var]

        self.region = validated_config["region"]

        memory = int(validated_config["memory"])
        if memory > 3008 or memory < 128 or memory % 64:
            errors.append("invalid value ({}) for memory. Must be 128 MB to 3,008 MB, in 64 MB increments.".format(memory))

        timeout = int(validated_config["timeout"])
        if timeout > 900:
            errors.append("invalid value ({}) for timeout.  Must be < 900 seconds.".format(validated_config["timeout"]))

        if "logs" in self.config:
            if ("retention" in self.config["logs"] and not
                self.config["logs"]["retention"] in valid_log_retention_in_days):
                error_msg = "invalid value ({}) for log retention. Must be one of {}"
                errors.append(error_msg.format(self.config["logs"]["retention"], str(valid_log_retention_in_days)))
            if self.env:
                if "level" in self.config["logs"]:
                    self.env.set("LOG_LEVEL", self.config["logs"]["level"].upper())
                    validated_config["env"] = self.env.env
            elif "level" in self.config["logs"]:
                self.env = EnvironmentVars({"LOG_LEVEL": self.config["logs"]["level"].upper()})
                validated_config["env"] = self.env.env

        if "vpc" in self.config:
            if isinstance(self.config["vpc"], dict):
                self.vpc = AWSVPCConfig(self.config["vpc"], profile=self.profile)
            else:
                self.vpc = AWSVPCConfig({}, profile=self.profile)
            self.vpc.validate()
            validated_config["vpc"] = self.vpc.config

        self.logger.debug(json.dumps(validated_config, indent=4))

        if "role" in validated_config or not "custom_role" in validated_config:
            if "custom_role" in validated_config:
                del validated_config["custom_role"]

            # more support of other Lambda features later...
            supported_features = ["sqs.amazonaws.com"]

            if "service" in validated_config and validated_config["service"] in supported_features:
                lambda_feature = validated_config["service"]
            else:
                lambda_feature = None

            self.logger.info("before AWSLambdaRole: {}".format(json.dumps(self.config, indent=4)))

            self.role = AWSLambdaRole(
                validated_config["name"],
                vpc_enabled=("vpc" in self.config),
                role=self.config.get("role"),
                profile=self.config.get("profile"),
                service=lambda_feature
                )

            validated_config["role"] = self.role.role
            validated_config["role_arn"] = self.role.role_arn

        if "service" in validated_config and "sqs" in validated_config["service"]:
            if "sqs" in validated_config:
                sqs_config = AWSSQSConfig(validated_config["name"], self.makala_config, **validated_config["sqs"])
            else:
                sqs_config = AWSSQSConfig(
                    validated_config["name"],
                    self.makala_config, {
                        profile : self.config.get("profile"),
                        queue_name : validated_config["name"]
                        }
                    )

            if not "queue_arn" in validated_config["sqs"]:
                validated_config["sqs"]["queue_arn"] = sqs_config.queue_arn

        if "profile" in self.config:
            validated_config["profile"] = self.config.get("profile")

        if validated_config["service"] and "sns" in  validated_config["service"]:
            if not validated_config.get("sns_topic"):
                errors.append("no sns topic defined")


        # if the Lambda is going to subscribe to a topic...
        # 1. check to see if topic exists
        # 2. add source_arn to config (if the topic does not exist the Makefile will create it)
        # 3. remove source_account from config

        if "sns_topic" in validated_config:
            topic = aws.validate_sns_topic(validated_config["sns_topic"], profile=self.config.get("profile"))
            if topic:
                self.sns_topic = validated_config["sns_topic"]
            else:
                warnings.append("no such topic: {}".format(validated_config["sns_topic"]))

            if "source_account" in validated_config:
                del validated_config["source_account"]

            validated_config["source_arn"] = "arn:aws:sns:{}:{}:{}".format(self.region, aws.get_caller_account(), validated_config["sns_topic"])

        if self.bucket:
            validated_config["bucket"] = self.bucket

        self.logger.debug(json.dumps(validated_config, indent=4))

        if len(errors) == 0:
            self.config = validated_config

        return len(errors) == 0

    def _write_vpc_config(self):
        """Write the vpc configuration.
        """

        if self.vpc:
            with open("{}/vpc-config.json".format(self.makala_config.cache_dir), "w") as f:  #pylint: disable=C0103q
                f.write(str(self.vpc))


    def _write_env_vars(self):
        """Write the environment variable configuration.
        """
        if self.env:
            filename = "{}/{}-env.json".format(self.makala_config.cache_dir, self.lambda_name)
            with open(filename, "w") as f: # pylint: disable=C0103
                f.write(str(self.env))

    def _write_role_arn(self):
        """Write the role arn to a file.
        """
        if self.role:
            filename = "{}/{}.arn".format(self.makala_config.cache_dir, self.role.role)
            with open(filename, "w") as f: # pylint: disable=C0103
                f.write(str(self.role))

    def generate_stub(self, pattern=None):
        if pattern:
            service = pattern["service"]
        else:
            service =""

        stub = {
            "handler" : "handler",
            "name"    : self.lambda_name,
            "description" : self.lambda_name,
            "role"    : "{}-role".format(self.lambda_name),
            "memory"  : self.makala_config.memory,
            "timeout" : self.makala_config.timeout,
            "runtime" : self.makala_config.runtime,
            "service" : service,
            "source_account" : aws.get_caller_account(),
            "region"  : self.makala_config.region,
            "logs"    : {"retention": self.makala_config.log_retention, "level" : "info"}
            }

        if self.source_arn:
            stub["source_arn"] = self.source_arn

        if self.bucket:
            stub["bucket"] = self.bucket

        return yaml.dump(stub)

    def generate_lambda_stub(self):
        stub_path="{}".format(pkg_resources.resource_filename("makala", 'data/lambda.py'))
        with open(stub_path) as fh: stub = fh.read()

        return stub

class EnvironmentVars():
    """Object representing the environment variables for the Lambda
    """
    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, env):
        self._env = env

    def set(self, key, value):
        env = self.env
        env[key] = value

    def __init__(self, env):
        self.env = env or {}

    # return the string representation for the aws CLI option --environment
    def __str__(self):
        env_vars = dict()
        for name in self.env:
            env_vars[name.upper()] = self.env[name]

        return json.dumps({"Variables": env_vars})

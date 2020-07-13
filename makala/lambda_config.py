import yaml
import os
import errno

import configparser
import copy
import json

from .aws.vpc_config import AWSVPCConfig
from .aws.lambda_role import AWSLambdaRole

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
    def vpc(self):
        return self._vpc

    @vpc.setter
    def vpc(self, vpc):
        self._vpc = vpc

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

    def __init__(self, **kwargs):
        self.role = None
        self.env = None
        self.vpc = None

        self.path = kwargs.get("path")
        self.lambda_name = kwargs["lambda_name"]
        self.makala_config = kwargs["makala_config"]
        if self.path:
            self.config = self._read_lambda_config()

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
            "role"    : None,
            "memory"  : self.makala_config.memory,
            "timeout" : self.makala_config.timeout,
            "runtime" : self.makala_config.runtime,
            "region"  : self.makala_config.region,
            "logs"    : {"retention": self.makala_config.log_retention, "level" : "info"}
        }

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
                    self.env.set("LOG_LEVEL", self.config["logs"]["level"])
                    validated_config["env"] = self.env.env
            elif "level" in self.config["logs"]:
                self.env = EnvironmentVars({"LOG_LEVEL": self.config["logs"]["level"].upper()})
                validated_config["env"] = self.env.env

        if "vpc" in self.config:
            if isinstance(self.config["vpc"], dict):
                self.vpc = AWSVPCConfig(self.config["vpc"])
            else:
                self.vpc = AWSVPCConfig({})
            self.vpc.validate()
            validated_config["vpc"] = self.vpc.config

        self.role = AWSLambdaRole(validated_config["name"],
                                  vpc_enabled=("vpc" in self.config),
                                  role=self.config.get("role"))
        validated_config["role"] = self.role.role

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

    def generate_stub(self):

        stub = {"handler" : "handler",
                "name"    : self.lambda_name,
                "description" : self.lambda_name,
                "role"    : "{}-role".format(self.lambda_name),
                "memory"  : self.makala_config.memory,
                "timeout" : self.makala_config.timeout,
                "runtime" : self.makala_config.runtime,
                "service" : "",
                "region"  : self.makala_config.region,
                "logs"    : {"retention": self.makala_config.log_retention, "level" : "info"}}

        return yaml.dump(stub)

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

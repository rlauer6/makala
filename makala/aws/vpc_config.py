import json
import logging

import  makala.aws.utils as aws

def main():
    vpc_config = AWSVPCConfig({"id": "vpc-9526f0ee"})
    vpc_config.validate()
    print(vpc_config)
    vpc_config = AWSVPCConfig({})
    vpc_config.validate()
    print(vpc_config)

class AWSVPCConfig():
    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger

    @property
    def subnet_ids(self):
        return self._subnet_ids

    @subnet_ids.setter
    def subnet_ids(self, subnet_ids):
        if isinstance(subnet_ids, list):
            self._subnet_ids = subnet_ids
        elif subnet_ids:
            self._subnet_ids = [subnet_ids]
        else:
            self._subnet_ids = []

    @property
    def security_group_name(self):
        return self._security_group_name

    @security_group_name.setter
    def security_group_name(self, security_group_name):
        self._security_group_name = security_group_name

    @property
    def vpc_id(self):
        return self._vpc_id

    @vpc_id.setter
    def vpc_id(self, vpc_id):
        self._vpc_id = vpc_id

    @property
    def security_group_ids(self):
        return self._security_group_ids

    @security_group_ids.setter
    def security_group_ids(self, security_group_ids):
        if isinstance(security_group_ids, list):
            self._security_group_ids = security_group_ids
        elif security_group_ids:
            self._security_group_ids = [security_group_ids]
        else:
            self._security_group_ids = []

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    def __init__(self, config):
        if not isinstance(config, dict):
            raise Exception("config must be dict")

        self.config = config
        self.vpc_id = config.get("id")
        self.subnet_ids = config.get("subnet_ids")
        self.security_group_ids = config.get("security_group_ids")
        self.security_group_name = config.get("security_group_name")
        self.logger = logging.getLogger()

    def validate(self):
        """Validate the vpc object in the configuration.
        """
        if self.vpc_id and self.vpc_id == "default":
            self.vpc_id = aws.get_default_vpc()["VpcId"]
            self.logger.info("using default vpc: {}".format(self.vpc_id))
            self.subnet_ids = aws.get_private_subnet_ids(self.vpc_id)
            self.security_group_ids = aws.get_default_security_group(self.vpc_id)["GroupId"]
        elif self.vpc_id:
            if self.security_group_name:
                sg = aws.get_security_group_by_name(self.vpc_id, self.security_group_name)
                if sg:
                    if len(self.security_group_ids):
                        if not sg["GroupId"] in self.security_group_ids:
                            self.security_group_ids.append(sg["GroupId"])
                    else:
                        self.security_group_ids = sg["GroupId"]
            elif len(self.security_group_ids) == 0:
                self.logger.info("using default security group for vpc: {}".format(self.vpc_id))
                self.security_group_ids = aws.get_default_security_group(self.vpc_id)["GroupId"]

            if len(self.subnet_ids) == 0:
                self.logger.info("using default private subnets for vpc: {}".format(self.vpc_id))
                self.subnet_ids = aws.get_private_subnet_ids(self.vpc_id)
        else:
            self.vpc_id = "default"
            self.validate()

        self.config = {
            "id": self.vpc_id,
            "security_group_ids" : self.security_group_ids,
            "subnet_ids" : self.subnet_ids
            }
        if self.security_group_name:
            self.logger.info("setting name: {}".format(self.security_group_name))
            self.config["security_group_name"] = self.security_group_name

        if len(self.subnet_ids) == 0:
            self.logger.warn("no private subnets for vpc: {}".format(self.vpc_id))

    def __str__(self):
        return json.dumps({"SubnetIds": self.subnet_ids, "SecurityGroupIds": self.security_group_ids, "SecurityGroupName": self.security_group_name})

if __name__ == "__main__":
    main()

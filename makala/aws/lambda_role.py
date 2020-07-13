import json

import makala.aws.utils as aws
import logging

def main():
    # create a role, then delete it
    lambda_role = AWSLambdaRole("buz")
    print(lambda_role)
    print(aws.list_role_policies("buz-role"))
    lambda_role.delete()

    lambda_role = AWSLambdaRole("bar", vpc_enabled=True)
    print(lambda_role)
    print(aws.list_role_policies("bar-role"))
    lambda_role.delete()

class AWSLambdaRole():

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger

    @property
    def role_arn(self):
        return self._role_arn

    @role_arn.setter
    def role_arn(self, role_arn):
        self._role_arn = role_arn

    @property
    def lambda_name(self):
        return self._lambda_name

    @lambda_name.setter
    def lambda_name(self, lambda_name):
        self._lambda_name = lambda_name

    @property
    def vpc_enabled(self):
        return self._vpc_enabled

    @vpc_enabled.setter
    def vpc_enabled(self, vpc_enabled):
        self._vpc_enabled = vpc_enabled

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, role):
        if role == "default" or not role:
            self._role = "{}-role".format(self.lambda_name)
        else:
            self._role = role

    @property
    def auto_create_role(self):
        return self._auto_create_role

    @auto_create_role.setter
    def auto_create_role(self, create_role):
        if isinstance(create_role, str):
            self._auto_create_role = create_role == "true"
        else:
            self._auto_create_role = create_role == True

    def __init__(self, lambda_name, **kwargs):
        self.logger = logging.getLogger()

        self.lambda_name = lambda_name
        self.role = kwargs.get("role")

        self.auto_create_role = kwargs.get("auto_create_role")
        self.vpc_enabled = kwargs.get("vpc_enabled") or False
        self._role_arn = kwargs.get("role_arn") or None
        self.role_arn = self.validate()

    def validate(self):
        role_arn = None
        if not self.role_arn and self.role:
            role_arn = aws.validate_role(self.role)
            if not role_arn:
                self.logger.info("creating lambda role: {}".format(self.role))
                role_arn = aws.create_lambda_role(role_name=self.role, vpc=self.vpc_enabled)

        elif not self.role_arn and self.auto_create_role:
            self.logger.info("creating lambda_role: {}".format(self.role))
            role_arn = aws.create_lambda_role(role_name=self.role, vpc=self.vpc_enabled)

        return role_arn

    def __str__(self):
        return self.role_arn

    def delete(self):
        if self.role_arn and self.role:
            policies = aws.list_role_policies(self.role)
            for a in policies:
                self.logger.inf("detaching policy: {} from: {}".format(a, self.role))
                aws.detach_role_policy(self.role, a)
        self.logger.inf("deleting role: {}".format(self.role))
        aws.delete_role(self.role)
        self.role_arn = None

if __name__ == "__main__":
    main()

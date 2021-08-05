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
    def service(self):
        return self._service

    @service.setter
    def service(self, service):
        self._service = service

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        self._profile = profile

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
        self.profile = kwargs.get("profile")
        self.service = kwargs.get("service")

        self.auto_create_role = kwargs.get("auto_create_role")
        self.vpc_enabled = kwargs.get("vpc_enabled") or False
        self.logger.info("vpc_enabled: {}".format(self.vpc_enabled))

        self._role_arn = kwargs.get("role_arn") or None
        self.role_arn = self.validate()

    def validate(self):
        role_arn = None

        if not self.role_arn and self.role:
            role_arn = aws.validate_role(self.role, profile=self.profile)
            self.logger.info("role_arn: {}".format(role_arn))
            if not role_arn:
                self.logger.info("creating lambda role: {}".format(self.role))
                role_arn = aws.create_lambda_role(role_name=self.role, vpc=self.vpc_enabled, service=self.service, profile=self.profile)
            else:
                self.validate_role()

        elif not self.role_arn and self.auto_create_role:
            self.logger.info("creating lambda_role: {}".format(self.role))
            role_arn = aws.create_lambda_role(role_name=self.role, vpc=self.vpc_enabled, service=self.service, profile=self.profile)

# role exists, so validate the execution role

        return role_arn

    def validate_role(self):
        policies = aws.list_role_policies(self.role, profile=self.profile)
        self.logger.info("validating role: {} {} vpc_enabled: {}".format(self.role, json.dumps(policies, indent=4), self.vpc_enabled))

        if self.vpc_enabled:
            if not any("AWSLambdaVPCAccessExecutionRole" in p for p in policies):
                if any("AWSLambdaBasicExecutionRole" in p for p in policies):
                    self.logger.info("detatching AWSLambdaBasicExecutionRole")
                    aws.detach_role_policy(self.role, self.format_policy_arn("AWSLambdaBasicExecutionRole"))
                    aws.attach_role_policy(self.role, self.format_policy_arn("AWSLambdaVPCAccessExecutionRole"))
        else:
            self.logger.info("VPC is not enabled!")
            if not any("AWSLambdaBasicExecutionRole" in p for p in policies):
                if any("AWSLambdaVPCAccessExecutionRole" in p for p in policies):
                    self.logger.info("detatching AWSLambdaVPCAccessExecutionRole")
                    aws.detach_role_policy(self.role, self.format_policy_arn("AWSLambdaVPCAccessExecutionRole"))
                    aws.attach_role_policy(self.role, self.format_policy_arn("AWSLambdaBasicExecutionRole"))

        return

    def __str__(self):
        return self.role_arn

    def format_policy_arn(self, policy_name):
        return "arn:aws:iam::aws:policy/service-role/{}".format(policy_name)

    def delete(self):
        if self.role_arn and self.role:
            policies = aws.list_role_policies(self.role, profile=self.profile)
            for a in policies:
                self.logger.info("detaching policy: {} from: {}".format(a, self.role))
                aws.detach_role_policy(self.role, a, profile=self.profile)
        self.logger.info("deleting role: {}".format(self.role))
        aws.delete_role(self.role, profile=self.profile)
        self.role_arn = None

if __name__ == "__main__":
    main()

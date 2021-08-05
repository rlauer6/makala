import yaml
import logging
import json
import boto3
import botocore.exceptions


import makala.aws.utils as aws

class AWSSQSConfig():
    """Class to represent the SQS configuration in the .yaml
    configuration file
    """

    @property
    def deduplication_scope(self):
        return self._deduplication_scope

    @deduplication_scope.setter
    def deduplication_scope(self, deduplication_scope):
        self._deduplication_scope = deduplication_scope

    @property
    def queue_arn(self):
        return self._queue_arn

    @queue_arn.setter
    def queue_arn(self, queue_arn):
        self._queue_arn = queue_arn

    @property
    def queue_name(self):
        return self._queue_name

    @queue_name.setter
    def queue_name(self, queue_name):
        self._queue_name = queue_name

    @property
    def delay_seconds(self):
        return self._delay_seconds

    @delay_seconds.setter
    def delay_seconds(self, delay_seconds):
        self._delay_seconds = delay_seconds

    @property
    def fifo_queue(self):
        return self._fifo_queue

    @fifo_queue.setter
    def fifo_queue(self, fifo_queue):
        self._fifo_queue = fifo_queue

    @property
    def kms_master_key_id(self):
        return self._kms_master_key_id

    @kms_master_key_id.setter
    def kms_master_key_id(self, kms_master_key_id):
        self._kms_master_key_id = kms_master_key_id

    @property
    def maximum_message_size(self):
        return self._maximum_message_size

    @maximum_message_size.setter
    def maximum_message_size(self, maximum_message_size):
        self._maximum_message_size = maximum_message_size

    @property
    def message_retention_period(self):
        return self._message_retention_period

    @message_retention_period.setter
    def message_retention_period(self, message_retention_period):
        self._message_retention_period = message_retention_period

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, policy):
        self._policy = policy

    @property
    def queue_url(self):
        return self._queue_url

    @queue_url.setter
    def queue_url(self, queue_url):
        self._queue_url = queue_url

    @property
    def receive_message_wait_time_seconds(self):
        return self._receive_message_wait_time_seconds

    @receive_message_wait_time_seconds.setter
    def receive_message_wait_time_seconds(self, receive_message_wait_time_seconds):
        self._receive_message_wait_time_seconds = receive_message_wait_time_seconds

    @property
    def redrive_policy(self):
        return self._redrive_policy

    @redrive_policy.setter
    def redrive_policy(self, redrive_policy):
        self._redrive_policy = redrive_policy

    @property
    def visibility_timeout(self):
        return self._visibility_timeout

    @visibility_timeout.setter
    def visibility_timeout(self, visibility_timeout):
        self._visibility_timeout = visibility_timeout

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        self._profile = profile

    @property
    def sqs_client(self):
        if self._sqs_client:
            return self._sqs_client
        else:
            self._sqs_client = aws.get_sqs_client(self.profile)
            
        return self._sqs_client

    @sqs_client.setter
    def sqs_client(self, sqs_client):
        self._sqs_client = sqs_client
        
    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, region):
        self._region = region

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
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger

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

    def __init__(self, lambda_name, makala_config, **kwargs):

        self.logger = logging.getLogger()
        
        self._sqs_client = None
        self._queue_url = kwargs.get("queue_url")
        self._deduplication_scope = kwargs.get("deduplication_scope")
        self._queue_arn = kwargs.get("queue_arn")
        self._delay_seconds = kwargs.get("delay_seconds")
        self._visibility_timeout = kwargs.get("visibility_timeout")
        self._redrive_policy = kwargs.get("redrive_policy")
        self._message_retention_period = kwargs.get("message_retention_period")
        self._maximum_message_size = kwargs.get("maximum_message_size")
        self._kms_master_key_id = kwargs.get("kms_master_key_id")
        self._fifo_queue = kwargs.get("fifo_queue")
        self._policy = kwargs.get("policy")
        self._receive_message_wait_time_seconds = kwargs.get("receive_message_wait_time_seconds")
       
        self.lambda_name = lambda_name
        self.makala_config = makala_config

        self.queue_name = kwargs.get("queue_name") or lambda_name
        
        self.config = kwargs.get("config") or {}
        self.profile = kwargs.get("profile")
        self.validate()
    
    def __str__(self):
        return yaml.dump(self._config)

    def format_queue_url(self):
        account = aws.get_caller_account()
        region = self.sqs_client.meta.region_name
        
        return "https://sqs.{}.amazonaws.com/{}/{}".format(region, account, self.queue_name)

    def format_queue_arn(self):
        account = aws.get_caller_account()
        region = self.sqs_client.meta.region_name
        
        return "arn:aws:sqs:{}:{}:{}".format(region, account, self.queue_name)
    
# To validate SQS queue configuration:
# 1. check to see if queue exists
# 2. check to see if event mapping has been completed
# 3. validate the queue configuration

    def validate(self):        
        if self.queue_exists():
            self.get_queue_attributes()
        else:
            self.create_queue()
            self.get_queue_attributes()
            self.save()
            
    def dump(self,what):
        self.logger.info(json.dumps(what, indent=4))
        
    def get_queue_attributes(self):
        sqs_client = aws.get_sqs_client(self.profile)
            
        self.queue_url = self.queue_url or self.format_queue_url()
        
        self.attributes = sqs_client.get_queue_attributes(AttributeNames=["All"], QueueUrl=self.queue_url)
        self.dump(self.attributes)
        self.queue_arn = self.attributes["Attributes"]["QueueArn"]

        self.visibility_timeout = self.attributes.get("VisibiltyTimeout")
        self.maximum_message_size = self.attributes.get("MaximumMessageSize")
        self.delay_seconds = self.attributes.get("DelaySeconds")
        self.receive_message_wait_time_seconds = self.attributes.get("ReceiveMessageWaitTimeSeconds")
        
        return self.attributes
    
    def queue_exists(self):
        sqs_client = self.sqs_client
        try:
            response = sqs_client.get_queue_url(QueueName=self.queue_name)
            return response["QueueUrl"]
        except botocore.exceptions.ClientError as error:
            return False

    def generate_stub(self):
        pass

    def save(self):
        if not self.queue_url:
            return False
        
        if self.queue_name:
            filename = "{}/{}-queue-url.json".format(self.makala_config.cache_dir, self.lambda_name)
            with open(filename, "w") as f: # pylint: disable=C0103
                f.write(json.dumps({ "QueueUrl" : self.queue_url }, indent=4))
                
        if self.attributes:
            filename = "{}/{}-queue-attributes.json".format(self.makala_config.cache_dir, self.lambda_name)
            with open(filename, "w") as f: # pylint: disable=C0103
                f.write(json.dumps(self.attributes, indent=4))

    # caller should verify that queue does not exist
    def create_queue(self):
        args = {
            "QueueName" : self.queue_name
            }
            
        attributes = {}
        
        if self.deduplication_scope:
            attributes["DeduplicationScope"] = self.deduplication_scope

        if self.delay_seconds:
            attributes["DelaySeconds"] = self.delay_seconds

        if self.fifo_queue:
            attributes["FifoQueue"] = self.fifo_queue

        if self.kms_master_key_id:
            attributes["KmsMasterKeyId"] = self.kms_master_key_id

        if self.maximum_message_size:
            attributes["MaximumMessageSize"] = self.maximum_message_size

        if self.message_retention_period:
            attributes["MessageRetentionPeriod"] = self.message_retention_period

        if self.policy:
            attributes["Policy"] = self.policy

        if self.receive_message_wait_time_seconds :
            attributes["ReceiveMessageWaitTimeSeconds "] = self.receive_message_wait_time_seconds 

        if self.redrive_policy:
            self.logger.info(self.dump(self.redrive_policy))
            
            attributes["RedrivePolicy"] = {
                "deadLetterTargetArn" : self.redrive_policy.get("dead_letter_target_arn"),
                "maxReceiveCount" : self.redrive_policy.get("maxReceiveCount")
                }
            
        if self.visibility_timeout:
            attributes["VisibilityTimeout"] = str(self.visibility_timeout)

        if len(attributes.keys()):
            args["Attributes"] = attributes
            
        response = self.sqs_client.create_queue(**args)
        return response["QueueUrl"]
    

# DeduplicationScope
# DelaySeconds
# FifoQueue
# KmsMasterKeyId
# MaximumMessageSize
# MessageRetentionPeriod
# Policy
# ReceiveMessageWaitTimeSeconds 
# RedrivePolicy
#   deadLetterTargetArn
#   maxReceiveCount
# VisibilityTimeout

# sqs:
#   queue_name:
#   deduplication_scope: 
#   delay_seconds:
#   fifo_queue:
#   kms_master_key_id:
#   maximum_message_size:
#   message_retention_period:
#   policy:
#   receive_message_wait_time_seconds :
#   redrive_policy:
#     deadletter_target_arn:
#     max_receive_count:
#   visibility_timeout:

#!/bin/env python
"""makala
"""

import argparse
import json
import os
import glob
import sys
import time
import shutil

from datetime import datetime

import pkg_resources

import yaml
import logging

from jinja2 import Environment, FileSystemLoader

import makala.aws.utils as aws
from makala import MakalaConfig
from makala import LambdaConfig

try:
    version = pkg_resources.get_distribution('makala').version
except:
    version = '0.0.0'

def main():
    """makala - a Makefile based serverless framework for AWS Lambdas
    """
    logging.basicConfig()
    logger = logging.getLogger()

    if "LOG_LEVEL" in os.environ:
        log_level = os.environ["LOG_LEVEL"].upper()

        if log_level == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif log_level == "INFO":
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

    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + str(version))

    parser.add_argument("-c", "--config", dest="config_file", type=str,
                        help="Configuration filename. default={lambda-name}.yaml")
    parser.add_argument('-o', '--overwrite',
                        dest="overwrite",
                        action="store_true", help="replace existing Makefile if it exists")

    parser.add_argument('-g', '--generate-config',
                        dest="generate",
                        action="store_true", help="generate a stub configuration file")

    parser.add_argument('-n', '--generate-bucket-notification-configuration',
                        dest="notification",
                        action="store_true", help="generate a bucket notification configuration file")

    parser.add_argument('-f', '--bucket-filter',
                        dest="bucket_filter", type=str,
                        help="bucket filter for S3 service (ex: prefix:foo, suffix:foo")

    parser.add_argument('-e', '--bucket-events',
                        dest="bucket_events", type=str,
                        help="bucket events for S3 service (ex: s3:ObjectCreated:Post,s3:ObjectCreate:Put")

    parser.add_argument('-b', '--bucket',
                        dest="bucket", type=str,
                        help="bucket name for S3 service")

    parser.add_argument('-t', '--terraform', dest="terraform",
                        action="store_true", help="generate terraform instead of Makefile")

    parser.add_argument('-s', '--service', dest="service",
                        action="store", help="generate a configuration file for a specific service")

    args = parser.parse_args()


    lambda_name = args.lambda_name
    split_name = os.path.splitext(lambda_name)
    if split_name[1]:
        logger.warn("using {} as Lambda name".format(split_name[0]))
        lambda_name = split_name[0]

    config_file = args.config_file or "{}.yaml".format(lambda_name)

    services_supported = {
        "events" : { "service": "events.amazonaws.com" },
        "sns"    : { "service": "sns.amazonaws.com" },
        "s3"     : { "service": "s3.amazonaws.com" },
        "sqs"    : { "service": "sqs.amazonaws.com" },
        "logs"   : { "service": "logs.amazonaws.com" }
        }

    bucket = args.bucket
    bucket_events = args.bucket_events
    bucket_filter = args.bucket_filter
    bucket_config = None
    source_arn = None

    if args.service and not args.generate:
        logger.error("--service only valid with --generate option");
        sys.exit(-1)
    elif args.service:
        if args.service in services_supported.keys():
            service_pattern = args.service
            if service_pattern != "s3" and bucket:
                logger.error("bucket option only valid with when service is s3")
                sys.exit(-1)
            else:
                if not aws.validate_bucket(bucket):
                    logger.warning("bucket {} does not exist".format(bucket))
                bucket_config = { "name" : bucket }
                if bucket_filter:
                    filter = bucket_filter.split(":")
                    bucket_config["filter"] = {
                        "name" : filter[0],
                        "value" : filter[1]
                        }
                if bucket_events:
                    events = bucket_events.split(",")
                    bucket_config["events"] = ["{}".format(a) for a in events]

                source_arn = "arn:aws:s3:::{}".format(bucket)
        else:
            logger.error("{} is not a supported service")
            print("Supported services:")
            print(" * {}".format("\n * ".join(services_supported.keys())))
            sys.exit(-1)
    else:
        service_pattern = None

    # this can only be done after the Lambda is created
    if args.notification:
        lambda_arn_file = "{}/{}.arn".format(makala_config.cache_dir, lambda_name)

        if not os.path.exists(lambda_arn_file):
            logger.error("Lambda must be created before you can create bucket notification")
            sys.exit(-1)

        lambda_config = get_lambda_config_file(config_file, lambda_name, makala_config)
        if not lambda_config:
            sys.exit(-1)

        bucket_config = lambda_config.config["bucket"]
        print(bucket_config)

        if "events" in bucket_config:
            events = bucket_config["events"]
            notification_id = "{}-notification".format(bucket_config["name"])
            lambda_arn = get_lambda_arn(makala_config.cache_dir, lambda_name)

            notification = {
                "LambdaFunctionConfigurations": [{
                    "Id" : notification_id,
                    "LambdaFunctionArn" : lambda_arn,
                    "Events" : [ ",".join(events) ]
                    }
                        ]
                }

            if "filter" in bucket_config:

                filter = {
                "Key": {
                    "FilterRules": [
                        {
                        "Name": bucket_config["filter"]["name"],
                        "Value": bucket_config["filter"]["value"]
                        }
                        ]
                    }
                }

                notification["LambdaFunctionConfigurations"][0]["Filter"] = filter

            notification_path = "{}/{}-bucket-notification.json.in".format(makala_config.cache_dir, bucket_config["name"])
            with open(notification_path, "w", encoding='utf-8') as f: #pylint: disable=C0103
                f.write(json.dumps(notification, indent=4))

            sys.exit(0)

    if args.generate:
        config_name = "{}.yaml".format(lambda_name)
        if os.path.exists(config_name) and not args.overwrite:
            logger.error("{} exists. Use -o (overwrite) option.".format(config_name))
            sys.exit(-1)

        lambda_config = LambdaConfig(lambda_name=lambda_name, makala_config=makala_config)

        if bucket_config:
            lambda_config.bucket = bucket_config

        if source_arn:
            lambda_config.source_arn = source_arn

        with open(config_name, "w") as f:
            f.write(lambda_config.generate_stub(pattern=services_supported.get(service_pattern)))

        stub_name = "{}.py".format(lambda_name)
        if os.path.exists(stub_name) and not args.overwrite:
            logger.error("{} exists. Use -o (overwrite) option.".format(stub_name))

        with open(stub_name, "w") as f:
            f.write(lambda_config.generate_lambda_stub())

        sys.exit(0)

    if not args.terraform:
        if os.path.exists("Makefile") and not args.overwrite:
            logger.error("Makefile exists. Use --overwrite.")
            sys.exit(-1)

    lambda_config = get_lambda_config_file(config_file, lambda_name, makala_config)
    if not lambda_config:
        sys.exit(-1)

    if bucket_config:
        lambda_config.bucket = bucket_config

    if source_arn:
        lambda_config.source_arn = source_arn

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
        template_dir = os.getcwd()
        logger.warn("using local Makefile template")
    else:
        template_name = pkg_resources.resource_filename("makala", 'data/Makefile.jinja2')
        template_dir = "/"
        shutil.copyfile(pkg_resources.resource_filename("makala", "data/Makefile.jinja2"), "Makefile.jinja2")

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

    if bucket_config:
        validated_config["bucket"] = bucket_config.get("name")

    target = "Makefile" # default target
    service = validated_config.get("service")
    account = aws.get_caller_account()

    # source_account may only be valid for S3 and SES
    if not ("source_account" in validated_config):
        if service in ("s3", "ses"):
            validated_config["source_account"] = account
    else:
        if ("source_account" in validated_config) and (service == "sns" or service == "events" or service == "logs"):
            del validated_config["source_account"]

    validated_config["account"] = account

    if source_arn:
        validated_config["source_arn"] = source_arn

    if not validated_config.get("source_arn"):
        logger.warn("no source_arn defined")

    if not args.terraform:
        text = render_output(template_dir=template_dir, template=template_name, config=validated_config)
        with open(target, "w") as f: # pylint: disable=C0103
            f.write(text)
    else:
        if not os.path.isdir('terraform'):
            os.mkdir("terraform")

        if not os.path.exists("terraform/Makefile"):
            shutil.copyfile(pkg_resources.resource_filename("makala", "data/Makefile-terraform"), "terraform/Makefile")

        if "vpc" not in validated_config:
            validated_config["vpc"] = { "subnet_ids" : [] }
        else:
            validated_config["security_group_name"] = validated_config["vpc"]["security_group_name"]

        templates = {
            "terraform": "main.tf",
            "terraform-provider": "provider.tf",
            "terraform-variables" : "variables.tfvars"
            }

        for t in templates.keys():
            target = "terraform/{}".format(templates[t])
            template_name = pkg_resources.resource_filename("makala", "data/{}.jinja2".format(t))
            template_dir = "/"
            text = render_output(template_dir=template_dir, template=template_name, config=validated_config)

            if os.path.exists(target) and not args.overwrite:
                logger.error("{} exists. Use -o (overwrite) option.".format(target))
            else:
                with open(target, "w") as f: # pylint: disable=C0103
                    f.write(text)

def render_output(**kwargs):
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
    config["version"] = version

    if "bucket" in config:
        bucket = config["bucket"]
        config["bucket"] = bucket.get("name")

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

def get_lambda_config_file(file_name, lambda_name, makala_config):
    lambda_config = None
    logger = logging.getLogger()

    try:
        lambda_config = LambdaConfig(path=file_name,
                                     lambda_name=lambda_name,
                                     makala_config=makala_config)
    except Exception as e:
        logger.error("{}-{}".format(str(e), "could not read configuration file!"))

    return lambda_config


def get_lambda_arn(cache_dir, lambda_name):
    lambda_arn_path="{}/{}.arn".format(cache_dir, lambda_name)
    with open(lambda_arn_path) as fh:
        lambda_arn = fh.read()

    return lambda_arn.strip("\n")

if __name__ == "__main__":

    main()

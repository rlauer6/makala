# README

# Background

`makala` is a Python script to create a light weight Makefile based
serverless framework for AWS Python lambdas.

# Why?

Sometimes a `Makefile` is a good thing and besides I'm smitten with
Makefiles.

# Requirements

* AWS CLI
* AWS permissions to:
  * create IAM roles
  * create IAM policies
  * create/update/invoke Lambdas
* boto3
* python >= 3.6
* GNU make

# Quick start

## Installation

```
git clone https://github.com/rlauer6/makala.git
cd makala
python setup.py install
```

## Create an AWS Python Lambda

1. Create a new project

        mkdir foo
        cd foo

1. Create a configuration file 

        cat <foo.yaml
        description: `my foo handler`
        handler: handler
        logs:
          level: info
          retention: 7
        name: foo
        ^D

1. Create the `Makefile`

        makala foo

1. Create a Python handler

        cat <foo.py
        import json
        
        def handler(event, context):
            return json.dumps(event)
        ^D

1. Install the Lambda

        make

1. Test your Lambda

        aws lambda invoke --function-name foo --payload '{"test":1}' foo.rsp

1. Make changes to the Lambda and redeploy

        touch foo.py
        make

1. Make changes to your Lambda configuration and redeploy

        touch foo.yaml
        make

1. Delete your Lambda

        make real-clean

# Gory Details

This script essentially creates a `Makefile` that will help you
quickly deploy and update Python based Lambda functions.  The
`Makefile` has been written to __do the right thing__ based on changes
to either your Lambda configuration file or the Lambda script itself.
Additionally, you can add dependencies on modules or other artifacts
you need to deploy by editing the `Makefile`.


## Adding Modules

...TBD

## Lambda Role

...TBD

## VPC

...TBD

## Logs

...TBD

## virtualenv

...TBD

## Setting defaults in `makala.cfg`

...TBD

# Troubleshooting

_An error occurred (ResourceConflictException) when calling the
UpdateFunctionCode operation: The operation cannot be performed at
this time. The function is currently in the following state:
'Pending'_

This is a known error that occurs when you try to update the function
code or function configuratoin before the Lambda is available.  Try
again later.

_An error occurred (InvalidParameterValueException) when calling the
CreateFunction operation: The role defined for the function cannot be
assumed by Lambda._

This error may occur if you delete a role (`make real-clean`) and then
attempt to create role of the same name.  Try re-deploying the Lambda:

```
touch foo.py
make
```

# FAQ

__Why is the script called "makala"?__

Originally it was going to be 'make-a-lambda' but that hardly rolls of
the tounge.  A mangled version of that might be 'makala' which is the
Hawaiian word that means "loosen" or "untie" among other meanings.  So
the hope here is that 'makala' loosens the friction for creating a Lambda.

# TBDs

* [ ] option to create configuration stub
* [ ] option to create configuration from an existing lambda
* [ ] add template path to configuration to allow users to edit
      template



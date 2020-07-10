# README

# Background

`makala` is a Python script to create a light weight Makefile based serverless
framework for AWS Python lambdas.

# Why?

Sometimes a `Makefile` is a good thing and I'm smitten with Makefiles.

# Requirements

...TBD

# Quick start

## Installation

```
git clone https://github.com/rlauer6/makala.git
cd makala
python setup.py install
```

## Create an AWS Python Lambda

1. Create a new project
```
mkdir foo
cd foo
```
1. Create a configuration file 
```
cat <foo.yaml
description: `my foo handler`
handler: handler
logs:
  level: info
  retention: 7
name: foo
^D
```
1. Create the `Makefile`
```
$ makala foo
```
1. Create a Python handler
```
cat <foo.py
import json

def handler(event, context):
    return json.dumps(event)
^D
```
1. Install the Lambda
```
make
```
1. Test your Lambda
```
aws lambda invoke --function-name foo --payload '{"test":1}' foo.rsp
```
1. Make changes to the Lambda and redeploy
```
touch foo.py
make
```
1. Make changes to your Lambda configuration and redeploy
```
touch foo.yaml
make
```
1. Delete your Lambda
```
make real-clean
```

# Gory Details

...TBD

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

# TBDs

* [ ] option to create configuration stub
* [ ] option to create configuration from an existing lambda


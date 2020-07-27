# README

# Background

`makala` is a Python script to create a light weight Makefile based
serverless framework for AWS Python lambdas.

# Why?

Sometimes a `Makefile` is a good thing and besides I'm smitten with
Makefiles.

# Requirements

* AWS CLI v2
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
make install
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

        aws lambda invoke --function-name foo --payload '{"test":1}' \
          --cli-binary-format raw-in-base64-out foo.rsp

1. Make changes to the Lambda and redeploy

        touch foo.py
        make

1. Make changes to your Lambda configuration and redeploy

        touch foo.yaml
        make

1. Delete your Lambda

        make uninstall

# Gory Details

This script essentially creates a `Makefile` that will help you
quickly deploy and update Python based Lambda functions.  The
`Makefile` has been written to __do the right thing__ based on changes
to your Lambda configuration file, the Lambda script itself or other
Python artifacts you've added to the project.

## Configuration files

`makala` uses two configuration files to create your `Makefile`:

* `makala.cfg`
* `{lambda-name}.yaml`

### `makala.cfg`

The package file `makala.cfg` provides default values for
your Lambda configuration.  If `makala` finds a `makala.cfg` in your
current working directory, it will use that to provide defaults.

```
[DEFAULT]
cache_dir = cache
region = us-east-1
timeout = 120
memory = 128
log_retention = 7
runtime = python3.6
```

### `{lambda-name}.yaml`

This file is used to configure the serverless environment for your
Lambda.

```
description: description of your lambda
env:
  KEY_NAME: value
handler: handler_entry_point
logs:
  level: info
  retention: 7
memory: 128
name: foo
region: us-east-1
role: foo-role
runtime: python3.6
service: sns.amazonaws.com
timeout: 120
vpc:
  subnet_ids:
  -
  -
  ...
  security_group_ids:
  -
  -
  ...
```

You can generate a stub configuration file thusly:

```
makala -g foo
```

This will create file that looks something like this:

```
description: foo
handler: handler
logs:
  level: info
    retention: 7
memory: 128
name: foo
region: us-east-1
role: foo-role
runtime: python3.6
service: ''
timeout: 120
```

## How the `Makefile` works

Makefiles work by building targets based on dependencies. A Lambda is
dependent on the following build artifacts:

* a zip file containing your code and possibly other modules and a
virtual environment for your Python handler
* the Python handler
* the configuration of the Lambda
  * memory allocated
  * VPC configuration if necessary
  * timeout
  * role
  * etc

When you invoke `make` the first time, the Lambda function and role if
necessary will be created along with several target files in your
local cache directory that maintain the state of the deployment.
Depending on the state of your configuration file, it too may be
updated to provide defaults.

## Adding Modules

To include additonal artifacts to your Lambda deployment package, you can add
a `modules` option listing the modules that should be included.

```
modules:
- foo/bar.py
- foo/baz.py
- foo/buz.py
```

Likewise to add packages that are local to your project, add a
`package` section listing the directory name where your package is
located.  It should reside in the root of your project.

```
packages:
- my_package
```

After editing the configuration file run `make`. Running `make` will
rebuild the zip file and redeploy your Lambda. Note that the
`Makefile` will be rewritten by `makala` as well whenever a change is
made to the configuration file. The zipfile has a dependency on any
modules or packages you might add using the `modules` option.  This
will cause the pattern rule for compliling Python scripts to check
your modules before packaging.

```
MODULES = \
    foo/bar.py

GMODULES = $(MODULES:.py=.pyc)
...
%.pyc: %.py
	python -c "import sys; import py_compile; sys.exit(0) if py_compile.compile('"$<"', '"$@"') else sys.exit(-1)"
```

## Lambda Role

You need to specify an IAM role that gives your [Lambda
permissions](https://docs.aws.amazon.com/lambda/latest/dg/lambda-permissions.html). The
role must exist before you attempt to create a new Lambda.
Accordingly, `makala` will automatically create an appropriate role
with the appropriate permissions and policy attachments if the role
speficied in your configuration file does not exist, you have not
specified a role value or you have not
specified a custom role using the `custom_role` option.

If you don't specify a custom role, `makala` will create the role with
the name you specify in the `role` option or it will use the default
role name *{lamda-name}-role*.

If you have specfied a VPC in your configuration file so that your
lambda can access VPC resources, the policy:

* arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

...will be attached to the role that `makala` creates. Otherwise, the
policy attached will be:

* arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

If you are managing the role outside of this
framework, set the `custom_role` option in your configuration file.

```
custom_role = my_custom_role_name
```

__NOTE__

_A `make uninistall` will delete roles created by `makala` but not
your externally managed role._

## Service Permissions

If you have specified a service in the configuration file
(e.g. `service: sns.amazonaws.com`), then the `Makefile` will add the
appropriate permissions to allow the service to invoke your Lambda.

_Note that if you change or remove the service entry the `Makefile`
will remove or add the new permissions._

## VPC

Some Lambdas may need access to resources in your private subnet.  You
specify the VPC, subnets and security groups in the configuration
file's `vpc` section.

```
vpc:
  id: {vpc-id}
  subnet_ids:
  - {subnet-id}
  ...
  security_group_ids:
  - {security-group-id}
  ...
```

`makala` will discover your private subnets and default VPC for you if
you specify a stub `vpc` section like this:

```
vpc:
  id: default
```

...then execute `makala` to rewrite your configuration file and
`Makefile`.

```
makala -o foo
```

## Logs

If `makala` creates the Lambda role it will either attach the
_AWSLambdaBasicExecutionRole_ or the _AWSLambdaVPCAccessExecutionRole_
both of which will include permissions that allow your Lambda to
produce CloudWatch log streams. Use the `logs` section to specify the
retention time in days for the logs.  Additionally, you can add a
`level` value (debug, info, warn, error) that will signal `makala` to
add an environment variable LOG_LEVEL to your Lambda configuration.
You could potentially use this in your Python handler.

```python
logger = logging.getLogger()

if "LOG_LEVEL" in os.environ:
    if os.environ["LOG_LEVEL"] == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif os.environ["LOG_LEVEL"] == "INFO":
        logger.setLevel(logging.INFO)
    elif os.environ["LOG_LEVEL"] == "WARN":
        logger.setLevel(logging.WARN)
    elif os.environ["LOG_LEVEL"] == "ERROR":
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.ERROR)
```

## virtualenv

You can add add dependencies to your project by creating a virtualenv
in the root directory of your project and then using `pip` to install
them.  The `Makefile` file automatically add this environment to the
deployment package.

```
python -m venv .
. bin/activate
pip install mysql-connector
```

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

This error may occur if you delete a role (`make uninstall`) and then
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

* [x] option to create configuration stub
* [ ] option to create configuration from an existing lambda
* [ ] add template path to configuration to allow users to edit
      template



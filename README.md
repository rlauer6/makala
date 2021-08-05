# README

# Overview

`makala` is a Python script to create a light-weight `Makefile` based
serverless framework for AWS Python based Lambdas. It can also create the
Terraform framework for your Lambda.

# Why?

Sometimes a `Makefile` is a good thing and besides I'm smitten with
`Makefile`s. If you're not, then you can still `makala` to create some
Terraform you can apply to create your serverless function.

## Why should I use the `Makefile`?

Using `make` does a few things _automagically_ for you:

* Quick syntax check of your Python code (TBD: linting, unit testing)
* Recognizes dependency changes to build new Lambda package (including
  requirements)
* Creates necessary IAM permission
* Creates other AWS resources (SNS, TBD: buckets)
* Rebuilds Lambda package (`make clean && make`)

## Why should I use the Terraform option?

If your requirements are more than basic and you are familiar with
Terraform, this option gives you the most flexibility by creating the
necessary Terraform resources that you can modify on your own.
`makala` does not provide for every scenario or for every option for
resources.  Using the Terraform option you can modify the resources
for your use case.

# Requirements

* AWS CLI v2 
* AWS permissions to:
  * create IAM roles
  * create IAM policies
  * create/update/invoke Lambdas
* boto3
* jinja2
* yaml
* python >= 3.6
* GNU make

_See `requirements.txt` for latest set of required Python modules._

# Quick start

## Installation

```
git clone https://github.com/rlauer6/makala.git
cd makala
pip install -r requirements.txt
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
   ```
   make
   ```
1. Test your Lambda
   ```
   echo '{"test":1}' > test-foo.json
   make test
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
   make uninstall
   ```
   
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

You create this file to configure your Lambda.

```
description: description of your lambda
profile: optional-aws-profile
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
source_arn: {optional source ARN}
source_account: {optional source account}
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
makala -s events -g foo
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
service: events.amazonaws.com
source_account: '311974035819'
source_arn: ''
timeout: 120
```

### Services
You can create stub configuration files for various services that you
want to be supported by your Lambda. The example above creates a stub
for a Lambda that supports a CloudWatch event. Support services include:

* '-s events' => events.amazonaws.com
* '-s sns'    => sns.amazonaws.com
* '-s s3'     => s3.amazonaws.com
* '-s sqs'    => sqs.amazonaws.com
* '-s logs'   => logs.amazonaws.com

#### SNS

For supporting SNS event, add a parameter of `sns-topic`
to your configuration file which describes the topic your Lambda
should subscribe to.

#### SQS

For supporting SQS events, the configuration should include a `sqs`
section as shown below:

```
sqs:
  queue_name:
  deduplication_scope: 
  delay_seconds:
  fifo_queue:
  kms_master_key_id:
  maximum_message_size:
  message_retention_period:
  policy:
  receive_message_wait_time_seconds :
  redrive_policy:
    deadletter_target_arn:
    max_receive_count:
  visibility_timeout:
```

If your service pattern selected is SQS and you do not have a section
for the SQS configuration, `makala` will add a section with defaults.
When you do a `make`, the `Makefile` will also create the queue and
the event mapping that allows your Lambda to service the queue.

#### S3

For supporting S3 events, the configuration includes a `bucket`
section.

```
bucket:
  events:
  - s3:ObjectCreated:Post
  filter:
    name: prefix
    value: ''
  name: REPLACE-ME-WITH-BUCKET-NAME
```

* `events` describes the events that will trigger your Lambda.  See
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html
  for more details on events that you can use to trigger your Lambda.
* `filter` describes one or more filters that are used to filter
  bucket events. `name` can be one of 'prefix' or 'suffix'.
* `name` is the name of your bucket.

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
* a role
* permissions

When you invoke `make` the first time, the Lambda function and role if
necessary will be created along with several target files in your
local cache directory that maintain the state of the deployment.
Depending on the state of your configuration file, it too may be
updated to provide defaults.

### Customizing the `Makefile`

The `Makefile` itself is generated from a jinja2 template that is
packaged with the script. When you create your first `Makefile`, the
jinja2 template will also be copied to your working directory.  Since
the `Makefile` itself is dependent on your `.yaml` configuration file,
any time it is updated, invoking `make` will recreate your `Makefile`
from the jinja2 template.

*If you want to customize the `Makefile`, make changes to the
template, not the `Makefile`.*  Rerun `makala` to generate a fresh
`Makefile` whenever you alter the template.  Add the template to your
code repo to make sure that it is preserved for future changes to your
project.

### `Makefile` Targets

* `make` or `make all`
  _...will 1) create the role if it does not exist, 2) check your Python
  script by compling, 3) add permissions to the Lambda as required, 4)
  create a `requirements.txt` file if it does not exist, 4) create the
  zip file to be uploaded and finally 5) upload the Lambda_
* `make check`
  _...will check the status of the Lambda and report if it is in a
  *Pending* or *Active* state_
* `make clean`
  _...will remove any `.pyc` files and the `.zip` file_
* `make zip`
  _...will create the zip file_
* `make test`
  _...will invoke your Lambda if a `.json` file of the form
  `test-{lambda-name}.json` exists in the current working directory_
* `make plan` or `make apply`
  _...will execute `terraform` if you have produced Terraform
  resources in the `./terraform` directory_
* `make uninstall`
  _...will delete your Lambda and the role associate with it if it is
  a role created by `makala`_
  
There are other intermediate targets that build the dependencies but
those should not generally be used from the command line.

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

To add other packages that you have added to your virtual enviroment,
add a `requirements.txt` file as described later in this `README`.

After editing the configuration file run `make`. Running `make` will
rebuild the zip file and redeploy your Lambda. *Note that the
`Makefile` will also be rewritten by `makala` as well whenever a
change is made to the configuration file.* The zipfile has a
dependency on any modules or packages you might add using the
`modules` option.  This will cause the pattern rule for compliling
Python scripts to check your modules before packaging.

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

## Services

### Permissions

If you have specified a service in the configuration file
(e.g. `service: sns.amazonaws.com`), then the `Makefile` will add the
appropriate permissions to allow the service to invoke your Lambda.

_Note that if you change or remove the service entry the `Makefile`
will remove or add the new permissions._

### S3

If your service is S3, presumably your Lambda is responding to a
bucket event.  Therefore you will want to configure the bucket and
bucket notifications.

Set the bucket name, bucket events that will trigger your Lambda and
if desired bucket filters.

```
bucket:
  name: my-bucket
  events:
  - s3:ObjectCreated:Put
  - s3:ObjectCreated:Post
  - s3:ObjectCreated:CompleteMultipartUpload
  filter:
    name: prefix
    value: foo
```

If the bucket does not exist the `Makefile` will create the
bucket. The `Makefile` will also create the notification.

### SNS Topic

If your service is SNS, presumably your Lambda is responding to an SNS
notification. Therefore, you probably want to subscribe to a topic.
`makala` will automatically create an SNS topic for you if it does not
exist and create the proper Lambda permissions so that SNS can invoke
your Lambda.  Set `sns_topic` in your configuration file to the name
of the topic you have created or want to create.

```
service: sns.amazonaws.com
sns_topic: foo-topic
```

### Logs

TBD

### Simple E-Mail Service

TBD

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
    log_level = os.environ["LOG_LEVEL"].upper()
    if log_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif log_level == "INFO":
        logger.setLevel(logging.INFO)
    elif log_level == "WARN":
        logger.setLevel(logging.WARN)
    elif log_level == "ERROR":
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.ERROR)
```

## Adding Package Dependencies

You can add add dependencies to your project by creating a virtualenv
in the root directory of your project and then using `pip` to install
them.


```sh
python -m venv .
. bin/activate
pip install mysql-connector
```

The `Makefile` file automatically add this environment to the
deployment package. `Makefile` will first look for a
`requirements.txt` file in your project root directory.  If it finds
one, it will add only those packages to the Lambda zipfile in order to
create the smallest possible deployment package.  If no
`requirements.txt` is found, then `Makefile` will run:

```sh
pip freeze > requirements.txt
```

# Troubleshooting

_An error occurred (ResourceConflictException) when calling the
UpdateFunctionCode operation: The operation cannot be performed at
this time. The function is currently in the following state:
'Pending'_

This is a known error that occurs when you try to update the function
code or function configuration before the Lambda is available.  Try
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

# Terraform

If you would like to produce the Terraform resources associated with
the serverless function you can have `makala` generate the necesary
Terraform files.

```
makala -t my-lambda-function
```

Normally, `makala` will create a `Makefile` you can use to create the
necessary resources to install and run your Lambda.  To create the
resources using Terraform, use the `-t` option.  This will create a
`terraform` directory in your current directory and produce the
following files:

* `main.tf` - provides the Terrform for creating the necessary
  resources
* `variables.tf` - variables file stub for adding variables you may
  need as you develop more infrastructure around your Lambda
* `provider.tf` - a provider stub you can alter before running
  `terraform init`
* `Makefile` - and of course a `Makefile` with target `plan` and `apply`

The Terraform that is produced will mimic and perform the same actions
as the `Makefile`. You can use both the `Makefile` and your Terraform
together to continue testing your Lambda, however if you start using
Terraform to create resources, you should only use the `Makefile` for
testing and executing Terraform.  In other words, you'll only want to
use these targets:

* `make test`
* `make check`
* `make clean`
* `make zip`
* `make plan`
* `make apply`

Typically you may start by using `makala` to create your `Makefile`, a
stub Python function, a role for your Lambda (if you do not have a
custom role that has already been created), and the necessary policies
that provide the permission for your Lambda to be invoked.  You can then
proceed to create the Terraform that will provide the same result.

```
makala -g my-lambda-funtion
makala -t my-lambda-function
cd terraform
terraform init
```

* Before running `terraform init` edit the `provider.tf` (or the
  `terraform-provider.jinja2` template and re-run `makala`) file to
  configure your own state file location and type.
* You'll also find that some resources are simply stubs for you to
  complete.  For example, if your Lambda is the target of a CloudWatch
  function, you'll want to configure some CloudWatch resources.
  `makala` provides some stubs for this purpose.  As `makala` matures,
  additionally stubs may be provided based on the service that is
  invoking the Lambda.
* When creating the zip file that contains your Lambda service, the
  `Makefile` will timestamp files with a constant time from the past
  so that the hash value of the zip file remains the same when no code
  changes are made.  Otherwise the sha256 value of the zip file will
  change even if there are no code differences between the curren
  Lambda state and your zip file.

## Customizing the Terraform and Terraform `Makefile`

`makala` gives you a headstart for building your infrastructure using
Terraform but may not provide all of the resources you need for your
specific application. To create additional resources you can edit the
`main.tf`, `provider.tf` and `variables.tvar` files created for you
when you ran `makala -t`.  If you want to keep things in sync with
your configuration file so you can re-run `makala`, edit the
`terraform.jinja2`, `terraform-provider.jinja2` or the
`terraform-variables.jinja2` files that are copied to your `terraform`
directory.

Likewise, when you generate the Terraform for your project `makala`
will use a jinja2 template for creating the `Makefile`.  The template
will be copied to your `terraform/` directory.  Modify this file if
you want to customize if for your needs.  When you re-run `makala` it
will use the template in your `terraform/` directory to recreate the
`Makefile`.


# NOTES and HINTS

* To view the permissions granted for a service to invoke a Lambda
  function use:
  ```
  aws lambda get-policy --function-name lambda-name | jq -r .Policy | jq -r . | less 
  ```
* To view the role for the Lambda funcion
  ```
  ROLE=$(aws iam get-role --role-name $(aws lambda get-function-configuration \
    --function-name lambda-function | jq -r .Role))
  ```
* To view the attached policies for the role
  ```
  aws iam list-attached-role-policies --role-name $ROLE
  ```
* For SES and S3 you must include the `source_account` or `source_arn`
  option. If you include the `source_account` with no value, `makala`
  will determine the account id using:
  ```
  aws sts get-caller-identity
  ```
* _Note that other services like SNS will not work with a `source_account`
  and do not require either option._


# RECIPES

## I want to create a Lambda that is triggered by an S3 bucket event.

```
TBD
```

## I want to create a Lambda that subscribes to an SNS topic.

```
TBD
```

## I want to create a Lambda that is launched by a CloudWatch event.

```
TBD
```

## I want to create a Lambda that is invoked by CloudWatch logs.

```
TBD
```

# FAQ

## __Why is the script called "makala"?__

Originally it was going to be 'make-a-lambda' but that hardly rolls of
the tongue.  A mangled version of that might be 'makala' which is the
Hawaiian word that means "loosen" or "untie" among other meanings.  So
the hope here is that 'makala' loosens the friction for creating a Lambda.

## __Makefile is breaking.  What should I do?__

Try `DEBUG=1 make` and view the steps carefully.  If you want to
modify the `Makefile`, modify the `Makefile.jinja2` template that is
copied to your working directory the first time you execute `makala`.
If you can't find the problem, submit an issue.

## __Should I use the `Makefile` or Terraform to create Lambda functions?__

Good question, there are some good reasons to try to manage all of
your application infrastructure using a single tool.  Lambdas often
rely on other resources (buckets, queues, event rules, etc) and your
Lambda may not be the only component that requires those resources.
Personally, I find that using the `Makefile` approach for prototyping
and testing is the most satisfying and efficient, while using
Terraform leads to a more maintainable and transparent infrastructure.

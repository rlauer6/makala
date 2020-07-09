# README

# `makala` - a Makefile based serverless framework for AWS Python lambdas.

# Why?

Sometimes a `Makefile` is a good thing.

# Quick start

## Create a serverless Python AWS Lambda

1. Create a configuration file 
   ```
$ cat <foo.yaml
description: `my foo handler`
env:
  log_level: INFO
handler: handler
logs:
  level: info
  retention: 7
name: foo
^D
   ```
1. Create the `Makefile`
   ```
$ makala.py foo
   ```
1. Create a Python handler
1. Install the Lambda
   ```
   $ make
   ```

# TBD

* option to create configuration stub
* option to create configuration from an existing lambda
* real-clean to delete role

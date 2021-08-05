import setuptools

with open("VERSION", "r") as fh:
    version = fh.readline()

with open("README.md", "r") as fh:
    long_description = fh.read()

    setuptools.setup(
        name="makala",
        version=version,
        author="Rob Lauer",
        package_data={
            'makala': [
                'data/Makefile.jinja2',
                'data/makala.cfg',
                'data/lambda.py',
                'data/terraform.jinja2',
                'data/terraform-Makefile.jinja2',
                'data/terraform-provider.jinja2',
                'data/terraform-variables.jinja2'
                ]
            },
        author_email="rlauer6@comcast.net",
        description="A Makefile based serverless framework for AWS Lambda",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/rlauer6/makala",
        packages=setuptools.find_packages(),
        entry_points={
            'console_scripts': [
                'makala = makala.makala:main'
            ]
        },
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        python_requires='>=3.6',
    )

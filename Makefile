VERSION = 0.0.1

MAKALA_SOURCE = \
    makala/makala.py \
    makala/makala_config.py \
    makala/lambda_config.py \
    makala/aws/utils.py \
    makala/aws/vpc_config.py \
    makala/aws/lambda_role.py \
    setup.py

GMAKALA_SOURCE = $(MAKALA_SOURCE:.py=.pyc)

PACKAGE_FILES = \
    makala/data/makala.cfg \
    makala/data/Makefile.jinja2 \
    makala/data/lambda.jinja2 \
    CHANGELOG \
    LICENSE.txt \
    README.md

%.pyc: %.py
	/usr/bin/python36 -c "import sys; import py_compile; sys.exit(0) if py_compile.compile('"$<"', '"$@"', doraise=False) else sys.exit(-1)"

PYTHON_PACKAGE = \
    dist/makala-$(VERSION)-py3-none-any.whl

all: $(PYTHON_PACKAGE)

$(PYTHON_PACKAGE): $(GMAKALA_SOURCE) $(PACKAGE_FILES)
	rm -rf build dist
	python3 setup.py sdist bdist_wheel

install: $(PYTHON_PACKAGE)
	/usr/local/bin/pip3 install -I dist/makala-$(VERSION)-py3-none-any.whl

CLEANFILES = \
    build \
    dist \
    makala.egg-info

clean:
	rm -rf $(CLEANFILES)
	find . -name '*.pyc' -exec rm {} \;

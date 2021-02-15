VERSION=$(shell cat VERSION)
VERSION=$(shell cat VERSION)

PROJECT_NAME=makala
PACKAGE_NAME=$(shell echo $(PROJECT_NAME) | perl -npe 's/_/\-/g;')

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
    CHANGELOG \
    LICENSE.txt \
    README.md

%.pyc: %.py
	python3 -c "import sys; import py_compile; sys.exit(0) if py_compile.compile('"$<"', '"$@"', doraise=False) else sys.exit(-1)"

PYTHON_PACKAGE = \
    dist/$(PROJECT_NAME)-$(VERSION)-py3-none-any.whl

all: $(PYTHON_PACKAGE)

$(PYTHON_PACKAGE): $(GMAKALA_SOURCE) $(PACKAGE_FILES)
	rm -rf build dist
	python3 setup.py sdist bdist_wheel

install: $(PYTHON_PACKAGE)
	pip3 install -I dist/$(PROJECT_NAME)-$(VERSION)-py3-none-any.whl

CLEANFILES = \
    build \
    dist \
    makala.egg-info

clean:
	rm -rf $(CLEANFILES)
	find . -name '*.pyc' -exec rm {} \;

VERSION = 0.0.1

MAKALA_SOURCE = \
    makala/makala.py \
    makala/makala_config.py \
    makala/lambda_config.py \
    makala/aws/utils.py \
    setup.py

GMAKALA_SOURCE = $(MAKALA_SOURCE:.py=.pyc)

PACKAGE_FILES = \
    makala/data/makala.cfg \
    makala/data/Makefile.jinja2 \
    CHANGELOG \
    LICENSE.txt \
    README.md

%.pyc: %.py
	python -c "import py_compile; py_compile.compile('"$<"', '"$@"')"

PYTHON_PACKAGE = \
    dist/makala-$(VERSION)-py3-none-any.whl

all: $(PYTHON_PACKAGE)

$(PYTHON_PACKAGE): $(GMAKALA_SOURCE) $(PACKAGE_FILES)
	rm -rf build dist
	python setup.py sdist bdist_wheel

install: $(PYTHON_PACKAGE)
	pip install dist/makala-$(VERSION)-py3-none-any.whl

CLEANFILES = \
    build \
    dist \
    makala.egg-info

clean:
	rm -rf $(CLEANFILES)
	find . -name '*.pyc' -exec rm {} \;

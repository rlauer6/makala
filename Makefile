VERSION = 0.0.1

MAKALA_SOURCE = \
    makala/makala.py

AWS_UTILS_SOURCE = \
    makala/aws/utils.py

PYTHON_PACKAGE_FILES = \
    CHANGELOG \
    LICENSE.txt \
    README.md \
    setup.py

PYTHON_PACKAGE = \
    dist/makala-$(VERSION)-py3-none-any.whl

MAKALA_BIN = $(subst .py,.cpython-36.pyc,$(subst makala/, makala/__pycache__/, $(MAKALA_SOURCE)))

AWS_UTILS_BIN = $(subst .py,.cpython-36.pyc,$(subst makala/aws, makala/aws/__pycache__/, $(AWS_UTILS_SOURCE)))

all: $(MAKALA_BIN) $(AWS_UTILS_BIN) $(PYTHON_PACKAGE)

$(MAKALA_BIN): $(MAKALA_SOURCE)
	python -m py_compile $<

$(AWS_UTILS_BIN): $(AWS_UTILS_SOURCE)
	python -m py_compile $<

# require a compile
$(PYTHON_PACKAGE): $(PACKAGE_FILES) $(MAKALA_BIN)
	rm -rf build dist
	python setup.py sdist bdist_wheel

install: $(PYTHON_PACKAGE)
	pip install dist/makala-$(VERSION)-py3-none-any.whl

CLEANFILES = \
    build \
    dist \
    makala/__pycache__ \
    makala/aws/__pycache__ \
    makala.egg-info

clean:
	rm -rf $(CLEANFILES)

bin = venv/bin/
pysources = src/ tests/

build:
	${bin}python -m build

check:
	${bin}black --check --diff --target-version=py38 ${pysources}
	${bin}flake8 ${pysources}
	${bin}mypy ${pysources}
	${bin}isort --check --diff ${pysources}

install: install-python

venv:
	python3 -m venv venv

install-python: venv
	${bin}pip install -U pip wheel
	${bin}pip install -U build
	${bin}pip install -r requirements.txt

format:
	${bin}autoflake --in-place --recursive ${pysources}
	${bin}isort ${pysources}
	${bin}black --target-version=py38 ${pysources}

publish:
	${bin}twine upload dist/*

test:
	${bin}pytest

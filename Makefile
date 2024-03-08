SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)

help: # preview Makefile commands
	@awk 'BEGIN { FS = ":.*#"; print "Usage:  make <target>\n\nTargets:" } \
	/^[-_[:alpha:]]+:.?*#/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: # install Python dependencies
	pipenv install --dev

update: install # update Python dependencies
	pipenv clean
	pipenv update --dev

######################
# Unit test commands
######################
test: # run tests and print a coverage report
	pipenv run coverage run --source=solenoid -m pytest -vv
	pipenv run coverage report -m

coveralls: test # write coverage data to an LCOV report
	pipenv run coverage lcov -o ./coverage/lcov.info

####################################
# Code quality and safety commands
####################################

lint: black mypy # run linters

black: # run 'black' linter and print a review of suggested changes
	pipenv run black --check --diff .

mypy: # run 'mypy' linter
	pipenv run mypy . 

lint-apply: black-apply # apply changes with 'black'

black-apply: # apply changes with 'black'
	pipenv run black .
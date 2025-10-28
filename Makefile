SHELL := /bin/bash
PY := python

.PHONY: setup build physics arch validate tables audit appendices all

setup:
	mkdir -p build/operators results/spectrum results/physics results/arch results/validate reports/appendices reports/validation audit overleaf/appendices
	@echo "Setup completo."

build:
	$(PY) scripts/prep/validate_inputs.py
	$(PY) scripts/build_types.py
	$(PY) scripts/spectrum/compute_spectrum.py
	$(PY) scripts/spectrum/check_convergence.py

physics:
	$(PY) scripts/physics/effective_resistance.py
	$(PY) scripts/physics/fenchel_energy.py

arch:
	$(PY) scripts/arch/metrics_profile.py
	$(PY) scripts/arch/poincare_young_validate.py

validate:
	$(PY) scripts/validate/validation_suite.py
	jupyter nbconvert --to pdf notebooks/validation/validation_report.ipynb --output-dir reports/validation

tables:
	$(PY) scripts/report/report_tables.py

audit:
	$(PY) scripts/audit/generate_hashes.py
	$(PY) scripts/audit/make_manifest.py
	-$(PY) scripts/audit/sign_manifest.py

appendices:
	$(PY) scripts/report/assemble_appendices.py

all: setup build physics arch validate tables audit appendices
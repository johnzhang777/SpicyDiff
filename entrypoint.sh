#!/bin/sh
# Ensure Python can find the spicydiff package regardless of working directory
export PYTHONPATH="/app:${PYTHONPATH}"
exec python -m spicydiff.main "$@"

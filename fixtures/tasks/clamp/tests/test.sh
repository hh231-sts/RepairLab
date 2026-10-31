#!/bin/sh
set -eu
mkdir -p /logs/verifier
if PYTHONPATH=/workspace python -m pytest -q -p no:cacheprovider /tests/test_hidden.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

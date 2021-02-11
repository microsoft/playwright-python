#!/bin/bash

set -e

NOT_ALLOWED_REFERENCES=("Dialog" "Request" "Route")

OUTPUT=$(python buildbots/assets/test-reference-count-async.py)

if [[ "$OUTPUT" != *"PW-OK"* ]]; then
  echo "Script did not run successfully!"
  echo "Output: $OUTPUT"
  exit 1
fi

for CLASS_NAME in ${NOT_ALLOWED_REFERENCES[*]}; do
  echo "Checking $CLASS_NAME"
  if [[ "$OUTPUT" == *"$CLASS_NAME"* ]]; then
    echo "There are $CLASS_NAME references in the memory!"
    echo "Output: $OUTPUT"
    exit 1
  fi
  echo "Check $CLASS_NAME passed"
done

echo "-> Reference count assertions passed!"

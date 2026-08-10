#!/bin/bash

# Feeds audio file to Pulse API.
# Returns transcripts JSON.
# Saves file locally.

AUDIO_FILE_PATH=$1
MODEL_NAME=pulse-pro
LANG=en

OUTPUT_PATH="../outputs/$(basename "${AUDIO_FILE_PATH%.*}").json"

echo "Using audio file: ${AUDIO_FILE_PATH}"

mkdir -p ../outputs

curl --request POST \
  --url "https://api.smallest.ai/waves/v1/stt/?model=${MODEL_NAME}&language=${LANG}" \
  --header "Authorization: Bearer $SMALLEST_API_KEY" \
  --header "Content-Type: application/octet-stream" \
  --data-binary "@${AUDIO_FILE_PATH}" > "$OUTPUT_PATH"

echo "Output is at ${OUTPUT_PATH}"

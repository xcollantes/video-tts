#!/bin/bash

# Feeds audio file to Pulse API.
# Returns an SRT subtitle file.
# Saves file locally.

AUDIO_FILE_PATH=$1
MODEL_NAME=pulse-pro
LANG=en

OUTPUT_PATH="outputs/$(basename "${AUDIO_FILE_PATH%.*}").srt"

echo "Using audio file: ${AUDIO_FILE_PATH}"

mkdir -p outputs

# ponytail: one subtitle cue per word (simplest correct SRT); group by
# gap/length into phrases like transcribe.py's words_to_srt if choppy.
curl --request POST \
  --url "https://api.smallest.ai/waves/v1/stt/?model=${MODEL_NAME}&language=${LANG}&word_timestamps=true" \
  --header "Authorization: Bearer $SMALLEST_API_KEY" \
  --header "Content-Type: application/octet-stream" \
  --data-binary "@${AUDIO_FILE_PATH}" \
  | jq -r '
      def srt_ts: (. as $s
        | ($s | floor | gmtime | strftime("%H:%M:%S")) as $hms
        | (($s * 1000 | floor) % 1000) as $ms
        | "\($hms),\($ms | tostring | if length==1 then "00"+. elif length==2 then "0"+. else . end)");
      .words | to_entries[] | "\(.key+1)\n\(.value.start|srt_ts) --> \(.value.end|srt_ts)\n\(.value.word)\n"
    ' > "$OUTPUT_PATH"

echo "Output is at ${OUTPUT_PATH}"

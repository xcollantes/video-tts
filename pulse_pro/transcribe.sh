#!/bin/bash

# Feeds audio file to Pulse API.
# Returns an SRT subtitle file.
# Saves file locally.

AUDIO_FILE_PATH=$1
MODEL_NAME=pulse-pro
LANG=en

OUTPUT_PATH="outputs/$(basename "${AUDIO_FILE_PATH%.*}").srt"
WORDS_PER_CUE=8

echo "Using audio file: ${AUDIO_FILE_PATH}"

mkdir -p outputs

# ponytail: fixed-size word chunks per cue (simple, no gap/silence
# awareness); switch to gap/length grouping like transcribe.py's
# words_to_srt if cues should break on pauses instead.
curl --request POST \
  --url "https://api.smallest.ai/waves/v1/stt/?model=${MODEL_NAME}&language=${LANG}&word_timestamps=true" \
  --header "Authorization: Bearer $SMALLEST_API_KEY" \
  --header "Content-Type: application/octet-stream" \
  --data-binary "@${AUDIO_FILE_PATH}" \
  | jq -r --argjson chunk "$WORDS_PER_CUE" '
      def srt_ts: (. as $s
        | ($s | floor | gmtime | strftime("%H:%M:%S")) as $hms
        | (($s * 1000 | floor) % 1000) as $ms
        | "\($hms),\($ms | tostring | if length==1 then "00"+. elif length==2 then "0"+. else . end)");
      .words as $w
      | [range(0; ($w|length); $chunk) | $w[.:.+$chunk]]
      | to_entries[]
      | .value as $c
      | "\(.key+1)\n\($c[0].start|srt_ts) --> \($c[-1].end|srt_ts)\n\($c | map(.word) | join(" "))\n"
    ' > "$OUTPUT_PATH"

echo "Output is at ${OUTPUT_PATH}"

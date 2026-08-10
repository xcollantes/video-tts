#!/bin/bash

# Extract audio from videos if necessary.

VIDEO_PATH=$1
OUTPUT_PATH="extraction_outputs/$(basename "${VIDEO_PATH%.*}").wav"

mkdir -p extraction_outputs

ffmpeg -i "$VIDEO_PATH" \
    -vn `# drop the video stream, audio only` \
    -ac 1 `# downmix to mono` \
    -ar 16000 `# resample to 16kHz` \
    -c:a pcm_s16le `# encode audio as 16-bit PCM WAV` \
    "$OUTPUT_PATH"


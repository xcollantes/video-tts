# Video STT

For cheaper Youtube and Social media transcriptions in English and beyond.

## Pulse Pro

At the time of this writing in August 2026, i found that Pulse Pro is most cost effective.


Quality - WER of 5.42% (lower better) which is top 3 of competitors
Price - $0.0004 per minute so $0.024 per hour of audio
Speed is decent at 25 RPM  

https://docs.smallest.ai/models/model-cards/speech-to-text/pulse-pro

## Process

Starting with a video file.

### Prereq

```bash
brew install ffmpeg        # or: apt install ffmpeg
```

Smallest API key.

```bash
export SMALLEST_API_KEY=
```

### pull out audio only

```bash
ffmpeg -i <VIDEO FILE> \
    -vn \         # Drops the video stream
    -ac 1 \       # downmixes to mono 
    -ar 16000 \   # resample audio
    -c:a pcm_s16le \
    audio.wav
```

### Call the API as a test

```bash
curl --request POST \
  --url "https://api.smallest.ai/waves/v1/stt/?model=pulse-pro&language=en&word_timestamps=true" \
  --header "Authorization: Bearer $SMALLEST_API_KEY" \
  --header "Content-Type: application/octet-stream" \  # just to test API connection
  --data-binary "@test.wav"
```

Response should be something:

```json
{
  "status": "success",
  "transcription": "full text here",
  "words": [{"word": "Hello", "start": 0.32, "end": 0.40, "confidence": 0.96}],
  "metadata": {"duration": 5.6, "processing_time_ms": 240.51, "rtfx": 23.3},
  "request_id": "uuid"
}
```

### Call real python file

```bash
uv venv
source .venv/bin/activate
uv sync
uv run transcribe_pulse.py ./videos --outdir ./transcripts
```

See options:

```
uv run transcribe.py --help
usage: transcribe.py [-h] [--outdir OUTDIR] [--diarize] input

positional arguments:
  input            MP4 file or directory of MP4 files

options:
  -h, --help       show this help message and exit
  --outdir OUTDIR
  --diarize        request speaker labels
```




#!/usr/bin/env python3
"""
Transcribe MP4 files with Smallest.ai Pulse Pro.

Usage:
    export SMALLEST_API_KEY=sk_...
    python transcribe_pulse.py /path/to/videos --outdir ./transcripts

Outputs per video: .txt (plain transcript), .srt (subtitles), .json (raw response).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

API_URL = "https://api.smallest.ai/waves/v1/stt/"
MODEL = "pulse-pro"          # English only. Use "pulse" for multilingual.
MAX_CHUNK_SECONDS = 1800     # 30 min per request keeps payloads manageable.
RATE_LIMIT_SLEEP = 2.5       # Standard plan allows 25 requests/min.


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{proc.stderr[-2000:]}")
    return proc.stdout


def duration_seconds(path: Path) -> float:
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(out.strip())


def extract_audio(video: Path, workdir: Path) -> list[Path]:
    """Extract 16 kHz mono WAV, split into chunks if long."""
    total = duration_seconds(video)
    stem = video.stem

    if total <= MAX_CHUNK_SECONDS:
        wav = workdir / f"{stem}.wav"
        run([
            "ffmpeg", "-y", "-i", str(video),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            str(wav),
        ])
        return [wav]

    pattern = workdir / f"{stem}_%04d.wav"
    run([
        "ffmpeg", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        "-f", "segment", "-segment_time", str(MAX_CHUNK_SECONDS),
        str(pattern),
    ])
    return sorted(workdir.glob(f"{stem}_*.wav"))


def transcribe_chunk(wav: Path, api_key: str, diarize: bool) -> dict:
    params = {
        "model": MODEL,
        "language": "en",
        "word_timestamps": "true",
    }
    if diarize:
        params["diarize"] = "true"

    with open(wav, "rb") as f:
        audio = f.read()

    for attempt in range(4):
        resp = requests.post(
            API_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/octet-stream",
            },
            data=audio,
            timeout=600,
        )
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"  rate limited, waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()

    raise RuntimeError(f"gave up on {wav.name} after repeated 429s")


def srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def words_to_srt(words: list[dict], max_chars: int = 42, max_gap: float = 0.8) -> str:
    """Group word-level timings into readable subtitle cues."""
    cues, current = [], []

    def flush():
        if not current:
            return
        text = " ".join(w["word"] for w in current).strip()
        cues.append((current[0]["start"], current[-1]["end"], text))
        current.clear()

    for w in words:
        if current:
            gap = w["start"] - current[-1]["end"]
            length = sum(len(x["word"]) + 1 for x in current)
            speaker_change = w.get("speaker") != current[-1].get("speaker")
            if gap > max_gap or length > max_chars or speaker_change:
                flush()
        current.append(w)
    flush()

    lines = []
    for i, (start, end, text) in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{srt_timestamp(start)} --> {srt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def process(video: Path, outdir: Path, api_key: str, diarize: bool) -> float:
    workdir = outdir / ".work"
    workdir.mkdir(parents=True, exist_ok=True)

    chunks = extract_audio(video, workdir)
    all_words, texts, minutes = [], [], 0.0
    offset = 0.0

    for chunk in chunks:
        print(f"  -> {chunk.name}")
        result = transcribe_chunk(chunk, api_key, diarize)
        texts.append(result.get("transcription", ""))

        for w in result.get("words", []):
            w = dict(w)
            w["start"] += offset
            w["end"] += offset
            all_words.append(w)

        chunk_len = result.get("metadata", {}).get("duration") or duration_seconds(chunk)
        offset += chunk_len
        minutes += chunk_len / 60
        chunk.unlink()
        time.sleep(RATE_LIMIT_SLEEP)

    stem = video.stem
    (outdir / f"{stem}.txt").write_text(" ".join(texts).strip(), encoding="utf-8")
    (outdir / f"{stem}.json").write_text(
        json.dumps({"words": all_words}, indent=2), encoding="utf-8"
    )
    if all_words:
        (outdir / f"{stem}.srt").write_text(words_to_srt(all_words), encoding="utf-8")

    return minutes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="MP4 file or directory of MP4 files")
    ap.add_argument("--outdir", default="transcripts")
    ap.add_argument("--diarize", action="store_true", help="request speaker labels")
    args = ap.parse_args()

    api_key = os.environ.get("SMALLEST_API_KEY")
    if not api_key:
        sys.exit("Set SMALLEST_API_KEY first.")

    src = Path(args.input)
    videos = sorted(src.glob("*.mp4")) if src.is_dir() else [src]
    if not videos:
        sys.exit(f"No MP4 files found in {src}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    total_minutes = 0.0
    for video in videos:
        print(f"[{video.name}]")
        try:
            total_minutes += process(video, outdir, api_key, args.diarize)
        except Exception as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)

    print(
        f"\nDone. {len(videos)} file(s), {total_minutes:.1f} audio minutes, "
        f"about ${total_minutes * 0.004:.2f} at $0.004/min."
    )


if __name__ == "__main__":
    main()

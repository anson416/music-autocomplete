#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: main.py

import argparse
import math
import shutil
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal

import uvicorn
from fastapi import Depends, FastAPI, UploadFile
from midi2audio import FluidSynth
from musgen.gansynth import synth
from musgen.magenta_rnn import MagentaRNN
from musgen.types_ import NoteDicts
from musgen.utils import notes2noteseq, noteseq2notes
from pydantic import BaseModel
from scipy.io import wavfile


class MagentaRNNArgs(BaseModel):
    notes: NoteDicts
    qpm: int
    extend_duration: int
    temperature: float = 1.0


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(tmp_dir)


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def main():
    return {"msg": "musgen"}


@app.post("/melody_rnn/{model}")
def melody_rnn(
    model: Literal["basic_rnn", "mono_rnn", "lookback_rnn", "attention_rnn"],
    args: MagentaRNNArgs = Depends(),
) -> NoteDicts:
    print(f"Extending notes using {model} from Melody RNN")
    last_end_time = max([note["start_time"] + note["duration"] for note in args.notes])
    generator = MagentaRNN.MelodyRNN(model)
    seq = generator(notes2noteseq(args.notes, args.qpm), args.extend_duration, args.temperature)
    return [note for note in noteseq2notes(seq) if note["start_time"] >= last_end_time]


@app.post("/performance_rnn/{model}")
def performance_rnn(
    model: Literal["performance", "performance_with_dynamics", "performance_with_dynamics_and_modulo_encoding", "density_conditioned_performance_with_dynamics", "pitch_conditioned_performance_with_dynamics", "multiconditioned_performance_with_dynamics"],
    args: MagentaRNNArgs = Depends(),
) -> NoteDicts:
    print(f"Extending notes using {model} from Performance RNN")
    generator = MagentaRNN.PerformanceRNN(model)
    seq = generator(notes2noteseq(args.notes, args.qpm), args.extend_duration, args.temperature)
    return noteseq2notes(seq)[len(args.notes):]


@app.post("/gansynth")
async def gansynth(
    midi_file: UploadFile,
    seconds_per_instrument: float = 5,
    sample_rate: int = 16000,
) -> List[float]:
    midi_path: Path = Path("tmp") / urllib.parse.quote(midi_file.filename)
    print(f"Synthesizing audio from MIDI {midi_path}")
    try:
        with open(midi_path, "wb") as f:
            f.write(await midi_file.read())
        audio = synth(midi_path, seconds_per_instrument, sample_rate).tolist()
        audio = [value for value in audio if not (math.isnan(value) or math.isinf(value))]
        return audio
    finally:
        if midi_path.exists():
            midi_path.unlink()


@app.post("/midi2wav")
async def midi2wav(midi_file: UploadFile):
    midi_path: Path = Path("tmp") / urllib.parse.quote(midi_file.filename)
    wav_path = Path(f"{midi_path}.wav")
    try:
        with open(midi_path, "wb") as f:
            f.write(await midi_file.read())
        fs = FluidSynth()
        fs.midi_to_audio(midi_path, wav_path)
        sr, audio = wavfile.read(wav_path)
        return {
            "sample_rate": sr,
            "audio": audio.tolist(),
            "dtype": audio.dtype.str,
        }
    finally:
        if midi_path.exists():
            midi_path.unlink()
        if wav_path.exists():
            wav_path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-host", "--host", default="0.0.0.0", type=str,
        help="Host used by FastAPI",
    )
    parser.add_argument(
        "-port", "--port", default=8000, type=int,
        help="Port used by FastAPI",
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)

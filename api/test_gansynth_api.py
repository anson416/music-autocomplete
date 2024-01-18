#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: test_gansynth_api.py

import mimetypes
from pathlib import Path

import numpy as np
import requests
from scipy.io import wavfile


def save_wav(audio: np.array, file_name, sample_rate: int = 16000):
    wavfile.write(file_name, sample_rate, audio.astype("float32"))


print(f"----- Testing GANSynth -----")

headers = {
    "Accept": "application/json",
}

params = {
    "seconds_per_instrument": 5,
    "sample_rate": 16000,
}

midi_path = "./demo/demo.mid"
with open(midi_path, "rb") as midi_file:
    files = {
        "midi_file": (Path(midi_path).name, midi_file, mimetypes.guess_type(midi_path)[0]),
    }
    response = requests.request(
        "POST",
        "http://localhost:8100/gansynth",
        params=params,
        headers=headers,
        files=files,
    ).json()

wav_path = f"gansynth_{Path(midi_path).stem}.wav"
save_wav(np.array(response), wav_path)

print(f"WAV saved to {wav_path}")
print("-" * 28 + "\n")

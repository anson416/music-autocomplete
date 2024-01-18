#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: test_gansynth_api.py

import mimetypes
from pathlib import Path

import numpy as np
import requests
from scipy.io import wavfile


def save_wav(audio: np.array, file_name, sample_rate: int = 44100):
    wavfile.write(file_name, sample_rate, audio)


midi_path = "./demo/demo.mid"

with open(midi_path, "rb") as midi_file:
    response = requests.request(
        "POST",
        "http://localhost:8100/midi2wav",
        headers={
            "Accept": "application/json",
        },
        files={
            "midi_file": (Path(midi_path).name, midi_file, mimetypes.guess_type(midi_path)[0]),
        },
    ).json()

# Output
wav_path = f"midi2wav_{Path(midi_path).stem}.wav"
save_wav(np.array(response["audio"], dtype=response["dtype"]), wav_path, sample_rate=response["sample_rate"])

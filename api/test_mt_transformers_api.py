#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: test_mt_transformers_api.py

import mimetypes
from pathlib import Path

import requests

headers = {
    "Accept": "application/json",
}
for model in ("ismir2021", "mt3"):
    print(f"----- Testing music_transcription_with_transformers/{model} -----")

    params = {
        "sample_rate": 16000,
    }
    audio_path = "./demo/demo.wav"
    with open(audio_path, "rb") as audio_file:
        files = {
            "audio_file": (Path(audio_path).name, audio_file, mimetypes.guess_type(audio_path)[0]),
        }
        response = requests.request(
            "POST",
            f"http://localhost:8200/music_transcription_with_transformers/{model}",
            params=params,
            headers=headers,
            files=files,
        ).json()

    print(response)
    print("-" * 60 + "\n")

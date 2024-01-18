#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: main.py

import argparse
import json
import shutil
import subprocess
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, UploadFile
from mustrans.types_ import NoteDicts


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(tmp_dir)


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def main():
    return {"msg": "mustrans"}


@app.post("/music_transcription_with_transformers/{model}")
async def music_transcription_with_transformers(
    model: Literal["ismir2021", "mt3"],
    audio_file: UploadFile,
    sample_rate: int = 16000,
) -> NoteDicts:
    audio_path = Path("tmp") / urllib.parse.quote(audio_file.filename)
    print(f"Transcribing audio using {model} from Music Transcription with Transformers")
    try:
        with open(audio_path, "wb") as f:
            f.write(await audio_file.read())
        result = subprocess.run(
            [
                "python3",
                "-c",
                f"from mustrans.mt_transformers import MTTransformers; from mustrans.utils import noteseq2notes; seq = MTTransformers('{model}')('{audio_path}', {sample_rate}); print(noteseq2notes(seq))",
            ],
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout.replace("'", "\""))
    finally:
        if audio_path.exists():
            audio_path.unlink()


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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: test_magenta_rnn_api.py

import json

import requests

notes = [
    {"note": 79, "start_time": 0.0, "duration": 3.5, "velocity": 80},
    {"note": 74, "start_time": 0.0, "duration": 3.5, "velocity": 70},
    {"note": 71, "start_time": 0.0, "duration": 3.5, "velocity": 60},
    {"note": 78, "start_time": 3.5, "duration": 0.25, "velocity": 70},
    {"note": 79, "start_time": 3.75, "duration": 0.25, "velocity": 70},
    {"note": 78, "start_time": 4, "duration": 2, "velocity": 70},
    {"note": 71, "start_time": 4, "duration": 4, "velocity": 80},
    {"note": 83, "start_time": 6, "duration": 2, "velocity": 70},
    {"note": 64, "start_time": 6, "duration": 2, "velocity": 60},
]

params = {
    "qpm": 60,
    "extend_duration": 20,
    "temperature": 0.5,
}

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

musgen_combs = (
    ("melody_rnn", "basic_rnn"),
    ("melody_rnn", "mono_rnn"),
    ("melody_rnn", "lookback_rnn"),
    ("melody_rnn", "attention_rnn"),
    ("performance_rnn", "performance"),
    ("performance_rnn", "performance_with_dynamics"),
    ("performance_rnn", "performance_with_dynamics_and_modulo_encoding"),
    ("performance_rnn", "density_conditioned_performance_with_dynamics"),
    ("performance_rnn", "pitch_conditioned_performance_with_dynamics"),
    ("performance_rnn", "multiconditioned_performance_with_dynamics"),
)

for comb in musgen_combs:
    print(f"----- Testing {comb[0]}/{comb[1]} -----")

    response = requests.request(
        "POST",
        f"http://localhost:8100/{comb[0]}/{comb[1]}",
        params=params,
        headers=headers,
        data=json.dumps(notes),
    ).json()
    
    print(response)
    print("-" * 70 + "\n")

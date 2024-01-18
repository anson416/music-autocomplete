# -*- coding: utf-8 -*-
# File: gansynth.py

"""
Copyright 2019 Google LLC. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import note_seq
import numpy as np
import tensorflow.compat.v1 as tf
from magenta.models.gansynth.lib import flags as lib_flags
from magenta.models.gansynth.lib import generate_util as gu
from magenta.models.gansynth.lib import model as lib_model
from magenta.models.gansynth.lib import util

tf.disable_v2_behavior()

# GLOBALS
model_directory_path = "model/acoustic_only"
CKPT_DIR = "gs://magentadata/models/gansynth/acoustic_only"
BATCH_SIZE = 16

# Load the model
tf.reset_default_graph()
flags = lib_flags.Flags({
    "batch_size_schedule": [BATCH_SIZE],
    "tfds_data_dir": "gs://tfds-data/datasets",
})
model = None


def load_midi(midi_path, min_pitch=36, max_pitch=84):
    """Load midi as a notesequence."""
    midi_path = util.expand_path(midi_path)
    ns = note_seq.midi_file_to_sequence_proto(midi_path)
    pitches = np.array([n.pitch for n in ns.notes])
    velocities = np.array([n.velocity for n in ns.notes])
    start_times = np.array([n.start_time for n in ns.notes])
    end_times = np.array([n.end_time for n in ns.notes])
    valid = np.logical_and(pitches >= min_pitch, pitches <= max_pitch)
    notes = {
        "pitches": pitches[valid],
        "velocities": velocities[valid],
        "start_times": start_times[valid],
        "end_times": end_times[valid],
    }
    return ns, notes


def get_envelope(t_note_length, t_attack=0.010, t_release=0.3, sr=16000):
    """Create an attack sustain release amplitude envelope."""
    t_note_length = min(t_note_length, 3.0)
    i_attack = int(sr * t_attack)
    i_sustain = int(sr * t_note_length)
    i_release = int(sr * t_release)
    i_tot = i_sustain + i_release  # attack envelope doesn't add to sound length
    envelope = np.ones(i_tot)
    # Linear attack
    envelope[:i_attack] = np.linspace(0.0, 1.0, i_attack)
    # Linear release
    envelope[i_sustain:i_tot] = np.linspace(1.0, 0.0, i_release)
    return envelope


def combine_notes(audio_notes, start_times, end_times, velocities, sr=16000):
    """
    Combine audio from multiple notes into a single audio clip.

    Args:
        audio_notes: Array of audio [n_notes, audio_samples].
        start_times: Array of note starts in seconds [n_notes].
        end_times: Array of note ends in seconds [n_notes].
        sr: Integer, sample rate.

    Returns:
        audio_clip: Array of combined audio clip [audio_samples]
    """

    n_notes = len(audio_notes)
    clip_length = end_times.max() + 3.0
    audio_clip = np.zeros(int(clip_length) * sr)

    for t_start, t_end, vel, i in zip(start_times, end_times, velocities, range(n_notes)):
        # Generate an amplitude envelope
        t_note_length = t_end - t_start
        envelope = get_envelope(t_note_length, sr=sr)
        length = len(envelope)
        audio_note = audio_notes[i, :length] * envelope
        # Normalize
        audio_note /= audio_note.max()
        audio_note *= (vel / 127.0)
        # Add to clip buffer
        clip_start = int(t_start * sr)
        clip_end = clip_start + length
        audio_clip[clip_start:clip_end] += audio_note

    # Normalize
    audio_clip /= audio_clip.max()
    audio_clip /= 2.0
    return audio_clip


def synth(midi_path: str, seconds_per_instrument: float = 5, sr: int = 16000):
    global model
    if model is None:
        if os.path.exists(model_directory_path):
            print("GANSynth model exists in local")
            model = lib_model.Model.load_from_path(model_directory_path, flags)
        else:
            print("GANSynth model is not in local")
            model = lib_model.Model.load_from_path(CKPT_DIR, flags)

    ns, notes = load_midi(midi_path)

    # Distribute latent vectors linearly in time
    z_instruments, t_instruments = gu.get_random_instruments(
        model, notes["end_times"][-1], secs_per_instrument=seconds_per_instrument)

    # Get latent vectors for each note
    z_notes = gu.get_z_notes(notes["start_times"], z_instruments, t_instruments)

    # Generate audio for each note
    audio_notes = model.generate_samples_from_z(z_notes, notes["pitches"])

    # Make a single audio clip
    audio_clip = combine_notes(
        audio_notes,
        notes["start_times"],
        notes["end_times"],
        notes["velocities"],
        sr=sr,
    )
    return audio_clip

# -*- coding: utf-8 -*-
# File: markov.py

"""
Example:
```python
import markov
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
new_notes = markov.generate(
    notes=notes,
    tick=1/96,
    extend_duration=20,
    variation=0.2,
    loosen=True,
    include_new=True,
)
```
"""

import random
from itertools import combinations, product
from typing import Any, Dict, List

DEBUG = False


def _round_to_tick(t: float, tick: float) -> float:
    """
    Round time `t` to the nearest multiple of `tick`.
    """

    return tick * round(t / tick)


def _markov_chain(
    bigram: Dict[Any, Dict[Any, int]],
    tgt: Any,
) -> Any:
    """
    Given a target, return the next output with the highest probability based on a bigram.

    Args:
        bigram (Dict[Any, Dict[Any, int]]): A dictionary where each key is the current state and the corresponding \
            value is another dictionary where each key is the next state and the corresponding value is the frequency \
            of that state appearing after the current state. Example:
            ```python
            {
                "a": {"b": 1, "c": 2},
                "b": {"a": 1, "b": 3, "c": 1},
                "c": {"a": 2}
            }
            ```
        tgt (Any): Target from which the next output will be generated

    Returns:
        Any: Next output
    """

    assert tgt in bigram, f"bigram has no key {tgt}"
    return random.choices(list(bigram[tgt].keys()), weights=bigram[tgt].values())[0]


def _get_all_combs(arr: List[Any]) -> List[Any]:
    """
    Return all possible nC1 + nC2 + ... + nCn = 2^n - 1 combinations from array `arr`.
    """

    combs = []
    for i in range(1, len(arr) + 1):
        combs.extend(combinations(arr, i))
    return combs


def _increment_dict(dic: Dict[Any, Any], key: Any, k: float = 1.0) -> None:
    dic[key] = dic[key] + k if key in dic else k


def generate(
    notes: List[Dict[str, float]],
    tick: float,
    extend_duration: float,
    variation: float = 0.0,
    loosen: bool = False,
    include_new: bool = False,
) -> List[Dict[str, float]]:
    """
    Extend notes based on the Markov Chain.

    Args:
        notes (List[Dict[str, float]]): List of notes
        tick (float): Duration (in second) of one tick
        extend_duration (float): Duration to extend
        variation (float, optional): Probability of omitting the Markov Chain and choose randomly. Defaults to 0.0.
        loosen (bool, optional): Create all possible combinations (2^n - 1) from each chord. Defaults to False.
        include_new (bool, optional): Insert each newly created chord into the Markov Chain. Defaults to False.

    Returns:
        List[Dict[str, float]]: New notes
    """

    assert len(notes) > 0, "notes must be non-empty"
    assert tick > 0, f"{tick} <= 0. tick must be a positive number."
    assert extend_duration > 0, f"{extend_duration} <= 0. extend_duration must be a positive number."
    assert 0.0 <= variation <= 1.0, "variation must be between 0 and 1 inclusively"

    # Gather all start times and end times
    times = [0.0]  # 0.0 is for possible pause at the beginning
    for note in notes:
        times.append(_round_to_tick(note["start_time"], tick))
        times.append(_round_to_tick(note["start_time"] + note["duration"], tick))  # End time
    times = sorted(set(times))  # len(times) - 1 equals the number of chords (including pauses)
    if DEBUG:
        print("times:", times)

    # Combine notes into individual chords (no overlapping)
    chords = []
    for t in range(len(times) - 1):  # Time complexity: O( |times| * |notes| )
        chord, velocity = [], []
        for note in notes:
            start_time = _round_to_tick(note["start_time"], tick)
            end_time = _round_to_tick(note["start_time"] + note["duration"], tick)
            if start_time <= times[t] and end_time >= times[t + 1]:  # Note exists in current time frame
                chord.append(note["note"])
                velocity.append(note["velocity"])
        if len(chord) == 0:
            chord.append(-1)  # Use -1 to represent pauses
            velocity.append(-1)
        chords.append({
            "chord": tuple(sorted(chord)),  # Sort to ensure uniqueness
            "start_time": times[t],
            "duration": times[t + 1] - times[t],
            "velocity": random.choice(velocity),  # Choose one velocity uniformly at random
        })
    if DEBUG:
        print("chords:", chords)

    # Count the totals for random selection
    chord_count, duration_count, velocity_count = {}, {}, {}
    for chord in chords:
        for c in (_get_all_combs(chord["chord"]) if loosen else (chord["chord"],)):
            _increment_dict(chord_count, c, k=1)
        _increment_dict(duration_count, chord["duration"], k=1)
        _increment_dict(velocity_count, chord["velocity"], k=1)
        if -1 in velocity_count:  # Prevent cases where a note is generated with velocity -1
            del velocity_count[-1]
    if DEBUG:
        print("chord_count:", chord_count)
        print("duration_count:", duration_count)
        print("velocity_count:", velocity_count)

    # Compute bigram for chords
    chord_bigram = {c: {} for c in chord_count}
    for i in range(len(chords) - 1):
        for p1, p2 in (product(_get_all_combs(chords[i]["chord"]), _get_all_combs(chords[i + 1]["chord"])) 
                       if loosen else ((chords[i]["chord"], chords[i + 1]["chord"]),)):
            _increment_dict(chord_bigram[p1], p2, k=1)
    if DEBUG:
        print("chord_bigram:", chord_bigram)

    # Compute bigram for durations
    duration_bigram = {d: {} for d in duration_count}
    for i in range(len(chords) - 1):
        curr_dur = chords[i]["duration"]
        next_dur = chords[i + 1]["duration"]
        _increment_dict(duration_bigram[curr_dur], next_dur, k=1)
    if DEBUG:
        print("duration_bigram:", duration_bigram)

    # Compute bigram for velocities
    velocity_bigram = {v: {} for v in velocity_count}
    for i in range(len(chords) - 1):
        curr_vel = chords[i]["velocity"]
        next_vel = chords[i + 1]["velocity"]
        if curr_vel != -1 and next_vel != -1:  # Prevent cases where a note is generated with velocity -1
            _increment_dict(velocity_bigram[curr_vel], next_vel, k=1)
    if DEBUG:
        print("velocity_bigram:", velocity_bigram)

    new_notes = []
    last_chord = chords[-1]
    last_end_time = chords[-1]["start_time"] + chords[-1]["duration"]
    tgt_end_time = last_end_time + extend_duration
    while last_end_time < tgt_end_time:
        curr_chord = last_chord["chord"]
        new_chord = _markov_chain(chord_bigram, curr_chord) \
                    if len(chord_bigram[curr_chord]) > 0 and random.random() >= variation \
                    else random.choices(list(chord_count.keys()), weights=chord_count.values())[0]
        curr_duration = last_chord["duration"]
        new_duration = _markov_chain(duration_bigram, curr_duration) \
                       if len(duration_bigram[curr_duration]) > 0 and random.random() >= variation \
                       else random.choices(list(duration_count.keys()), weights=duration_count.values())[0]
        curr_velocity = last_chord["velocity"]
        new_velocity = _markov_chain(velocity_bigram, curr_velocity) \
                       if len(velocity_bigram[curr_velocity]) > 0 and random.random() >= variation \
                       else random.choices(list(velocity_count.keys()), weights=velocity_count.values())[0]
        if include_new:
            _increment_dict(chord_bigram[curr_chord], new_chord, k=1)
            _increment_dict(chord_count, new_chord, k=1)
            _increment_dict(duration_bigram[curr_duration], new_duration, k=1)
            _increment_dict(duration_count, new_duration, k=1)
            _increment_dict(velocity_bigram[curr_velocity], new_velocity, k=1)
            _increment_dict(velocity_count, new_velocity, k=1)
        last_chord = {
            "chord": new_chord,
            "start_time": last_end_time,
            "duration": new_duration,
            "velocity": new_velocity,
        }
        for note in new_chord:
            if note != -1:
                new_notes.append({
                    "note": note,
                    "start_time": last_end_time,
                    "duration": new_duration,
                    "velocity": new_velocity,
                })
        last_end_time += new_duration
    if DEBUG:
        print("new_notes:")
        for note in new_notes:
            print(note)

    return new_notes

# -*- coding: utf-8 -*-
# File: utils.py

import copy

import note_seq
from note_seq.protobuf import music_pb2
from note_seq.protobuf.music_pb2 import NoteSequence

from .types_ import NoteDicts


def noteseq2midi(seq: NoteSequence, output_path: str) -> None:
    note_seq.sequence_proto_to_midi_file(seq, output_path)


def notes2noteseq(notes: NoteDicts, qpm: float) -> NoteSequence:
    seq = music_pb2.NoteSequence()
    for note in notes:
        seq.notes.add(
            pitch=int(note["note"]),
            start_time=note["start_time"],
            end_time=note["start_time"] + note["duration"],
            velocity=int(note["velocity"]),
        )
    seq.tempos.add(qpm=qpm)
    return seq


def noteseq2notes(seq: NoteSequence) -> NoteDicts:
    return [
        {
            "note": note.pitch,
            "start_time": note.start_time,
            "duration": note.end_time - note.start_time,
            "velocity": note.velocity,
        } for note in seq.notes
    ]


def change_tempo(seq: NoteSequence, new_tempo: float) -> NoteSequence:
    """
    Credit: https://stackoverflow.com/a/66074474
    """

    new_seq = copy.deepcopy(seq)
    ratio = seq.tempos[0].qpm / new_tempo
    for note in new_seq.notes:
        note.start_time = note.start_time * ratio
        note.end_time = note.end_time * ratio
    new_seq.tempos[0].qpm = new_tempo
    return new_seq


def copy_velocity(from_seq: NoteSequence, to_seq: NoteSequence) -> NoteSequence:
    new_seq = copy.deepcopy(to_seq)
    for i in range(min(len(from_seq.notes), len(to_seq.notes))):
        new_seq.notes[i].velocity = from_seq.notes[i].velocity
    return new_seq

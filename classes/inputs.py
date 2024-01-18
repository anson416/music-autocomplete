import os
import math
import platform
import tkinter
import mimetypes
import requests
import wave
import threading
from tkinter.filedialog import askopenfilename
from pathlib import Path

import librosa
import mido
import numpy as np
import pygame
import pyaudio

from classes.constants import *
from classes.ui_elements import Button
from classes.pianoroll import Note, PianoRoll


def midi_to_dict(filename):
    mid = mido.MidiFile(filename)
    print(mid.ticks_per_beat)
    note_dict_list = []
    for i, track in enumerate(mid.tracks):
        print('Track {}: {}'.format(i, track.name))

        note_list = [{"start time": 0, "velocity": 0} for _ in range(128)]
        total_time = 0
        for msg in track:
            # print(msg)
            msg.time = msg.time * TICKS_IN_BEAT / mid.ticks_per_beat
            total_time += msg.time

            if msg.type == "note_on" and msg.velocity > 0:
                note_list[msg.note]["start time"] = total_time 
                note_list[msg.note]["velocity"] = msg.velocity
                
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                duration = total_time - note_list[msg.note]["start time"]
                note_dict = {"note": msg.note, "start_time": note_list[msg.note]["start time"], "duration": duration, "velocity": note_list[msg.note]["velocity"]}
                note_dict_list.append(note_dict)
        # print(note_list)

    return note_dict_list


def read_midi(filename, piano_roll: PianoRoll):
    note_dict_list = midi_to_dict(filename)
    smallest_time = int(TICKS_IN_BEAT / 4)
    for note in note_dict_list:
        note["start_time"] = round(note["start_time"] / smallest_time) * smallest_time
        note["duration"] = math.ceil(note["duration"] / smallest_time) * smallest_time
        new_note = Note(note["note"], note["start_time"], note["duration"], note["velocity"])
        piano_roll.add_note(new_note)


def read_librosa(filename, piano_roll: PianoRoll):
    y, sr = librosa.load(filename)

    # both usual and backtrack onsets are used
    onset_frame = librosa.onset.onset_detect(y=y, sr=sr)
    onset_time_backtrack = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True, units="time")

    # track bpm
    bpm, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = int(round(bpm))
    piano_roll.bpm = bpm

    onset_tick = onset_time_backtrack * TICKS_IN_BEAT / (60 / bpm)

    # correct the notes to nearest TICKS_IN_BEAT, 
    note_duration_list = []
    for i in range(len(onset_tick)):
        note_duration_list.append(0)
        if (onset_tick[i] % TICKS_IN_BEAT / 4) < TICKS_IN_BEAT / 8:
            onset_tick[i] -= onset_tick[i] % (TICKS_IN_BEAT / 4)
        else:
            onset_tick[i] += (TICKS_IN_BEAT / 4) - onset_tick[i] % (TICKS_IN_BEAT / 4)
        # handle overlapping
        if i > 0 and onset_tick[i] == onset_tick[i-1]:
            onset_tick[i-1] -= (TICKS_IN_BEAT / 4)
        # record places where pauses may occur
        if i > 0 and (onset_tick[i] - onset_tick[i-1]) > (TICKS_IN_BEAT / 4) * 3 / 2:
            j = onset_tick[i-1] + (TICKS_IN_BEAT / 4) * 3 / 2 
            while(j < onset_tick[i]):
                note_duration_list[i-1] += 1
                j += (TICKS_IN_BEAT / 4)
                
    # for computing pitch
    S = np.abs(librosa.stft(y))
    pitches_frame, magnitudes = librosa.piptrack(S=S, sr=sr)

    # for computing the loudness / velocity
    S_db = np.square(S)
    freqs = librosa.fft_frequencies(sr=sr)
    S_db = librosa.perceptual_weighting(S_db, freqs)

    # sum and normalize the loudnesses
    velocity = librosa.db_to_amplitude(S_db)
    velocity_sum = np.mean(velocity, axis=0)
    velocity_sum = velocity_sum * 127 / np.max(velocity_sum)

    pitches_tick = []
    for i, t in enumerate(onset_frame):
        # finsing the most significant pitch
        index = magnitudes[:, t].argmax()
        pitch = pitches_frame[index, t]

        onset_velocity = velocity_sum[t]
        duration = (TICKS_IN_BEAT / 4)

        for j in range(note_duration_list[i]):
            # check if the note continues, by looking at the magnitude
            next_beat_frame = librosa.time_to_frames(((onset_tick[i] + duration + (TICKS_IN_BEAT / 4) / 2) * (60 / bpm)) / TICKS_IN_BEAT)
            if velocity_sum[next_beat_frame] > onset_velocity * 0.1:
                duration += (TICKS_IN_BEAT / 4)
            else:
                break

        pitches_tick.append({"frame": t, "note": librosa.hz_to_note(min(pitch, 20000)), "duration":duration, "velocity": int(onset_velocity)})

    for i in range(len(onset_tick)):
        piano_roll.add_note(Note(librosa.note_to_midi(pitches_tick[i]["note"]), onset_tick[i], pitches_tick[i]["duration"], pitches_tick[i]["velocity"]))
    
    print("Done!")


def read_mt3(filename, piano_roll: PianoRoll):
    y, sr = librosa.load(filename)

    # track bpm
    bpm, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = int(round(bpm))
    piano_roll.bpm = bpm

    headers = {
        "Accept": "application/json",
    }
    params = {
        "sample_rate": sr,
    }
    with open(filename, "rb") as audio_file:
        files = {
            "audio_file": (Path(filename).name, audio_file, mimetypes.guess_type(filename)[0]),
        }
        
        try:
            response = requests.request(
                "POST",
                f"http://localhost:8200/music_transcription_with_transformers/mt3",
                params=params,
                headers=headers,
                files=files,
            ).json()
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to API: {e}")
            return
    
    for note in response:
        note["note"] = int(note["note"])
        note["start_time"] = note["start_time"] * TICKS_IN_BEAT / (60 / bpm)
        note["duration"] = note["duration"] * TICKS_IN_BEAT / (60 / bpm)
        note["velocity"] = int(note["velocity"])

        piano_roll.add_note(Note(note["note"], note["start_time"], note["duration"], note["velocity"]))
    # print(response)

class Inputs():
    def __init__(self, piano_roll: PianoRoll):
        self.image = pygame.Surface([INPUTS_WIDTH, INPUTS_HEIGHT])
        self.rect = self.image.get_rect()
        self.rect.topleft = [INPUTS_LEFT_BOUND, INPUTS_UP_BOUND]

        self.piano_roll = piano_roll
        self.midi_button = Button("MIDI", (SCREEN_WIDTH / 10 , ROLL_UP_BOUND / 2))
        self.librosa_button = Button("Librosa", (SCREEN_WIDTH / 4 , ROLL_UP_BOUND / 2))
        self.mt3_button = Button("Transformer",  (SCREEN_WIDTH * 3 / 7 , ROLL_UP_BOUND / 2))

        self.record_button = Button("Record", (SCREEN_WIDTH * 9 / 10 , ROLL_UP_BOUND / 2))        
        self.recording = False


    def record_audio(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
        
        wf = wave.open("inputs/recording.wav", 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)

        print("* recording")
        while self.recording:
            data = stream.read(CHUNK)
            wf.writeframes(data)

        print("* done recording")
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()

        read_librosa("inputs/recording.wav", self.piano_roll)


    def handle_mouse(self, mouse_pos, event):
        midi_flag = self.midi_button.handle_mouse(mouse_pos, event)
        librosa_flag = self.librosa_button.handle_mouse(mouse_pos, event)
        mt3_flag = self.mt3_button.handle_mouse(mouse_pos, event)

        if midi_flag or librosa_flag or mt3_flag:
            if platform.system() == "Windows":
                tkinter.Tk().withdraw()
                filename = askopenfilename()
                if midi_flag and filename.endswith(".mid"):
                    self.piano_roll.clear_notes()
                    read_midi(filename, self.piano_roll)
                elif librosa_flag and (filename.endswith(".wav") or filename.endswith(".mp3")):
                    self.piano_roll.clear_notes()
                    read_librosa(filename, self.piano_roll)
                elif mt3_flag and (filename.endswith(".wav") or filename.endswith(".mp3")):
                    self.piano_roll.clear_notes()
                    read_mt3(filename, self.piano_roll)
                else:
                    print("Not valid file!")

            elif platform.system() == "Darwin":
                file_found = False
                for dir_path, dirs, files in os.walk("inputs"):
                    for filename in files:
                        filename = os.path.join(dir_path, filename)
                        
                        if midi_flag and filename.endswith(".mid"):
                            self.piano_roll.clear_notes()
                            read_midi(filename, self.piano_roll)
                            file_found = True
                            break
                        elif librosa_flag and (filename.endswith(".wav") or filename.endswith(".mp3")):
                            self.piano_roll.clear_notes()
                            read_librosa(filename, self.piano_roll)
                            file_found = True
                            break
                        elif mt3_flag and (filename.endswith(".wav") or filename.endswith(".mp3")):
                            self.piano_roll.clear_notes()
                            read_mt3(filename, self.piano_roll)
                            file_found = True
                            break
                    if file_found:
                        break
                if not file_found:
                    print("No valid file found!")

        
        if self.record_button.handle_mouse(mouse_pos, event) and self.recording == False:
            self.record_button.change_text("Stop Recording")
            self.recording = True
            self.piano_roll.clear_notes()
            threading.Thread(target=self.record_audio).start()
        elif self.record_button.handle_mouse(mouse_pos, event) and self.recording == True:
            self.record_button.change_text("Record")
            self.recording = False
                            

    def update(self):
        self.midi_button.draw_button()
        self.librosa_button.draw_button()
        self.mt3_button.draw_button()
        self.record_button.draw_button()



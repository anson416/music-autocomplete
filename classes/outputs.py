import datetime
import json
import mimetypes
import os
import platform
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import numpy as np
import pretty_midi
import pygame
import requests
from pydub import AudioSegment
from scipy.io import wavfile

import classes.markov as markov
from classes.constants import *
from classes.inputs import read_midi
from classes.pianoroll import PianoRoll
from classes.ui_elements import Button

GANSYNTH_INPUT_PATH = "synthesis/input/input.mid"
GANSYNTH_OUTPUT_PATH = "synthesis/output/output.wav"
GANSYNTH_OUTPUT_MP3_PATH = "synthesis/output/output.mp3"
TEMP_MIDI_FILE = "temp.mid"
GEN_MIDI_FILE = "gen.mid"
LAST_GEN_MIDI_FILE_PATH = os.path.join(TEMP_MUSIC_DIRECTORY, GEN_MIDI_FILE)
MACOS_EXPORT_FOLDER = "export"

if not os.path.exists(TEMP_MUSIC_DIRECTORY):
    os.makedirs(TEMP_MUSIC_DIRECTORY)
if not os.path.exists("synthesis/input"):
    os.makedirs("synthesis/input")
if not os.path.exists("synthesis/output"):
    os.makedirs("synthesis/output")
if not os.path.exists(MACOS_EXPORT_FOLDER):
    os.makedirs(MACOS_EXPORT_FOLDER)

def gansynth(midi_path, seconds_per_instrument):
    """connected to api."""
    print(f'seconds per instruments: {seconds_per_instrument}')
    headers = {
        "Accept": "application/json",
    }
    params = {
        "seconds_per_instrument": seconds_per_instrument,
        "sample_rate": 16000,
    }

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

    print('ready to create .wav')

    def save_wav(audio, fname, sr=16000):
        wavfile.write(fname, sr, audio.astype('float32'))
        print('Saved to {}'.format(fname))

    save_wav(np.array(response), GANSYNTH_OUTPUT_PATH)
    AudioSegment.from_wav(GANSYNTH_OUTPUT_PATH).export(GANSYNTH_OUTPUT_MP3_PATH, format="mp3")


def midi2wav_api(input_midi, output_wav):
    def save_wav(audio: np.array, file_name, sample_rate: int = 44100):
        wavfile.write(file_name, sample_rate, audio)

    with open(input_midi, "rb") as midi_file:
        try:
            response = requests.request(
                "POST",
                "http://localhost:8100/midi2wav",
                headers={
                    "Accept": "application/json",
                },
                files={
                    "midi_file": (Path(input_midi).name, midi_file, mimetypes.guess_type(input_midi)[0]),
                },
            ).json()
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to midi2wav API: {e}")
            return

    save_wav(np.array(response["audio"], dtype=response["dtype"]), output_wav, sample_rate=response["sample_rate"])

def play_music(path, piano_roll: PianoRoll, output_obj=None):
    '''play midi or mp3'''
    if not os.path.exists(path):
        print(f"Error: File {path} not found.")
        return None

    #pygame.init()
    music = pygame.mixer.music
    output_obj.generated_music_channel = music
    playhead_start_tick = piano_roll.playhead_pos
    ticks_from_start = playhead_start_tick
    tick_duration = 60000/(piano_roll.bpm * TICKS_IN_BEAT) #in ms
    playhead_start_time = playhead_start_tick * tick_duration if path == GANSYNTH_OUTPUT_MP3_PATH else 0
    try:
        music.load(path) # returns None
        music.play(start=playhead_start_time/1000)
        while (music.get_busy()):
            ticks_from_start = playhead_start_tick + int(music.get_pos() / tick_duration)
            if (ticks_from_start > playhead_start_tick):
                piano_roll.set_playhead_tick(ticks_from_start)
    except pygame.error as e:
        print(e)
    return music    

class DurationSlider():
    """music extension duration"""
    def __init__(self):
        super().__init__()
        self.width = 300
        self.height = 30
        self.image = pygame.Surface([self.width, self.height], pygame.SRCALPHA)
        self.base_color = pygame.Color((*BLACK, 128))
        self.rect: pygame.Rect = self.image.get_rect(topleft=(435, OUTPUTS_HEIGHT - 80)) 
        self.slider_width = 150
        self.left_slider_margin = 100

        self.text_pos = (10, self.height // 2) #left middle
        self.font = pygame.font.Font(None, 18)

        self.slider_x = self.left_slider_margin + self.slider_width // 2     #center
        self.slider_y = self.height // 2
        self.slider_y_margin = 15
        self.indicator_width = 15
        self.indicator_height = 15

        self.extend_duration = 20
        self.max_duration = 300

        self.is_dragging = False
    
    def get_indicator_pos(self):
        indicator_x = self.left_slider_margin + int(self.extend_duration / self.max_duration * self.slider_width)
        indicator_y = self.slider_y
        return indicator_x, indicator_y
    
    def on_slider(self, mouse_pos):
        mouse_x = mouse_pos[0] - self.rect.left
        mouse_y = mouse_pos[1] - self.rect.top
        return abs(mouse_x - self.slider_x) <= self.slider_width // 2 \
           and abs(mouse_y - self.slider_y) <= self.slider_y_margin
    
    def set_duration(self, mouse_pos):
        mouse_x = mouse_pos[0] - self.rect.left
        self.extend_duration = (mouse_x - self.left_slider_margin) / self.slider_width * self.max_duration
        self.extend_duration = max(min(self.extend_duration, self.max_duration), 0)
    
    def release_slider(self):
        self.is_dragging = False
        self.extend_duration = int(self.extend_duration)

    def handle_mouse(self, mouse_pos, event):
        if event.type == pygame.MOUSEBUTTONUP:
            self.release_slider()
        elif event.type == pygame.MOUSEBUTTONDOWN and self.on_slider(mouse_pos):
            self.set_duration(mouse_pos)
            self.is_dragging = True
        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            self.set_duration(mouse_pos)
        if self.is_dragging and not self.rect.collidepoint(mouse_pos):
            self.release_slider()

    def draw(self, screen: pygame.Surface):
        self.image.fill(self.base_color)
        duration_str = f'{int(self.extend_duration)}'
        text_image = self.font.render(f'Duration = {duration_str}', 1, WHITE)
        text_rect = text_image.get_rect(midleft=self.text_pos)
        pygame.draw.line(self.image, 
                         WHITE, 
                         (self.left_slider_margin, self.slider_y),
                         (self.left_slider_margin + self.slider_width, self.slider_y))
        indicator_image = pygame.Surface((self.indicator_width, self.indicator_height))
        indicator_image.fill(LIGHT_GREY)
        indicator_rect = indicator_image.get_rect(center=self.get_indicator_pos())
        self.image.blit(indicator_image, indicator_rect)
        self.image.blit(text_image, text_rect)
        screen.blit(self.image, self.rect)


class ModelOptions():
    """select model"""
    def __init__(self):
        self.width = 400
        self.height = 30
        self.image = pygame.Surface((self.width, self.height))
        self.rect = self.image.get_rect(topleft=(10, OUTPUTS_HEIGHT - 80))
        self.font = pygame.font.Font(None, 18)
        self.margin = 30
        self.left_arrow = Button('<', (self.margin, self.rect.height//2))
        self.right_arrow = Button('>', (self.width-self.margin, self.rect.height//2))             
        self.model_num = 0
        self.models = (
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
            ("custom", "markov_chain")
        )
        self.models_len = len(self.models)
    
    def get_model(self):
        return self.models[self.model_num]
    
    def draw(self, surface):

        self.image.fill(BLACK)
        self.image.blit(self.left_arrow.surface, self.left_arrow.rect)
        self.image.blit(self.right_arrow.surface, self.right_arrow.rect)

        model_text = self.models[self.model_num][1]
        text_surface = self.font.render(model_text, True, WHITE)
        text_rect = text_surface.get_rect(center=(self.width // 2, self.height // 2))
        self.image.blit(text_surface, text_rect)

        surface.blit(self.image, self.rect)

        return
    
    def handle_mouse(self, pos, event):
        pos = (pos[0] - self.rect.left, pos[1] - self.rect.top)
        if self.left_arrow.handle_mouse(pos, event):
            self.model_num = (self.model_num - 1) % self.models_len
        elif self.right_arrow.handle_mouse(pos, event):
            self.model_num = (self.model_num + 1) % self.models_len
        

class Output():
    """bottom row buttons"""
    def __init__(self, piano_roll):
        self.piano_roll: PianoRoll = piano_roll

        self.image = pygame.Surface([OUTPUTS_WIDTH, OUTPUTS_HEIGHT])
        self.rect = self.image.get_rect()
        self.rect.topleft = [OUTPUTS_LEFT_BOUND, OUTPUTS_UP_BOUND]

        self.generated_button = Button("Generate", (50, OUTPUTS_HEIGHT - 25))
        self.quick_play_button = Button("Quick Play", (160, OUTPUTS_HEIGHT - 25))
        self.add_to_piano_roll_button = Button("Update", (270, OUTPUTS_HEIGHT - 25))
        self.gansynth_button = Button("GANSynth", (380, OUTPUTS_HEIGHT - 25))
        self.play_button = Button("Play", (470, OUTPUTS_HEIGHT - 25))
        self.export_wav_button = Button("Export WAV", (OUTPUTS_RIGHT_BOUND - 200, OUTPUTS_HEIGHT - 25))
        self.export_midi_button = Button("Export MIDI", (OUTPUTS_RIGHT_BOUND - 70, OUTPUTS_HEIGHT - 25))
        self.duration_slider = DurationSlider()

        self.down_instrument_second = Button("<", (290, OUTPUTS_HEIGHT - 25))
        self.show_instrument_second = Button("", (305, OUTPUTS_HEIGHT - 25))
        self.up_instrument_second = Button(">", (320, OUTPUTS_HEIGHT - 25))
        self.instrument_second = 2

        self.extend_options = ModelOptions()
        self.generated_music_channel = None
        self.generated_music_playing = False
        self.music_thread = None


    def piano_roll_to_midi(self, filepath, playhead_time = 0.0):
        """
        convert notes in piano roll to midi, starting from playhead_time to end.
        if playhead_time=0, that means converting the whole piano roll into midi.
        """
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        to_realtime = 60/(TICKS_IN_BEAT*self.piano_roll.bpm)
        for note_info in self.piano_roll.notes:
            pitch = note_info.pitch  # Convert note to integer
            if filepath == GANSYNTH_INPUT_PATH:
                if pitch < 24:
                    pitch = 24
                elif pitch > 84:
                    pitch = 84
            start_time = to_realtime * note_info.start - playhead_time
            end_time = to_realtime * note_info.end - playhead_time
            velocity = note_info.velocity
            if start_time < 0:
                start_time = 0
            if end_time > 0:
                note = pretty_midi.Note(velocity=int(velocity), pitch=int(pitch), start=float(start_time), end=float(end_time))
                instrument.notes.append(note)
        
        midi_data.instruments.append(instrument)
        midi_data.write(filepath)

    def export(self, file_extension):
        """export a midi/wav file"""
        if platform.system() == "Windows":
            root = tk.Tk()
            root.withdraw()
            export_path = filedialog.asksaveasfilename(defaultextension=f".{file_extension}")
            if export_path:
                self.export_folder, self.export_filename = os.path.split(export_path)
                print(f"Exporting {self.export_filename} in {self.export_folder}")
                if file_extension == "mid":
                    self.piano_roll_to_midi(export_path)
                elif file_extension == "wav":
                    temp_midi_path = os.path.join(TEMP_MUSIC_DIRECTORY, TEMP_MIDI_FILE)
                    self.piano_roll_to_midi(temp_midi_path)
                    midi2wav_api(temp_midi_path, export_path)
        else: # using macOS
            current_time = datetime.datetime.now()
            formatted_time = current_time.strftime("%Y%m%d_%H%M%S")
            file_name = f"{formatted_time}.{file_extension}"
            file_name = os.path.join(MACOS_EXPORT_FOLDER, file_name)
            if file_extension == "mid":
                print(f"Exporting {file_name} in {MACOS_EXPORT_FOLDER}")
                self.piano_roll_to_midi(file_name)
            elif file_extension == "wav":
                print(f"Exporting {file_name} in {MACOS_EXPORT_FOLDER}")
                temp_midi_path = os.path.join(TEMP_MUSIC_DIRECTORY, TEMP_MIDI_FILE)
                self.piano_roll_to_midi(temp_midi_path)
                midi2wav_api(temp_midi_path, export_path)

    def handle_generate_click(self):
        """connected to api"""
        if self.generated_music_playing and self.generated_music_channel is not None:
            self.generated_music_channel.stop()
            self.generated_music_playing = False

        to_realtime = 60/(96*self.piano_roll.bpm)
        notes = [{'note': int(note.pitch),
                'start_time': float(to_realtime * note.start),
                'duration': float(to_realtime * note.duration),
                'velocity': float(note.velocity)} for note in self.piano_roll.notes]

        params = {
            "qpm": int(self.piano_roll.bpm),
            "extend_duration": self.duration_slider.extend_duration,
            "temperature": 0.5,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        model_type, model_name = self.extend_options.get_model()

        if model_name == 'markov_chain':
            response = markov.generate(
                notes=notes,
                tick=1/96,
                extend_duration=params['extend_duration'],
                variation=0.2,
            )

        else:
            try:
                response = requests.request(
                    "POST",
                    f"http://localhost:8100/{model_type}/{model_name}",
                    params=params,
                    headers=headers,
                    data=json.dumps(notes),
                ).json()
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to API: {e}")
                return

        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        for note_info in self.piano_roll.notes:
            pitch = note_info.pitch  # Convert note to integer
            start_time = to_realtime * note_info.start
            end_time = to_realtime * note_info.end
            velocity = note_info.velocity
            note = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start_time, end=end_time)
            instrument.notes.append(note)

        print("notes generated")

        for note_info in response:
            pitch = int(note_info['note'])  # Convert note to integer
            start_time = round(note_info['start_time'], 3)
            end_time = round(start_time + note_info['duration'], 3)
            velocity = int(note_info['velocity'])  # Convert velocity to integer
            note = pretty_midi.Note(velocity=velocity, pitch=pitch, start=start_time, end=end_time)
            instrument.notes.append(note)
        
        midi_data.instruments.append(instrument)
        midi_data.write(LAST_GEN_MIDI_FILE_PATH)

        self.piano_roll.clear_notes()
        read_midi(LAST_GEN_MIDI_FILE_PATH, self.piano_roll)

    def handle_play_click(self):
        """play generated wav from GANSynth"""
        if self.play_button.text == "Stop":
            self.generated_music_channel.stop()
            self.generated_music_playing = False
            self.music_thread.join()
        else:
            if not os.path.exists(GANSYNTH_OUTPUT_MP3_PATH):
                print('No MP3 to play. Generate with GANSynth first.')
                return
            self.music_thread = threading.Thread(target=play_music, args=(GANSYNTH_OUTPUT_MP3_PATH, self.piano_roll, self))
            self.generated_music_playing = "wav"
            self.music_thread.start()

    def handle_quick_play_click(self):
        """play midi from notes in piano roll"""
        if self.quick_play_button.text == "Stop":
            self.generated_music_channel.stop()
            self.generated_music_playing = False
            self.music_thread.join()
        else:
            temp_midi_path = os.path.join(TEMP_MUSIC_DIRECTORY, TEMP_MIDI_FILE)
            self.piano_roll_to_midi(temp_midi_path, self.piano_roll.get_playhead_time())
            self.music_thread = threading.Thread(target=play_music, args=(temp_midi_path, self.piano_roll, self))
            self.generated_music_playing = "mid"
            self.music_thread.start()

    def handle_gansynth_click(self):
        if self.generated_music_playing and self.generated_music_channel is not None:
            self.generated_music_channel.stop()
            self.generated_music_playing = False
            self.music_thread.join()
        try:
            if self.generated_music_channel:
                self.generated_music_channel.unload()
            self.piano_roll_to_midi(GANSYNTH_INPUT_PATH)
            gansynth(GANSYNTH_INPUT_PATH, self.instrument_second)
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to API: {e}")
            print("Maybe music duration is too low or duration for each instrument is too long, try to extend the music or lower the duration for each instrument")
            return

    def handle_export_wav_click(self):
        self.export("wav")

    def handle_export_midi_click(self):
        self.export("mid")

    def handle_down_instrument_second_click(self):
        """decrease duration per instrument in GANSynth"""
        if self.instrument_second > 2:
            self.instrument_second -= 1

    def handle_up_instrument_second_click(self):
        self.instrument_second += 1

    def handle_mouse(self, pos, event):
        pos = (pos[0] - self.rect.topleft[0], pos[1] - self.rect.topleft[1])
        if self.generated_button.handle_mouse(pos, event):
            self.handle_generate_click()
        if self.quick_play_button.handle_mouse(pos, event):
            self.handle_quick_play_click()
        if self.gansynth_button.handle_mouse(pos, event):
            self.handle_gansynth_click()
        if self.play_button.handle_mouse(pos, event):
            self.handle_play_click()
        if self.export_wav_button.handle_mouse(pos, event):
            self.handle_export_wav_click()
        if self.export_midi_button.handle_mouse(pos, event):
            self.handle_export_midi_click()
        if self.down_instrument_second.handle_mouse(pos, event):
            self.handle_down_instrument_second_click()
        if self.up_instrument_second.handle_mouse(pos, event):
            self.handle_up_instrument_second_click()
        self.extend_options.handle_mouse(pos, event)
        self.duration_slider.handle_mouse(pos, event)

    def button_text_update(self):
        if self.generated_music_channel:
            if not self.generated_music_channel.get_busy():
                self.quick_play_button.change_text("Quick Play")
                self.play_button.change_text("Play")
            elif self.generated_music_playing == "mid":
                self.quick_play_button.change_text("Stop")
                self.play_button.change_text("Play")
            elif self.generated_music_playing == "wav":
                self.quick_play_button.change_text("Quick Play")
                self.play_button.change_text("Stop")
        else:
            self.quick_play_button.change_text("Quick Play")
            self.play_button.change_text("Play")

        self.show_instrument_second.change_text(str(self.instrument_second))


    def update(self):
        self.image.fill(DARK_GREY)
        self.button_text_update()
        self.image.fill(DARK_GREY)
        self.generated_button.draw_button(self.image)
        self.play_button.draw_button(self.image)
        self.quick_play_button.draw_button(self.image)
        self.gansynth_button.draw_button(self.image)
        self.export_wav_button.draw_button(self.image)
        self.export_midi_button.draw_button(self.image)

        self.down_instrument_second.draw_button(self.image)
        self.show_instrument_second.draw_button(self.image)
        self.up_instrument_second.draw_button(self.image)

        self.extend_options.draw(self.image)
        self.duration_slider.draw(self.image)
        SCREEN.blit(self.image, self.rect.topleft)

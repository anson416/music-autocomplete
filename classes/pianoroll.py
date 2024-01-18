from typing import List

import numpy as np
import pygame
from pygame import Color, Surface

from classes.clicktimer import ClickTimer
from classes.constants import *
from classes.ui_elements import Button


class Note():
    '''
    Stores attributes of a note in symbolic representation.
    Contains pitch, start time, duration, end time and velocity attributes.
    '''

    def __init__(self, pitch, start, duration=TICKS_IN_BEAT, velocity=80):
        self.pitch = pitch
        self.start = start
        self.duration = duration
        self.end = self.start + self.duration
        self.velocity = velocity

    def __repr__(self):
        return f'{{{self.pitch}, ({self.start}, {self.end}), {self.velocity}}}'
    
    def __str__(self):
        return f'{{{self.pitch}, ({self.start}, {self.end}), {self.velocity}}}'
    
    def contains_cell(self, cell):
        x, y = cell
        return self.pitch == y and self.start <= x <= self.end
    
class VelocitySlider():
    '''
    A UI element for modifying the velocity of a note.
    '''
    def __init__(self, pos):
        super().__init__()
        self.width = 250
        self.height = 75
        self.image = Surface([self.width, self.height], pygame.SRCALPHA)
        self.base_color = Color((*BLACK, 128))
        self.rect = self.image.get_rect(topright=pos) 
        self.velocity = -1
        self.slider_width = 200
        self.slider_margin = (self.width - self.slider_width) / 2
        self.notes: List[Note] = []

        self.text_pos = (20, 20) #left middle

        self.slider_x = self.width // 2     #center
        self.slider_y = 50
        self.slider_y_margin = 15
        self.indicator_width = 15
        self.indicator_height = 15

        self.is_dragging = False
    
    def get_indicator_pos(self):
        indicator_x = self.slider_margin + int(self.velocity / 100 * self.slider_width)
        indicator_y = self.slider_y
        return indicator_x, indicator_y
    
    def on_slider(self, mouse_pos):
        '''Checks if the mouse is on the slider.'''
        mouse_x, mouse_y = mouse_pos - self.rect.topleft
        return abs(mouse_x - self.slider_x) <= self.slider_width // 2 \
           and abs(mouse_y - self.slider_y) <= self.slider_y_margin
    
    def set_velocity(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos - self.rect.topleft
        self.velocity = (mouse_x - self.slider_margin) / self.slider_width * 100
        self.velocity = max(min(self.velocity, 100), 0)
    
    def add_note(self, note: Note):
        self.notes.append(note)
        self.velocity = note.velocity
    
    def clear_notes(self):
        self.notes.clear()
        self.velocity = -1
    
    def release_slider(self):
        '''Releases the slider and saves the new velocity to the notes.'''
        self.is_dragging = False
        self.velocity = int(self.velocity)
        for note in self.notes:
                note.velocity = self.velocity

    def handle_event(self, mouse_pos, event):
        '''Handle mouse events on the velocity slider.'''
        if event.type == pygame.MOUSEBUTTONUP:
            self.release_slider()
        elif event.type == pygame.MOUSEBUTTONDOWN and self.on_slider(mouse_pos):
            self.set_velocity(mouse_pos)
            self.is_dragging = True
        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            self.set_velocity(mouse_pos)


    def get_velocity(self):
        if self.notes:
            return self.notes[0].velocity
        else:
            return -1


    def draw(self, screen: Surface):
        '''Draws the slider on screen.'''
        self.image.fill(self.base_color)
        velocity_str = f'{int(self.velocity)}' if self.velocity >= 0 else '--'
        text_image = FONT.render(f'Velocity = {velocity_str}', 1, WHITE)
        text_rect = text_image.get_rect(midleft=self.text_pos)
        pygame.draw.line(self.image, 
                         WHITE, 
                         (self.slider_margin, self.slider_y),
                         (self.slider_margin + self.slider_width, self.slider_y))
        indicator_image = pygame.Surface((self.indicator_width, self.indicator_height))
        indicator_image.fill(LIGHT_GREY)
        indicator_rect = indicator_image.get_rect(center=self.get_indicator_pos())
        self.image.blit(indicator_image, indicator_rect)
        self.image.blit(text_image, text_rect)
        screen.blit(self.image, self.rect)

class PianoRoll():
    '''
    An interface for editing the timing and velocity of music notes.
    '''
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([ROLL_WIDTH, ROLL_HEIGHT])
        self.image.fill(BLACK)
        self.rect = self.image.get_rect()
        self.rect.topleft = [ROLL_LEFT_BOUND, ROLL_UP_BOUND]

        self.notes = []             # notes in the roll
        self.selected_note: Note = None
        self.edge_pressed = False

        self.window_x = 0           # ticks from the start of the piece
        self.window_y = 72          # highest midi note number shown
        self.cell_width = 40
        self.cell_height = 24

        self.minus_button = Button("-", (25, self.cell_height//2))
        self.plus_button = Button("+", (ROLL_GRID_START-25, self.cell_height//2))
        self.velocity_slider = VelocitySlider((SCREEN_WIDTH-16, 32))
        self.playhead_pos = 0       # in ticks

        self.beats_in_bar = 4
        self.cells_in_beat = 4
        self.bpm = 120
    
    def get_ticks_in_cell(self):
        return TICKS_IN_BEAT // self.cells_in_beat
    
    def get_window_range(self):
        return [self.get_ticks_in_cell() * (ROLL_WIDTH - ROLL_GRID_START) // self.cell_width,
                ROLL_HEIGHT // self.cell_height - 1]

    def click_to_cell_pos(self, pos):
        '''Translates click positions to the corresponding cell in the piano roll.'''
        x, y = pos
        absolute_x = (x-ROLL_GRID_START) // self.cell_width * self.get_ticks_in_cell() + self.window_x
        absolute_y = self.window_y - (y-self.cell_height)//self.cell_height
        return (absolute_x, absolute_y)
    
    def cell_in_grid(self, cell):
        '''Checks if the current cell is visible on screen.'''
        x, y = cell
        x_range, y_range = self.get_window_range()
        x_in_grid = self.window_x <= x <= self.window_x + x_range
        y_in_grid = self.window_y - y_range + 1 <= y <= self.window_y
        return x_in_grid and y_in_grid
    
    def note_from_cell(self, cell):
        '''Selects the top most note to be edited.'''
        for note_idx, note in enumerate(reversed(self.notes)):
            if note.contains_cell(cell):
                return note
        return None
    
    def get_pitch_name(self, note_num):
        octave = (note_num - 12)//12
        pitch = PITCHES[note_num % 12]
        return f'{pitch}{octave}'

    def add_note(self, note):
        self.notes.append(note)
        self.select_note(note)
        return
    
    def delete_note(self, note):
        self.notes.remove(note)
        self.selected_note = None
        #print(self.notes)
        return
    
    def clear_notes(self):
        self.notes = []   
        return
    
    def select_note(self, note):
        self.deselect_note()
        self.selected_note = note
        self.velocity_slider.add_note(note)
        return
    
    def deselect_note(self):
        self.selected_note: Note = None
        self.velocity_slider.clear_notes()
        self.edge_pressed = False
        return

    def set_playhead(self, mouse_pos):
        mouse_x = mouse_pos[0] - ROLL_GRID_START
        grid_width = ROLL_WIDTH - ROLL_GRID_START
        ticks_in_window, _ = self.get_window_range()
        current_tick = int(self.window_x + mouse_x / grid_width * ticks_in_window)
        self.playhead_pos = current_tick
        return
    
    def set_playhead_tick(self, tick):
        self.playhead_pos = tick
        ticks_in_window, _ = self.get_window_range()
        if (tick < self.window_x):
            ticks_in_cell = self.get_ticks_in_cell()
            self.window_x = tick // ticks_in_cell * ticks_in_cell
        if (tick - self.window_x) > ticks_in_window:
            self.window_x += ticks_in_window
        return
    
    def get_playhead_time(self):
        '''Expresses playhead position in terms of seconds from the start of the roll.'''
        tick = self.playhead_pos
        time = tick/TICKS_IN_BEAT * 60/self.bpm
        return time
    
    def handle_grid_click(self, mouse_pos, cell, event, click_timer: ClickTimer):
        '''Handles clicks on the grid.'''
        mouse_x, mouse_y = mouse_pos
        cell_x, cell_y = cell
        if event.button == 1:   
            #left click
            if not click_timer.in_double_click():
                # single click
                click_timer.reset()
                note = self.note_from_cell(cell)
                if (note):
                    # click on note
                    self.select_note(note)
                    #print("note selected")
                    cells_from_lbound = (cell_x - self.window_x) // self.cell_width + 1
                    edge_x = ROLL_GRID_START + cells_from_lbound * self.cell_width
                    if (cell_x + self.get_ticks_in_cell() == self.selected_note.end) and (edge_x - mouse_x <= 10):
                        self.edge_pressed = True
            elif cell_y <= self.window_y:
                # double click
                new_note = Note(
                    pitch = cell_y, 
                    start = cell_x, 
                )
                self.add_note(new_note)
        if event.button == 3:   #right click
            if (cell_y <= self.window_y):
                note_to_delete = self.note_from_cell(cell)
                if (note_to_delete):
                    self.delete_note(note_to_delete)

    
    def handle_click(self, mouse_pos, event, click_timer: ClickTimer):
        '''Handles clicks in the piano roll area.'''
        cell = self.click_to_cell_pos(mouse_pos)
        if self.cell_in_grid(cell):
            self.handle_grid_click(mouse_pos, cell, event, click_timer)
        return

    
    def handle_motion(self, event, mouse_pos):
        '''Handles mouse motion in the piano roll area.'''
        move_x, move_y = event.rel
        if self.edge_pressed:
            step = move_x / self.cell_width * self.get_ticks_in_cell()
            self.selected_note.duration += step
            self.selected_note.end += step
        elif self.selected_note:
            new_start, new_pitch = self.click_to_cell_pos(mouse_pos)
            #print((new_start, new_pitch))
            if self.cell_in_grid((new_start, new_pitch)):
                self.selected_note.start = new_start
                self.selected_note.end = new_start + self.selected_note.duration
                self.selected_note.pitch = new_pitch
            else:
                self.deselect_note()
        return
    
    def handle_release(self, event):
        '''Handles releases of mouse buttons in the piano roll area.'''
        if event.button == 1:
            if not self.selected_note:
                return
            if self.edge_pressed:
                #release edge on selected_note
                self.edge_pressed = False
                self.selected_note.duration = round(self.selected_note.duration / self.get_ticks_in_cell()) * self.get_ticks_in_cell()
                self.selected_note.end = self.selected_note.start + self.selected_note.duration
                if (self.selected_note.duration <= 0):
                    self.delete_note(self.selected_note)
                #print('edge released')
            else: 
                #release note
                x_range, y_range = self.get_window_range()
                self.selected_note.start = min(max(self.selected_note.start, self.window_x), self.window_x+x_range)
                self.selected_note.end = self.selected_note.start + self.selected_note.duration
                self.selected_note.pitch = min(max(self.selected_note.pitch, self.window_y-y_range+1), self.window_y)
            self.selected_note = None


    
    def handle_wheel(self, event):
        '''Handles scrolling in the piano roll area.'''
        x_range, y_range = self.get_window_range()
        if (event.y):
            #vertical scroll
            step = event.y
            new_y = self.window_y + step
            new_y = max(new_y, 11+y_range)
            new_y = min(new_y, 127)
            self.window_y = new_y
            # print(self.window_y)
        elif (event.x):
            # horizontal scroll
            step = event.x
            new_x = self.window_x + step * self.get_ticks_in_cell()
            new_x = max(0, new_x)
            self.window_x = new_x
            # print(self.window_x)
        return
    
    def on_ruler(self, mouse_pos):
        '''Checks if the mouse is on the ruler (where the bar numbers are shown).'''
        mouse_x, mouse_y = mouse_pos
        return mouse_x > ROLL_GRID_START and 0 <= mouse_y <= self.cell_height
    
    def handle_mouse(self, mouse_pos, event, click_timer):
        '''Handle all mouse operations in the piano roll.'''
        mouse_pos = np.array(mouse_pos) - np.array([ROLL_LEFT_BOUND, ROLL_UP_BOUND]) # adjust for screen
        if self.velocity_slider.rect.collidepoint(mouse_pos):
            self.velocity_slider.handle_event(mouse_pos, event)
        else:
            self.velocity_slider.release_slider()
        if self.plus_button.handle_mouse(mouse_pos, event):
            self.bpm += 1
        if self.minus_button.handle_mouse(mouse_pos, event):
            self.bpm -= 1
        if self.on_ruler(mouse_pos) and event.type == pygame.MOUSEBUTTONDOWN:
            self.set_playhead(mouse_pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_click(mouse_pos, event, click_timer)
        if event.type == pygame.MOUSEMOTION:
            self.handle_motion(event, mouse_pos)
        if event.type == pygame.MOUSEBUTTONUP:
            self.handle_release(event)
        if event.type == pygame.MOUSEWHEEL:
            self.handle_wheel(event)
        return

    
    def draw_notes(self):
        for note in self.notes:
            window_ticks = self.get_ticks_in_cell() * ROLL_WIDTH // self.cell_width
            x_in_range = (note.end >= self.window_x) and (note.start <= self.window_x + window_ticks)
            y_in_range = 0 <= (self.window_y - note.pitch) < (ROLL_HEIGHT // self.cell_height - 1)
            if x_in_range and y_in_range:
                # draw note
                x_left_offset = ROLL_GRID_START + max(-40, (note.start - self.window_x) * ROLL_WIDTH // window_ticks)
                x_right_offset = ROLL_GRID_START + min(ROLL_WIDTH, (note.end - self.window_x) * ROLL_WIDTH // window_ticks)
                y_offset = self.cell_height + (self.window_y - note.pitch) * self.cell_height
                x_length = x_right_offset-x_left_offset
                note_rect = pygame.Rect(
                    x_left_offset, y_offset,
                    x_length, self.cell_height
                )
                pygame.draw.rect(self.image, GREEN, note_rect, border_radius=10)

    
    def draw_bounds(self):
        '''Draw boundaries of the piano roll area.'''
        # horizontal
        pygame.draw.line(self.image, WHITE, (0, 0), (ROLL_WIDTH, 0), width=3)
        pygame.draw.line(self.image, WHITE, (0, self.cell_height), (ROLL_WIDTH, self.cell_height), width=2)
        pygame.draw.line(self.image, WHITE, (0, ROLL_HEIGHT), (ROLL_WIDTH, ROLL_HEIGHT), width=3)
        # vertical
        pygame.draw.line(self.image, WHITE, (ROLL_GRID_START, 0), (ROLL_GRID_START, ROLL_HEIGHT), width=3)
        pygame.draw.line(self.image, WHITE, (0, 0), (0, ROLL_HEIGHT), width=3)
        pygame.draw.line(self.image, WHITE, (ROLL_WIDTH-1, 0), (ROLL_WIDTH-1, ROLL_HEIGHT), width=3)
        
    def draw_grid(self):
        # draw horizontal lines
        y_list = np.arange(2*self.cell_height, ROLL_HEIGHT, self.cell_height)
        for y in y_list:
            x_start = ROLL_GRID_START
            x_end = ROLL_WIDTH
            pygame.draw.line(self.image, GREY, (x_start, y), (x_end, y))
        # draw vertical lines
        x_list = np.arange(ROLL_GRID_START, ROLL_WIDTH, self.cell_width)
        for x in x_list:
            color = GREY
            absolute_x, _ = self.click_to_cell_pos([x, 0])
            y_start = self.cell_height
            y_end = ROLL_HEIGHT
            bar_num = None
            if (absolute_x % (TICKS_IN_BEAT * self.beats_in_bar) == 0):  # bars
                color = WHITE
                y_start = 0
                bar_num = absolute_x // (TICKS_IN_BEAT * self.beats_in_bar) + 1
            elif (absolute_x % (TICKS_IN_BEAT) == 0): # beats
                color = LIGHT_GREY
                y_start = 0
            pygame.draw.line(self.image, color, (x, y_start), (x, y_end))
            if bar_num:
                num_text = FONT.render(f'{bar_num}', 1, WHITE)
                num_rect = num_text.get_rect(midleft=(x+5, self.cell_height//2))
                self.image.blit(num_text, num_rect)

    
    def draw_bpm(self):
        bpm_surface = FONT.render(str(f'BPM = {self.bpm}'), True, WHITE)
        bpm_rect = bpm_surface.get_rect(center=(ROLL_GRID_START//2, self.cell_height//2))
        self.image.blit(bpm_surface, bpm_rect)
        self.image.blit(self.plus_button.surface, self.plus_button.rect)
        self.image.blit(self.minus_button.surface, self.minus_button.rect)
    
    def draw_pitches(self):
        '''Draw pitches indicated on the left hand side of the piano roll.'''
        _, y_range = self.get_window_range()
        note_nums = np.arange(self.window_y, self.window_y-y_range, -1)
        for i, pitch in enumerate(note_nums, 1):
            pitch_name = self.get_pitch_name(pitch)
            #print(pitch_name)
            if pitch_name[1] == '#':
                key_color = BLACK
                text_color = WHITE
            else:
                key_color = WHITE
                text_color = BLACK
            pygame.draw.rect(
                self.image, 
                key_color, 
                pygame.Rect(0, self.cell_height*i, ROLL_GRID_START, self.cell_height)
            )
            note_text_surface = FONT.render(pitch_name, True, text_color)
            note_text_rect = note_text_surface.get_rect(midright=(ROLL_GRID_START-10, self.cell_height*(i+0.5)))
            self.image.blit(note_text_surface, note_text_rect)
            pygame.draw.line(
                self.image,
                BLACK,
                (0, self.cell_height*i), 
                (ROLL_GRID_START, self.cell_height*i)
            )
    
    def draw_playhead(self):
        ticks_in_window, _ = self.get_window_range()
        frac = (self.playhead_pos - self.window_x) / ticks_in_window
        render_x = ROLL_GRID_START + frac * (ROLL_WIDTH - ROLL_GRID_START)
        pygame.draw.line(
            self.image,
            pygame.Color('yellow'),
            (render_x, 0),
            (render_x, ROLL_HEIGHT)
        )


    def update(self):
        '''Draw all parts of the piano roll on screen.'''
        self.image.fill(DARK_GREY)
        self.draw_grid()
        self.draw_notes()
        self.draw_playhead()
        self.draw_pitches()
        self.draw_bpm()
        self.draw_bounds()
        self.velocity_slider.draw(self.image)
        SCREEN.blit(self.image, self.rect)

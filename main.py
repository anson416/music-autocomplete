import shutil
import sys

import pygame

from classes.clicktimer import ClickTimer
from classes.constants import *
from classes.inputs import Inputs
from classes.outputs import Output
from classes.pianoroll import PianoRoll

if __name__ == '__main__':
    pygame.init()
    piano_roll = PianoRoll()
    click_timer = ClickTimer()
    output = Output(piano_roll)
    inputs = Inputs(piano_roll)

    pygame.display.set_caption("Music Auto-complete")
    pygame.display.update()
    while True:

        # handle events
        mouse_pos = pygame.mouse.get_pos()

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                shutil.rmtree(TEMP_MUSIC_DIRECTORY)  # Remove temporary music directory
                sys.exit()
            if piano_roll.rect.collidepoint(mouse_pos):
                piano_roll.handle_mouse(mouse_pos, event, click_timer)
            else:
                piano_roll.deselect_note()
                
            if output.rect.collidepoint(mouse_pos):
                output.handle_mouse(mouse_pos, event)

            if inputs.rect.collidepoint(mouse_pos):
                inputs.handle_mouse(mouse_pos, event)
                

        # click timer
        click_timer.tick()
        
        SCREEN.fill(DARK_GREY)
        piano_roll.update()
        output.update()
        click_timer.tick()

        inputs.update()

        pygame.display.update()


from pygame.time import Clock

from classes.constants import *


class ClickTimer():
    '''
    A timer used to detect double clicks.
    '''
    def __init__(self):
        self.clock = Clock()
        self.click_time = DOUBLE_CLICK_TIME              #milliseconds
        self.timer = self.click_time
        self.dt = 0
    
    def in_double_click(self):
        return self.timer < self.click_time
    
    def tick(self):
        self.dt = self.clock.tick(FPS)
        if (self.timer < self.click_time):
            self.timer += self.dt
    
    def reset(self):
        self.timer = 0
       
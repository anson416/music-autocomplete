from classes.constants import *


class Button():
    def __init__(self, text, centre):
        self.text = text
        self.surface = FONT.render(self.text, True, (255, 255, 255))
        self.rect = self.surface.get_rect(center = centre)
        self.colour = DARK_GREY
        self.centre = centre

    def handle_mouse(self, mouse_pos, event):
        if self.rect.collidepoint(mouse_pos):
            self.colour = LIGHT_GREY
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.colour = WHITE
                return True
        else:
            self.colour = DARK_GREY
        return False
    
    def change_text(self, new_text):
        self.text = new_text
        self.surface = FONT.render(self.text, True, (255, 255, 255))
        self.rect = self.surface.get_rect(center = self.centre)

    def draw_button(self, SCREEN=SCREEN):
        pygame.draw.rect(SCREEN, self.colour, self.rect)
        SCREEN.blit(self.surface, self.rect)

import pygame
import sys
import math
import os

from chess_offline import run as run_offline
from chess_multiplayer import run as run_multiplayer

# --- MENU CONFIG ---
WIDTH, HEIGHT = 800, 600
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "audio")

# Invisible clickable regions (measured to the artwork)
OFFLINE_RECT      = pygame.Rect(114, 477, 249, 65)
MULTIPLAYER_RECT  = pygame.Rect(437, 475, 249, 64)

# Glow look
GLOW_COLOR = (255, 215, 0)   # gold
GLOW_RADIUS = 12             # rounded corners
PULSE_SPEED = 0.1            # pulse rate (smaller = slower)
PULSE_MIN_THICK = 3
PULSE_MAX_THICK = 7


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Chess Game")
    clock = pygame.time.Clock()

    # Music: menu theme
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    try:
        pygame.mixer.music.load(os.path.join(AUDIO_DIR, "main_music.mp3"))
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"[warn] Could not start menu music: {e}")

    # Background art
    bg = None
    try:
        bg = pygame.image.load(os.path.join(ASSETS_DIR, "main_menu_sprite.png"))
        bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))
    except Exception as e:
        print(f"[warn] Could not load background: {e}")

    buttons = [
        ("Offline",     OFFLINE_RECT,     run_offline),
        ("Multiplayer", MULTIPLAYER_RECT, run_multiplayer),
    ]

    frame = 0
    debug_mode = False   # press D to toggle outlines always-on

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:
                    debug_mode = not debug_mode
                    print("Debug glow:", debug_mode)

            if event.type == pygame.MOUSEBUTTONDOWN:
                for name, rect, callback in buttons:
                    if rect.collidepoint(event.pos):
                        print(f"{name} clicked at {event.pos} → Rect: {rect}")

                        # stop menu music before entering game
                        try:
                            pygame.mixer.music.stop()
                        except:
                            pass

                        # launch game; when it returns, we're back to menu
                        callback()

                        # Recreate menu surface in case the game changed size
                        screen = pygame.display.set_mode((WIDTH, HEIGHT))

                        # resume menu music
                        try:
                            pygame.mixer.music.load(os.path.join(AUDIO_DIR, "main_music.mp3"))
                            pygame.mixer.music.play(-1)
                        except Exception as e:
                            print(f"[warn] Could not resume menu music: {e}")

        # draw background
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill((30, 30, 30))

        # hover glow (pulse)
        mouse_pos = pygame.mouse.get_pos()
        frame += 1
        pulse = (math.sin(frame * PULSE_SPEED) + 1) / 2.0  # 0..1
        glow_thickness = PULSE_MIN_THICK + int(pulse * (PULSE_MAX_THICK - PULSE_MIN_THICK))

        for _, rect, _ in buttons:
            if rect.collidepoint(mouse_pos) or debug_mode:
                pygame.draw.rect(screen, GLOW_COLOR, rect, glow_thickness, border_radius=GLOW_RADIUS)

        pygame.display.flip()
        clock.tick(FPS)

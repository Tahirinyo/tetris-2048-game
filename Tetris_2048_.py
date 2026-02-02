"""
Tetris 2048: Combined Tetris and 2048 gameplay with enhanced UI features

This script:
  - Sets up the game environment and canvas
  - Handles user input (keyboard and mouse)
  - Renders the game grid, falling pieces, and side panel
  - Manages game state including:
      • Grid contents and collision logic
      • Falling tetromino creation, movement, rotation, hard drop
      • Hold piece functionality and next piece preview
      • Scoring system and level-based speed increases
  - Provides bonus features:
      • High-score saving and top-5 leaderboard
      • Auto-save, auto-resume, and manual save
      • Sound effects and background music with mute/unmute
      • Pause menu, controls screen, and game-over screen

Uses:
  - lib.stddraw for drawing and UI elements
  - pygame for audio playback and mixer
  - Custom classes: GameGrid, Tetromino, Tile, Point
"""

import lib.stddraw as stddraw  # drawing utilities for game canvas
from lib.picture import Picture    # class to load and display images
from lib.color import Color        # class to handle colors
import os                          # file and directory operations
import json                        # load and save JSON data
import random                      # generate random choices
from point import Point            # 2D point representation
from game_grid import GameGrid     # main grid logic for game state
from tetromino import Tetromino    # tetromino shapes and behavior
import pickle                      # serialize game state for saving
import pygame                      # multimedia library for sound
import sys                         # system functions and exit
from tile import Tile              # tile objects that compose tetrominoes

# -----------------------------------------------------------------------------
# Initialize pygame mixer for sound effects
pygame.mixer.init()               # start the sound mixer subsystem
sound_land = None                  # placeholder for landing sound
is_muted = False                   # track if sound is muted

# Determine directory where this script resides
today_dir = os.path.dirname(os.path.realpath(__file__))

pygame.mixer.init()               # reinitialize mixer (redundant but safe)

# Attempt to load and play background music
try:
    bgm_path = os.path.join(today_dir, "sounds", "Tetris Theme.mp3")
    pygame.mixer.music.load(bgm_path)    # load the main theme music
    pygame.mixer.music.set_volume(0.1)   # set BGM volume low
    pygame.mixer.music.play(-1)          # loop music forever
except Exception:
    print("Background music failed to load, skipping BGM.")

# Attempt to load sound effect files
try:
    sound_land  = pygame.mixer.Sound(os.path.join(today_dir, "sounds", "land.mp3"))
except Exception as e:
    print("Sound effects failed to load:", e)
    sound_land  = None               # disable land sound on failure

# -----------------------------------------------------------------------------
# Global variables for bonus features
HIGHSCORES_FILE = "highscores.json"  # file to store top scores
SAVEGAME_FILE   = "savegame.dat"     # file to auto-save current game

hold_piece = None                       # currently held tetromino
hold_used  = False                      # whether hold was used this drop

initial_fall_delay = 300               # starting delay between drops (ms)
fall_delay = initial_fall_delay         # dynamic delay for leveling
level      = 1                          # current game level

# Container for top-5 high score entries
high_scores = []  # each entry is a dict: {"name": str, "score": int}

def load_high_scores():
    global high_scores
    # Load existing high scores from JSON if file exists
    if os.path.exists(HIGHSCORES_FILE):
        try:
            raw = json.load(open(HIGHSCORES_FILE, "r", encoding="utf-8"))
            high_scores.clear()                # clear previous entries
            for item in raw:
                # if already a dict with name/score, accept as-is
                if isinstance(item, dict) and "name" in item and "score" in item:
                    high_scores.append(item)
                # if just a number, wrap in anonymous entry
                elif isinstance(item, int):
                    high_scores.append({"name": "Anonim", "score": item})
            # sort descending and keep only top 5
            high_scores.sort(key=lambda e: e["score"], reverse=True)
            if len(high_scores) > 5:
                del high_scores[5:]
        except Exception:
            high_scores = []  # reset on load error
    else:
        high_scores = []      # no file => empty list


def save_high_scores():
    # Save current high_scores list to JSON file
    with open(HIGHSCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(high_scores, f, ensure_ascii=False, indent=2)

def qualifies_top(score):
    # Check if score is high enough to be in top 5
    return len(high_scores) < 5 or score > high_scores[-1]["score"]

def try_add_score(score):
    # If score qualifies, prompt for name and insert entry
    if not qualifies_top(score):
        return False

    name = get_name_input(score, high_scores)
    if name is None:
        return False

    entry = {"name": name.strip() or "Anonim", "score": score}
    high_scores.append(entry)
    high_scores.sort(key=lambda e: e["score"], reverse=True)
    if len(high_scores) > 5:
        high_scores.pop()                    # remove lowest if over 5

    save_high_scores()                     # persist updated list
    return True

# -----------------------------------------------------------------------------
# Auto-save and resume functions to persist game progress

def auto_save(game_state):
    with open(SAVEGAME_FILE, "wb") as f:
        pickle.dump(game_state, f)          # write serialized state

def auto_resume():
    # Load saved game state if available
    if os.path.exists(SAVEGAME_FILE):
        try:
            with open(SAVEGAME_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return None                      # corrupt or unreadable
    return None                             # no save file

def delete_save():
    # Remove save file to start fresh
    if os.path.exists(SAVEGAME_FILE):
        os.remove(SAVEGAME_FILE)

# -----------------------------------------------------------------------------
# Helper to create a random tetromino shape
def create_tetromino():
    return Tetromino(random.choice(['I','O','Z','S','T','J','L']))

# Draw a small preview of a tetromino at given position and scale
def draw_tetromino_preview(t, bx, by, scale):
    n = len(t.tile_matrix)               # dimension of its matrix
    # center offset so preview stays centered
    ox = bx - (n - 1) * scale / 2
    oy = by - (n - 1) * scale / 2
    for r in range(n):
        for c in range(n):
            if t.tile_matrix[r][c] is not None:
                # compute draw position for each tile
                p = Point(ox + c * scale, oy + (n - 1 - r) * scale)
                t.tile_matrix[r][c].draw(p, length=scale)

# Handle text input for player name when a high score is achieved
def get_name_input(score, top_scores):
    # if no room in top 5, skip input
    if len(top_scores) >= 5 and score <= top_scores[-1]["score"]:
        return None

    name = ""                  # accumulated input
    cursor_visible = True       # blinking cursor state
    blink_timer = 0             # timer for blink toggle
    gw, gh, extra = 16, 20, 10   # grid width, height, panel size
    max_length = 12             # maximum name length

    btn_w, btn_h = 3, 1.2       # OK button dimensions
    btn_x = (gw + extra - btn_w) / 2
    btn_y = gh - 13.5

    while True:
        stddraw.clear(Color(42, 69, 99))  # dark-blue background

        # Title announcing top score
        stddraw.setFontSize(30)
        stddraw.setPenColor(Color(255, 255, 0))
        stddraw.text((gw + extra - 1) / 2, gh - 3, "You've Entered the Top 5!")

        # Display the player's score
        stddraw.setFontSize(20)
        stddraw.setPenColor(Color(255, 255, 255))
        stddraw.text((gw + extra - 1) / 2, gh - 6, f"Your Score: {score}")

        # Input box background
        stddraw.setPenColor(Color(200, 200, 200))
        stddraw.filledRectangle((gw + extra - 6) / 2, gh - 10, 6, 1.5)

        # Render current name + cursor
        stddraw.setPenColor(Color(0, 0, 0))
        stddraw.setFontSize(22)
        display_text = name + ("|" if cursor_visible else "")
        stddraw.text((gw + extra - 1) / 2, gh - 9.2, display_text)

        # Prompt instructions
        stddraw.setFontSize(16)
        stddraw.setPenColor(Color(255, 255, 255))
        stddraw.text((gw + extra - 1) / 2, gh - 12, "Enter your name and click OK")

        # Draw OK button
        stddraw.setPenColor(Color(80, 80, 80))
        stddraw.filledRectangle(btn_x, btn_y, btn_w, btn_h)
        stddraw.setPenColor(Color(255, 255, 255))
        stddraw.setFontSize(18)
        stddraw.text(btn_x + btn_w / 2, btn_y + btn_h / 2, "OK")

        stddraw.show(100)  # update frame

        # Toggle cursor visibility periodically
        blink_timer += 1
        if blink_timer > 5:
            cursor_visible = not cursor_visible
            blink_timer = 0

        # Handle typed keys
        if stddraw.hasNextKeyTyped():
            key = stddraw.nextKeyTyped()
            if key == "backspace":
                name = name[:-1]
            elif len(key) == 1 and len(name) < max_length:
                name += key

        # Handle mouse click on OK
        if stddraw.mousePressed():
            mx, my = stddraw.mouseX(), stddraw.mouseY()
            if (btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h):
                return name.strip() or "Anonim"

    # Fallback loop handling 'Enter' key instead of click
    name = ""
    cursor_visible = True
    blink_timer = 0
    gw, gh, extra = 16, 20, 10
    max_length = 12

    while True:
        stddraw.clear(Color(42, 69, 99))
        # Similar UI drawing code omitted for brevity...
        if stdddraw.hasNextKeyTyped():
            key = stddraw.nextKeyTyped()
            if key in ["enter", "\n", "\r", "Return"]:
                return name.strip() or "Anonim"
            elif key == "backspace":
                name = name[:-1]
            elif len(key) == 1 and len(name) < max_length:
                name += key

# -----------------------------------------------------------------------------
# Draw Pause, Exit, and Mute/Unmute buttons on side panel
def draw_buttons(pause_rect, exit_rect):
    global is_muted
    # Draw pause button
    stddraw.setPenColor(Color(80,80,80))
    stddraw.filledRectangle(*pause_rect)
    stddraw.setPenColor(Color(255,255,255))
    stddraw.setFontSize(16)
    px, py, pw, ph = pause_rect
    stddraw.text(px + pw/2, py + ph/2, "Pause")

    # Draw exit button
    stddraw.setPenColor(Color(80,80,80))
    stddraw.filledRectangle(*exit_rect)
    stddraw.setPenColor(Color(255,255,255))
    ex, ey, ew, eh = exit_rect
    stddraw.text(ex + ew/2, ey + eh/2, "Exit and Save")

    # Draw mute/unmute toggle below pause
    mute_rect = (px, ey - 1.5, pw, ph)
    stddraw.setPenColor(Color(80,80,80))
    stddraw.filledRectangle(*mute_rect)
    stddraw.setPenColor(Color(255,255,255))
    # label changes based on current mute state
    stddraw.text(px + pw/2, ey - 1.5 + ph/2, "Mute" if not is_muted else "Unmute")

    return {"pause": pause_rect, "exit": exit_rect, "mute": mute_rect}

# Render the side panel with score, next/hold previews, and controls
def draw_side_panel(gw, gh, extra, grid, nxt, hold, lvl):
    """
    Show side panel that includes:
      - Current score and level
      - Top 5 high scores list
      - Previews for next and held tetrominoes
      - Control buttons (Pause, Exit, Mute/Unmute)
    """
    # Position and size of panel
    px, py = gw - 0.5, -0.5
    pw, ph = extra, gh
    # Draw panel background
    stddraw.setPenColor(Color(220, 220, 220))
    stddraw.filledRectangle(px, py, pw, ph)

    # Display score
    stddraw.setPenColor(Color(0, 0, 0))
    stddraw.setFontSize(18)
    tx, ty = px + 1, gh - 2
    stddraw.text(tx + 0.5, ty, f'Score: {grid.score}')
    ty -= 1

    # Display Top-5 heading
    stddraw.setFontSize(18)
    stddraw.text(tx + 0.5, ty, 'Top Scores:')
    ty -= 1
    # List high scores
    for i, entry in enumerate(high_scores, start=1):
        stddraw.text(tx, ty, f"{i}. {entry['name']}:{entry['score']}")
        ty -= 1
    ty -= 0.5

    # Labels for next and hold previews
    half = pw / 2
    stddraw.setPenColor(Color(0, 0, 0))
    stddraw.setFontSize(18)
    stddraw.text(tx, ty, 'Next:')
    stddraw.text(tx + half, ty, 'Hold:')
    # Position for preview graphics
    preview_y = ty - 2.0
    # Draw next piece
    draw_tetromino_preview(nxt, tx + 1, preview_y, 0.8)
    # Draw held piece if exists
    if hold:
        draw_tetromino_preview(hold, tx + half + 1, preview_y, 0.8)
    # Update ty for further UI
    ty = preview_y - 3

    # Draw bottom section for Pause/Exit buttons
    bottom_h = 6.0
    stddraw.setPenColor(Color(190, 190, 190))
    stddraw.filledRectangle(px, py, pw, bottom_h)
    bw, bh = 4, 1.2
    bx = px + (pw - bw) / 2
    pause_r = (bx, py + bottom_h - 2, bw, bh)
    exit_r  = (bx, py + bottom_h - 4, bw, bh)
    return draw_buttons(pause_r, exit_r)

# -----------------------------------------------------------------------------
# Utility: check if a point is inside a rectangle
def is_inside_rect(x, y, rect):
    """Return True if (x,y) lies within rect=(rx,ry,rw,rh)."""
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh

# -----------------------------------------------------------------------------
# Main game menu overlay, returns None or saved state
def display_game_menu(gh, gw, extra):
    """
    Draws and handles interactions for:
      - Start New Game
      - Resume Saved Game (if available)
      - Controls Screen
    """
    # Colors for background and buttons
    bg   = Color(42, 69, 99)
    btnc = Color(25, 255, 228)
    txtc = Color(31, 160, 239)
    stddraw.clear(bg)

    # Center coordinates
    cx = ((gw + extra - 0.5) + (-0.5)) / 2
    cy = ((gh - 0.5) + (-0.5)) / 2 + gh * 0.2

    # Optional menu image
    try:
        pic = Picture(os.path.join(os.path.dirname(__file__), 'images', 'menu_image.png'))
        stddraw.picture(pic, cx, cy)
    except:
        pass  # safely ignore missing image

    # Button layout
    bw, bh = (gw + extra) * 0.6, 2.0
    spacing = 1.2
    start_btn  = (cx - bw/2, cy - 5, bw, bh)
    resume_btn = None
    resume_y   = start_btn[1] - bh - spacing
    if os.path.exists(SAVEGAME_FILE):
        resume_btn = (cx - bw/2, resume_y, bw, bh)
    ctrl_btn   = (cx - bw/2, resume_y - (bh + spacing), bw, bh)

    # Draw "Start New Game" button
    stddraw.setFontSize(20)
    stddraw.setPenColor(btnc)
    stddraw.filledRectangle(*start_btn)
    stddraw.setPenColor(txtc)
    stddraw.text(cx, start_btn[1] + bh/2, "Start New Game")

    # Draw "Resume Saved Game" if file exists
    if resume_btn:
        stddraw.setPenColor(btnc)
        stddraw.filledRectangle(*resume_btn)
        stddraw.setPenColor(txtc)
        stddraw.text(cx, resume_btn[1] + bh/2, "Resume Saved Game")

    # Draw "Controls" button
    stddraw.setPenColor(btnc)
    stddraw.filledRectangle(*ctrl_btn)
    stddraw.setPenColor(txtc)
    stddraw.text(cx, ctrl_btn[1] + bh/2, "Controls")

    stddraw.show(0)

    # Input loop for menu interactions
    while True:
        stddraw.show(100)
        # Mouse click handling
        if stddraw.mousePressed():
            mx, my = stddraw.mouseX(), stddraw.mouseY()
            if is_inside_rect(mx, my, start_btn):
                delete_save()
                return None
            if resume_btn and is_inside_rect(mx, my, resume_btn):
                return auto_resume()
            if is_inside_rect(mx, my, ctrl_btn):
                show_control_screen(gw, gh, extra)
                return display_game_menu(gh, gw, extra)
        # Keyboard shortcuts
        if stddraw.hasNextKeyTyped():
            k = stddraw.nextKeyTyped().lower()
            if k == 's':
                delete_save()
                return None
            if k == 'r' and resume_btn:
                return auto_resume()
            if k == 'c':
                show_control_screen(gw, gh, extra)
                return display_game_menu(gh, gw, extra)

def show_control_screen(gw, gh, extra,
                        grid=None, cur=None, nxt=None,
                        hold=None, used=None, delay=None, level=None):
    """
    Display the control legend screen.
    Wait for any keypress or mouse click to return.
    """
    # Fill background
    bg = Color(42, 69, 99)
    stddraw.clear(bg)

    # Draw the title
    stddraw.setPenColor(Color(255, 255, 0))  # bright yellow
    stddraw.setFontSize(30)
    stddraw.text((gw + extra - 1) / 2, gh - 2, "Controls")

    # List each control instruction
    stddraw.setFontSize(18)
    stddraw.setPenColor(Color(255, 255, 255))  # white
    controls = [
        "← → ↓ : Move left/right/down",
        "↑       : Rotate",
        "Space   : Hard drop",
        "H       : Hold piece",
        "P       : Pause",
        "Esc/Click: Back to Menu"
    ]
    y = gh - 6
    for line in controls:
        stddraw.text((gw + extra - 1) / 2, y, line)
        y -= 2  # move down for next line

    stddraw.show(0)

    # Pause here until user indicates they want to continue
    while True:
        stddraw.show(100)
        if stddraw.hasNextKeyTyped() or stddraw.mousePressed():
            break


def pause_game(gw, gh, extra, grid, cur, nxt, hold, used, delay, level):
    """
    Show the pause menu with four options:
      - Resume
      - Controls
      - Save Game
      - Exit
    Handle both clicks and shortcut keys.
    """
    # Dark background and 'Paused' banner
    stddraw.clear(Color(42, 69, 99))
    stddraw.setPenColor(Color(255, 255, 0))
    stddraw.setFontSize(36)
    cx = (gw + extra - 1) / 2
    cy = gh / 2 + 4
    stddraw.text(cx, cy, "Paused")

    # Define button rectangles
    bw, bh = 6, 1.5
    resume_btn = (cx - bw/2, cy - 3, bw, bh)
    ctrl_btn   = (cx - bw/2, cy - 5, bw, bh)
    save_btn   = (cx - bw/2, cy - 7, bw, bh)
    exit_btn   = (cx - bw/2, cy - 9, bw, bh)

    # Draw all buttons with labels
    for rect, label in [(resume_btn, "Resume"),
                        (ctrl_btn,   "Controls"),
                        (save_btn,   "Save Game"),
                        (exit_btn,   "Exit")]:
        stddraw.setPenColor(Color(80,80,80))    # dark gray
        stddraw.filledRectangle(*rect)
        stddraw.setPenColor(Color(255,255,255)) # white text
        stddraw.setFontSize(18)
        x, y, w, h = rect
        stddraw.text(x + w/2, y + h/2, label)

    stddraw.show(0)

    # Input loop: respond to clicks or keys
    while True:
        stddraw.show(100)

        # Handle mouse clicks on buttons
        if stddraw.mousePressed():
            mx, my = stddraw.mouseX(), stddraw.mouseY()
            if is_inside_rect(mx, my, resume_btn):
                return  # back to main loop (resume)
            if is_inside_rect(mx, my, ctrl_btn):
                # show controls screen, then return here
                show_control_screen(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
                pause_game(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
                return
            if is_inside_rect(mx, my, save_btn):
                auto_save({
                    "grid": grid,
                    "current_tetromino": cur,
                    "next_tetromino": nxt,
                    "hold_piece": hold,
                    "hold_used": used,
                    "fall_delay": delay,
                    "level": level
                })  # immediately write save file
            if is_inside_rect(mx, my, exit_btn):
                sys.exit(0)  # quit program

        # Keyboard shortcuts
        if stddraw.hasNextKeyTyped():
            k = stddraw.nextKeyTyped().lower()
            if k == 'p':   # resume
                return
            if k == 'c':   # show controls
                show_control_screen(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
                pause_game(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
                return
            if k == 's':   # save game
                auto_save({
                    "grid": grid,
                    "current_tetromino": cur,
                    "next_tetromino": nxt,
                    "hold_piece": hold,
                    "hold_used": used,
                    "fall_delay": delay,
                    "level": level
                })
                # brief visual confirmation
                stddraw.setPenColor(Color(255,255,255))
                stddraw.setFontSize(24)
                stddraw.text(cx, cy - 10, "Game Saved!")
                stddraw.show(500)
            if k == 'e':   # exit immediately
                sys.exit(0)
    # -----------------------------------------------------------------------------
    # In-pause overlay inside pause_game (draw_overlay):
    def draw_overlay():
        """
        Show the pause overlay instructions:
          - P: Resume
          - C: Controls
          - S: Save Game
          - E: Exit
        """
        stddraw.clear(Color(42, 69, 99))  # dark background
        stddraw.setPenColor(Color(255, 255, 0))  # bright yellow text
        stddraw.setFontSize(36)
        stddraw.text(cx, cy, "Paused")  # title
        stddraw.setFontSize(20)
        # list key instructions
        stddraw.text(cx, cy - 2, "Press 'P' to Resume")
        stddraw.text(cx, cy - 4, "Press 'C' for Controls")
        stddraw.text(cx, cy - 6, "Press 'S' to Save Game")
        stddraw.text(cx, cy - 8, "Press 'E' to Exit")
        stddraw.show(0)  # render immediately

    # call the overlay once
    draw_overlay()

    # loop until user chooses an action
    while True:
        stddraw.show(100)  # pause between frames
        if stddraw.hasNextKeyTyped():
            k = stddraw.nextKeyTyped().lower()  # read key

            if k == 'p':  # resume
                break

            elif k == 'c':  # show controls then overlay again
                show_control_screen(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
                draw_overlay()

            elif k == 's':  # save state and confirm visually
                auto_save({
                    "grid": grid,
                    "current_tetromino": cur,
                    "next_tetromino": nxt,
                    "hold_piece": hold,
                    "hold_used": used,
                    "fall_delay": delay,
                    "level": lvl
                })
                stddraw.setPenColor(Color(255, 255, 255))
                stddraw.setFontSize(24)
                stddraw.text(cx, cy - 10, "Game Saved!")
                stddraw.show(500)  # show confirmation briefly
                draw_overlay()

            elif k == 'e':  # quit game
                sys.exit(0)
# -----------------------------------------------------------------------------
# Final Game Over screen after loss
def game_over_screen(gw, gh, extra, score):
    """
    Display 'Game Over', final score, list top 5 highs,
    and wait for 'R' to restart or 'Q' to quit.
    """
    # grey background
    stddraw.clear(Color(130, 130, 130))

    # big red 'Game Over!' text
    stddraw.setPenColor(Color(255, 100, 100))
    stddraw.setFontSize(60)
    stddraw.text((gw + extra - 1) / 2, gh / 2 + 6, "Game Over!")

    # show the player's score
    stddraw.setFontSize(24)
    stddraw.setPenColor(Color(255, 255, 255))
    stddraw.text((gw + extra - 1) / 2, gh / 2 + 2, f"Your Score: {score}")

    # list out top-5 high scores
    y = gh / 2 - 2
    for i, entry in enumerate(high_scores, start=1):
        stddraw.text((gw + extra - 1) / 2, y, f"{i}. {entry['name']}: {entry['score']}")
        y -= 1

    # instructions to restart or quit
    stddraw.setFontSize(28)
    stddraw.setPenColor(Color(255, 100, 100))
    stddraw.text(
        (gw + extra - 1) / 2,
        gh / 2 - 8,
        "Press 'R' to Restart or 'Q' to Quit"
    )

    stddraw.show(0)  # render frame

    # wait for valid key
    while True:
        stddraw.show(100)
        if stddraw.hasNextKeyTyped():
            key = stddraw.nextKeyTyped().lower()
            if key == "r":                      # restart game
                stddraw._windowCreated = False  # reset drawing window
                start()                         # back to main loop
            elif key == "q":                    # quit
                sys.exit(0)

def start():
    """
    Initialize and run the main game loop.
    Handles menu, game state setup, input, piece dropping, leveling, and game over.
    """
    global hold_piece, hold_used, fall_delay, level, is_muted

    # Load saved top scores from disk
    load_high_scores()

    # Grid dimensions and side-panel width
    gh, gw = 20, 16
    extra = 10

    # Configure drawing canvas size and coordinate system
    stddraw.setCanvasSize(40 * (gw + extra), 40 * gh)
    stddraw.setXscale(-0.5, gw + extra - 0.5)
    stddraw.setYscale(-0.5, gh - 0.5)

    # Inform Tetromino class how big the grid is
    Tetromino.grid_height = gh
    Tetromino.grid_width  = gw

    # Show main menu; state==None for new game, or contains saved state
    state = display_game_menu(gh, gw, extra)
    if state:
        # Resume from saved state
        grid  = state["grid"]
        cur   = state["current_tetromino"]
        nxt   = state["next_tetromino"]
        hold  = state["hold_piece"]
        used  = state["hold_used"]
        delay = state["fall_delay"]
        level = state["level"]
    else:
        # Fresh start: new grid, score reset, two random pieces
        grid = GameGrid(gh, gw)
        grid.score = 0
        grid.cleared_lines = 0
        cur  = create_tetromino()
        grid.current_tetromino = cur
        nxt  = create_tetromino()
        hold = None
        used = False
        delay = initial_fall_delay
        level = 1

    running = True
    # Main game loop
    while running:
        # Keyboard input handling
        if stddraw.hasNextKeyTyped():
            k = stddraw.nextKeyTyped()
            if k in ("left", "right", "down"):
                cur.move(k, grid)           # move piece
            elif k == "up":
                cur.rotate(grid)            # rotate piece
            elif k == "space":
                # hard drop until collision
                while cur.move("down", grid):
                    pass
            elif k == "p":
                # pause menu
                pause_game(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
            elif k == "h" and not used:
                # hold piece logic: swap or set hold
                if hold is None:
                    hold = cur
                    cur  = nxt
                    nxt  = create_tetromino()
                else:
                    cur, hold = hold, cur
                # reset the new current piece to top in random column
                n = len(cur.tile_matrix)
                cur.bottom_left_cell = Point()
                cur.bottom_left_cell.y = Tetromino.grid_height - 1
                cur.bottom_left_cell.x = random.randint(0, Tetromino.grid_width - n)
                grid.current_tetromino = cur
                used = True
            # clear any extra key events
            stddraw.clearKeysTyped()

        # Mouse clicks on side-panel buttons
        if stddraw.mousePressed():
            mx, my = stddraw.mouseX(), stddraw.mouseY()
            btns = draw_side_panel(gw, gh, extra, grid, nxt, hold, level)
            if is_inside_rect(mx, my, btns["pause"]):
                pause_game(gw, gh, extra, grid, cur, nxt, hold, used, delay, level)
            elif is_inside_rect(mx, my, btns["exit"]):
                # save and exit to menu
                auto_save({
                    "grid": grid,
                    "current_tetromino": cur,
                    "next_tetromino": nxt,
                    "hold_piece": hold,
                    "hold_used": used,
                    "fall_delay": delay,
                    "level": level
                })
                running = False
            elif is_inside_rect(mx, my, btns["mute"]):
                # toggle mute state for music and effects
                is_muted = not is_muted
                pygame.mixer.music.set_volume(0 if is_muted else 0.1)
                if sound_land:  sound_land.set_volume(0 if is_muted else 1.0)

        # Automatic piece drop each frame
        if not cur.move("down", grid):
            # piece has landed
            if sound_land:
                sound_land.play()
            tiles, pos = cur.get_min_bounded_tile_matrix(True)
            over = grid.update_grid(tiles, pos)  # lock tiles into grid
            if over:
                # game over condition
                running = False
                break
            # advance to next piece
            cur = nxt
            nxt = create_tetromino()
            grid.current_tetromino = cur
            used = False

        # Level up every 5 lines cleared: speed up drop
        if grid.cleared_lines >= level * 5:
            level += 1
            fall_delay = max(50, fall_delay - 20)

        # Redraw entire frame
        stddraw.clear(Color(42, 69, 99))
        grid.display()                                  # draw the grid and tiles
        draw_side_panel(gw, gh, extra, grid, nxt, hold, level)
        stddraw.show(fall_delay)                        # pause for fall_delay ms

    # After loop ends: handle game over
    delete_save()                                       # remove any autosave
    try_add_score(grid.score)                           # prompt for high-score name
    game_over_screen(gw, gh, extra, grid.score)        # show final game-over screen

if __name__ == "__main__":
    start()

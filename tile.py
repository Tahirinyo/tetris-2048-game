"""
Tile: Represents a single 2048 tile with a numeric value, color mapping, and rendering logic.
This class handles:
  - Random initial value (2 or 4)
  - Mapping numbers to background and text colors
  - Drawing itself as a colored square with border and number text
  - Merging with another tile to double its value
"""
import lib.stddraw as stddraw    # drawing utilities for shapes and text
from lib.color import Color       # color representation for backgrounds and text
import random                     # random choice for initial tile number

class Tile:
    # Thickness of the tile border when drawing
    boundary_thickness = 0.001
    # Default font settings for tile numbers
    font_family = "Arial"
    font_size = 14

    def __init__(self):
        # Start with either 2 or 4 at random
        self.number = random.choice([2, 4])
        # Set colors based on this initial number
        self.set_colors()

    def set_colors(self):
        """
        Choose background and text colors based on the tile's number.
        For numbers >4, use light text; otherwise use dark text.
        """
        # Predefined color palette for each power-of-two value
        color_map = {
        2:    Color(240, 235, 225),  # soft beige
        4:    Color(235, 225, 210),  # warm cream
        8:    Color(230, 200, 170),  # peach tan
        16:   Color(225, 180, 140),  # darker peach
        32:   Color(220, 160, 110),  # orange-tan
        64:   Color(215, 140, 90),   # orange
        128:  Color(210, 120, 70),   # burnt orange
        256:  Color(205, 100, 50),   # strong coral
        512:  Color(200, 80, 30),    # warm red-orange
        1024: Color(190, 60, 20),    # deep orange-red
        2048: Color(175, 45, 5),     # rich reddish tone
    }
    # Choose light or dark text for readability
        fg_dark  = Color(60, 60, 60)       # dark gray text
        fg_light = Color(255, 255, 255)    # white text

        # Background based on number, fallback to gray
        self.background_color = color_map.get(self.number, Color(100, 100, 100))
        # Text color: dark for small numbers, light for larger
        self.foreground_color = fg_dark if self.number <= 4 else fg_light
        # Outline color always black
        self.box_color = Color(0, 0, 0)

    def draw(self, position, length=1):
        """
        Render the tile at a given Point with a square of side 'length'.
        Draw background, border, and centered number text.
        """
        # Draw filled square background
        stddraw.setPenColor(self.background_color)
        stddraw.filledSquare(position.x, position.y, length / 2)
        # Draw border around square
        stddraw.setPenColor(self.box_color)
        stddraw.setPenRadius(Tile.boundary_thickness)
        stddraw.square(position.x, position.y, length / 2)
        stddraw.setPenRadius()  # reset to default
        # Draw the number centered in the tile
        stddraw.setPenColor(self.foreground_color)
        stddraw.setFontFamily(Tile.font_family)
        stddraw.setFontSize(Tile.font_size)
        stddraw.text(position.x, position.y, str(self.number))

    def merge_with(self, other_tile):
        """
        Double this tile's number if it matches other_tile, update colors,
        and optionally log the merge for debugging.
        """
        if self.number == other_tile.number:
            self.number *= 2
            print(f"MERGE: New number = {self.number}")
            # Recompute colors for the new value
            self.set_colors()

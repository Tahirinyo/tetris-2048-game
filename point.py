"""
Point: A simple 2D coordinate class used for positioning tiles, tetrominoes,
and UI elements on the drawing canvas.
Provides methods to move or translate the point.
"""

class Point:
    def __init__(self, x=0, y=0):
        """
        Initialize a new Point at (x, y). Defaults to origin (0,0).
        """
        self.x = x  # horizontal coordinate
        self.y = y  # vertical coordinate

    def translate(self, dx, dy):
        """
        Shift the point by dx in the x-direction and dy in the y-direction.
        """
        self.x += dx
        self.y += dy

    def move(self, x, y):
        """
        Set the point's coordinates directly to (x, y).
        """
        self.x = x
        self.y = y

    def __str__(self):
        """
        Return a human-readable string representation, e.g. "(3, 5)".
        """
        return f"({self.x}, {self.y})"

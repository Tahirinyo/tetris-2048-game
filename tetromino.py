"""
Tetromino: Represents one of the seven Tetris pieces (I, O, Z, S, T, J, L).
Manages:
  - Shape initialization and tile placement in a square matrix
  - Position tracking on the game grid via bottom-left reference point
  - Drawing of its tiles onto the canvas
  - Movement (left, right, down) with collision checks
  - Clockwise rotation with boundary and collision validation
  - Extraction of minimal bounding submatrix for locking into grid
"""
from tile import Tile      # tile objects to populate tetromino matrix
from point import Point    # 2D point for tile placement
import copy as cp          # deep copy for tile matrices
import random              # random starting column and tile numbers
import numpy as np         # matrix operations for rotation and slicing

class Tetromino:
    # Class-wide grid dimensions; set by main before creating pieces
    grid_height, grid_width = None, None

    def __init__(self, shape):
        """
        Initialize a new tetromino of given shape type.
        Creates an n×n tile_matrix and populates occupied_cells positions.
        """
        self.type = shape
        occupied_cells = []
        # Define cell coordinates for each shape in a small square grid
        if self.type == 'I':  # straight line (4×4)
            n = 4
            occupied_cells += [(1,0), (1,1), (1,2), (1,3)]
        elif self.type == 'O':  # square block (2×2)
            n = 2
            occupied_cells += [(0,0), (1,0), (0,1), (1,1)]
        elif self.type == 'Z':  # Z-shape (3×3)
            n = 3
            occupied_cells += [(0,1), (1,1), (1,2), (2,2)]
        elif self.type == 'S':  # S mirror of Z (3×3)
            n = 3
            occupied_cells += [(1,1), (2,1), (0,2), (1,2)]
        elif self.type == 'T':  # T-shape (3×3)
            n = 3
            occupied_cells += [(0,1), (1,1), (2,1), (1,0)]
        elif self.type == 'J':  # J-shape (3×3)
            n = 3
            occupied_cells += [(0,1), (1,1), (2,1), (2,2)]
        elif self.type == 'L':  # L-shape (3×3)
            n = 3
            occupied_cells += [(0,2), (0,1), (1,1), (2,1)]
        # Create empty n×n matrix and fill occupied positions with new Tiles
        self.tile_matrix = np.full((n, n), None)
        for col_index, row_index in occupied_cells:
            self.tile_matrix[row_index][col_index] = Tile()
        # Set initial bottom-left cell so the piece appears at top of grid
        self.bottom_left_cell = Point()
        self.bottom_left_cell.y = Tetromino.grid_height - 1
        # Random horizontal start column within bounds
        self.bottom_left_cell.x = random.randint(0, Tetromino.grid_width - n)

    def get_cell_position(self, row, col):
        """
        Convert matrix indices (row,col) to absolute grid Point.
        """
        n = len(self.tile_matrix)
        position = Point()
        position.x = self.bottom_left_cell.x + col
        position.y = self.bottom_left_cell.y + (n - 1) - row
        return position

    def get_min_bounded_tile_matrix(self, return_position=False):
        """
        Crop the tile_matrix to its minimal bounding box (remove empty rows/cols).
        Returns just the cropped matrix or (matrix, new bottom-left Point) if requested.
        """
        n = len(self.tile_matrix)
        # Determine min/max rows and columns containing tiles
        min_row, max_row = n-1, 0
        min_col, max_col = n-1, 0
        for r in range(n):
            for c in range(n):
                if self.tile_matrix[r][c] is not None:
                    min_row = min(min_row, r)
                    max_row = max(max_row, r)
                    min_col = min(min_col, c)
                    max_col = max(max_col, c)
        # Build the cropped matrix
        height = max_row - min_row + 1
        width  = max_col - min_col + 1
        cropped = np.full((height, width), None)
        for r in range(min_row, max_row+1):
            for c in range(min_col, max_col+1):
                tile = self.tile_matrix[r][c]
                if tile is not None:
                    cropped[r-min_row][c-min_col] = cp.deepcopy(tile)
        if not return_position:
            return cropped
        # Compute new bottom-left reference point after cropping
        blc = cp.copy(self.bottom_left_cell)
        blc.translate(min_col, (n - 1) - max_row)
        return cropped, blc

    def draw(self):
        """
        Draw each tile in the active tetromino on the canvas if within grid.
        """
        n = len(self.tile_matrix)
        for r in range(n):
            for c in range(n):
                tile = self.tile_matrix[r][c]
                if tile is not None:
                    pos = self.get_cell_position(r, c)
                    if pos.y < Tetromino.grid_height:
                        tile.draw(pos)

    def move(self, direction, game_grid):
        """
        Attempt to move left/right/down; return True if moved, else False.
        """
        if not self.can_be_moved(direction, game_grid):
            return False
        if direction == "left":
            self.bottom_left_cell.x -= 1
        elif direction == "right":
            self.bottom_left_cell.x += 1
        else:  # down
            self.bottom_left_cell.y -= 1
        return True

    def can_be_moved(self, direction, game_grid):
        """
        Check for collisions or out-of-bounds if moving in given direction.
        """
        n = len(self.tile_matrix)
        if direction in ("left", "right"):
            for r in range(n):
                # Scan leftmost or rightmost tiles per row
                indices = range(n) if direction=="left" else range(n-1, -1, -1)
                for c in indices:
                    if self.tile_matrix[r][c] is not None:
                        pos = self.get_cell_position(r, c)
                        # Check wall collisions and occupied cells
                        if (direction=="left" and (pos.x == 0 or game_grid.is_occupied(pos.y, pos.x-1))) or \
                           (direction=="right" and (pos.x == Tetromino.grid_width-1 or game_grid.is_occupied(pos.y, pos.x+1))):
                            return False
                        break
        else:  # downwards movement
            for c in range(n):
                # scan bottommost tile in each column
                for r in range(n-1, -1, -1):
                    if self.tile_matrix[r][c] is not None:
                        pos = self.get_cell_position(r, c)
                        if pos.y == 0 or game_grid.is_occupied(pos.y-1, pos.x):
                            return False
                        break
        return True

    def rotate(self, game_grid):
        """
        Attempt clockwise rotation: check boundaries and collisions,
        then commit if valid, else leave unchanged.
        """
        # Create rotated copy of matrix
        rotated = np.rot90(self.tile_matrix, -1)
        n = len(rotated)
        # Validate each occupied cell after rotation
        for r in range(n):
            for c in range(n):
                if rotated[r][c] is not None:
                    new_x = self.bottom_left_cell.x + c
                    new_y = self.bottom_left_cell.y + (n-1) - r
                    # Check walls and existing grid tiles
                    if new_x<0 or new_x>=Tetromino.grid_width or new_y<0 or new_y>=Tetromino.grid_height:
                        return False
                    if game_grid.is_occupied(new_y, new_x):
                        return False
        # Commit rotation
        self.tile_matrix = rotated
        return True

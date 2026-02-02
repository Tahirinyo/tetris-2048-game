"""
GameGrid: Manages the Tetris-2048 combined grid state, rendering, and merging logic.
This class handles:
  - Storing tile objects in a 2D matrix
  - Drawing the background, grid lines, current tetromino, and borders
  - Locking tiles into place when a tetromino lands
  - Merging matching numbers (2048 mechanic) bottom-up
  - Clearing full rows (Tetris mechanic) and updating score
  - Letting unsupported tiles fall down after merges/clears
"""
import lib.stddraw as stddraw
from lib.color import Color
from point import Point
import numpy as np
from collections import deque
from tile import Tile

class GameGrid:
    def __init__(self, grid_h, grid_w):
        # Initialize grid dimensions and storage
        self.grid_height = grid_h
        self.grid_width = grid_w
        # 2D array of Tile or None, initially empty
        self.tile_matrix = np.full((grid_h, grid_w), None)
        self.current_tetromino = None  # active falling tetromino
        self.game_over = False         # flag for end of game
        # Colors and thickness settings for drawing
        self.empty_cell_color = Color(42, 69, 99)
        self.line_color = Color(0, 100, 200)
        self.boundary_color = Color(0, 100, 200)
        self.line_thickness = 0.001
        self.box_thickness = 5 * self.line_thickness
        self.score = 0               # current player score

    def display(self):
        """
        Draw the grid background, grid lines, active tetromino, and outer boundary.
        """
        # Fill empty cells area
        center_x = (self.grid_width - 1) / 2
        center_y = (self.grid_height - 1) / 2
        stddraw.setPenColor(self.empty_cell_color)
        stddraw.filledRectangle(
            center_x, center_y,
            self.grid_width / 2, self.grid_height / 2
        )
        # Draw all locked tiles and grid lines
        self.draw_grid()
        # Draw the falling tetromino on top
        if self.current_tetromino is not None:
            self.current_tetromino.draw()
        # Draw the border rectangle
        self.draw_boundaries()

    def draw_grid(self):
        """
        Render each locked tile and then overlay grid lines.
        """
        # Draw tiles in each cell
        for row in range(self.grid_height):
            for col in range(self.grid_width):
                tile = self.tile_matrix[row][col]
                if tile is not None:
                    tile.draw(Point(col, row))
        # Draw vertical and horizontal grid lines
        stddraw.setPenColor(self.line_color)
        stddraw.setPenRadius(self.line_thickness)
        # Vertical lines
        for x in np.arange(-0.5 + 1, self.grid_width - 0.5, 1):
            stddraw.line(x, -0.5, x, self.grid_height - 0.5)
        # Horizontal lines
        for y in np.arange(-0.5 + 1, self.grid_height - 0.5, 1):
            stddraw.line(-0.5, y, self.grid_width - 0.5, y)
        # Reset pen radius
        stddraw.setPenRadius()

    def draw_boundaries(self):
        """
        Draw a thick rectangle around the grid as a boundary.
        """
        stddraw.setPenColor(self.boundary_color)
        stddraw.setPenRadius(self.box_thickness)
        stddraw.rectangle(
            -0.5, -0.5,
            self.grid_width, self.grid_height
        )
        stddraw.setPenRadius()

    def is_occupied(self, row, col):
        """
        Return True if a cell is within bounds and contains a tile.
        """
        return self.is_inside(row, col) and self.tile_matrix[row][col] is not None

    def is_inside(self, row, col):
        """
        Return True if given row,col lies inside grid boundaries.
        """
        return 0 <= row < self.grid_height and 0 <= col < self.grid_width

    def update_grid(self, tiles_to_lock, blc_position):
        """
        Lock the falling tetromino tiles into the grid, then
        repeatedly merge matching tiles bottom-up, clear full rows,
        and let disconnected tiles fall. Returns True if game over.
        """
        # Remove active tetromino reference
        self.current_tetromino = None
        n_rows, n_cols = len(tiles_to_lock), len(tiles_to_lock[0])
        affected_cols = set()

        # Place each locked tile into matrix
        for col in range(n_cols):
            for row in range(n_rows):
                tile = tiles_to_lock[row][col]
                if tile is not None:
                    pos = Point(
                        blc_position.x + col,
                        blc_position.y + (n_rows - 1 - row)
                    )
                    # Check if within grid
                    if self.is_inside(pos.y, pos.x):
                        self.tile_matrix[pos.y][pos.x] = tile
                        affected_cols.add(pos.x)
                    else:
                        # Locking outside => game over
                        self.game_over = True

        if self.game_over:
            return True

        # Chain merges bottom-up until no further merges occur
        while True:
            merged = self.chain_bottom_up_merge(affected_cols)
            if merged:
                # After merges, let any unsupported tiles fall
                self.fall_disconnected_tiles()
            else:
                break

        # Clear any full rows and let tiles above fall
        cleared_cols = self.clear_full_rows_return_columns()
        self.fall_disconnected_tiles()

        return False

    def chain_bottom_up_merge(self, columns):
        """
        For each affected column, scan bottom-up to merge adjacent equal tiles.
        Increase score by merged value. Returns True if any merge occurred.
        """
        merged = False
        for col in columns:
            row = 0
            while row < self.grid_height - 1:
                current = self.tile_matrix[row][col]
                above = self.tile_matrix[row + 1][col]
                # Merge if two adjacent tiles share the same number
                if current and above and current.number == above.number:
                    current.merge_with(above)  # doubles number, updates color
                    self.tile_matrix[row + 1][col] = None
                    self.score += current.number
                    merged = True
                    row += 1  # skip next row which was just merged
                row += 1
        return merged

    def clear_full_rows_return_columns(self):
        """
        Remove any row fully filled with tiles (Tetris clear),
        shift rows above down by one, accumulate score from cleared tiles,
        and return set of all columns cleared.
        """
        cleared_cols = set()
        cleared_score = 0
        row = 0
        while row < self.grid_height:
            if None not in self.tile_matrix[row]:  # full row
                # Mark all columns for clearing
                for col in range(self.grid_width):
                    cleared_cols.add(col)
                # Add up score from each tile in the row
                for tile in self.tile_matrix[row]:
                    if tile:
                        cleared_score += tile.number
                # Remove this row and shift above down
                self.shift_down_above_row(row)
            else:
                row += 1
        # Add cleared row score
        self.score += cleared_score
        return cleared_cols

    def fall_disconnected_tiles(self):
        """
        After merges or clears, some tiles may be floating. This
        performs a flood-fill from the bottom row to mark supported
        tiles, then lets unsupported tiles fall downward.
        """
        visited = [[False]*self.grid_width for _ in range(self.grid_height)]
        queue = deque()

        # Start from tiles on the bottom row
        for col in range(self.grid_width):
            if self.tile_matrix[0][col] is not None:
                visited[0][col] = True
                queue.append((0, col))

        # BFS to find all connected supported tiles
        while queue:
            r, c = queue.popleft()
            for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nr, nc = r+dr, c+dc
                if self.is_inside(nr, nc) and not visited[nr][nc]:
                    if self.tile_matrix[nr][nc] is not None:
                        visited[nr][nc] = True
                        queue.append((nr, nc))

        # Let unsupported tiles fall
        for col in range(self.grid_width):
            for row in range(self.grid_height - 2, -1, -1):
                if self.tile_matrix[row][col] is not None and not visited[row][col]:
                    dest = row
                    # Find next supported or bottom spot
                    while dest > 0 and self.tile_matrix[dest-1][col] is None:
                        dest -= 1
                    if dest != row:
                        # Move tile down
                        self.tile_matrix[dest][col] = self.tile_matrix[row][col]
                        self.tile_matrix[row][col] = None

    def shift_down_above_row(self, row_index):
        """
        Delete the row at row_index by shifting all rows above it down by one.
        """
        for r in range(row_index, self.grid_height - 1):
            self.tile_matrix[r] = self.tile_matrix[r+1]
        # Empty out top row
        self.tile_matrix[self.grid_height-1] = [None]*self.grid_width

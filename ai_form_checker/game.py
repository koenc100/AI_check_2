import pygame
import sys
import random

# ----------------------
# Constants and Settings
# ----------------------
CELL_SIZE = 40                # Size of each cell in pixels
MAZE_WIDTH = 16               # Maze grid width (cells)
MAZE_HEIGHT = 16              # Maze grid height (cells)
SCREEN_WIDTH = CELL_SIZE * MAZE_WIDTH
SCREEN_HEIGHT = CELL_SIZE * MAZE_HEIGHT

# Colors (RGB)
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
BLUE    = (0, 0, 255)
GREEN   = (0, 255, 0)
RED     = (255, 0, 0)
YELLOW  = (255, 255, 0)
BROWN   = (165, 42, 42)

# ----------------------
# Maze Class
# ----------------------
class Maze:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Create a grid with a dictionary in each cell that holds wall info.
        # True means a wall exists on that side.
        self.grid = [[{'N': True, 'S': True, 'E': True, 'W': True} for _ in range(height)] for _ in range(width)]
        self.visited = [[False for _ in range(height)] for _ in range(width)]
        self.generate_maze(0, 0)  # Generate starting at cell (0, 0)

    def generate_maze(self, cx, cy):
        """Generate maze using recursive backtracking."""
        self.visited[cx][cy] = True

        # Define directions: (direction name, (dx, dy), wall from current, opposite wall for neighbor)
        directions = [
            ('N', (0, -1), 'N', 'S'),
            ('S', (0, 1), 'S', 'N'),
            ('E', (1, 0), 'E', 'W'),
            ('W', (-1, 0), 'W', 'E')
        ]
        random.shuffle(directions)
        for _, (dx, dy), wall, opposite in directions:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < self.width and 0 <= ny < self.height and not self.visited[nx][ny]:
                # Remove walls between the current cell and the neighbor.
                self.grid[cx][cy][wall] = False
                self.grid[nx][ny][opposite] = False
                self.generate_maze(nx, ny)

    def draw(self, surface):
        """Draw the maze walls."""
        for x in range(self.width):
            for y in range(self.height):
                x1 = x * CELL_SIZE
                y1 = y * CELL_SIZE
                cell = self.grid[x][y]
                if cell['N']:
                    pygame.draw.line(surface, BLACK, (x1, y1), (x1 + CELL_SIZE, y1), 2)
                if cell['S']:
                    pygame.draw.line(surface, BLACK, (x1, y1 + CELL_SIZE), (x1 + CELL_SIZE, y1 + CELL_SIZE), 2)
                if cell['E']:
                    pygame.draw.line(surface, BLACK, (x1 + CELL_SIZE, y1), (x1 + CELL_SIZE, y1 + CELL_SIZE), 2)
                if cell['W']:
                    pygame.draw.line(surface, BLACK, (x1, y1), (x1, y1 + CELL_SIZE), 2)

# ----------------------
# Player Class
# ----------------------
class Player:
    def __init__(self, x, y):
        self.x = x  # Cell coordinate x
        self.y = y  # Cell coordinate y
        self.color = GREEN
        self.direction = (0, 0)  # Last movement direction (for shooting)

    def move(self, dx, dy, maze):
        """Attempt to move the player by (dx, dy) if no wall blocks the way."""
        new_x = self.x + dx
        new_y = self.y + dy

        # Check bounds
        if new_x < 0 or new_x >= maze.width or new_y < 0 or new_y >= maze.height:
            return

        # Check for a wall in the direction of movement.
        if dx == 1 and maze.grid[self.x][self.y]['E']:
            return
        if dx == -1 and maze.grid[self.x][self.y]['W']:
            return
        if dy == 1 and maze.grid[self.x][self.y]['S']:
            return
        if dy == -1 and maze.grid[self.x][self.y]['N']:
            return

        # If no wall, update the position and record the direction.
        self.x = new_x
        self.y = new_y
        self.direction = (dx, dy)

    def draw(self, surface):
        """Draw the player as a circle with a hat."""
        center_x = self.x * CELL_SIZE + CELL_SIZE // 2
        center_y = self.y * CELL_SIZE + CELL_SIZE // 2
        radius = CELL_SIZE // 3
        pygame.draw.circle(surface, self.color, (center_x, center_y), radius)
        # Draw a simple hat (a rectangle on top of the circle)
        hat_rect = pygame.Rect(center_x - radius, center_y - radius - 10, radius * 2, 10)
        pygame.draw.rect(surface, BLACK, hat_rect)

# ----------------------
# Enemy Class (Taco)
# ----------------------
class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.color = RED
        self.move_delay = 30  # Frames between moves
        self.move_counter = 0

    def update(self, maze):
        """Move the enemy randomly if possible."""
        self.move_counter += 1
        if self.move_counter >= self.move_delay:
            self.move_counter = 0
            possible_moves = []
            cell = maze.grid[self.x][self.y]
            # Check each direction for an opening.
            if not cell['N'] and self.y > 0:
                possible_moves.append((0, -1))
            if not cell['S'] and self.y < maze.height - 1:
                possible_moves.append((0, 1))
            if not cell['E'] and self.x < maze.width - 1:
                possible_moves.append((1, 0))
            if not cell['W'] and self.x > 0:
                possible_moves.append((-1, 0))
            if possible_moves:
                dx, dy = random.choice(possible_moves)
                self.x += dx
                self.y += dy

    def draw(self, surface):
        """Draw the enemy as a small circle with the label 'Taco'."""
        center_x = self.x * CELL_SIZE + CELL_SIZE // 2
        center_y = self.y * CELL_SIZE + CELL_SIZE // 2
        radius = CELL_SIZE // 4
        pygame.draw.circle(surface, self.color, (center_x, center_y), radius)
        # Draw label text (requires pygame.font)
        font = pygame.font.SysFont(None, 20)
        text = font.render("Taco", True, WHITE)
        text_rect = text.get_rect(center=(center_x, center_y))
        surface.blit(text, text_rect)

# ----------------------
# Projectile Class (Burrito)
# ----------------------
class Projectile:
    def __init__(self, x, y, direction):
        self.x = x  # current cell x
        self.y = y  # current cell y
        self.direction = direction  # Direction tuple (dx, dy)
        self.move_delay = 5  # Frames between moves
        self.move_counter = 0
        self.active = True  # Whether the projectile is still flying

    def update(self, maze):
        """Move the projectile one cell at a time along its direction, unless a wall blocks it."""
        self.move_counter += 1
        if self.move_counter >= self.move_delay:
            self.move_counter = 0
            dx, dy = self.direction

            # Check if a wall blocks the projectile in its current cell.
            current_cell = maze.grid[self.x][self.y]
            if dx == 1 and current_cell['E']:
                self.active = False
                return
            if dx == -1 and current_cell['W']:
                self.active = False
                return
            if dy == 1 and current_cell['S']:
                self.active = False
                return
            if dy == -1 and current_cell['N']:
                self.active = False
                return

            # Move the projectile to the next cell.
            new_x = self.x + dx
            new_y = self.y + dy
            if new_x < 0 or new_x >= maze.width or new_y < 0 or new_y >= maze.height:
                self.active = False
            else:
                self.x = new_x
                self.y = new_y

    def draw(self, surface):
        """Draw the projectile as a small brown circle."""
        center_x = self.x * CELL_SIZE + CELL_SIZE // 2
        center_y = self.y * CELL_SIZE + CELL_SIZE // 2
        radius = CELL_SIZE // 8
        pygame.draw.circle(surface, BROWN, (center_x, center_y), radius)

# ----------------------
# Main Game Loop
# ----------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Mexican Hat Maze")
    clock = pygame.time.Clock()

    # Create the maze, player, and finish cell.
    maze = Maze(MAZE_WIDTH, MAZE_HEIGHT)
    player = Player(0, 0)
    finish_cell = (MAZE_WIDTH - 1, MAZE_HEIGHT - 1)

    # Place a few enemy tacos in random cells (avoiding the player and finish cell).
    enemies = []
    enemy_count = 5
    while len(enemies) < enemy_count:
        ex = random.randint(0, MAZE_WIDTH - 1)
        ey = random.randint(0, MAZE_HEIGHT - 1)
        if (ex, ey) in [(player.x, player.y), finish_cell]:
            continue
        if any(e.x == ex and e.y == ey for e in enemies):
            continue
        enemies.append(Enemy(ex, ey))

    projectiles = []
    running = True
    game_over = False
    win = False

    while running:
        # Handle events.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Player controls (only when game is not over).
            if event.type == pygame.KEYDOWN and not game_over:
                if event.key == pygame.K_LEFT:
                    player.move(-1, 0, maze)
                elif event.key == pygame.K_RIGHT:
                    player.move(1, 0, maze)
                elif event.key == pygame.K_UP:
                    player.move(0, -1, maze)
                elif event.key == pygame.K_DOWN:
                    player.move(0, 1, maze)
                elif event.key == pygame.K_SPACE:
                    # Shoot a burrito in the last movement direction.
                    if player.direction != (0, 0):
                        projectiles.append(Projectile(player.x, player.y, player.direction))

        if not game_over:
            # Update projectiles.
            for proj in projectiles:
                if proj.active:
                    proj.update(maze)
            projectiles = [p for p in projectiles if p.active]

            # Update enemies.
            for enemy in enemies:
                enemy.update(maze)

            # Check projectile–enemy collisions.
            for proj in projectiles:
                for enemy in enemies:
                    if proj.x == enemy.x and proj.y == enemy.y:
                        if enemy in enemies:
                            enemies.remove(enemy)
                        proj.active = False
                        break

            # Check enemy–player collisions.
            for enemy in enemies:
                if enemy.x == player.x and enemy.y == player.y:
                    game_over = True

            # Check if the player reached the finish.
            if (player.x, player.y) == finish_cell:
                win = True
                game_over = True

        # Draw everything.
        screen.fill(WHITE)
        maze.draw(screen)

        # Highlight finish cell.
        finish_rect = pygame.Rect(finish_cell[0] * CELL_SIZE + 2,
                                  finish_cell[1] * CELL_SIZE + 2,
                                  CELL_SIZE - 4, CELL_SIZE - 4)
        pygame.draw.rect(screen, YELLOW, finish_rect)

        player.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)
        for proj in projectiles:
            proj.draw(screen)

        # If the game is over, display a message.
        if game_over:
            font = pygame.font.SysFont(None, 48)
            if win:
                text = font.render("You Win!", True, BLUE)
            else:
                text = font.render("Game Over", True, RED)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text, text_rect)

        pygame.display.flip()
        clock.tick(60)  # 60 FPS

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

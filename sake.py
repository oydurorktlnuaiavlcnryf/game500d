import pygame
import random
import sys
import json
import os
from enum import Enum
from typing import List, Tuple, Dict, Optional

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 128, 0)

# Game States
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    HIGH_SCORES = 5

# Direction Enum
class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class Food:
    def __init__(self, x: int, y: int, food_type: str = "normal"):
        self.x = x
        self.y = y
        self.food_type = food_type
        self.value = {"normal": 10, "golden": 50, "poison": -20}.get(food_type, 10)
        self.color = {"normal": RED, "golden": YELLOW, "poison": PURPLE}.get(food_type, RED)
        self.lifetime = {"normal": float('inf'), "golden": 300, "poison": 200}.get(food_type, float('inf'))
        self.age = 0
    
    def update(self):
        self.age += 1
        return self.age < self.lifetime
    
    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, self.color, 
                        (self.x * GRID_SIZE, self.y * GRID_SIZE, GRID_SIZE, GRID_SIZE))
        if self.food_type == "golden":
            pygame.draw.rect(screen, ORANGE, 
                           (self.x * GRID_SIZE + 5, self.y * GRID_SIZE + 5, 
                            GRID_SIZE - 10, GRID_SIZE - 10))

class Snake:
    def __init__(self, x: int, y: int):
        self.body = [(x, y)]
        self.direction = Direction.RIGHT
        self.grow_pending = 0
        self.speed = 5
        self.invulnerable_time = 0
        
    def move(self):
        if self.invulnerable_time > 0:
            self.invulnerable_time -= 1
            
        head_x, head_y = self.body[0]
        dx, dy = self.direction.value
        new_head = (head_x + dx, head_y + dy)
        
        self.body.insert(0, new_head)
        
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
    
    def grow(self, segments: int = 1):
        self.grow_pending += segments
    
    def check_collision(self) -> bool:
        head = self.body[0]
        # Wall collision
        if (head[0] < 0 or head[0] >= GRID_WIDTH or 
            head[1] < 0 or head[1] >= GRID_HEIGHT):
            return True
        # Self collision
        if self.invulnerable_time == 0 and head in self.body[1:]:
            return True
        return False
    
    def change_direction(self, new_direction: Direction):
        # Prevent moving into itself
        opposite = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        if new_direction != opposite.get(self.direction):
            self.direction = new_direction
    
    def draw(self, screen: pygame.Surface):
        for i, (x, y) in enumerate(self.body):
            color = DARK_GREEN if i == 0 else GREEN
            if self.invulnerable_time > 0 and self.invulnerable_time % 10 < 5:
                color = BLUE  # Flashing effect when invulnerable
            pygame.draw.rect(screen, color, 
                           (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE))
            if i == 0:  # Draw eyes on head
                eye_size = 3
                pygame.draw.circle(screen, WHITE, 
                                 (x * GRID_SIZE + 6, y * GRID_SIZE + 6), eye_size)
                pygame.draw.circle(screen, WHITE, 
                                 (x * GRID_SIZE + 14, y * GRID_SIZE + 6), eye_size)

class PowerUp:
    def __init__(self, x: int, y: int, power_type: str):
        self.x = x
        self.y = y
        self.power_type = power_type
        self.lifetime = 400
        self.age = 0
        self.colors = {
            "speed": BLUE,
            "invincible": ORANGE,
            "double_score": PURPLE
        }
    
    def update(self):
        self.age += 1
        return self.age < self.lifetime
    
    def draw(self, screen: pygame.Surface):
        color = self.colors.get(self.power_type, WHITE)
        pygame.draw.circle(screen, color, 
                          (self.x * GRID_SIZE + GRID_SIZE // 2, 
                           self.y * GRID_SIZE + GRID_SIZE // 2), 
                          GRID_SIZE // 2)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.state = GameState.MENU
        self.reset_game()
        self.high_scores = self.load_high_scores()
        self.power_up_active = {"type": None, "time": 0}
        
    def reset_game(self):
        self.snake = Snake(GRID_WIDTH // 2, GRID_HEIGHT // 2)
        self.foods: List[Food] = []
        self.power_ups: List[PowerUp] = []
        self.score = 0
        self.level = 1
        self.foods_eaten = 0
        self.game_speed = 8
        self.score_multiplier = 1
        self.spawn_food()
    
    def spawn_food(self):
        while len(self.foods) < 3:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            
            if (x, y) not in self.snake.body and not any(f.x == x and f.y == y for f in self.foods):
                food_type = random.choices(
                    ["normal", "golden", "poison"],
                    weights=[70, 20, 10]
                )[0]
                self.foods.append(Food(x, y, food_type))
    
    def spawn_power_up(self):
        if len(self.power_ups) < 2 and random.randint(1, 200) == 1:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            
            if ((x, y) not in self.snake.body and 
                not any(f.x == x and f.y == y for f in self.foods) and
                not any(p.x == x and p.y == y for p in self.power_ups)):
                
                power_type = random.choice(["speed", "invincible", "double_score"])
                self.power_ups.append(PowerUp(x, y, power_type))
    
    def handle_collisions(self):
        head = self.snake.body[0]
        
        # Food collision
        for food in self.foods[:]:
            if head[0] == food.x and head[1] == food.y:
                self.foods.remove(food)
                points = food.value * self.score_multiplier
                self.score += points
                self.foods_eaten += 1
                
                if food.food_type == "normal":
                    self.snake.grow(1)
                elif food.food_type == "golden":
                    self.snake.grow(2)
                    self.game_speed += 0.5
                elif food.food_type == "poison":
                    if len(self.snake.body) > 3:
                        self.snake.body = self.snake.body[:-2]
                    self.snake.invulnerable_time = 60
                
                # Level progression
                if self.foods_eaten % 10 == 0:
                    self.level += 1
                    self.game_speed += 1
                
                break
        
        # Power-up collision
        for power_up in self.power_ups[:]:
            if head[0] == power_up.x and head[1] == power_up.y:
                self.power_ups.remove(power_up)
                self.activate_power_up(power_up.power_type)
                break
    
    def activate_power_up(self, power_type: str):
        self.power_up_active = {"type": power_type, "time": 300}
        
        if power_type == "speed":
            self.game_speed *= 1.5
        elif power_type == "invincible":
            self.snake.invulnerable_time = 300
        elif power_type == "double_score":
            self.score_multiplier = 2
    
    def update_power_ups(self):
        if self.power_up_active["time"] > 0:
            self.power_up_active["time"] -= 1
            
            if self.power_up_active["time"] == 0:
                if self.power_up_active["type"] == "speed":
                    self.game_speed /= 1.5
                elif self.power_up_active["type"] == "double_score":
                    self.score_multiplier = 1
                self.power_up_active["type"] = None
    
    def load_high_scores(self) -> List[int]:
        try:
            with open("high_scores.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return [0] * 10
    
    def save_high_scores(self):
        self.high_scores.append(self.score)
        self.high_scores.sort(reverse=True)
        self.high_scores = self.high_scores[:10]
        
        with open("high_scores.json", "w") as f:
            json.dump(self.high_scores, f)
    
    def handle_menu_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.state = GameState.PLAYING
                self.reset_game()
            elif event.key == pygame.K_h:
                self.state = GameState.HIGH_SCORES
            elif event.key == pygame.K_q:
                return False
        return True
    
    def handle_game_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = GameState.PAUSED
            elif event.key == pygame.K_UP:
                self.snake.change_direction(Direction.UP)
            elif event.key == pygame.K_DOWN:
                self.snake.change_direction(Direction.DOWN)
            elif event.key == pygame.K_LEFT:
                self.snake.change_direction(Direction.LEFT)
            elif event.key == pygame.K_RIGHT:
                self.snake.change_direction(Direction.RIGHT)
        return True
    
    def handle_pause_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING
            elif event.key == pygame.K_q:
                self.state = GameState.MENU
        return True
    
    def handle_game_over_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.state = GameState.PLAYING
                self.reset_game()
            elif event.key == pygame.K_q:
                self.state = GameState.MENU
        return True
    
    def handle_high_scores_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                self.state = GameState.MENU
        return True
    
    def update_game(self):
        self.snake.move()
        
        if self.snake.check_collision():
            self.state = GameState.GAME_OVER
            self.save_high_scores()
            return
        
        self.handle_collisions()
        
        # Update foods
        self.foods = [food for food in self.foods if food.update()]
        self.spawn_food()
        
        # Update power-ups
        self.power_ups = [power_up for power_up in self.power_ups if power_up.update()]
        self.spawn_power_up()
        self.update_power_ups()
    
    def draw_menu(self):
        self.screen.fill(BLACK)
        
        title = self.font.render("SNAKE ADVENTURE", True, GREEN)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)
        
        instructions = [
            "Press ENTER to Start",
            "Press H for High Scores",
            "Press Q to Quit",
            "",
            "Use Arrow Keys to Move",
            "Avoid Poison Food (Purple)",
            "Collect Golden Food for Bonus",
            "Collect Power-ups for Special Effects"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, WHITE)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 250 + i * 25))
            self.screen.blit(text, text_rect)
    
    def draw_game(self):
        self.screen.fill(BLACK)
        
        self.snake.draw(self.screen)
        
        for food in self.foods:
            food.draw(self.screen)
        
        for power_up in self.power_ups:
            power_up.draw(self.screen)
        
        # Draw UI
        score_text = self.small_font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        level_text = self.small_font.render(f"Level: {self.level}", True, WHITE)
        self.screen.blit(level_text, (10, 35))
        
        length_text = self.small_font.render(f"Length: {len(self.snake.body)}", True, WHITE)
        self.screen.blit(length_text, (10, 60))
        
        if self.power_up_active["type"]:
            power_text = self.small_font.render(f"Power-up: {self.power_up_active['type']}", True, YELLOW)
            self.screen.blit(power_text, (10, 85))
    
    def draw_pause(self):
        self.draw_game()
        
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        pause_text = self.font.render("PAUSED", True, WHITE)
        pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(pause_text, pause_rect)
        
        instruction_text = self.small_font.render("Press ESC to Resume or Q for Menu", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40))
        self.screen.blit(instruction_text, instruction_rect)
    
    def draw_game_over(self):
        self.screen.fill(BLACK)
        
        game_over_text = self.font.render("GAME OVER", True, RED)
        game_over_rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 50))
        self.screen.blit(game_over_text, game_over_rect)
        
        score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        self.screen.blit(score_text, score_rect)
        
        instruction_text = self.small_font.render("Press ENTER to Play Again or Q for Menu", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
        self.screen.blit(instruction_text, instruction_rect)
    
    def draw_high_scores(self):
        self.screen.fill(BLACK)
        
        title = self.font.render("HIGH SCORES", True, YELLOW)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)
        
        for i, score in enumerate(self.high_scores):
            score_text = self.small_font.render(f"{i + 1:2d}. {score:6d}", True, WHITE)
            score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 150 + i * 30))
            self.screen.blit(score_text, score_rect)
        
        back_text = self.small_font.render("Press ESC to go back", True, GRAY)
        back_rect = back_text.get_rect(center=(WINDOW_WIDTH // 2, 500))
        self.screen.blit(back_text, back_rect)
    
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if self.state == GameState.MENU:
                    running = self.handle_menu_input(event)
                elif self.state == GameState.PLAYING:
                    running = self.handle_game_input(event)
                elif self.state == GameState.PAUSED:
                    running = self.handle_pause_input(event)
                elif self.state == GameState.GAME_OVER:
                    running = self.handle_game_over_input(event)
                elif self.state == GameState.HIGH_SCORES:
                    running = self.handle_high_scores_input(event)
            
            if self.state == GameState.PLAYING:
                self.update_game()
            
            # Draw based on current state
            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.PLAYING:
                self.draw_game()
            elif self.state == GameState.PAUSED:
                self.draw_pause()
            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()
            elif self.state == GameState.HIGH_SCORES:
                self.draw_high_scores()
            
            pygame.display.flip()
            self.clock.tick(self.game_speed if self.state == GameState.PLAYING else 60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()

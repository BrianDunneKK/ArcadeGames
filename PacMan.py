# To Do: Create PacManLevel.add_event()
# To Do: In choose_move(), (self.since_last_choice < delay) needs to validate choice
# To Do: Scale PacMan Grid to suit screen size

# import sys
# sys.path.insert(0, "cdkk")
import cdkk
import pygame
import random

### --------------------------------------------------

PACMAN_SPEED = 20
PACMAN_MOVE_TIMER = 20  # msecs

class Sprite_PacMan(cdkk.Sprite_ImageGridActor):
    def __init__(self, start_cell, cell0, speed=PACMAN_SPEED, move_timer=PACMAN_MOVE_TIMER/1000.0):
        super().__init__("PacMan", start_cell, cell0, speed, move_timer)
        self.image_dir = "R"

    def load_image(self):
        self.load_spritesheet("PacManR", "PacMan.png", 16, 4, start=0,  end=16)
        self.load_spritesheet("PacManL", "PacMan.png", 16, 4, start=16, end=32)
        self.load_spritesheet("PacManD", "PacMan.png", 16, 4, start=32, end=48)
        self.load_spritesheet("PacManU", "PacMan.png", 16, 4, start=48, end=64)

### --------------------------------------------------

GHOST_SPEED = 10

def ai_calc_score(mo, name):
    score = -1

    if name == "Blinky":
        if mo.can_move:
            score = mo.to_barrier
            if mo.is_turn:
                score = score + 20
            if mo.same_dir:
                score = score + 15
            score = score + random.randint(0,10)
            score = score + mo.distance("target") * 10
            score = max(0,score) + max(0,20-(mo.next_cell_history*5))
    elif name == "Pinky":
        if mo.can_move:
            if mo.same_dir:
                score = 3
            elif mo.is_turn:
                score = 2
            else:
                score = 1
    elif name == "Inky":
        if mo.can_move:
            if mo.is_turn:
                score = 3
            elif mo.same_dir:
                score = 2
            else:
                score = 1
    else:
        if mo.can_move:
            score = random.randint(0,10)

    return score

class Sprite_Ghost(cdkk.Sprite_ImageGridActor):
    def __init__(self, name, start_cell, cell0, sprite_offset=(0,0)):
        self._sprite_offset = sprite_offset
        super().__init__(name, start_cell, cell0, GHOST_SPEED)
        self.calc_score = ai_calc_score

    def load_image(self):
        offset = self._sprite_offset[0] + self._sprite_offset[1] * 16
        self.load_spritesheet("GhostR", "PacManGhost.png", 16, 4, start=0+offset, length=1)
        self.load_spritesheet("GhostL", "PacManGhost.png", 16, 4, start=1+offset, length=1)
        self.load_spritesheet("GhostD", "PacManGhost.png", 16, 4, start=2+offset, length=1)
        self.load_spritesheet("GhostU", "PacManGhost.png", 16, 4, start=3+offset, length=1)

### --------------------------------------------------

class Sprite_PacDot(cdkk.Sprite):
    def __init__(self, ID, rect):
        super().__init__(name=ID)
        self.load_image_from_spritesheet("PacManGrid.png", 4, 4, 12, scale_to=rect.size)
        self.rect.center = rect.center

### --------------------------------------------------

class PacManager(cdkk.SpriteManager):
    def __init__(self, pacman_level, limits):
        super().__init__("PacManager")
        self.limits = limits
        self._maze_events = pacman_level.events

        self._maze = pacman_level.maze
        self._maze_sprites = self._maze.grid_map("image")
        self._maze_pacdots = self._maze.grid_map("pacdot")
        self._pacdot_count = self._maze.grid_map_count("pacdot")

        self._grid = cdkk.Sprite_ImageGrid()
        self._grid.setup_grid(self._maze.cols_rows, pacman_level.cell_size)
        self._grid.setup_image_grid(["PacManGrid.png",4,4], self._maze_sprites)
        self._grid.rect.center = self.limits.center
        self.add(self._grid)

        for i in range(0,self._maze.rows):
            for j in range (0,self._maze.cols):
                pacdotID = self._maze.cell_index(j, i)
                if self._maze_pacdots[pacdotID]:
                    r = self._grid.cell_rect(j,i)
                    dot = Sprite_PacDot(pacdotID, r)
                    self._maze_pacdots[pacdotID] = dot.uuid
                    self.add(dot)
                else:
                    self._maze_pacdots[pacdotID] = None

        self._pacman = Sprite_PacMan(pacman_level.start["PacMan"], self._grid.cell_rect(0,0))
        self._ghosts = [
            Sprite_Ghost("Blinky", pacman_level.start["Ghost-Blinky"], self._grid.cell_rect(0,0), (0,0)),
            Sprite_Ghost("Pinky",  pacman_level.start["Ghost-Pinky" ], self._grid.cell_rect(0,0), (0,1)),
            Sprite_Ghost("Inky",   pacman_level.start["Ghost-Inky"  ], self._grid.cell_rect(0,0), (0,2)),
            Sprite_Ghost("Clyde",  pacman_level.start["Ghost-Clyde" ], self._grid.cell_rect(0,0), (0,3))
        ]

    def start_game(self):
        super().start_game()
        self.add(self._pacman)
        for ghost in self._ghosts:
            self.add(ghost)

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == cdkk.EVENT_GAME_CONTROL and self.game_is_active:
            if e.action == "PacManJump":
                self._pacman.move_to(e.info["toCell"])
                dealt_with = True
            elif e.action in ["MoveUp", "MoveDown", "MoveLeft", "MoveRight"]:
                self._pacman.next_dir = e.action[4:5]  # U, D, L or R
                dealt_with = True
        return dealt_with

    def update_pacman(self):
        # Move PacMan
        cell = self._pacman.cell
        barriers = self._maze.move_options(cell, self._pacman.direction)
        self._pacman.set_grid_info(barriers)

        if not self._pacman.move_dir(True):
            self._pacman.move_dir()

        # Eat PacDots
        pacdotID = self._maze.cell_index(cell[0], cell[1])
        if self.kill_uuid(self._maze_pacdots[pacdotID]):
            self._pacdot_count = self._pacdot_count - 1
            self._maze_pacdots[pacdotID] = None
            cdkk.EventManager.post_game_control("UpdateScore", score=1)  # PacDot = 1

        if self._pacdot_count == 0:
            ev = cdkk.EventManager.create_event(cdkk.EVENT_GAME_TIMER_1)
            cdkk.EventManager.post(ev)

        # Post events
        cellc = self._grid.find_cell_centre(self._pacman.centre)
        for e in self._maze_events:
            if cellc == e.info["fromCell"] and self._pacman.direction == e.info["dir"]:
                cdkk.EventManager.post(e)

    def update_ghosts(self):
        for ghost in self._ghosts:
            barriers = self._maze.move_options(ghost.cell, "barrier")
            ghost.set_grid_info(barriers, self._pacman.cell_pos)
            ghost.direction = ghost.choose_move()
            ghost.move_dir()

    def update(self):
        super().update()
        self.update_pacman()
        self.update_ghosts()

### --------------------------------------------------

class Manager_Scoreboard(cdkk.SM_Scoreboard):
    def __init__(self, game_time):
        score_style = {"xpos":10, "ypos":10, "textcolour":"white", "textsize":28}
        timer_style = cdkk.merge_dicts(score_style, {"ypos": 40})
        fps_style = cdkk.merge_dicts(score_style, {"ypos":70, "invisible": False})
        super().__init__(game_time, score_style=score_style, timer_style=timer_style, fps_style=fps_style)

    def end_game(self):
        if self._timer.time_up():
            self.game_over.text = "You Lost"
        else:
            self.game_over.text = "You Won!!"
        super().end_game()

### --------------------------------------------------

class PacManLevel:
    def __init__(self, level):
        self.level = level
        self.init_maze = ""
        self.maze = None
        self.cell_size = (32, 32)
        self.start = {}
        self.events = []

    def add_start_cell(self, actor, start_cell):
        self.start[actor] = start_cell

mazeLevel1 = """
┌────────────┐
│●●●●●●●●●●●●│
│●┌──┐●┌───┐●│
│●│██│●│███│●│
│●└──┘●└───┘●└
│●●●●●●●●●●●●●
│●┌──┐●┌┐●┌───
│●└──┘●││●└──┐
│●●●●●●││●●●●│
└────┐●│└──┐●│
█████│●│┌──┘●└
█████│●││●●●●●
█████│●││●┌───
─────┘●└┘●│███
●●●●●●●●●●│███
"""

### --------------------------------------------------

class PacManGame(cdkk.PyGameApp):
    def init(self):
        super().init()

        mirrorMap = {"┌":"└┐", "┐":"┘┌", "└":"┌┘", "┘":"┐└", "├":"├┤", "┤":"┤├", "┬":"┴┬", "┴":"┬┴" }
        imageMap = { "─":1, "│":2, "┌":3, "┐":4, "└":5, "┘":6, "├":7, "┤":8, "┬":9, "┴":10, "┼":11, "●":0, "█":0, "X":15, ".":0 }
        barrierMap = { "─":True, "│":True, "┌":True, "┐":True, "└":True, "┘":True, "├":True, "┤":True, "┬":True, "┴":True, "┼":True, "●":False, "█":False, "X":True, ".":False }
        pacdotMap = { "●":True, ".":True }

        pacmanLevel1 = PacManLevel(1)
        pacmanLevel1.init_maze = mazeLevel1
        pacmanLevel1.add_start_cell("PacMan", (13,23))
        pacmanLevel1.add_start_cell("Ghost-Blinky", (1,1))
        pacmanLevel1.add_start_cell("Ghost-Pinky" , (12,1))
        pacmanLevel1.add_start_cell("Ghost-Inky"  , (15,1))
        pacmanLevel1.add_start_cell("Ghost-Clyde" , (26,1))
        pacmanLevel1.events = [
            cdkk.EventManager.gc_event("PacManJump", fromCell=(0,14), toCell=(27,14), dir="L"),
            cdkk.EventManager.gc_event("PacManJump", fromCell=(27,14), toCell=(0,14), dir="R")
        ]

        pacmanLevel1.maze = cdkk.GridMaze(pacmanLevel1.init_maze, mirrorMap, True, True, True, False)
        pacmanLevel1.maze.update_grid(pacmanLevel1.start["PacMan"], "█")
        pacmanLevel1.maze.add_map("image", imageMap)
        pacmanLevel1.maze.add_map("barrier", barrierMap)
        pacmanLevel1.maze.add_map("pacdot", pacdotMap, False)
        
        self.pacmanager = PacManager(pacmanLevel1, self.boundary.move(50,0))
        self.scoreboard_mgr = Manager_Scoreboard(game_time=90)

        self.add_sprite_mgr(self.pacmanager)
        self.add_sprite_mgr(self.scoreboard_mgr)

        user_event_map = {
            cdkk.EVENT_GAME_TIMER_1 : "GameOver"
        }
        self.event_mgr.event_map(key_event_map=cdkk.PyGameApp.default_key_map, user_event_map=user_event_map)

    def update(self):
        super().update()
        self.scoreboard_mgr.set_fps(self.loops_per_sec)

### --------------------------------------------------

app_config = {
    "width":1200, "height":920,
    "background_fill":"black",
    "caption":"Pac-Man",
    "key_repeat_time":30,   # msecs (lower=faster)
    "auto_start":True,
    "image_path":"ArcadeGames\\Images\\"
    }
PacManGame(app_config).execute()

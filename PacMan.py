# To Do: Chnage PacMaze to GirdMap an move to cdkkUtils
# To Do: Make dots_left more efficient - returns list; count required
# To Do: Create PacManLevel.add_event()

import sys
sys.path.append("../pygame-cdkk")
from cdkkPyGameApp import *
from cdkkSpriteExtra import *

### --------------------------------------------------

PACMAN_SPEED = 5
PACMAN_MOVE_TIMER = 20  # msecs

class Sprite_PacMan(Sprite_ImageGridActor):
    def __init__(self, start_cell, cell0, speed=PACMAN_SPEED, move_timer=PACMAN_MOVE_TIMER/1000.0):
        super().__init__("PacMan", start_cell, cell0, speed, move_timer)
        self.direction = "R"

    def load_image(self):
        self.load_spritesheet("PacManR", "Images\\PacMan.png", 16, 4, start=0,  end=16)
        self.load_spritesheet("PacManL", "Images\\PacMan.png", 16, 4, start=16, end=32)
        self.load_spritesheet("PacManD", "Images\\PacMan.png", 16, 4, start=32, end=48)
        self.load_spritesheet("PacManU", "Images\\PacMan.png", 16, 4, start=48, end=64)

### --------------------------------------------------

GHOST_SPEED = 2

class Sprite_Ghost(Sprite_ImageGridActor):
    def __init__(self, start_cell, cell0):
        super().__init__("Ghost", start_cell, cell0, GHOST_SPEED)

    def load_image(self):
        self.load_spritesheet("GhostR", "Images\\PacManGhost.png", 16, 4, start=0, end=1)
        self.load_spritesheet("GhostL", "Images\\PacManGhost.png", 16, 4, start=1, end=2)
        self.load_spritesheet("GhostD", "Images\\PacManGhost.png", 16, 4, start=2, end=3)
        self.load_spritesheet("GhostU", "Images\\PacManGhost.png", 16, 4, start=3, end=4)

    def choose_move(self, can_move):
        if can_move[self.direction]:
            return self.direction
        else:
            found_dir = False
            while not found_dir:
                next_dir = random.sample(list(can_move), 1)
                found_dir = can_move[next_dir[0]]
            return next_dir[0]

### --------------------------------------------------

class Sprite_PacDot(Sprite):
    def __init__(self, ID, rect):
        super().__init__(name=ID)
        self.load_image_from_spritesheet("Images\\PacManGrid.png", 4, 4, 12, scale_to=rect.size)
        self.rect.center = rect.center

### --------------------------------------------------

class PacMaze(StringLOL):
    def __init__(self, maze_as_mlstr, mirror_map=None, mirror_H=False, mirror_last_H=False, mirror_V=False, mirror_last_V=False):
        super().__init__(maze_as_mlstr, mirror_map)
        self.transform(mirror_H, mirror_last_H, mirror_V, mirror_last_V)
        self._maps = {}

    def map_maze(self, name, map_dict, default_map=None):
        self._maps[name] = self.map_as_list(map_dict, default_map)

    def mapped(self, name):
        return self._maps[name]

    @property
    def cols(self):
        return len(self._lol[0])

    @property
    def rows(self):
        return len(self._lol)

    def update_maze(self, maze_pos, maze_ch):
        self.update_lol(maze_pos[0], maze_pos[1], maze_ch)

    def find_nearest_item_R(self, maze_name, col, row, item=True):
        maze = self.mapped(maze_name)
        found = False
        xpos = col + 1
        while not found:
            found = (xpos >= self.cols)
            if not found:
                i = row * self.cols + xpos
                if i>=0 and i<len(maze):
                    found = (maze[i] == item)
            if not found:
                xpos = xpos + 1

        return (xpos if found else -1)

    def find_nearest_item_L(self, maze_name, col, row, item=True):
        maze = self.mapped(maze_name)
        found = False
        xpos = col - 1
        while not found:
            found = (xpos < 0)
            if not found:
                i = row * self.cols + xpos
                if i>=0 and i<len(maze):
                    found = (maze[i] == item)
            if not found:
                xpos = xpos - 1

        return (xpos if found else -1)

    def find_nearest_item_D(self, maze_name, col, row, item=True):
        maze = self.mapped(maze_name)
        found = False
        ypos = row + 1
        while not found:
            found = (ypos > self.rows)
            if not found:
                i = ypos * self.cols + col
                if i>=0 and i<len(maze):
                    found = (maze[i] == item)
            if not found:
                ypos = ypos + 1

        return (ypos if found else -1)

    def find_nearest_item_U(self, maze_name, col, row, item=True):
        maze = self.mapped(maze_name)
        found = False
        ypos = row - 1
        while not found:
            found = (ypos < 0)
            if not found:
                i = ypos * self.cols + col
                if i>=0 and i<len(maze):
                    found = (maze[i] == item)
            if not found:
                ypos = ypos - 1

        return (ypos if found else -1)

    def find_nearest_item(self, maze_name, cell_pos, item=True):
        col =  cell_pos[0]
        row =  cell_pos[1]
        return {
            'R': self.find_nearest_item_R(maze_name, col, row),
            'L': self.find_nearest_item_L(maze_name, col, row),
            'D': self.find_nearest_item_D(maze_name, col, row),
            'U': self.find_nearest_item_U(maze_name, col, row)
        }

### --------------------------------------------------

class PacManager(SpriteManager):
    def __init__(self, pacman_level, limits):
        super().__init__("PacManager")
        self.limits = limits

        self._maze = pacman_level.maze
        self._maze_sprites = self._maze.mapped("image")
        self._maze_barriers = self._maze.mapped("barrier")
        self._maze_pacdots = self._maze.mapped("pacdot")

        self._maze_events = pacman_level.events

        self._grid = Sprite_ImageGrid()
        xsize, ysize = pacman_level.size
        self._grid.setup_image_grid(["Images\\PacManGrid.png",4,4], self._maze_sprites, self._maze_barriers, xsize, self._maze.cols, ysize, self._maze.rows)
        self._grid.rect.center = self.limits.center
        self.add(self._grid)

        for i in range(0,self._maze.rows):
            for j in range (0,self._maze.cols):
                pacdotID = i*self._maze.cols+j
                if self._maze_pacdots[pacdotID]:
                    r = cdkkRect(self._grid.rect.left + j*xsize, self._grid.rect.top + i*ysize, xsize, ysize)
                    dot = Sprite_PacDot(pacdotID, r)
                    self._maze_pacdots[pacdotID] = dot.uuid
                    self.add(dot)
                else:
                    self._maze_pacdots[pacdotID] = None

        self._pacman = Sprite_PacMan(pacman_level.start["PacMan"], self._grid.cell_rect(0,0))
        self._pacman_curr_dir = self._pacman_next_dir = ""
        self.update_pacman()

        self._ghost = Sprite_Ghost(pacman_level.start["Ghost"], self._grid.cell_rect(0,0))

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == EVENT_GAME_CONTROL and self.game_is_active:
            if e.action == "PacManJump":
                self._pacman.move_to(e.info["toCell"])
                dealt_with = True
            elif e.action in ["PacManUp", "PacManDown", "PacManLeft", "PacManRight"]:
                self._pacman_next_dir = e.action[6:7]  # U, D, L or R
                self.update_pacman()
                dealt_with = True
        return dealt_with

    def add_pacman(self):
        self.add(self._pacman)
        self.add(self._ghost)

    def update_pacman(self):
        # Move PacMan
        cell_pos = self._grid.find_cellp(self._pacman.centre)
        barriers = self._maze.find_nearest_item("barrier", cell_pos)
        self._pacman.set_pos(cell_pos, barriers)

        if self._pacman.move(self._pacman_next_dir):
            self._pacman_curr_dir = self._pacman_next_dir
        else:
            self._pacman.move(self._pacman_curr_dir)

        # Eat PacDots
        pacdotID = cell_pos[1]*self._maze.cols + cell_pos[0]
        if self.kill_uuid(self._maze_pacdots[pacdotID]):
            self._maze_pacdots[pacdotID] = None
            EventManager.post_game_control("IncreaseScore", score=1)  # PacDot = 1

        dots_left = [x for x in self._maze_pacdots if x is not None]  # reduces to 0
        if len(dots_left) == 0:
            ev = EventManager.create_event(EVENT_GAME_TIMER_1)
            EventManager.post(ev)

        # Post events
        cellc = self._grid.find_cell_centre(self._pacman.centre)
        for e in self._maze_events:
            if cellc == e.info["fromCell"] and self._pacman_curr_dir == e.info["dir"]:
                EventManager.post(e)

    def update_ghosts(self):
        cell_pos = self._grid.find_cellp(self._ghost.centre)
        barriers = self._maze.find_nearest_item("barrier", cell_pos)
        self._ghost.set_pos(cell_pos, barriers)
        self._ghost.move()

    def update(self):
        super().update()
        self.update_pacman()
        self.update_ghosts()

    def start_game(self):
        super().start_game()
        self.add_pacman()

### --------------------------------------------------

class Manager_Scoreboard(SpriteManager):
    def __init__(self, game_time, limits):
        super().__init__("Scoreboard Manager")
        score_style = {"textcolour":"white", "fillcolour":None, "align_horiz":"L"}

        self._game_time = game_time
        self._timer = None
        self._time_left = Sprite_DynamicText("Time Left", cdkkRect(10, 10, 200, 40), score_style)
        self._time_left.set_text_format("Time Left: {0:0.1f}", 0)
        self.add(self._time_left)

        self._fps = Sprite_DynamicText("FPS", cdkkRect(10, 60, 200, 40), score_style)
        self._fps.set_text_format("FPS: {0:4.1f}", 0)
        self.add(self._fps)

        self._score = 0
        self._scoreboard = Sprite_DynamicText("Score", cdkkRect(10, 110, 200, 40), score_style)
        self._scoreboard.set_text_format("Score: {0}", 0)
        self.add(self._scoreboard)

        self._game_over = Sprite_GameOver(limits)

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        self._score = new_score
        self._scoreboard.set_text(self.score)

    def set_fps(self, new_fps):
        self._fps.set_text(new_fps)

    def slow_update(self):
        if self.game_is_active:
            self._time_left.set_text(self._timer.time_left)
            
    def start_game(self):
        super().start_game()
        self._timer = Timer(self._game_time, EVENT_GAME_TIMER_1, auto_start=True)
        self.remove(self._game_over)

    def end_game(self):
        if self._timer.time_up():
            self._game_over.text = "You Lost"
        else:
            self._game_over.text = "You Won!!"

        self.add(self._game_over)
        super().end_game()

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == EVENT_GAME_CONTROL:
            if e.action == "IncreaseScore":
                self.score = self.score + e.info['score']
                dealt_with = True
        return dealt_with

### --------------------------------------------------

class PacManLevel:
    def __init__(self, level):
        self.level = level
        self.init_maze = ""
        self.maze = None
        self.size = (32, 32)
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

# mazeLevel2 = """
# XXXXXXXXXXXXX
# X...X...X...X
# X.X...X...X..
# X...X...X...X
# XX.XXX.XXX.XX
# X...X...X...X
# X.X...X...X..
# X...X...X...X
# XX.XXX.XXX.XX
# """
# mazeLevel2_size = (32, 32)
# mazeLevel2_start = (1, 1)


class MyGame(PyGameApp):
    def init(self):
        super().init()

        mirrorMap = {"┌":"└┐", "┐":"┘┌", "└":"┌┘", "┘":"┐└", "├":"├┤", "┤":"┤├", "┬":"┴┬", "┴":"┬┴" }
        imageMap = { "─":1, "│":2, "┌":3, "┐":4, "└":5, "┘":6, "├":7, "┤":8, "┬":9, "┴":10, "┼":11, "●":0, "█":0, "X":15, ".":0 }
        barrierMap = { "─":True, "│":True, "┌":True, "┐":True, "└":True, "┘":True, "├":True, "┤":True, "┬":True, "┴":True, "┼":True, "●":False, "█":False, "X":True, ".":False }
        pacdotMap = { "●":True, ".":True }

        pacmanLevel1 = PacManLevel(1)
        pacmanLevel1.init_maze = mazeLevel1
        pacmanLevel1.add_start_cell("PacMan", (13, 23))
        pacmanLevel1.add_start_cell("Ghost", (1, 1))
        pacmanLevel1.events = [
            EventManager.gc_event("PacManJump", fromCell=(0,14), toCell=(27,14), dir="L"),
            EventManager.gc_event("PacManJump", fromCell=(27,14), toCell=(0,14), dir="R")
        ]

        pacmanLevel1.maze = PacMaze(pacmanLevel1.init_maze, mirrorMap, True, True, True, False)
        pacmanLevel1.maze.update_maze(pacmanLevel1.start["PacMan"], "█")
        pacmanLevel1.maze.map_maze("image", imageMap)
        pacmanLevel1.maze.map_maze("barrier", barrierMap)
        pacmanLevel1.maze.map_maze("pacdot", pacdotMap, False)
        
        self.pacmanager = PacManager(pacmanLevel1, self.boundary)
        self.scoreboard_mgr = Manager_Scoreboard(90, self.boundary)

        self.add_sprite_mgr(self.pacmanager)
        self.add_sprite_mgr(self.scoreboard_mgr)

        key_map = {
            pygame.K_q : "Quit",
            pygame.K_s : "StartGame",
            pygame.K_UP : "PacManUp",
            pygame.K_DOWN : "PacManDown",
            pygame.K_LEFT : "PacManLeft",
            pygame.K_RIGHT : "PacManRight",
        }
        user_event_map = {
            EVENT_GAME_TIMER_1 : "GameOver"
        }
        self.event_mgr.event_map(key_event_map=key_map, user_event_map=user_event_map)

    def update(self):
        super().update()
        self.scoreboard_mgr.set_fps(theApp.loops_per_sec)

### --------------------------------------------------

app_config = {
    "width":1200, "height":920,
    "background_fill":"black",
    "caption":"My Game",
    "key_repeat_time":30,   # msecs (lower=faster)
    "auto_start":True
    }
theApp = MyGame(app_config)
theApp.execute()

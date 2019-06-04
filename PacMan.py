# To Do: Make dots_left more efficient - returns list; count required

import sys
sys.path.append("../pygame-cdkk")
from cdkkPyGameApp import *
from cdkkSpriteExtra import *

### --------------------------------------------------

class Sprite_GridActor(Sprite_Animation):
    def __init__(self, name, start_cell, speed, cell0):
        super().__init__(name)
        self._cell_pos = [None, None, None, None]
        self.direction = "R"
        self._speed = speed
        self._cell0 = cell0
        self.move_to(start_cell)

    @property
    def centre(self):
        return self.rect.center

    @property
    def cell_pos(self):
        # cell_x, cell_y, cell_px, cell_py
        return self._cell_pos

    @cell_pos.setter
    def cell_pos(self, new_cell_pos):
        self._cell_pos = new_cell_pos

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, new_direction):
        if new_direction in ["U", "D", "L", "R"]:
            self._direction = new_direction
            self.set_animation(self.name + new_direction, ANIMATE_SHUTTLE, 2)
            self._draw_reqd = True

    def _convert_dir(self, dir):
        # Convert dir string to dx, dy
        if   dir == "R": dx, dy = 1, 0
        elif dir == "L": dx, dy = -1, 0
        elif dir == "D": dx, dy = 0, 1
        elif dir == "U": dx, dy = 0, -1
        else: dx, dy = 0, 0
        return (dx, dy)

    def _can_move(self, barriers):
        x = self._cell_pos[0]
        y = self._cell_pos[1]
        px = self._cell_pos[2]
        py = self._cell_pos[3]

        dir_ok = { "R":True, "L":True, "D":True, "U":True }

        # Check if barrier is too close
        if px >= 50: dir_ok["R"] = ((x+1) < barriers["R"]) and (py>35 and py<65)
        if px <= 50: dir_ok["L"] = ((x-1) > barriers["L"]) and (py>35 and py<65)
        if py >= 50: dir_ok["D"] = ((y+1) < barriers["D"]) and (px>35 and px<65)
        if py <= 50: dir_ok["U"] = ((y-1) > barriers["U"]) and (px>35 and px<65)

        return dir_ok

    def move(self, dir, barriers):
        if dir not in ["R", "L", "D", "U"]:
            return

        dir_ok = self._can_move(barriers)

        dx = dy = 0
        if dir == "R" and dir_ok["R"]: dx = self._speed
        if dir == "L" and dir_ok["L"]: dx = -self._speed
        if dir == "D" and dir_ok["D"]: dy = self._speed
        if dir == "U" and dir_ok["U"]: dy = -self._speed

        if dir_ok[dir]:
            if dx != 0: dy = ((50 - self._cell_pos[3]) / 100.0 ) * self._cell0.height
            if dy != 0: dx = ((50 - self._cell_pos[2]) / 100.0 ) * self._cell0.width
            self.direction = dir
            self.move_by(dx, dy)

        return dir_ok[dir]

    def move_by(self, dx, dy):
        self.rect.move_physics(dx, dy)

    def move_to(self, col_row, new_dir=None):
        col, row = col_row
        self.rect.centerx = self._cell0.left + (col + 0.5) * self._cell0.width
        self.rect.centery = self._cell0.top + (row + 0.5) * self._cell0.height
        self._cell_pos = [col, row, 50, 50]
        if new_dir is not None:
            self.direction = new_dir

### --------------------------------------------------

class Sprite_PacMan(Sprite_GridActor):
    def __init__(self, start_cell, speed, cell0):
        super().__init__("PacMan", start_cell, speed, cell0)
        self.load_spritesheet("PacManR", "Images\\PacMan.png", 16, 4, start=0,  end=16)
        self.load_spritesheet("PacManL", "Images\\PacMan.png", 16, 4, start=16, end=32)
        self.load_spritesheet("PacManD", "Images\\PacMan.png", 16, 4, start=32, end=48)
        self.load_spritesheet("PacManU", "Images\\PacMan.png", 16, 4, start=48, end=64)
        self.move_to(start_cell, "R")
        self._timer = Timer(0.02)

    def move_by(self, dx, dy):
        if self._timer.time_up():
            super().move_by(dx, dy)

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

### --------------------------------------------------

PACMAN_SPEED = 5

class PacManager(SpriteManager):
    def __init__(self, pacmaze, limits, grid_size, pac_start, maze_events):
        super().__init__("Pac-Manager")
        self.limits = limits

        self._maze = pacmaze
        self._maze_sprites = pacmaze.mapped("image")
        self._maze_barriers = pacmaze.mapped("barrier")
        self._maze_pacdots = pacmaze.mapped("pacdot")
        self._maze_events = maze_events

        self._grid = Sprite_Grid()
        xsize, ysize = grid_size
        self._grid.setup_grid(["Images\\PacManGrid.png",4,4], self._maze_sprites, self._maze_barriers, xsize, self._maze.cols, ysize, self._maze.rows)
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

        self._pacman = Sprite_PacMan(pac_start, PACMAN_SPEED, self._grid.cell_rect(0,0))
        self._pacman_curr_dir = self._pacman_next_dir = ""
        self.update_pacman()

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

    def update_pacman(self):
        x, y = self._pacman.centre
        self._pacman.cell_pos = self._grid.find_cellp(x,y)
        barriers = self._grid.find_barriers(self._pacman.cell_pos[0], self._pacman.cell_pos[1], self._pacman_next_dir)
        dir_ok = self._pacman.move(self._pacman_next_dir, barriers)
        if dir_ok:
            self._pacman_curr_dir = self._pacman_next_dir
        else:
            barriers = self._grid.find_barriers(self._pacman.cell_pos[0], self._pacman.cell_pos[1], self._pacman_curr_dir)
            self._pacman.move(self._pacman_curr_dir, barriers)

        x, y = self._pacman.centre
        cellp = self._grid.find_cellp(x,y)
        pacdotID = cellp[1]*self._maze.cols + cellp[0]
        if self.kill_uuid(self._maze_pacdots[pacdotID]):
            self._maze_pacdots[pacdotID] = None
            EventManager.post_game_control("IncreaseScore", score=1)  # PacDot = 1

        dots_left = [x for x in self._maze_pacdots if x is not None]  # reduces to 0
        if len(dots_left) == 0:
            ev = EventManager.create_event(EVENT_GAME_TIMER_1)
            EventManager.post(ev)

        cellc = self._grid.find_cell_centre(x, y)
        for e in self._maze_events:
            if cellc == e.info["fromCell"] and self._pacman_curr_dir == e.info["dir"]:
                EventManager.post(e)

        return dir_ok

    def update(self):
        super().update()
        self.update_pacman()

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
mazeLevel1_size = (32, 32)
mazeLevel1_start = (13, 23)
mazeLevel1_events = [
    EventManager.gc_event("PacManJump", fromCell=(0,14), toCell=(27,14), dir="L"),
    EventManager.gc_event("PacManJump", fromCell=(27,14), toCell=(0,14), dir="R")
]

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

        level1 = PacMaze(mazeLevel1, mirrorMap, True, True, True, False)
        level1.update_maze(mazeLevel1_start, "█")
        level1.map_maze("image", imageMap)
        level1.map_maze("barrier", barrierMap)
        level1.map_maze("pacdot", pacdotMap, False)
        
        self.pacmanager = PacManager(level1, self.boundary, mazeLevel1_size, mazeLevel1_start, mazeLevel1_events)
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

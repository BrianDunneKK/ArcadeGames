import sys
sys.path.append("../pygame-cdkk")
from cdkkPyGameApp import *
from cdkkSpriteExtra import *

### --------------------------------------------------

class Sprite_PacMan(Sprite_Animation):
    def __init__(self, posx, posy, speed, cell0):
        super().__init__("PacMan")
        self.load_spritesheet("PacManR", "Images\\PacMan.png", 16, 4, start=0,  end=16)
        self.load_spritesheet("PacManL", "Images\\PacMan.png", 16, 4, start=16, end=32)
        self.load_spritesheet("PacManD", "Images\\PacMan.png", 16, 4, start=32, end=48)
        self.load_spritesheet("PacManU", "Images\\PacMan.png", 16, 4, start=48, end=64)
        self.rect.center = (posx, posy)
        self._posx = [None, None]
        self._posy = [None, None]
        self.direction = "Right"
        self._speed = speed
        self._cell0 = cell0

    @property
    def centre(self):
        return self.rect.center

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, new_direction):
        self._direction = new_direction
        if new_direction == "Right":
            self.set_animation("PacManR", ANIMATE_SHUTTLE, 2)
        elif new_direction == "Left":
            self.set_animation("PacManL", ANIMATE_SHUTTLE, 2)
        elif new_direction == "Down":
            self.set_animation("PacManD", ANIMATE_SHUTTLE, 2)
        elif new_direction == "Up":
            self.set_animation("PacManU", ANIMATE_SHUTTLE, 2)
        self._draw_reqd = True

    def move(self, x, y, px, py, new_dir, barrier):
        # Set current position (cell x & y) and percentage within cell
        self._posx = [x, px]
        self._posy = [y, py]

        dx = dy = 0
        if   new_dir == "Right": dx = 1
        elif new_dir == "Left": dx = -1
        elif new_dir == "Down": dy = 1
        elif new_dir == "Up": dy = -1

        # Check if barrier is too close
        new_dir_ok = True

        if dx ==  1 and px >= 50: new_dir_ok = ((x+dx) < barrier)
        if dx == -1 and px <= 50: new_dir_ok = ((x+dx) > barrier)
        if dy ==  1 and py >= 50: new_dir_ok = ((y+dy) < barrier)
        if dy == -1 and py <= 50: new_dir_ok = ((y+dy) > barrier)

        # Check if lined up with grid
        if dx != 0: new_dir_ok = new_dir_ok and (py>35 and py<65)
        if dy != 0: new_dir_ok = new_dir_ok and (px>35 and px<65)

        dx = dx * self._speed
        dy = dy * self._speed

        if new_dir_ok and dx != 0: dy = ((50 - py) / 100.0 ) * self._cell0.height
        if new_dir_ok and dy != 0: dx = ((50 - px) / 100.0 ) * self._cell0.width

        if new_dir_ok:
            self.direction = new_dir
            self.rect.move_physics(dx, dy)

        return new_dir_ok

    def start_game(self):
        super().start_game()
        # Start goes here

    def end_game(self):
        # End goes here
        super().end_game()

    def update(self):
        super().update()

    def draw(self):
        super().draw()

### --------------------------------------------------

maze = """
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
1●●●●●●●●●│███
"""

class PacManager(SpriteManager):
    mirrorMap = {"┌":"└┐", "┐":"┘┌", "└":"┌┘", "┘":"┐└", "├":"├┤", "┤":"┤├", "┬":"┴┬", "┴":"┬┴" }
    mazeMap = { "─":1, "│":2, "┌":3, "┐":4, "└":5, "┘":6, "├":7, "┤":8, "┬":9, "┴":10, "┼":11, "●":0, "█":0, "1":0 }
    barrierMap = { "─":True, "│":True, "┌":True, "┐":True, "└":True, "┘":True, "├":True, "┤":True, "┬":True, "┴":True, "┼":True, "●":False, "█":False, "1":False }

    def __init__(self, limits):
        super().__init__("Pac-Manager")
        self.limits = limits

        self._maze_sprites = StringLOL(maze, PacManager.mirrorMap, PacManager.mazeMap)
        self._maze_sprites.transform(True, True, True, False)
        maze_sprites = self._maze_sprites.map_as_list()

        self._maze_barriers = StringLOL(maze, PacManager.mirrorMap, PacManager.barrierMap)
        self._maze_barriers.transform(True, True, True, False)
        maze_barriers = self._maze_barriers.map_as_list()

        self._grid = Sprite_Grid()
        self._grid.setup_grid(["Images\\PacManGrid.png",4,4], maze_sprites, maze_barriers, xsize=32, cols=28, ysize=32, rows=29)
        self._grid.rect.center = self.limits.center
        self.add(self._grid)

        posx = self.limits.centerx
        posy = 748
        self._pacman = Sprite_PacMan(posx, posy, 5, self._grid.cell_rect(0,0))
        self.update_pacman(0)

    def event(self, e):
        dealt_with = super().event(e)
        new_direction = None
        if not dealt_with and e.type == EVENT_GAME_CONTROL and self.game_is_active:
            if e.action in ["PacManUp", "PacManDown", "PacManLeft", "PacManRight"]:
                new_direction = e.action[6:]
        if new_direction is not None:
            dealt_with = True
            self.update_pacman(new_direction)
        return dealt_with

    def add_pacman(self):
        self.add(self._pacman)

    def update_pacman(self, new_direction):
        x, y = self._pacman.centre
        cellp = self._grid.find_cellp(x,y)
        barrier = self._grid.find_barrier(cellp[0], cellp[1], new_direction)
        new_dir_ok = self._pacman.move(cellp[0], cellp[1], cellp[2], cellp[3], new_direction, barrier)
        return new_dir_ok

    def update(self):
        super().update()
        # Update is called for the sprite during every game loop
        # For moving objects, call self.rect.move_physics()

    def start_game(self):
        super().start_game()
        self.add_pacman()
        # This is called each time a game starts
        # Typically this is where sprites are created/reset

    def end_game(self):
        # This is called each time a game ends
        # Typically this is where sprites are removed
        super().end_game()

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

        self._game_over = Sprite_GameOver(limits)

    def set_fps(self, new_fps):
        self._fps.set_text(new_fps)

    def slow_update(self):
        # This is called around 3 times per sec and is for updates that don't need to happen every game loop
        if self.game_is_active:
            self._time_left.set_text(self._timer.time_left)
            
    def start_game(self):
        super().start_game()
        self._timer = Timer(self._game_time, EVENT_GAME_TIMER_1, auto_start=True)
        self.remove(self._game_over)

    def end_game(self):
        self.add(self._game_over)
        super().end_game()

### --------------------------------------------------

class MyGame(PyGameApp):
    def init(self):
        super().init()

        self.ninja_mgr = PacManager(self.boundary)
        self.scoreboard_mgr = Manager_Scoreboard(60, self.boundary)

        self.add_sprite_mgr(self.ninja_mgr)
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
        # Manage interaction between Sprites in different SpriteManagers

### --------------------------------------------------

app_config = {
    "width":1200, "height":920,
    "background_fill":"black",
    "caption":"My Game",
    "key_repeat_time":30,   # msecs (lower=faster)
    "auto_start":False
    }
theApp = MyGame(app_config)
theApp.execute()


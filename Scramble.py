# To Do: Chanage find_collisions to use SpriteGroup.collide()

import cProfile
import pstats
from pstats import SortKey

import sys
sys.path.append("../pygame-cdkk")
from PyGameApp import *

### --------------------------------------------------

USE_PROFILING = False

GAME_SPEED = 50    # msecs (lower=faster)
EVENT_MOVE_ROCKET = EVENT_NEXT_USER_EVENT

### --------------------------------------------------

class Sprite_Cave(Sprite_Shape):
    def __init__(self, cave_rect, min_gap, section_size=10):
        super().__init__("Cave")
        self.cave_height = cave_rect.height
        self.cave_min_gap = min_gap
        self.cave_section_size = section_size
        self.cave_sections = (cave_rect.width // self.cave_section_size) + 1
        self.update_reqd = False

        self.setup_shape(cave_rect)
        self.walls = Sprite_ShapeSetManager("Cave Shapes", cave_rect)

        self.cave_top = Sprite_Shape("Cave Top")
        self.cave_top.setup_shape(cave_rect, ["blue"], "Polygon")
        self.walls.add_shape(self.cave_top)

        self.cave_bottom = Sprite_Shape("Cave Bottom")
        self.cave_bottom.setup_shape(cave_rect, ["red3"], "Polygon")
        self.walls.add_shape(self.cave_bottom)

        self.setup()

    def setup(self):
        self.scrolling = True
        self.cave_top_queue = RandomQueue(self.cave_sections, 5, 500)
        self.cave_bottom_queue = RandomQueue(self.cave_sections, 5, 500)

    def scroll(self):
        if self.scrolling:
            self.cave_top_queue.append(self.cave_height - self.cave_bottom_queue.next_value - self.cave_min_gap)
            self.cave_bottom_queue.append(self.cave_height - self.cave_top_queue.next_value - self.cave_min_gap)
            self.update_reqd = True

    def update(self):
        if self.update_reqd:
            poly = self._queue_to_polygon(self.cave_top_queue.queue, 0)
            self.cave_top.setup_polygon(poly)
            poly = self._queue_to_polygon(self.cave_bottom_queue.queue, self.cave_height)
            self.cave_bottom.setup_polygon(poly)
            self._draw_reqd = True
            self.update_reqd = False

    def _queue_to_polygon(self, queue, height):
        poly = [[0, height]]
        x = 0
        for p in queue:
            if height == 0:
                pt = [x, p]
            else:
                pt = [x, height - p]
                pass
            x += self.cave_section_size
            poly.append(pt)

        poly.append([x - self.cave_section_size, height])
        return poly

    def draw(self):
        self.create_canvas()
        super().draw()
        self.walls.draw_shapes(self.image)

    def cave_top_bottom(self, posx, rel_screen=True):
        if rel_screen:
            rel_posx = posx - self.rect.left  # Convert to same coordinates as cave
        else:
            rel_posx = posx
        section = rel_posx // self.cave_section_size

        top = 0
        bottom = self.rect.height
        if section < self.cave_top_queue.queue.maxlen:
            top = self.cave_top_queue.queue[section]
            bottom = self.cave_height - self.cave_bottom_queue.queue[section]

        if rel_screen:
            top = top + self.rect.top
            bottom = bottom + self.rect.top

        return [top, bottom]

### --------------------------------------------------

class Sprite_CaveItem(Sprite_Animation):
    def __init__(self, name):
        super().__init__(name)
        self.scroll_count = 0
        self.set_desc("Cave Item", True)

    def setup(self, posx, posy, limits):
        self.rect.right = posx
        self.rect.bottom = posy - 1
        ev = EventManager.gc_event("KillSpriteUUID")
        ev.uuid = self.uuid
        self.rect.add_limit(Physics_Limit(limits, LIMIT_KEEP_INSIDE, AT_LIMIT_XY_DO_NOTHING, ev))

    def scroll(self, dx):
        self.rect.move_physics(dx, 0)
        self.scroll_count = self.scroll_count + 1

### --------------------------------------------------

class Sprite_Rocket(Sprite_CaveItem):
    def __init__(self, posx, posy, limits):
        super().__init__("Rocket")
        self.load_spritesheet("Rocket", "Images\\Rocket.png", 2, 1)
        self.set_animation("Rocket", ANIMATE_LOOP)
        self.launch_at = random.randint(30,100)
        self.launch_speed = -random.randint(1,5)
        self.rect.set_velocity(0, 0)
        self.setup(posx, posy, limits)
        self.rect.go()

    def update(self):
        self.rect.move_physics()

    def scroll(self, dx):
        super().scroll(dx)
        if self.scroll_count == self.launch_at:
            self.rect.set_velocity(0, self.launch_speed)

### --------------------------------------------------

class Sprite_FuelTank(Sprite_CaveItem):
    def __init__(self, posx, posy, limits):
        super().__init__("Fuel Tank")
        self.load_spritesheet("Fuel Tank", "Images\\fuel_tank.png", 1, 1)
        self.set_animation("Fuel Tank", ANIMATE_MANUAL)
        self.setup(posx, posy, limits)

### --------------------------------------------------

class Manager_Cave(SpriteManager):
    def __init__(self, cave_rect, spaceship_height, name = "Cave Manager"):
        super().__init__(name)
        self._cave_rect = cave_rect
        self.cave_background = Sprite_Shape("Cave background", cave_rect, ["green"])
        self.add(self.cave_background)
        self.cave = Sprite_Cave(cave_rect, spaceship_height*5)
        self.add(self.cave)
        self._timer = Timer(GAME_SPEED/1000.0, EVENT_GAME_TIMER_1)
        self.rockets = SpriteGroup()
        self.rocket_launch_at = random.randint(15, 30)
        self.rocket_loop = 0
        self.fuel_tanks = SpriteGroup()

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with:
            if e.type == EVENT_GAME_CONTROL:
                if e.action == "ScrollCave":
                    self.cave.scroll()
                    self.move_cave_items()
                    self.add_rocket()
                    self.add_fuel_tank()
                    EventManager.post_game_control("IncreaseScore", score=1)
                elif e.action == "StartGame":
                    self.cave.setup()
                elif e.action == "SpaceshipCrash":
                    self.cave.scrolling = False
        return dealt_with

    def collision_with_cave(self, corners):
        collision = False
        for c in corners:
            top_bottom = self.cave.cave_top_bottom(c[0])
            if not collision:
                collision = (top_bottom[0] > c[1] or top_bottom[1] < c[1])
        return collision

    def move_cave_items(self):
        if self.cave.scrolling:
            sprites = self.find_sprites_by_desc("Cave Item", True)
            for s in sprites:
                s.scroll(-self.cave.cave_section_size)

    def add_rocket(self):
        self.rocket_loop = self.rocket_loop + 1
        if self.rocket_loop == self.rocket_launch_at:
            self.rocket_loop = 0
            self.rocket_launch_at = random.randint(15, 30)
            posx = self.cave.rect.right - 10
            posy = self.cave.cave_top_bottom(posx)
            rocket = Sprite_Rocket(posx, posy[1], self.cave.rect)
            self.add(rocket)
            self.rockets.add(rocket)

    def add_fuel_tank(self):
        if self.rocket_loop == self.rocket_launch_at-10:
            posx = self.cave.rect.right - 10
            posy = min(self.cave.cave_top_bottom(posx)[1] + 10, self._cave_rect.bottom - 2)
            fuel_tank = Sprite_FuelTank(posx, posy, self._cave_rect)
            self.add(fuel_tank)
            self.fuel_tanks.add(fuel_tank)

    def update(self):
        super().update()
        self.rockets.collide(self.cave.walls, dokilla=True, dokillb=False)

### --------------------------------------------------

class Sprite_Spaceship(Sprite_Animation):
    def __init__(self, value, limits):
        super().__init__(str(value))
        self.load_animation("Spaceship", "Images\\Spaceship{0:02d}.png", 7, crop=self.crop_image)
        self.load_spritesheet("Explosion", "Images\\Explosion.png", 4, 4)
        self.show_spaceship()
        self.rect.centerx = limits.width/4
        self.rect.centery = limits.height/2
        self.rect.add_limit(Physics_Limit(limits, LIMIT_KEEP_INSIDE, AT_LIMIT_X_HOLD_POS_X+AT_LIMIT_Y_HOLD_POS_Y))

        return_speed = 3
        limit_rect = pygame.Rect(0,0,return_speed*2,0)
        limit_rect.center = self.rect.center
        xlimit = Physics_Limit(limit_rect, LIMIT_MOVE_TO, AT_LIMIT_X_MOVE_TO_X)
        xlimit.motion = Physics_Motion()
        xlimit.motion.velocity_x = return_speed
        self.rect.add_limit(xlimit)
        self.rect.go()

    @property
    def crop_image(self):
        # Crop the imported image by ... [left, right, top, bottom]
        return [0,0,20,20]

    @property
    def corners(self):
        corners = []
        corners.append((self.rect.left+34, self.rect.top))
        corners.append((self.rect.right, self.rect.centery-5))
        corners.append((self.rect.left+34, self.rect.bottom))
        corners.append((self.rect.right, self.rect.centery+5))
        return corners

    def update(self):
        self.rect.move_physics()

    def show_explosion(self):
        self.set_animation("Explosion", ANIMATE_SHUTTLE_ONCE+ANIMATE_REVERSE, 1)

    def show_spaceship(self):
        self.set_animation("Spaceship", ANIMATE_LOOP)

### --------------------------------------------------

class Sprite_Bullet (Sprite_Shape):
    def __init__(self, bullet_type, posx, posy, limits):
        super().__init__(bullet_type)
        if bullet_type == "Bullet":
            self.setup_shape(pygame.Rect(posx,posy,20,3), ["orange"])
            self.rect.set_velocity(20, 0)
        elif bullet_type == "Bomb":
            self.setup_shape(pygame.Rect(posx,posy,10,10), ["orange"], "Ellipse")
            self.rect.set_velocity(5, 0)
            self.rect.set_acceleration(0, Physics.gravity)

        ev = EventManager.gc_event("DeleteBullet")
        ev.uuid = self.uuid
        self.rect.add_limit(Physics_Limit(limits, LIMIT_KEEP_INSIDE, AT_LIMIT_XY_DO_NOTHING, ev))
        self.rect.go()

    def update(self):
        self.rect.move_physics()

### --------------------------------------------------

class Manager_Spaceship(SpriteManager):
    def __init__(self, limits, name = "Spaceship Manager"):
        super().__init__(name)
        self._limits = limits
        self._spaceship = Sprite_Spaceship("Spaceship", self._limits)
        self.add(self._spaceship, layer=9)  # Layer 9: Above everything else
        self._bullets = SpriteGroup()
        self._bullet_time_limit = 250  # Minimum time between bullets (msecs)
        self._bullet_timer = Timer(self._bullet_time_limit/1000.0)

    @property
    def spaceship_rect(self):
        return self._spaceship.rect

    @property
    def spaceship_corners(self):
        return self._spaceship.corners

    @property
    def bullets_rect(self):
        return self._bullets.sprites_uuid_rect

    def fire_bullet(self, bullet_type):
        if self._bullet_timer.time_left == 0:
            posx = self.spaceship_rect.centerx + 15
            posy = self.spaceship_rect.centery - 5
            bullet = Sprite_Bullet(bullet_type, posx, posy, self._limits)
            self.add(bullet, layer=1)
            self._bullets.add(bullet)
            EventManager.post_game_control("IncreaseScore", score=-1)
            self._bullet_timer = Timer(self._bullet_time_limit/1000.0)

    def spaceship_collide(self, *dangers):
        collide = False
        for sprite_group in dangers:
            if not collide:
                collide = self._spaceship.collide(sprite_group)
        if collide:
            self._spaceship.show_explosion()
        return collide

    def bullets_collide(self, dangers, dokill, inc_score, inc_time):
        coll_dict = self._bullets.collide(dangers, dokilla=True, dokillb=dokill)
        if inc_score:
            for bullet, items in coll_dict.items():
                if len(items) > 0:
                    EventManager.post_game_control("IncreaseScore", score=len(items)*100)
        if inc_time:
            for bullet, items in coll_dict.items():
                if len(items) > 0:
                    EventManager.post_game_control("IncreaseTime", increment=10)

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == EVENT_GAME_CONTROL:
            dealt_with = True
            if e.action == "SpaceshipUp":
                self._spaceship.rect.move_physics(0,-5)
            elif e.action == "SpaceshipDown":
                self._spaceship.rect.move_physics(0,5)
            elif e.action == "SpaceshipLeft":
                self._spaceship.rect.move_physics(-10,0)
            elif e.action == "SpaceshipRight":
                self._spaceship.rect.move_physics(10,0)
            elif e.action == "SpaceshipCrash":
                self._spaceship.show_explosion()
            elif e.action == "FireBullet":
                self.fire_bullet("Bullet")
            elif e.action == "FireBomb":
                self.fire_bullet("Bomb")
            elif e.action == "DeleteBullet":
                self.kill_uuid(e.uuid)
            else:
                dealt_with = False
        return dealt_with

### --------------------------------------------------

class Manager_Scoreboard(SpriteManager):
    def __init__(self, game_time, limits, name = "Scoreboard Manager"):
        super().__init__(name)
        self.count=0
        self._score = 0
        self._game_time = game_time

        self._scoreboard = Sprite_TextBox("Score", auto_size=False)
        self._scoreboard.setup_textbox(200, 40)
        self._scoreboard.setup_text(36, "black", "Score: {0}")
        self._scoreboard.rect.topleft = (70, 10)
        self.add(self._scoreboard)
        self.score = 0

        self._timer = Timer(self._game_time, EVENT_GAME_TIMER_2)
        self._time_left = Sprite_TextBox("Time Left", auto_size=False)
        self._time_left.setup_textbox(200, 40)
        self._time_left.setup_text(36, "black", "Time Left: {0:0.1f}")
        self._time_left.set_text(0)
        self._time_left.rect.topleft = (limits.width - 250, 10)
        self.add(self._time_left)

        self._fps = Sprite_TextBox("FPS", auto_size=False)
        self._fps.setup_textbox(150, 40)
        self._fps.setup_text(36, "black", "FPS: {0:4.1f}")
        self._fps.rect.topleft = (limits.centerx, 10)
        self.add(self._fps)

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        self._score = new_score
        self._scoreboard.set_text(self.score)

    def set_fps(self, new_fps):
        self._fps.set_text(new_fps)

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == EVENT_GAME_CONTROL:
            if e.action == "IncreaseScore":
                self.score = self.score + e.info['score']
                dealt_with = True
            elif e.action == "IncreaseTime":
                self._timer.extend_timer(e.info["increment"])
                dealt_with = True
        return dealt_with

    def slow_update(self):
        self._time_left.set_text(self._timer.time_left)

### --------------------------------------------------

class ScrambleApp(PyGameApp):
    def init(self):
        size = (1200, 800)
        super().init(size)
        pygame.display.set_caption("Scramble")
        self.background_fill = "burlywood"

        cave_rect = self.boundary
        cave_rect = cave_rect.inflate(-100, -100)
        cave_rect.topleft = (50, 50)

        self.spaceship_mgr = Manager_Spaceship(cave_rect)
        self.cave_mgr = Manager_Cave(cave_rect, self.spaceship_mgr.spaceship_rect.height)
        self.scoreboard_mgr = Manager_Scoreboard(15, self.boundary)

        # Sequence: Bottom to top layer
        self.add_sprite_mgr(self.cave_mgr)
        self.add_sprite_mgr(self.spaceship_mgr)
        self.add_sprite_mgr(self.scoreboard_mgr)

        self.set_fast_keys(30)
        self.event_mgr.keyboard_event(pygame.K_q, "Quit")
        self.event_mgr.keyboard_event(pygame.K_r, "StartGame")
        self.event_mgr.keyboard_event(pygame.K_UP, "SpaceshipUp")
        self.event_mgr.keyboard_event(pygame.K_DOWN, "SpaceshipDown")
        self.event_mgr.keyboard_event(pygame.K_LEFT, "SpaceshipLeft")
        self.event_mgr.keyboard_event(pygame.K_RIGHT, "SpaceshipRight")
        self.event_mgr.keyboard_event(pygame.K_a, "FireBullet")
        self.event_mgr.keyboard_event(pygame.K_z, "FireBomb")
        self.event_mgr.user_event(EVENT_GAME_TIMER_1, "ScrollCave")

    def update(self):
        super().update()
        self.spaceship_mgr.spaceship_collide(self.cave_mgr.cave.walls, self.cave_mgr.rockets, self.cave_mgr.fuel_tanks)
        self.spaceship_mgr.bullets_collide(self.cave_mgr.cave.walls, dokill=False, inc_score=False, inc_time=False)
        self.spaceship_mgr.bullets_collide(self.cave_mgr.rockets, dokill=True, inc_score=True, inc_time=False)
        self.spaceship_mgr.bullets_collide(self.cave_mgr.fuel_tanks, dokill=True, inc_score=False, inc_time=True)
        self.scoreboard_mgr.set_fps(theApp.loops_per_sec)

### --------------------------------------------------

theApp = ScrambleApp()

if not USE_PROFILING:
    theApp.execute()
else:
    cProfile.run('theApp.execute()', 'scramble_stats.log')
    p = pstats.Stats('scramble_stats.log')
    print("Sort by internal time: (exc sub-functions)")
    print("----------------------")
    p.strip_dirs().sort_stats(SortKey.TIME).print_stats(20)
    p.strip_dirs().sort_stats(SortKey.TIME).print_callers('blit')

    # print("Sort by cumulative time: (inc sub-functions)")
    # p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(20)

    # print("Sort by call count:")
    # p.strip_dirs().sort_stats(SortKey.CALLS).print_stats(20)


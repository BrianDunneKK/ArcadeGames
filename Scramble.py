# To Do: Because of fastkeys, StartGame being sent multiple times
# To DO: Is hitting fuel generating multiple IncreaseTime events?
# To Do: Change spaceship from frames to spritesheet

# import cProfile
# import pstats
# from pstats import SortKey

# import sys
# sys.path.insert(0, "cdkk")
import cdkk
import pygame
import random

### --------------------------------------------------

USE_PROFILING = False

GAME_SPEED = 50    # msecs (lower=faster)
EVENT_MOVE_ROCKET = cdkk.EVENT_NEXT_USER_EVENT

### --------------------------------------------------

class Sprite_Cave(cdkk.Sprite_Shape):
    def __init__(self, cave_rect, min_gap, section_size=10):
        super().__init__("Cave", cave_rect, cdkk.stylesheet.style("Invisible"))
        self.cave_height = cave_rect.height
        self.cave_min_gap = min_gap
        self.cave_section_size = section_size
        self.cave_sections = (cave_rect.width // self.cave_section_size) + 1
        self.update_reqd = False

        self.walls = cdkk.SpriteGroup("Cave Shapes")

        top_style = {"fillcolour":"blue", "outlinecolour":None, "shape":"Polygon"}
        self.cave_top = cdkk.Sprite_Shape("Cave Top", cave_rect, top_style)
        self.walls.add(self.cave_top)

        bottom_style = {"fillcolour":"red3", "outlinecolour":None, "shape":"Polygon"}
        self.cave_bottom = cdkk.Sprite_Shape("Cave Bottom", cave_rect, bottom_style)
        self.walls.add(self.cave_bottom)

    def start_game(self):
        super().start_game()
        self.cave_top_queue = cdkk.RandomQueue(self.cave_sections, 5, 500)
        self.cave_bottom_queue = cdkk.RandomQueue(self.cave_sections, 5, 500)

    def scroll(self):
        self.cave_top_queue.append(self.cave_height - self.cave_bottom_queue.next_value - self.cave_min_gap)
        self.cave_bottom_queue.append(self.cave_height - self.cave_top_queue.next_value - self.cave_min_gap)
        self.update_reqd = True

    def update(self):
        super().update()
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
        self.walls.draw_sprites(self.image)

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

class Sprite_CaveItem(cdkk.Sprite_Animation):
    def __init__(self, name):
        super().__init__(name)
        self.scroll_count = 0
        self.set_config("Cave Item", True)

    def setup(self, posx, posy, limits):
        self.rect.right = posx
        self.rect.bottom = posy - 1
        ev = cdkk.EventManager.gc_event("KillSpriteUUID", uuid=self.uuid, trace="CaveItem-Limit")
        self.rect.add_limit(cdkk.Physics_Limit(limits, cdkk.LIMIT_KEEP_INSIDE, cdkk.AT_LIMIT_XY_DO_NOTHING, ev))

    def scroll(self, dx):
        self.rect.move_physics(dx, 0)
        self.scroll_count = self.scroll_count + 1

    def start_game(self):
        super().start_game()
        self.kill()

### --------------------------------------------------

class Sprite_Rocket(Sprite_CaveItem):
    def __init__(self, posx, posy, limits):
        super().__init__("Rocket")
        self.load_spritesheet("Rocket", "Rocket.png", 2, 1)
        self.set_animation("Rocket", cdkk.ANIMATE_LOOP)
        self.launch_at = random.randint(30,100)
        self.launch_speed = -random.randint(1,5)
        self.rect.set_velocity(0, 0)
        self.setup(posx, posy, limits)
        self.rect.go()
        self.set_config("auto_move_physics", True)

    def scroll(self, dx):
        super().scroll(dx)
        if self.scroll_count == self.launch_at:
            self.rect.set_velocity(0, self.launch_speed)

### --------------------------------------------------

class Sprite_FuelTank(Sprite_CaveItem):
    def __init__(self, posx, posy, limits):
        super().__init__("Fuel Tank")
        self.load_spritesheet("Fuel Tank", "fuel_tank.png", 1, 1)
        self.set_animation("Fuel Tank", cdkk.ANIMATE_MANUAL)
        self.setup(posx, posy, limits)

### --------------------------------------------------

class Manager_Cave(cdkk.SpriteManager):
    def __init__(self, cave_rect, spaceship_height, name = "Cave Manager"):
        super().__init__(name)
        self._cave_rect = cave_rect
        self.cave_background = cdkk.Sprite_Shape("Cave background", cave_rect, style={"fillcolour":"green", "outlinecolour":None})
        self.add(self.cave_background)
        self.cave = Sprite_Cave(cave_rect, spaceship_height*5)
        self.add(self.cave)
        self.rockets = cdkk.SpriteGroup("Rockets")
        self.rocket_launch_at = random.randint(15, 30)
        self.rocket_loop = 0
        self.fuel_tanks = cdkk.SpriteGroup("Fuel Tanks")

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == cdkk.EVENT_GAME_CONTROL:
            if e.action == "ScrollGame":
                if self.game_is_active:
                    self.cave.scroll()
                    self.move_cave_items()
                    self.add_rocket()
                    self.add_fuel_tank()
                    cdkk.EventManager.post_game_control("UpdateScore", score=1)
        return dealt_with

    def move_cave_items(self):
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

    def start_game(self):
        super().start_game()
        self.rocket_loop = 0

### --------------------------------------------------

class Sprite_Spaceship(cdkk.Sprite_Animation):
    def __init__(self, limits):
        super().__init__("Spaceship")
        self._limits = limits
        self.load_animation("Spaceship", "Spaceship{0:02d}.png", 7, crop=self.crop_image)
        self.load_spritesheet("Explosion", "Explosion.png", 4, 4)
        self.show_spaceship()
        self.rect.centerx = limits.width/4
        self.rect.centery = limits.height/2
        self.rect.add_limit(cdkk.Physics_Limit(limits, cdkk.LIMIT_KEEP_INSIDE, cdkk.AT_LIMIT_X_HOLD_POS_X+cdkk.AT_LIMIT_Y_HOLD_POS_Y))

        return_speed = 3
        limit_rect = cdkk.cdkkRect(0,0,return_speed*2,0)
        limit_rect.center = self.rect.center
        xlimit = cdkk.Physics_Limit(limit_rect, cdkk.LIMIT_MOVE_TO, cdkk.AT_LIMIT_X_MOVE_TO_X)
        xlimit.motion = cdkk.Physics_Motion()
        xlimit.motion.velocity_x = return_speed
        self.rect.add_limit(xlimit)
        self.rect.go()
        self.set_config("auto_move_physics", True)

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

    def show_explosion(self):
        self.set_animation("Explosion", cdkk.ANIMATE_SHUTTLE_ONCE+cdkk.ANIMATE_REVERSE, 1)

    def show_spaceship(self):
        self.set_animation("Spaceship", cdkk.ANIMATE_LOOP)

    def start_game(self):
        super().start_game()
        self.show_spaceship()
        self.rect.centerx = self._limits.width/4
        self.rect.centery = self._limits.height/2

### --------------------------------------------------

class Sprite_Ammunition (cdkk.Sprite_Shape):
    ammunition_style = {"fillcolour":"orange", "outlinecolour":None}
    bullet_style = cdkk.merge_dicts(ammunition_style, {"width":20, "height":3, "shape":"Rectangle"})
    bomb_style = cdkk.merge_dicts(ammunition_style, {"width":10, "height":10, "shape":"Ellipse"})

    def __init__(self, bullet_type, posx, posy, limits):
        super().__init__(bullet_type)
        if bullet_type == "Bullet":
            self.update_style(Sprite_Ammunition.bullet_style)
            self.rect.set_velocity(20, 0)
        elif bullet_type == "Bomb":
            self.update_style(Sprite_Ammunition.bomb_style)
            self.rect.set_velocity(5, 0)
            self.rect.set_acceleration(0, cdkk.Physics.gravity)
        self.rect.topleft = (posx, posy)

        ev = cdkk.EventManager.gc_event("KillSpriteUUID", uuid=self.uuid, trace="Bullet-Limit")
        self.rect.add_limit(cdkk.Physics_Limit(limits, cdkk.LIMIT_KEEP_INSIDE, cdkk.AT_LIMIT_XY_DO_NOTHING, ev))
        self.rect.go()
        self.set_config("auto_move_physics", True)

### --------------------------------------------------

class Manager_Spaceship(cdkk.SpriteManager):
    def __init__(self, limits, name = "Spaceship Manager"):
        super().__init__(name)
        self._limits = limits
        self._spaceship = Sprite_Spaceship(self._limits)
        self.add(self._spaceship, layer=9)  # Layer 9: Above everything else
        self._bullets = cdkk.SpriteGroup("Bullets")
        self._bullet_time_limit = 250  # Minimum time between bullets (msecs)
        self._bullet_timer = cdkk.Timer(self._bullet_time_limit/1000.0)

    @property
    def spaceship_rect(self):
        return self._spaceship.rect

    @property
    def spaceship_corners(self):
        return self._spaceship.corners

    def fire_bullet(self, bullet_type):
        if self._bullet_timer.time_left == 0:
            posx = self.spaceship_rect.centerx + 15
            posy = self.spaceship_rect.centery - 5
            bullet = Sprite_Ammunition(bullet_type, posx, posy, self._limits)
            self.add(bullet, layer=1)
            self._bullets.add(bullet)
            cdkk.EventManager.post_game_control("UpdateScore", score=-1)
            self._bullet_timer = cdkk.Timer(self._bullet_time_limit/1000.0)

    def spaceship_collide(self, *dangers):
        collide = False
        for sprite_group in dangers:
            if not collide:
                collide = self._spaceship.collide(sprite_group)
        if collide:
            cdkk.EventManager.post_game_control("SpaceshipCrash")
        return collide

    def bullets_collide(self, dangers, dokill, inc_score, inc_time):
        coll_dict = self._bullets.collide(dangers, dokilla=True, dokillb=dokill)
        if inc_score:
            for bullet, items in coll_dict.items():
                if len(items) > 0:
                    cdkk.EventManager.post_game_control("UpdateScore", score=len(items)*100)
        if inc_time:
            for bullet, items in coll_dict.items():
                if len(items) > 0:
                    cdkk.EventManager.post_game_control("IncreaseTime", increment=5)

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == cdkk.EVENT_GAME_CONTROL and self.game_is_active:
            if e.action == "MoveUp":
                self._spaceship.rect.move_physics(0,-5)
                dealt_with = True
            elif e.action == "MoveDown":
                self._spaceship.rect.move_physics(0,5)
                dealt_with = True
            elif e.action == "MoveLeft":
                self._spaceship.rect.move_physics(-10,0)
                dealt_with = True
            elif e.action == "MoveRight":
                self._spaceship.rect.move_physics(10,0)
                dealt_with = True
            elif e.action == "SpaceshipCrash":
                self._spaceship.show_explosion()
                cdkk.EventManager.post_game_control("GameOver")
            elif e.action == "FireBullet":
                self.fire_bullet("Bullet")
                dealt_with = True
            elif e.action == "FireBomb":
                self.fire_bullet("Bomb")
                dealt_with = True
        return dealt_with

### --------------------------------------------------

class Manager_Scoreboard(cdkk.SM_Scoreboard):
    def __init__(self, game_time):
        super().__init__(game_time, fps_style={"invisible": False})       

### --------------------------------------------------

class ScrambleApp(cdkk.PyGameApp):
    def init(self):
        super().init()

        cave_rect = self.boundary.inflate(-100, -100)
        cave_rect.topleft = (50, 50)

        self.spaceship_mgr = Manager_Spaceship(cave_rect)
        self.cave_mgr = Manager_Cave(cave_rect, self.spaceship_mgr.spaceship_rect.height)
        self.scoreboard_mgr = Manager_Scoreboard(10)

        # Sequence: Bottom to top layer
        self.add_sprite_mgr(self.cave_mgr)
        self.add_sprite_mgr(self.spaceship_mgr)
        self.add_sprite_mgr(self.scoreboard_mgr)

        key_map = cdkk.merge_dicts(cdkk.PyGameApp.default_key_map,
                                   {pygame.K_a: "FireBullet", pygame.K_z: "FireBomb"})
        user_event_map = {
            cdkk.EVENT_GAME_TIMER_1 : "GameOver"
        }
        self.event_mgr.event_map(key_event_map=key_map, user_event_map=user_event_map)

    def update(self):
        super().update()
        self.spaceship_mgr.spaceship_collide(self.cave_mgr.cave.walls, self.cave_mgr.rockets, self.cave_mgr.fuel_tanks)
        self.spaceship_mgr.bullets_collide(self.cave_mgr.cave.walls, dokill=False, inc_score=False, inc_time=False)
        self.spaceship_mgr.bullets_collide(self.cave_mgr.rockets, dokill=True, inc_score=True, inc_time=False)
        self.spaceship_mgr.bullets_collide(self.cave_mgr.fuel_tanks, dokill=True, inc_score=False, inc_time=True)
        self.scoreboard_mgr.set_fps(self.loops_per_sec)

### --------------------------------------------------

app_config = {
    "width":1200, "height":800,
    "background_fill":"burlywood",
    "caption":"Scramble",
    "key_repeat_time":30,   # msecs (lower=faster)
    "scroll_time":50,       # msecs (lower=faster)
    "image_path":"ArcadeGames\\Images\\"
    }
ScrambleApp(app_config).execute()

# if not USE_PROFILING:
#     theApp.execute()
# else:
#     cProfile.run('theApp.execute()', 'scramble_stats.log')
#     p = pstats.Stats('scramble_stats.log')
#     print("Sort by internal time: (exc sub-functions)")
#     print("----------------------")
#     p.strip_dirs().sort_stats(SortKey.TIME).print_stats(20)
#     p.strip_dirs().sort_stats(SortKey.TIME).print_callers('blit')

#     # print("Sort by cumulative time: (inc sub-functions)")
#     # p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(20)

#     # print("Sort by call count:")
#     # p.strip_dirs().sort_stats(SortKey.CALLS).print_stats(20)

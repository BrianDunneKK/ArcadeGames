# import sys
# sys.path.insert(0, "cdkk")
import pygame
import cdkk
import random

sprite_extra_styles = {
    "Scoreboard": {"fillcolour": None, "outlinecolour": None, "textsize": 36, "align_horiz": "L"}
}
cdkk.stylesheet.add_stylesheet(sprite_extra_styles)

# --------------------------------------------------


class Sprite_Bird(cdkk.Sprite_Animation):
    def __init__(self, posx, posy, gravity, limits):
        super().__init__("FlappyBird")
        self._gravity = gravity
        self._limits = limits
        self.load_spritesheet("Bird", "FlappyBird.png", 4, 4, start=0, end=3,
                              set_anim=True, img_process=("scale", (96, 96)))
        self.rect.center = (posx, posy)
        self.rect.set_acceleration(0, self._gravity)
        self.rect.add_limit(cdkk.Physics_Limit(self._limits, cdkk.LIMIT_KEEP_INSIDE,
                                               cdkk.AT_LIMIT_Y_HOLD_POS_Y))
        self.rect.go()
        self.set_config("auto_move_physics", True)

    def flap(self):
        self.rect.set_velocity(0, -self._gravity/2)

# --------------------------------------------------


class Sprite_Pipe(cdkk.SpriteGroup):
    def __init__(self, speed, limits, gap_top, gap_size):
        super().__init__("Pipe")
        self._pipe_t = cdkk.Sprite("PipeTop")
        self._pipe_b = cdkk.Sprite("PipeBottom")
        pipe_h = self._pipe_t.rect.height
        pipe_w = self._pipe_t.rect.width
        xpos = limits.right + pipe_w
        stretch_t = gap_top - pipe_h
        stretch_b = limits.height - gap_top - gap_size - pipe_h
        self._pipe_t.load_image_from_spritesheet("FlappyBird.png", 4, 4, 6,
                                                 img_process=("stretch", [0, 0, stretch_t, 0]))
        self._pipe_b.load_image_from_spritesheet("FlappyBird.png", 4, 4, 5,
                                                 img_process=("stretch", [0, 0, 0, stretch_b]))
        self._pipe_t.rect.bottomleft = (xpos, gap_top)
        self._pipe_b.rect.topleft = (xpos, gap_top+gap_size)
        self.add(self._pipe_t)
        self.add(self._pipe_b)

        pipe_limit = cdkk.cdkkRect(
            limits.left-pipe_w, limits.top, 1, limits.height)
        for s in self.sprites():
            s.set_config("Type", "Pipe")
            s.rect.set_velocity(-speed, 0)
            ev = cdkk.EventManager.gc_event("KillSpriteUUID", uuid=s.uuid)
            limit = cdkk.Physics_Limit(pipe_limit, cdkk.LIMIT_KEEP_OUTSIDE,
                                       cdkk.AT_LIMIT_XY_DO_NOTHING, event=ev)
            s.rect.add_limit(limit)
            s.rect.go()
            s.set_config("auto_move_physics", True)

# --------------------------------------------------


class Manager_FlappyBird(cdkk.SpriteManager):
    def __init__(self, limits, bird_speed, pipe_freq, difficulty):
        super().__init__("FlapyBird Manager")
        self._limits = limits
        self._bird_speed = bird_speed   # Bird speed (gravity)
        self._difficulty = difficulty   # Pipe gap (1..9)
        self._pipe_timer = cdkk.Timer(pipe_freq, cdkk.EVENT_GAME_TIMER_2,
                                      auto_start=False)    # Pipe frequency in seconds

        self._bird = None
        self._pipe_gap = 0
        self.add(cdkk.Sprite_Background("FlappyBackground.png", self._limits),
                 layer=0)

    def event(self, e):
        dealt_with = super().event(e)
        if not dealt_with and e.type == cdkk.EVENT_GAME_CONTROL:
            if e.action == "Flap":
                dealt_with = True
                if self._bird is not None:
                    self._bird.flap()
            elif e.action == "AddPipe":
                dealt_with = True
                if self.game_is_active:
                    gap_top = random.randint(
                        150, self._limits.bottom-self._pipe_gap-150)
                    self.add(Sprite_Pipe(5, self._limits,
                                         gap_top, self._pipe_gap))
        return dealt_with

    def start_game(self):
        super().start_game()
        self._bird = Sprite_Bird(200, self._limits.height/2,
                                 self._bird_speed, self._limits)
        self.add(self._bird)
        self._pipe_gap = int(self._bird.rect.height *
                             (2-0.5*self._difficulty/10))

        self._pipe_timer.start()
        cdkk.EventManager.post_game_control("AddPipe")

    def end_game(self):
        self.remove(self._bird)
        self.kill_sprites_by_desc("Type", "Pipe")
        self._pipe_timer.stop()
        super().end_game()

    def update(self):
        super().update()
        collide = self._bird.collide(self.find_sprites_by_desc("Type", "Pipe"))
        if collide:
            cdkk.EventManager.post_game_control("GameOver")

        for s in self.find_sprites_by_name("PipeTop"):
            if s.rect.right < self._bird.rect.left:
                if s.get_config("UpdateScore", True):
                    s.set_config("UpdateScore", False)
                    cdkk.EventManager.post_game_control(
                        "UpdateScore", score=self._difficulty)

# --------------------------------------------------


class Manager_Scoreboard(cdkk.SM_Scoreboard):
    def __init__(self, game_time):
        score_style = cdkk.stylesheet.style("Scoreboard")
        timer_style = cdkk.stylesheet.style("Scoreboard")
        super().__init__(game_time, score_style=score_style, timer_style=timer_style)
        sb_rect = cdkk.cdkkRect(self.app_boundary.right-200, 10, 200, 40)
        self.timer_text.rect = sb_rect
        self.score_text.rect = sb_rect.move(0, 40)
        self.game_over.text = "You hit a pipe!"

# --------------------------------------------------


class FlappyBirdGame(cdkk.PyGameApp):
    def init(self):
        super().init()

        self.bird_mgr = Manager_FlappyBird(self.boundary, 10, 2, 5)
        self.scoreboard_mgr = Manager_Scoreboard(10)

        self.add_sprite_mgr(self.bird_mgr)
        self.add_sprite_mgr(self.scoreboard_mgr)

        key_map = cdkk.merge_dicts(cdkk.PyGameApp.default_key_map,
                                   {pygame.K_SPACE: "Flap"})
        user_event_map = {
            cdkk.EVENT_GAME_TIMER_1: "GameOver",
            cdkk.EVENT_GAME_TIMER_2: "AddPipe"
        }
        self.event_mgr.event_map(
            key_event_map=key_map, user_event_map=user_event_map)

    def update(self):
        super().update()

# --------------------------------------------------


app_config = {
    "width": 1200, "height": 800,
    "background_fill": "burlywood",
    "caption": "Flappy Bird",
    "auto_start": True,
    "image_path": "ArcadeGames\\Images\\"
}
FlappyBirdGame(app_config).execute()

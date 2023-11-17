from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
import sys
import numpy as np
import pygame as pg
import json

class Main:

    def __init__(self):
        self.create_variables()
        self.load_settings()

    def create_variables(self):
        self.forward_key = StringVar()
        self.right_key = StringVar()
        self.left_key = StringVar()
        self.backward_key = StringVar()
        self.steering = IntVar()
        
        self.master_sound = IntVar()
        self.engine_sound = IntVar()
        self.tire_sound = IntVar()
        self.music_sound = IntVar()
    
    def load_settings(self):
        try:
            with open("settings.json", "r") as file:
                settings = json.load(file)

            self.master_sound.set(settings.get("master_sound"))
            self.engine_sound.set(settings.get("engine_sound"))
            self.tire_sound.set(settings.get("tire_sound"))
            self.music_sound.set(settings.get("music_sound"))
            self.forward_key.set(settings.get("forward_key") or "W")
            self.left_key.set(settings.get("left_key") or "A")
            self.right_key.set(settings.get("right_key") or "D")
            self.backward_key.set(settings.get("backward_key") or "S")
            self.steering.set(settings.get("steering"))

        except FileNotFoundError:
            print("Settings file not found. Using default settings.")

class Game(Main):

    def __init__(self):
        super().__init__()
        pg.init()
        pg.mixer.init()
        self.load_resources()
        self.screen = pg.display.set_mode()
        self.width, self.height = self.screen.get_size()
        self.running = True
        self.first_crossing = True
        self.clock = pg.time.Clock()
        self.acceleration = 0
        self.rot_over_time = 0
        self.hres = 120
        self.halfvres = self.height // 2  
        self.mod = self.hres / 60
        self.posx, self.posy, self.rot = 19.7, 18.15, 4.73
        self.prev_posx, self.prev_posy = self.posx, self.posy
        self.start_ticks = pg.time.get_ticks()

    def run(self):
        while self.running:
            pressed_keys = pg.key.get_pressed()
            self.check_events()
            self.surface()
            self.car()
            self.check_finish_line()
            self.gauge(self.width - 200, self.height - 150)
            self.timer()
            self.minimap()
            self.movement(pressed_keys)
            pg.display.update()

        pg.quit()

    def load_resources(self):
        self.track_border = pg.surfarray.array2d(pg.image.load(r"resources\track1_mask.png"))
        self.map = pg.surfarray.array3d(pg.image.load(r"resources\track1.png"))

        self.car_images = { i: pg.image.load((f"car/frame_{i:02d}.png")) for i in range(1, 10) }
        
        self.sky = pg.image.load(r"resources\skybox.jpg")

        self.tire_screech_sound = pg.mixer.Sound(r"resources\tire.mp3")
        self.eng_sound = pg.mixer.Sound(r"resources\acc_sound.mp3")

    def check_finish_line(self):
        # Define the finish line as a line segment (start and end points)
        finish_line_start = (18.5, 16)
        finish_line_end = (21, 17)

        # Define the car's previous and current positions as a line segment
        car_path_start = (self.prev_posx, self.prev_posy)
        car_path_end = (self.posx, self.posy)

        # Check for intersection
        if self.line_intersects(
            car_path_start, car_path_end, finish_line_start, finish_line_end
        ):
            if not self.first_crossing:  # Save record on the second crossing
                self.save_record()
                self.running = False  # Stop the game
            self.first_crossing = False

    def line_intersects(self, line1_start, line1_end, line2_start, line2_end):
        # Line 1
        x1, y1 = line1_start
        x2, y2 = line1_end

        # Line 2
        x3, y3 = line2_start
        x4, y4 = line2_end

        # Calculate determinants
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0:
            return False  # Lines are parallel

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den

        # Check if intersection point is on both line segments
        return 0 <= t <= 1 and 0 <= u <= 1

    def save_record(self):
        time_taken = (pg.time.get_ticks() - self.start_ticks) / 1000
        last_play = 0

        try:
            with open("race_record.txt", "r") as file:
                lines = file.readlines()
                if lines:
                    # Extracting the play count from the last line
                    last_play_line = lines[-1]
                    last_play = int(
                        last_play_line.split("Play")[1].split(":")[0].strip()
                    )
        except FileNotFoundError:
            pass  # File not found, last_play remains 0

        with open("race_record.txt", "a") as file:
            file.write(f"Play {last_play + 1}: Time taken: {time_taken} seconds\n")

    def car(self):
        offset = 1.5
        frame_index = min(max(int(self.rot_over_time / (0.03 * offset) * 4 + 5), 1), 9)
        car = self.car_images[frame_index]
        car = pg.transform.scale(car, (500, 500))
        self.screen.blit(car, (self.width / 2 - 250, self.height / 2 + 75))

    def check_events(self):
        for event in pg.event.get():
            if (
                event.type == pg.QUIT
                or event.type == pg.KEYDOWN
                and event.key == pg.K_ESCAPE
            ):
                self.running = False

    def update_rotation(self, pressed_keys):
        left_pressed = (
            pressed_keys[pg.K_LEFT]
            or pressed_keys[ord(f"{self.left_key.get()}".lower())]
        )
        right_pressed = (
            pressed_keys[pg.K_RIGHT]
            or pressed_keys[ord(f"{self.right_key.get()}".lower())]
        )

        value = 0.003 * self.steering.get() / 5

        if left_pressed and self.rot_over_time > -0.1:
            self.rot_over_time -= value
        if right_pressed and self.rot_over_time < 0.1:
            self.rot_over_time += value

        if abs(self.rot_over_time) > 0.01:
            self.rot_over_time -= 0.001 * np.sign(self.rot_over_time)
        elif not left_pressed and not right_pressed:
            self.rot_over_time = 0

        if (left_pressed or right_pressed) and abs(self.acceleration) > 2:
            if not self.tire_screech_sound.get_num_channels():
                self.tire_screech_sound.set_volume(self.tire_sound.get())
                self.tire_screech_sound.play()

    def update_acceleration(self, pressed_keys):
        forward_pressed = (
            pressed_keys[pg.K_UP]
            or pressed_keys[ord(f"{self.forward_key.get()}".lower())]
        )
        backward_pressed = (
            pressed_keys[pg.K_DOWN]
            or pressed_keys[ord(f"{self.backward_key.get()}".lower())]
        )

        if forward_pressed and self.acceleration <= 3:
            self.acceleration += 0.01
        elif backward_pressed and self.acceleration >= -3:
            self.acceleration -= 0.01
        elif (
            not forward_pressed
            and not backward_pressed
            and abs(self.acceleration) > 0.001
        ):
            self.acceleration -= 0.005 * np.sign(self.acceleration)
        elif -3 <= self.acceleration >= 3:
            self.acceleration == self.acceleration
        else:
            self.acceleration = 0

        self.eng_sound.set_volume( self.engine_sound.get() / 10 * self.master_sound.get() / 10 * int(self.acceleration) / 3 )
        if (forward_pressed or backward_pressed) and abs(self.acceleration) > 0.1:
            if not self.eng_sound.get_num_channels():
                self.eng_sound.play()

    def update_position(self, et):
        x, y = (
            self.posx + et * np.cos(self.rot) * self.acceleration,
            self.posy + et * np.sin(self.rot) * self.acceleration,
        )
        return x, y

    def limit_race_area(self, x, y):
        if 1 <= x <= 29 and 1 <= y <= 29:
            self.posx, self.posy = x, y

    def check_track_border(self):
        if self.track_border[int(self.posx * 34.13)][int(self.posy * 34.13)] != 0:
            self.acceleration -= 0.01
            fontt = pg.font.SysFont("Terminal", 50)
            text = fontt.render("Do not cross the track", True, "red")
            textRect = text.get_rect()
            textRect.center = (self.width // 2, self.height // 5)
            self.screen.blit(text, textRect)

    def movement(self, pressed_keys):
        self.prev_posx, self.prev_posy = self.posx, self.posy
        et = self.clock.tick() / 500

        self.update_rotation(pressed_keys)
        self.update_acceleration(pressed_keys)

        new_x, new_y = self.update_position(et)
        self.limit_race_area(new_x, new_y)
        self.check_track_border()

        self.rot += self.rot_over_time * self.acceleration
        self.rot = self.rot % (np.pi * 2)

    def gauge(self, x, y):
        col = (255, 0, 0)
        s = abs(self.acceleration / 3 * 260)
        for i in range(0, 29):
            xcos = np.cos(np.radians(140 + i * 9.28))
            ysin = np.sin(np.radians(140 + i * 9.28))
            pg.draw.line(
                self.screen,
                "white",
                (
                    x + (105 if i % 2 == 0 else 110) * xcos,
                    y + (105 if i % 2 == 0 else 110) * ysin,
                ),
                (
                    x + 115 * xcos,
                    y + 115 * ysin,
                ),
                2,
            )
            if i % 2 == 0:
                num = pg.font.SysFont("Terminal", 20)
                km = num.render(f"{i*10}", True, "white")
                trkm = km.get_rect()
                trkm.center = (
                    x + 90 * xcos,
                    y + 90 * ysin,
                )
                self.screen.blit(km, trkm)
        pg.draw.line(
            self.screen,
            "red",
            (x, y),
            (
                x + 100 * np.cos(np.radians(140 + s)),
                y + 100 * np.sin(np.radians(140 + s)),
            ),
            5,
        )
        pg.draw.circle(self.screen, "red", (x, y), 5)

    def timer(self):
        seconds = (pg.time.get_ticks() - self.start_ticks) / 1000
        fontt = pg.font.SysFont("Terminal", 50)
        text = fontt.render(f"Timer: {seconds}", True, "white")
        textRect = text.get_rect()
        textRect.center = (self.width // 2, self.height // 10)
        self.screen.blit(text, textRect)

    def minimap(self):
        
        minimap = pg.transform.scale(pg.image.load(r"resources\minimapt1.png"), (200,200))
        self.screen.blit(minimap, (self.width - 250, 50))
        pg.draw.circle(
            self.screen,
            "white",
            (self.width - 250 + self.posx / 30 * 200, 50 + self.posy / 30 * 200),
            5,
        )

    def surface(self):
        sky = pg.surfarray.array3d(
            pg.transform.scale(self.sky, (360, self.halfvres * 1.5))
        )
        ns = self.halfvres / (
            (self.halfvres + 0.1 - np.linspace(0, self.halfvres, self.halfvres))
        )  # depth
        cos22 = np.cos(
            np.deg2rad(np.linspace(-30, 30, self.hres) / self.mod)
        )  # perspective correction

        shade = 0.4 + 0.6 * (
            np.linspace(0, self.halfvres, self.halfvres) / self.halfvres
        )
        shade = np.dstack((shade, shade, shade))
        frame = np.ones([self.hres, self.halfvres * 2, 3])
        for i in range(self.hres):
            rot_i = self.rot + np.deg2rad(i / self.mod - 30)
            sin, cos, cos2 = (
                np.sin(rot_i),
                np.cos(rot_i),
                np.cos(np.deg2rad(i / self.mod - 30)),
            )
            frame[i][: self.halfvres] = (
                sky[int(np.rad2deg(rot_i) % 360)][: self.halfvres] / 255
            )
            xs, ys = self.posx + ns * cos / cos2, self.posy + ns * sin / cos2
            xxs, yys = (xs / 30 % 1 * 1023).astype("int"), (ys / 30 % 1 * 1023).astype(
                "int"
            )
            frame[i][2 * self.halfvres - len(ns) : 2 * self.halfvres] = (
                shade * self.map[np.flip(xxs), np.flip(yys)] / 255
            )
        surf = pg.surfarray.make_surface(frame * 255)
        surf = pg.transform.scale(surf, (self.width, self.height))
        self.screen.blit(surf, (0, 0))

class Car(Game):

    def __init__(self):
        super().__init__()


class Menu(Main):

    def __init__(self):
        self.root = Tk()
        super().__init__()
        pg.mixer.init()
        self.setup_window()
        self.create_styles()
        self.bind_events()
        self.adjust_variables()
        self.save_settings()
        self.create_main_menu()
        self.create_setting_frame()
        self.setup_music()

    def setup_window(self):
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.attributes("-fullscreen", True)

    def setup_music(self):
        pg.mixer.init() 
        pg.mixer.music.load(r'resources\bg_music.mp3')  
        pg.mixer.music.play(-1) 

    def create_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.theme_settings(
            "default",
            {
                "TFrame": {
                    "configure": {"background": "white"},
                },
                "TButton": {
                    "configure": {"padding": 5, "font": ["Terminal", 40], "background": "white"},
                    "map": {
                        "background": [
                            ("pressed", "!disabled", "white"),
                            ("active", "white"),
                        ],
                        "foreground": [("pressed", "red"), ("active", "blue")],
                    },
                },
                "TNotebook.Tab": {
                    "configure": {"font": ["Terminal", 15], "padding": [100, 10]},
                    "map": {"background": [("selected", "white")]},
                },
                "TNotebook": {"map": {"background": [("selected", "red")]}},
            },
        )

    def bind_events(self):
        self.root.bind("<Alt_R>", self.AltOn)
        self.root.bind("<KeyRelease-Alt_R>", self.AltOff)
        self.root.bind("<Return>", self.changescreen)

    def adjust_variables(self):

        self.engine_sound.trace_add('write', lambda *args: self.save_settings())
        self.tire_sound.trace_add('write', lambda *args: self.save_settings())
        self.master_sound.trace_add('write', lambda *args: self.save_settings())
        self.music_sound.trace_add('write', lambda *args: self.save_settings())
        self.master_sound.trace_add('write', lambda *args: self.adjust_volume())
        self.music_sound.trace_add('write', lambda *args: self.adjust_volume())

        self.steering.trace_add('write', lambda *args: self.save_settings())

    def create_main_menu(self):
        bg = Image.open("resources/bg.png")
 
        resize_image = bg.resize((self.width, self.height))
        self.img = ImageTk.PhotoImage(resize_image)  # Store it as an attribute

        self.cv = Canvas(self.root, width=self.width, height=self.height)
        self.cv.pack(fill="both", expand=True)

        self.cv.create_image(0, 0, image=self.img, anchor="nw")  # Use the attribute here
        self.cv.create_text(
            self.width / 2,
            100,
            text="Gran Bitrismo",
            font=("Terminal", 150),
            anchor="n",
            justify="center",
        )

        start = ttk.Button(self.root, text="Start", command=self.start)
        start.place(x=self.width / 2 - 250, y=300, height=100, width=500)

        setting = ttk.Button(self.root, text="Settings", command=self.to_setting)
        setting.place(x=self.width / 2 - 250, y=500, height=100, width=500)

        exit = ttk.Button(self.root, text="Exit", command=self.quit)
        exit.place(x=self.width / 2 - 250, y=700, height=100, width=500)

    def create_setting_frame(self):
        self.setting_frame = Frame(self.root, width=self.width, height=self.height)
        self.tomain = Button(self.setting_frame, text="To main menu", font=("Terminal", 30), command=self.tomain)

        self.tabControl = ttk.Notebook(self.setting_frame, width=self.width-300, height=self.height-200)

        tab1 = ttk.Frame(self.tabControl)
        tab2 = ttk.Frame(self.tabControl)
        tab3 = ttk.Frame(self.tabControl)
        tab4 = ttk.Frame(self.tabControl)

        self.create_graphics_tab(tab4)
        self.create_controls_tab(tab3)
        self.create_sensitivity_tab(tab2)
        self.create_sound_tab(tab1)

        self.tabControl.add(tab1, text="Sound")
        self.tabControl.add(tab2, text="Sensitivity")
        self.tabControl.add(tab3, text="Control")
        self.tabControl.add(tab4, text="Video")

    def run(self):
        self.root.mainloop()

    def AltOn(self, event):
        self.alt = True

    def AltOff(self, event):
        self.alt = False

    def changescreen(self, event):
        if self.alt:
            self.screen_offset = not self.screen_offset
            self.root.attributes("-fullscreen", self.screen_offset)

    def to_setting(self):
        self.setting_frame.pack()
        self.cv.pack_forget()
        self.tabControl.place(x=140, y=130)
        self.tomain.place(x=50, y=50)

    def tomain(self):
        self.setting_frame.pack_forget()
        self.cv.pack()

    def quit(self):
        sys.exit()

    def create_graphics_tab(self, tab):

        Label(tab, text="Resolution", font=("Terminal", 15)).grid(row=0, column=0, sticky=W, padx=10, pady=10)
        resolution_var = StringVar()
        resolution_choices = ["1920x1080", "1280x720", "800x600"]
        resolution_menu = OptionMenu(tab, resolution_var, *resolution_choices)
        resolution_menu.grid(row=0, column=1, sticky=W)

        fullscreen_var = BooleanVar()
        Checkbutton(tab, text="Fullscreen", variable=fullscreen_var).grid(row=1, column=0, sticky=W, padx=10, pady=10)

    def create_controls_tab(self, tab):

        Label(tab, text="Key Bindings", font=("Terminal", 15)).grid(row=0, column=0, sticky=W, padx=10, pady=10)
        
        Label(tab, text="Forward", font=("Terminal", 15)).grid(row=1, column=0, sticky=W, padx=10, pady=10)
        Button(tab, textvariable=self.forward_key, command=lambda: self.set_key_binding(self.forward_key)).grid(row=1, column=1, sticky=W)

        Label(tab, text="Left", font=("Terminal", 15)).grid(row=2, column=0, sticky=W, padx=10, pady=10)
        Button(tab, textvariable=self.left_key, command=lambda: self.set_key_binding(self.left_key)).grid(row=2, column=1, sticky=W)

        Label(tab, text="Backward", font=("Terminal", 15)).grid(row=3, column=0, sticky=W, padx=10, pady=10)
        Button(tab, textvariable=self.backward_key, command=lambda: self.set_key_binding(self.backward_key)).grid(row=3, column=1, sticky=W)

        Label(tab, text="Right", font=("Terminal", 15)).grid(row=4, column=0, sticky=W, padx=10, pady=10)
        Button(tab, textvariable=self.right_key, command=lambda: self.set_key_binding(self.right_key)).grid(row=4, column=1, sticky=W)

        Button(tab, text="Reset Key Bindings to Default", command=self.reset_key_bindings_to_default).grid(row=7, column=0, columnspan=2, sticky=W+E, padx=10, pady=10)

    def set_key_binding(self, key_var):
        popup = Toplevel(self.root)
        popup.title("Press a key")
        popup.geometry("200x100")
        Label(popup, text="Press a key for the binding").pack(pady=20)

        def on_key_press(event):
            key_var.set(event.keysym)
            self.save_settings()
            popup.destroy()

        popup.bind("<Key>", on_key_press)
        popup.focus_set()

    def create_sound_tab(self, tab):

        scale_length = self.width // 2

        Label(tab, text="Master sound", font=("Terminal", 15), background="white").place(x=50, y=80)
        Scale(tab, from_=0, to=10, variable=self.master_sound, orient=HORIZONTAL, length=scale_length).place(x=200, y=80)

        Label(tab, text="Tire sound", font=("Terminal", 15), background="white").place(x=50, y=160)
        Scale(tab, from_=0, to=10, variable=self.tire_sound, orient=HORIZONTAL, length=scale_length).place(x=200, y=160)

        Label(tab, text="Engine sound", font=("Terminal", 15), background="white").place(x=50, y=240)
        Scale(tab, from_=0, to=10, variable=self.engine_sound, orient=HORIZONTAL, length=scale_length).place(x=200, y=240)

        Label(tab, text="Music", font=("Terminal", 15), background="white").place(x=50, y=320)
        Scale(tab, from_=0, to=10, variable=self.music_sound, orient=HORIZONTAL, length=scale_length).place(x=200, y=320)

    def adjust_volume(self):
        volume_level = self.music_sound.get() / 10.0 * self.master_sound.get() / 10.0
        pg.mixer.music.set_volume(volume_level)

    def create_sensitivity_tab(self, tab):
        steering_sensitivity = Scale(tab, from_=0, to=10, variable=self.steering, orient=HORIZONTAL)
        steering_sensitivity.grid(row=0, column=1, padx=10, pady=10)
        Label(tab, text="Steering Sensitivity", font=("Terminal", 15)).grid(row=0, column=0, sticky=W, padx=10, pady=10)

    def save_settings(self):
        settings = {
            "master_sound": self.master_sound.get(),
            "engine_sound": self.engine_sound.get(),
            "tire_sound": self.tire_sound.get(),
            "music_sound": self.music_sound.get(),
            "forward_key": self.forward_key.get(),
            "left_key": self.left_key.get(),
            "right_key": self.right_key.get(),
            "backward_key": self.backward_key.get(),
            "steering" : self.steering.get()
        }
        with open("settings.json", "w") as file:
            json.dump(settings, file)

    def reset_key_bindings_to_default(self):
        default_settings = self.read_default_settings()
        self.forward_key.set(default_settings['forward_key'])
        self.left_key.set(default_settings['left_key'])
        self.backward_key.set(default_settings['backward_key'])
        self.right_key.set(default_settings['right_key'])
        self.save_settings()

    @staticmethod
    def read_default_settings():
        with open("default_settings.json", "r") as file:
            return json.load(file)

    def create_track_selection_screen(self):
        self.cv.pack_forget()
        self.track_selection_frame = Frame(self.root, width=self.width, height=self.height)
        
        Button(self.track_selection_frame, text="Track 1", command=lambda: self.load_game("track1")).place(x=140, y=130)
        # Button(self.track_selection_frame, text="Track 2", command=lambda: self.load_game("track2")).grid(row=1, column=0, padx=10, pady=10)
        # Button(self.track_selection_frame, text="Track 3", command=lambda: self.load_game("track3")).grid(row=2, column=0, padx=10, pady=10)

        Button(self.track_selection_frame, text="Back", command=self.back_to_main_menu).place(x=50, y=50)

    def start(self):
        self.root.destroy()
        # self.create_track_selection_screen()
        # self.track_selection_frame.pack()

    def load_game(self, track):
        print(f"Loading game with {track}")

    def back_to_main_menu(self):
        self.track_selection_frame.destroy()
        self.cv.pack()


if __name__ == "__main__":
    
    while True:
        menu = Menu()
        game = Game()
        menu.run()
        game.run()

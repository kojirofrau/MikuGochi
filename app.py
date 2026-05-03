import random
import base64
import ctypes
import json
import subprocess
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


WINDOW_WIDTH = 512
WINDOW_HEIGHT = 640
CHARACTER_AREA_HEIGHT = 340
CHARACTER_AREA_BG = "#c8f4ec"
TOP_BUTTON_SIZE = 32
MENU_BUTTON_WIDTH = 64
STATUS_CHECK_INTERVAL_MS = 20_000
STATUS_CHANGE_CHANCE = 0.6
DEATH_COUNTDOWN_SECONDS = 30
SAVE_FILE = Path(__file__).with_name("save.json")
NOTIFICATION_SOUND_FILE = Path(__file__).with_name("assets") / "audio" / "notification_1.mp3"
TIMER_SOUND_FILE = Path(__file__).with_name("assets") / "audio" / "notification_timer_1.mp3"
SOUNDTRACK_FILES = [
    Path(__file__).with_name("assets") / "audio" / "soundtrack_beautiful_ruin.mp3",
    Path(__file__).with_name("assets") / "audio" / "soundtrack_love_wa_survival.mp3",
    Path(__file__).with_name("assets") / "audio" / "soundtrack_monomi-sensei_no_kyouiku_jisshuu.mp3",
    Path(__file__).with_name("assets") / "audio" / "soundtrack_re__beautiful_morning.mp3",
]
WEATHER_BACKGROUND_SPRITESHEET = (
    Path(__file__).with_name("assets")
    / "weather"
    / "background"
    / "weather_background_spritesheet.png"
)
WEATHER_EFFECTS_SPRITESHEET = (
    Path(__file__).with_name("assets")
    / "weather"
    / "effects"
    / "weather_effects_spritesheet.png"
)
NOTIFICATION_SOUND_VOLUME = 500
SOUNDTRACK_VOLUME = NOTIFICATION_SOUND_VOLUME // 2
NOTIFICATION_SOUND_CLOSE_DELAY_MS = 5_000
SOUNDTRACK_MONITOR_INTERVAL_MS = 2_000
SOUNDTRACK_FALLBACK_DURATION_MS = 180_000
DAY_DURATION_SECONDS = 120
NIGHT_DURATION_SECONDS = 60
WEATHER_CYCLE_SECONDS = 120
WEATHER_ANIMATION_INTERVAL_MS = 450
WEATHER_FRAME_COUNT = 6
MAX_STATUS_SEVERITY = 3
MAX_ENERGY = 100
CARE_ACTION_ENERGY_COST = 5
REST_ENERGY_GAIN = 10
REST_STATUS_TRIGGERS = 3
STARTING_MONEY = 0
WORK_MONEY_GAIN = 2000
WORK_ENERGY_COST = 10
WORK_STATUS_TRIGGERS = 3
INVENTORY_ITEM_LIMIT = 3
REPEATED_ACTION_LIMIT = 2
LEADERBOARD_LIMIT = 5
SCORE_PER_SURVIVAL_MINUTE = 10
SCORE_PER_CARE_ACTION = 50
SCORE_PER_REST = 15
SCORE_PER_WORK = 25
SCORE_PER_ITEM = 20
SCORE_MONEY_DIVISOR = 100


CHARACTERS = {
    "miku": {"name": "Hatsune Miku", "short_name": "Miku"},
    "kaito": {"name": "Kaito", "short_name": "Kaito"},
    "rin": {"name": "Kagamine Rin", "short_name": "Rin"},
    "len": {"name": "Kagamine Len", "short_name": "Len"},
    "luka": {"name": "Megurine Luka", "short_name": "Luka"},
    "meiko": {"name": "Meiko", "short_name": "Meiko"},
}
DEFAULT_CHARACTER_KEY = "miku"
STARTING_WEATHER = "sunny"
WEATHER_OPTIONS = ("sunny", "cloudy", "rainy")
WEATHER_SPRITE_ROWS = {
    ("sunny", "day"): 0,
    ("sunny", "night"): 1,
    ("cloudy", "day"): 2,
    ("cloudy", "night"): 3,
    ("rainy", "day"): 4,
    ("rainy", "night"): 5,
}
WEATHER_EFFECT_OPTIONS = {
    "sunny": (None, "sakura_petals"),
    "cloudy": (None,),
    "rainy": ("raindrops", "snow"),
}
WEATHER_EFFECT_SPRITE_ROWS = {
    "raindrops": 0,
    "sakura_petals": 1,
    "snow": 2,
}


ITEMS = {
    "energy_drink": {
        "name": "Energy Drink",
        "price": 500,
        "description": "Restores 5 energy.",
        "effect": {"energy": 5},
    },
    "medicine": {
        "name": "Medicine",
        "price": 1000,
        "description": "Removes 2 points from Disease.",
        "effect": {"status": "sickness", "amount": 2},
    },
    "noodles": {
        "name": "Noodles",
        "price": 500,
        "description": "Removes 2 hunger.",
        "effect": {"status": "hunger", "amount": 2},
    },
    "magazine": {
        "name": "Magazine",
        "price": 750,
        "description": "Removes 2 laziness.",
        "effect": {"status": "lazy", "amount": 2},
    },
}

DEFAULT_INVENTORY = {key: 0 for key in ITEMS}


DEFAULT_STATUSES = {
    "hunger": 0,
    "sickness": 0,
    "dirty_room": 0,
    "lazy": 0,
}


DEFAULT_STATISTICS = {
    "games_played": 0,
    "character_deaths": 0,
    "times_fed": 0,
    "times_healed": 0,
    "times_cleaned": 0,
    "times_entertained": 0,
}


DEFAULT_GAME_STATISTICS = {
    "started_at": 0,
    "times_fed": 0,
    "times_healed": 0,
    "times_cleaned": 0,
    "times_entertained": 0,
    "times_rested": 0,
    "times_worked": 0,
    "items_bought": 0,
    "items_used": 0,
    "money_earned": 0,
}


class MikuGochiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("MikuGochi Prototype")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.statuses = DEFAULT_STATUSES.copy()
        self.statistics = DEFAULT_STATISTICS.copy()
        self.current_game_statistics = self._new_game_statistics()
        self.last_game_statistics: dict[str, object] | None = None
        self.leaderboard: list[dict[str, object]] = []
        self.energy = MAX_ENERGY
        self.money = STARTING_MONEY
        self.inventory = DEFAULT_INVENTORY.copy()
        self.has_save = SAVE_FILE.exists()
        self.game_started = False
        self.game_view_mode = "normal"
        self.character_dead = False
        self.current_character_key: str | None = None
        self.current_weather = STARTING_WEATHER
        self.current_weather_effect: str | None = self._choose_weather_effect(self.current_weather)
        self.weather_cycle_index = 0
        self.weather_animation_frame = 0
        self.last_repeated_action: str | None = None
        self.repeated_action_count = 0
        self.sound_enabled = True
        self.status_roll_job: str | None = None
        self.death_countdown_job: str | None = None
        self.death_countdown_remaining: int | None = None
        self.weather_animation_job: str | None = None
        self.sound_close_job: str | None = None
        self.soundtrack_next_job: str | None = None
        self.soundtrack_monitor_job: str | None = None
        self.current_soundtrack: Path | None = None
        self.soundtrack_backend: str | None = None
        self.pygame_mixer = None
        self.soundtrack_process: subprocess.Popen | None = None
        self.screen_frame: tk.Frame | ttk.Frame | None = None
        self.tooltip_window: tk.Toplevel | None = None

        self.status_labels: dict[str, ttk.Label] = {}
        self.shop_buttons: dict[str, ttk.Button] = {}
        self.character_scene_canvas: tk.Canvas | None = None
        self.energy_label: ttk.Label | None = None
        self.money_label: ttk.Label | None = None
        self.score_label: ttk.Label | None = None
        self.mood_label: ttk.Label | None = None
        self.character_state_label: ttk.Label | None = None
        self.death_timer_label: ttk.Label | None = None
        self.sound_buttons: list[ttk.Button] = []
        self.sound_images = self._create_sound_images()
        self.weather_background_frames = self._load_weather_background_frames()
        self.weather_effect_frames = self._load_weather_effect_frames()

        self.configure(bg="#f6f7fb")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_save()
        self._show_menu()
        self.after(100, self._ensure_soundtrack_playing)

    def _clear_screen(self) -> None:
        if self.status_roll_job is not None:
            try:
                self.after_cancel(self.status_roll_job)
            except tk.TclError:
                pass
            self.status_roll_job = None

        self._cancel_death_countdown()
        self._cancel_weather_animation()

        if self.screen_frame is not None:
            self.screen_frame.destroy()
            self.screen_frame = None

        self.sound_buttons = []
        self.shop_buttons = {}
        self.character_scene_canvas = None
        self.energy_label = None
        self.money_label = None
        self.score_label = None
        self.mood_label = None
        self.character_state_label = None
        self.death_timer_label = None
        self._hide_tooltip()

    def _show_menu(
        self,
        show_new_game_warning: bool = False,
        show_reset_warning: bool = False,
    ) -> None:
        self._clear_screen()
        show_new_game_warning = show_new_game_warning and self.has_save

        frame = tk.Frame(self, bg="#f6f7fb", padx=44, pady=44)
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        self._add_reset_button(frame, x=8, y=0)
        self._add_sound_button(frame, x=-8, y=0)

        ttk.Label(
            frame,
            text="MikuGochi",
            anchor="center",
            font=("Segoe UI", 28, "bold"),
        ).pack(fill="x", pady=(28, 8))

        ttk.Label(
            frame,
            text="Take care of your current companion, start fresh, or review your records.",
            anchor="center",
            wraplength=360,
        ).pack(fill="x", pady=(0, 34))

        continue_button = ttk.Button(frame, text="Continue", command=self.continue_game)
        continue_button.pack(fill="x", pady=6, ipady=6)
        if not self.has_save or self.character_dead:
            continue_button.state(["disabled"])

        if show_new_game_warning:
            warning_frame = ttk.Frame(frame, padding=(0, 4, 0, 0))
            warning_frame.pack(fill="x")

            ttk.Label(
                warning_frame,
                text="Starting a new game will delete the current save. Continue?",
                anchor="center",
                wraplength=360,
            ).pack(fill="x", pady=(0, 8))

            choice_frame = ttk.Frame(warning_frame)
            choice_frame.pack(fill="x", pady=6)
            choice_frame.columnconfigure(0, weight=1, uniform="new_game_choice")
            choice_frame.columnconfigure(1, weight=1, uniform="new_game_choice")

            ttk.Button(choice_frame, text="Continue", command=self._start_new_game).grid(
                row=0,
                column=0,
                padx=(0, 4),
                sticky="ew",
                ipady=6,
            )
            ttk.Button(choice_frame, text="Cancel", command=self._show_menu).grid(
                row=0,
                column=1,
                padx=(4, 0),
                sticky="ew",
                ipady=6,
            )
        else:
            ttk.Button(frame, text="New Game", command=self.new_game).pack(fill="x", pady=6, ipady=6)

        if show_reset_warning:
            warning_frame = ttk.Frame(frame, padding=(0, 10, 0, 0))
            warning_frame.pack(fill="x")

            ttk.Label(
                warning_frame,
                text="Reset progress will delete the current save and all statistics. Continue?",
                anchor="center",
                wraplength=360,
            ).pack(fill="x", pady=(0, 8))

            choice_frame = ttk.Frame(warning_frame)
            choice_frame.pack(fill="x", pady=6)
            choice_frame.columnconfigure(0, weight=1, uniform="reset_choice")
            choice_frame.columnconfigure(1, weight=1, uniform="reset_choice")

            ttk.Button(choice_frame, text="Reset", command=self._reset_progress).grid(
                row=0,
                column=0,
                padx=(0, 4),
                sticky="ew",
                ipady=6,
            )
            ttk.Button(choice_frame, text="Cancel", command=self._show_menu).grid(
                row=0,
                column=1,
                padx=(4, 0),
                sticky="ew",
                ipady=6,
            )

        ttk.Button(frame, text="Statistics", command=self._show_statistics).pack(fill="x", pady=6, ipady=6)
        ttk.Button(frame, text="Top Scores", command=self._show_top_scores).pack(fill="x", pady=6, ipady=6)
        ttk.Button(frame, text="Close", command=self._on_close).pack(fill="x", pady=6, ipady=6)

    def _show_game(self, mode: str = "normal") -> None:
        self._clear_screen()
        self.game_started = True
        self.game_view_mode = mode
        self.status_labels = {}

        frame = tk.Frame(self, bg="#f6f7fb")
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        character_frame = tk.Frame(
            frame,
            width=WINDOW_WIDTH,
            height=CHARACTER_AREA_HEIGHT,
            bg=CHARACTER_AREA_BG,
            highlightbackground="#c8ccd6",
            highlightthickness=1,
        )
        character_frame.pack_propagate(False)
        character_frame.pack(fill="x", side="top")

        self.character_scene_canvas = tk.Canvas(
            character_frame,
            width=WINDOW_WIDTH,
            height=CHARACTER_AREA_HEIGHT,
            bg=CHARACTER_AREA_BG,
            highlightthickness=0,
        )
        self.character_scene_canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self._draw_character_scene()

        self._add_menu_button(character_frame, x=-12, y=12)
        self._add_sound_button(character_frame, x=-(12 + MENU_BUTTON_WIDTH + 8), y=12)

        self.energy_label = ttk.Label(
            character_frame,
            text=f"Energy: {self.energy}/{MAX_ENERGY}",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            background=CHARACTER_AREA_BG,
        )
        self.energy_label.place(x=14, y=14, anchor="nw")

        self.money_label = ttk.Label(
            character_frame,
            text=f"Money: {self.money}¥",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            background=CHARACTER_AREA_BG,
        )
        self.money_label.place(x=14, y=38, anchor="nw")

        self.score_label = ttk.Label(
            character_frame,
            text=f"Score: {self._current_score()}",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            background=CHARACTER_AREA_BG,
        )
        self.score_label.place(x=14, y=62, anchor="nw")

        self.mood_label = ttk.Label(
            character_frame,
            text="Mood: Excellent",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            background=CHARACTER_AREA_BG,
        )
        self.mood_label.place(x=14, rely=1.0, y=-18, anchor="sw")

        self.death_timer_label = ttk.Label(
            character_frame,
            text="",
            anchor="e",
            font=("Segoe UI", 11, "bold"),
            foreground="#b3261e",
            background=CHARACTER_AREA_BG,
        )
        self.death_timer_label.place(relx=1.0, x=-14, rely=1.0, y=-18, anchor="se")

        controls_frame = ttk.Frame(frame, padding=(16, 14, 16, 12))
        controls_frame.pack(fill="both", expand=True)

        status_frame = ttk.Frame(controls_frame)
        status_frame.pack(fill="x")

        self._add_status(status_frame, "hunger", "Hunger", 0)
        self._add_status(status_frame, "sickness", "Health", 1)
        self._add_status(status_frame, "dirty_room", "Dirt", 2)
        self._add_status(status_frame, "lazy", "Lazy", 3)

        if mode == "konbini":
            self._add_konbini_controls(controls_frame)
        elif mode == "inventory":
            self._add_inventory_controls(controls_frame)
        else:
            self._add_normal_game_controls(controls_frame)

        self.feedback_label = ttk.Label(
            controls_frame,
            text="All good for now.",
            anchor="center",
        )
        self.feedback_label.pack(fill="x", pady=(16, 0))

        self._refresh_status_ui()
        self._schedule_weather_animation()
        if mode == "normal":
            self._update_death_countdown()
            self._schedule_status_roll()

    def _show_statistics(self) -> None:
        self._clear_screen()

        frame = tk.Frame(self, bg="#f6f7fb", padx=32, pady=24)
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        self._add_menu_button(frame, x=-8, y=0)
        self._add_sound_button(frame, x=-(8 + MENU_BUTTON_WIDTH + 8), y=0)

        ttk.Label(
            frame,
            text="Statistics",
            anchor="center",
            font=("Segoe UI", 24, "bold"),
        ).pack(fill="x", pady=(34, 22))

        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill="x", pady=(0, 22))

        rows = [
            ("Total games played", self.statistics["games_played"]),
            ("Character deaths", self.statistics["character_deaths"]),
            ("Current score", self._current_score()),
            ("Current money", f"{self.money}¥"),
            ("Times fed", self.statistics["times_fed"]),
            ("Times healed", self.statistics["times_healed"]),
            ("Times cleaned", self.statistics["times_cleaned"]),
            ("Times entertained", self.statistics["times_entertained"]),
        ]

        if self.last_game_statistics is not None:
            rows.extend(
                [
                    ("Last score", self.last_game_statistics["score"]),
                    ("Last survival minutes", self.last_game_statistics["survived_minutes"]),
                    ("Last times fed", self.last_game_statistics["times_fed"]),
                    ("Last times healed", self.last_game_statistics["times_healed"]),
                    ("Last times cleaned", self.last_game_statistics["times_cleaned"]),
                    ("Last times entertained", self.last_game_statistics["times_entertained"]),
                ]
            )

        for row, (label, value) in enumerate(rows):
            stats_frame.columnconfigure(0, weight=1)
            stats_frame.columnconfigure(1, weight=0)
            ttk.Label(stats_frame, text=label).grid(row=row, column=0, sticky="w", pady=7)
            ttk.Label(stats_frame, text=str(value), font=("Segoe UI", 11, "bold")).grid(
                row=row,
                column=1,
                sticky="e",
                pady=7,
            )

        ttk.Label(
            frame,
            text="Progress and statistics are saved when returning to the menu or closing the app.",
            anchor="center",
            wraplength=400,
        ).pack(fill="x", pady=(8, 0))

    def _show_top_scores(self) -> None:
        self._clear_screen()

        frame = tk.Frame(self, bg="#f6f7fb", padx=32, pady=24)
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        self._add_menu_button(frame, x=-8, y=0)
        self._add_sound_button(frame, x=-(8 + MENU_BUTTON_WIDTH + 8), y=0)

        ttk.Label(
            frame,
            text="Top Scores",
            anchor="center",
            font=("Segoe UI", 24, "bold"),
        ).pack(fill="x", pady=(34, 22))

        scores_frame = ttk.Frame(frame)
        scores_frame.pack(fill="x", pady=(0, 20))
        headers = ("#", "Character", "Score", "Minutes", "Money")
        for column in range(len(headers)):
            scores_frame.columnconfigure(column, weight=1 if column == 1 else 0)
        for column, header in enumerate(headers):
            ttk.Label(scores_frame, text=header, font=("Segoe UI", 10, "bold")).grid(
                row=0,
                column=column,
                sticky="e" if column else "w",
                padx=(0, 12),
                pady=(0, 8),
            )

        if not self.leaderboard:
            ttk.Label(
                scores_frame,
                text="No scores yet. They are recorded after a game over.",
                anchor="center",
            ).grid(row=1, column=0, columnspan=len(headers), sticky="ew", pady=24)
        else:
            for row, entry in enumerate(self.leaderboard, start=1):
                values = (
                    row,
                    self._character_short_name_for(entry.get("character")),
                    entry["score"],
                    entry["survived_minutes"],
                    f"{entry['money']}¥",
                )
                for column, value in enumerate(values):
                    ttk.Label(
                        scores_frame,
                        text=str(value),
                        font=("Segoe UI", 11, "bold") if column == 2 else ("Segoe UI", 10),
                    ).grid(
                        row=row,
                        column=column,
                        sticky="e" if column else "w",
                        padx=(0, 12),
                        pady=7,
                    )

        ttk.Label(
            frame,
            text="Score = survival time, care actions, work, items, and total money earned.",
            anchor="center",
            wraplength=400,
        ).pack(fill="x", pady=(8, 0))

    def _show_death_screen(self) -> None:
        self._clear_screen()

        frame = tk.Frame(self, bg="#f6f7fb", padx=36, pady=28)
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        self._add_sound_button(frame, x=-8, y=0)

        ttk.Label(
            frame,
            text="Game Over",
            anchor="center",
            font=("Segoe UI", 24, "bold"),
        ).pack(fill="x", pady=(28, 10))

        ttk.Label(
            frame,
            text=f"{self._character_name()} could not keep going.",
            anchor="center",
        ).pack(fill="x", pady=(0, 20))

        stats = self.last_game_statistics or {
            "character": self._character_key(),
            "survived_minutes": self._current_survival_minutes(),
            "money": self.money,
            "times_fed": self.current_game_statistics["times_fed"],
            "times_healed": self.current_game_statistics["times_healed"],
            "times_cleaned": self.current_game_statistics["times_cleaned"],
            "times_entertained": self.current_game_statistics["times_entertained"],
            "times_rested": self.current_game_statistics["times_rested"],
            "times_worked": self.current_game_statistics["times_worked"],
            "items_bought": self.current_game_statistics["items_bought"],
            "items_used": self.current_game_statistics["items_used"],
            "money_earned": self.current_game_statistics["money_earned"],
        }
        stats["score"] = self._calculate_score(stats)

        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=0)

        rows = [
            ("Character", self._character_name_for(stats.get("character"))),
            ("Score", stats["score"]),
            ("Survived minutes", stats["survived_minutes"]),
            ("Money", f"{stats['money']}¥"),
            ("Money earned", f"{stats['money_earned']}¥"),
            ("Times fed", stats["times_fed"]),
            ("Times healed", stats["times_healed"]),
            ("Times cleaned", stats["times_cleaned"]),
            ("Times entertained", stats["times_entertained"]),
        ]

        for row, (label, value) in enumerate(rows):
            ttk.Label(stats_frame, text=label).grid(row=row, column=0, sticky="w", pady=7)
            ttk.Label(stats_frame, text=str(value), font=("Segoe UI", 11, "bold")).grid(
                row=row,
                column=1,
                sticky="e",
                pady=7,
            )

        ttk.Button(frame, text="New Game", command=self._start_new_game).pack(fill="x", pady=6, ipady=6)
        ttk.Button(frame, text="Menu", command=self._save_and_show_menu).pack(fill="x", pady=6, ipady=6)

    def _add_status(self, parent: ttk.Frame, key: str, label: str, column: int) -> None:
        parent.columnconfigure(column, weight=1, uniform="status")

        frame = ttk.Frame(parent, padding=(4, 0))
        frame.grid(row=0, column=column, sticky="nsew")

        icon = ttk.Label(frame, text="OK", anchor="center", font=("Segoe UI", 14, "bold"))
        icon.pack(fill="x")

        text = ttk.Label(frame, text=label, anchor="center")
        text.pack(fill="x", pady=(4, 0))

        self.status_labels[key] = icon

    def _add_button(
        self,
        parent: ttk.Frame,
        label: str,
        command: callable,
        column: int,
    ) -> None:
        parent.columnconfigure(column, weight=1, uniform="button")
        button = ttk.Button(parent, text=label, command=command)
        button.grid(row=0, column=column, padx=4, sticky="ew")

    def _add_normal_game_controls(self, parent: ttk.Frame) -> None:
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(18, 0))

        self._add_button(button_frame, "Feed", self.feed, 0)
        self._add_button(button_frame, "Heal", self.heal, 1)
        self._add_button(button_frame, "Clean", self.clean, 2)
        self._add_button(button_frame, "Entertain", self.entertain, 3)

        rest_frame = ttk.Frame(parent)
        rest_frame.pack(fill="x", pady=(10, 0))
        rest_frame.columnconfigure(0, weight=1, uniform="recovery")
        rest_frame.columnconfigure(1, weight=1, uniform="recovery")
        ttk.Button(rest_frame, text="Rest", command=self.rest).grid(
            row=0,
            column=0,
            padx=(0, 4),
            sticky="ew",
        )
        ttk.Button(rest_frame, text="Go to Work", command=self.go_to_work).grid(
            row=0,
            column=1,
            padx=(4, 0),
            sticky="ew",
        )

        visit_frame = ttk.Frame(parent)
        visit_frame.pack(fill="x", pady=(10, 0))
        visit_frame.columnconfigure(0, weight=1, uniform="visit")
        visit_frame.columnconfigure(1, weight=1, uniform="visit")
        ttk.Button(visit_frame, text="Konbini", command=self.open_konbini).grid(
            row=0,
            column=0,
            padx=(0, 4),
            sticky="ew",
        )
        ttk.Button(visit_frame, text="Inventory", command=self.open_inventory).grid(
            row=0,
            column=1,
            padx=(4, 0),
            sticky="ew",
        )

    def _add_konbini_controls(self, parent: ttk.Frame) -> None:
        shop_frame = ttk.Frame(parent)
        shop_frame.pack(fill="x", pady=(18, 0))
        for column in range(2):
            shop_frame.columnconfigure(column, weight=1, uniform="shop")

        for index, key in enumerate(ITEMS):
            item = ITEMS[key]
            count = self.inventory.get(key, 0)
            button = ttk.Button(
                shop_frame,
                text=f"{item['name']} {item['price']}¥ ({count}/{INVENTORY_ITEM_LIMIT})",
                command=lambda item_key=key: self.buy_item(item_key),
            )
            button.grid(
                row=index // 2,
                column=index % 2,
                padx=4,
                pady=4,
                sticky="ew",
            )
            if count >= INVENTORY_ITEM_LIMIT:
                button.state(["disabled"])
            self.shop_buttons[key] = button
            self._bind_tooltip(button, item["description"])

        ttk.Button(parent, text="Return", command=self.return_to_game).pack(fill="x", pady=(14, 0))

    def _add_inventory_controls(self, parent: ttk.Frame) -> None:
        inventory_frame = ttk.Frame(parent)
        inventory_frame.pack(fill="x", pady=(18, 0))
        for column in range(2):
            inventory_frame.columnconfigure(column, weight=1, uniform="inventory")

        for index, key in enumerate(ITEMS):
            item = ITEMS[key]
            count = self.inventory.get(key, 0)
            button = ttk.Button(
                inventory_frame,
                text=f"{item['name']} x{count}",
                command=lambda item_key=key: self.use_item(item_key),
            )
            button.grid(
                row=index // 2,
                column=index % 2,
                padx=4,
                pady=4,
                sticky="ew",
            )
            if count <= 0:
                button.state(["disabled"])
            self._bind_tooltip(button, item["description"])

        ttk.Button(parent, text="Return", command=self.return_to_game).pack(fill="x", pady=(14, 0))

    def _bind_tooltip(self, widget: tk.Widget, text: str) -> None:
        widget.bind("<Enter>", lambda event: self._show_tooltip(event, text))
        widget.bind("<Leave>", lambda _event: self._hide_tooltip())

    def _show_tooltip(self, event: tk.Event, text: str) -> None:
        self._hide_tooltip()
        self.tooltip_window = tk.Toplevel(self)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

        label = ttk.Label(
            self.tooltip_window,
            text=text,
            padding=(8, 5),
            relief="solid",
            borderwidth=1,
            background="#fffbe8",
            wraplength=220,
        )
        label.pack()

    def _hide_tooltip(self) -> None:
        if self.tooltip_window is not None:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None

    def _add_sound_button(self, parent: tk.Frame | ttk.Frame, x: int, y: int) -> None:
        button = ttk.Button(parent, image=self._sound_button_image(), command=self._toggle_sound)
        self._place_top_button(button, x, y, TOP_BUTTON_SIZE)
        self.sound_buttons.append(button)

    def _add_menu_button(self, parent: tk.Frame | ttk.Frame, x: int, y: int) -> None:
        button = ttk.Button(parent, text="Menu", command=self._save_and_show_menu)
        self._place_top_button(button, x, y, MENU_BUTTON_WIDTH)

    def _add_reset_button(self, parent: tk.Frame | ttk.Frame, x: int, y: int) -> None:
        button = ttk.Button(parent, text="Reset", command=self._show_reset_warning)
        button.place(x=x, y=y, width=MENU_BUTTON_WIDTH, height=TOP_BUTTON_SIZE, anchor="nw")

    def _place_top_button(self, button: ttk.Button, x: int, y: int, width: int) -> None:
        button.place(
            relx=1.0,
            x=x,
            y=y,
            width=width,
            height=TOP_BUTTON_SIZE,
            anchor="ne",
        )

    def _toggle_sound(self) -> None:
        self.sound_enabled = not self.sound_enabled
        if self.sound_enabled and self.death_countdown_remaining is not None:
            self._play_timer_sound()
        else:
            self._close_timer_sound()
        if self.sound_enabled:
            self._ensure_soundtrack_playing()
        else:
            self._close_soundtrack()
        self._refresh_sound_buttons()
        self._save_progress()

    def _refresh_sound_buttons(self) -> None:
        for button in self.sound_buttons:
            button.configure(image=self._sound_button_image())

    def _sound_button_image(self) -> tk.PhotoImage:
        return self.sound_images["on" if self.sound_enabled else "off"]

    def _schedule_status_roll(self) -> None:
        self.status_roll_job = self.after(STATUS_CHECK_INTERVAL_MS, self._roll_random_status)

    def _reset_status_roll_timer(self) -> None:
        if self.status_roll_job is not None:
            try:
                self.after_cancel(self.status_roll_job)
            except tk.TclError:
                pass
            self.status_roll_job = None

        if not self.character_dead:
            self._schedule_status_roll()

    def _roll_random_status(self) -> None:
        if not self._try_worsen_random_status():
            self.feedback_label.configure(text="Nothing changed for now.")
            self._refresh_status_ui()
            self._save_progress()

        self._update_death_countdown()

        if not self.character_dead:
            self._schedule_status_roll()

    def _try_worsen_random_status(self) -> bool:
        if random.random() >= STATUS_CHANGE_CHANCE:
            return False

        return self._worsen_random_status()

    def _worsen_random_status(self) -> bool:
        available_statuses = [
            key for key, severity in self.statuses.items() if severity < MAX_STATUS_SEVERITY
        ]

        if available_statuses:
            key = random.choice(available_statuses)
            self.statuses[key] += 1
            self.feedback_label.configure(
                text=f"{self._display_name(key)} increased to {self.statuses[key]}/{MAX_STATUS_SEVERITY}."
            )
            self._refresh_status_ui()
            self._play_notification_sound()
            self._save_progress()
            return True

        return False

    def _refresh_status_ui(self) -> None:
        self._update_weather_cycle()
        self._draw_character_scene()

        for key, label in self.status_labels.items():
            severity = self.statuses[key]
            label.configure(text="OK" if severity == 0 else f"{severity}/{MAX_STATUS_SEVERITY}")

        if self.energy_label is not None:
            self.energy_label.configure(text=f"Energy: {self.energy}/{MAX_ENERGY}")

        if self.money_label is not None:
            self.money_label.configure(text=f"Money: {self.money}¥")

        if self.score_label is not None:
            self.score_label.configure(text=f"Score: {self._current_score()}")

        if self.mood_label is not None:
            self.mood_label.configure(text=f"Mood: {self._current_mood()}")

        if self.character_state_label is not None:
            self.character_state_label.configure(text=self._character_state_text())

        if self.death_timer_label is not None:
            if self.death_countdown_remaining is None:
                self.death_timer_label.configure(text="")
            else:
                self.death_timer_label.configure(text=f"Danger: {self.death_countdown_remaining}s")

    def _draw_character_scene(self) -> None:
        canvas = self.character_scene_canvas
        if canvas is None:
            return

        canvas.delete("scene")
        layers = self._character_scene_layers()

        for layer in layers:
            if layer["kind"] == "weather":
                image = self._current_weather_image()
                if image is None:
                    canvas.create_rectangle(
                        0,
                        0,
                        WINDOW_WIDTH,
                        CHARACTER_AREA_HEIGHT,
                        fill=CHARACTER_AREA_BG,
                        outline="",
                        tags=("scene",),
                    )
                    canvas.create_text(
                        WINDOW_WIDTH // 2,
                        104,
                        text=layer["text"],
                        anchor="center",
                        fill="#263238",
                        font=("Segoe UI", 12, "bold"),
                        tags=("scene",),
                    )
                else:
                    canvas.create_image(0, 0, image=image, anchor="nw", tags=("scene",))
            elif layer["kind"] == "weather_effect":
                image = self._current_weather_effect_image()
                if image is not None:
                    canvas.create_image(0, 0, image=image, anchor="nw", tags=("scene",))
            elif layer["kind"] == "text":
                canvas.create_text(
                    layer["x"],
                    layer["y"],
                    text=layer["text"],
                    anchor=layer.get("anchor", "center"),
                    fill=layer.get("color", "#263238"),
                    font=layer.get("font", ("Segoe UI", 13, "bold")),
                    tags=("scene",),
                )
            elif layer["kind"] == "panel":
                canvas.create_rectangle(
                    layer["x1"],
                    layer["y1"],
                    layer["x2"],
                    layer["y2"],
                    fill=layer["fill"],
                    outline=layer["outline"],
                    tags=("scene",),
                )
                canvas.create_text(
                    layer["x"],
                    layer["y"],
                    text=layer["text"],
                    anchor="center",
                    fill=layer.get("color", "#263238"),
                    font=layer.get("font", ("Segoe UI", 13, "bold")),
                    tags=("scene",),
                )

    def _character_scene_layers(self) -> list[dict[str, object]]:
        time_name = self._scene_time_name()
        weather_name = self.current_weather.title()
        location = "Conbini sprite" if self.game_view_mode == "konbini" else "Room sprite"
        trash_text = f"Trash layer: Dirt {self.statuses['dirty_room']}/{MAX_STATUS_SEVERITY}"
        actor = "Vendor" if self.game_view_mode == "konbini" else "Character"

        return [
            {
                "kind": "weather",
                "text": f"Layer 1: Weather sprite - {time_name.title()}, {weather_name}",
            },
            {
                "kind": "weather_effect",
            },
            {
                "kind": "panel",
                "text": f"Layer 3: {location}",
                "x1": 76,
                "y1": 156,
                "x2": WINDOW_WIDTH - 76,
                "y2": 256,
                "x": WINDOW_WIDTH // 2,
                "y": 176,
                "fill": "#d9fff7",
                "outline": "#79cabe",
            },
            {
                "kind": "text",
                "text": f"Layer 4: {trash_text}",
                "x": 96,
                "y": 236,
                "anchor": "w",
                "font": ("Segoe UI", 11),
            },
            {
                "kind": "text",
                "text": f"Layer 5: {actor} - {self._character_state_text()}",
                "x": WINDOW_WIDTH // 2,
                "y": 218,
                "font": ("Segoe UI", 18, "bold"),
            },
            {
                "kind": "interface",
            },
        ]

    def _is_night_scene(self) -> bool:
        return self._scene_time_name() == "night"

    def _scene_time_name(self) -> str:
        started_at = int(self.current_game_statistics.get("started_at", int(time.time())))
        elapsed = max(0, int(time.time()) - started_at)
        cycle_length = DAY_DURATION_SECONDS + NIGHT_DURATION_SECONDS
        return "day" if elapsed % cycle_length < DAY_DURATION_SECONDS else "night"

    def _update_weather_cycle(self) -> None:
        started_at = int(self.current_game_statistics.get("started_at", int(time.time())))
        elapsed = max(0, int(time.time()) - started_at)
        cycle_index = elapsed // WEATHER_CYCLE_SECONDS
        if cycle_index <= self.weather_cycle_index:
            return

        self.weather_cycle_index = cycle_index
        self.current_weather = self._choose_next_weather(self.current_weather)
        self.current_weather_effect = self._choose_weather_effect(self.current_weather)
        self.weather_animation_frame = 0
        self._save_progress()

    def _schedule_weather_animation(self) -> None:
        self._cancel_weather_animation()
        if self.character_scene_canvas is None:
            return

        self.weather_animation_job = self.after(
            WEATHER_ANIMATION_INTERVAL_MS,
            self._advance_weather_animation,
        )

    def _advance_weather_animation(self) -> None:
        self.weather_animation_job = None
        if self.character_scene_canvas is None:
            return

        self.weather_animation_frame = (self.weather_animation_frame + 1) % WEATHER_FRAME_COUNT
        self._refresh_status_ui()
        self._schedule_weather_animation()

    def _cancel_weather_animation(self) -> None:
        if self.weather_animation_job is None:
            return

        try:
            self.after_cancel(self.weather_animation_job)
        except tk.TclError:
            pass
        self.weather_animation_job = None

    def _current_weather_image(self) -> ImageTk.PhotoImage | None:
        time_name = self._scene_time_name()
        frames = self.weather_background_frames.get((self.current_weather, time_name), [])
        if not frames:
            return None

        return frames[self.weather_animation_frame % len(frames)]

    def _current_weather_effect_image(self) -> ImageTk.PhotoImage | None:
        if self.current_weather_effect is None:
            return None

        frames = self.weather_effect_frames.get(self.current_weather_effect, [])
        if not frames:
            return None

        return frames[self.weather_animation_frame % len(frames)]

    def _weather_fill(self) -> str:
        if self._is_night_scene():
            return "#a8d8df"

        return CHARACTER_AREA_BG

    def _clear_status(
        self,
        key: str,
        statistic_key: str,
        clear_message: str,
        idle_message: str,
    ) -> None:
        if self.energy < CARE_ACTION_ENERGY_COST:
            self.feedback_label.configure(text="Not enough energy. Rest first.")
            self._refresh_status_ui()
            self._save_progress()
            return

        if self.statuses[key]:
            self.energy -= CARE_ACTION_ENERGY_COST
            self.statuses[key] = max(0, self.statuses[key] - 1)
            self.statistics[statistic_key] += 1
            self.current_game_statistics[statistic_key] += 1
            self._reset_repeated_action_streak()
            self.feedback_label.configure(text=clear_message)
            self._refresh_status_ui()
            self._update_death_countdown()
            self._save_progress()
            return

        self.feedback_label.configure(text=idle_message)
        self._refresh_status_ui()
        self._save_progress()

    def feed(self) -> None:
        self._clear_status("hunger", "times_fed", "Fed. Hunger reduced.", "Not hungry right now.")

    def heal(self) -> None:
        self._clear_status("sickness", "times_healed", "Healed. Health improved.", "Already healthy.")

    def clean(self) -> None:
        self._clear_status("dirty_room", "times_cleaned", "Cleaned. Dirt reduced.", "Room is already clean.")

    def entertain(self) -> None:
        self._clear_status("lazy", "times_entertained", "Entertained. Laziness reduced.", "Already entertained.")

    def open_konbini(self) -> None:
        self._save_progress()
        self._show_game(mode="konbini")

    def open_inventory(self) -> None:
        self._save_progress()
        self._show_game(mode="inventory")

    def return_to_game(self) -> None:
        self._save_progress()
        self._show_game()

    def buy_item(self, key: str) -> None:
        item = ITEMS[key]
        price = int(item["price"])
        if self.inventory.get(key, 0) >= INVENTORY_ITEM_LIMIT:
            self.feedback_label.configure(text=f"You can only carry {INVENTORY_ITEM_LIMIT} of each item.")
            self._refresh_status_ui()
            self._refresh_shop_buttons()
            self._save_progress()
            return

        if self.money < price:
            self.feedback_label.configure(text="Not enough money.")
            self._refresh_status_ui()
            self._save_progress()
            return

        self.money -= price
        self.inventory[key] = self.inventory.get(key, 0) + 1
        self.current_game_statistics["items_bought"] += 1
        self._reset_repeated_action_streak()
        self.feedback_label.configure(text=f"Bought {item['name']}.")
        self._refresh_status_ui()
        self._refresh_shop_buttons()
        self._save_progress()

    def use_item(self, key: str) -> None:
        if self.inventory.get(key, 0) <= 0:
            self.feedback_label.configure(text="That item is not in inventory.")
            self._refresh_status_ui()
            self._save_progress()
            return

        item = ITEMS[key]
        effect = item["effect"]
        if "energy" in effect:
            self.energy = min(MAX_ENERGY, self.energy + int(effect["energy"]))
        else:
            status_key = str(effect["status"])
            amount = int(effect["amount"])
            self.statuses[status_key] = max(0, self.statuses[status_key] - amount)

        self.inventory[key] -= 1
        self.current_game_statistics["items_used"] += 1
        self._reset_repeated_action_streak()
        self.feedback_label.configure(text=f"Used {item['name']}.")
        self._refresh_status_ui()
        self._save_progress()
        self._show_game(mode="inventory")

    def _can_take_repeated_action(self, action: str) -> bool:
        if self.death_countdown_remaining is not None:
            self.feedback_label.configure(text="Too dangerous for that. Clear a status before resting or working.")
            self._refresh_status_ui()
            self._save_progress()
            return False

        if self.last_repeated_action == action and self.repeated_action_count >= REPEATED_ACTION_LIMIT:
            self.feedback_label.configure(text=f"You cannot {action} more than {REPEATED_ACTION_LIMIT} times in a row.")
            self._refresh_status_ui()
            self._save_progress()
            return False

        return True

    def _record_repeated_action(self, action: str) -> None:
        if self.last_repeated_action == action:
            self.repeated_action_count += 1
        else:
            self.last_repeated_action = action
            self.repeated_action_count = 1

    def _reset_repeated_action_streak(self) -> None:
        self.last_repeated_action = None
        self.repeated_action_count = 0

    def _refresh_shop_buttons(self) -> None:
        for key, button in self.shop_buttons.items():
            item = ITEMS[key]
            count = self.inventory.get(key, 0)
            button.configure(text=f"{item['name']} {item['price']}¥ ({count}/{INVENTORY_ITEM_LIMIT})")
            if count >= INVENTORY_ITEM_LIMIT:
                button.state(["disabled"])
            else:
                button.state(["!disabled"])

    def rest(self) -> None:
        if not self._can_take_repeated_action("rest"):
            return

        self.energy = min(MAX_ENERGY, self.energy + REST_ENERGY_GAIN)
        self.current_game_statistics["times_rested"] += 1
        self._record_repeated_action("rest")
        worsened_count = 0
        for _ in range(REST_STATUS_TRIGGERS):
            if self._try_worsen_random_status():
                worsened_count += 1

        self.feedback_label.configure(
            text=f"Rested. Energy +{REST_ENERGY_GAIN}; statuses worsened {worsened_count} time(s)."
        )
        self._refresh_status_ui()
        self._update_death_countdown()
        self._reset_status_roll_timer()
        self._save_progress()

    def go_to_work(self) -> None:
        if not self._can_take_repeated_action("work"):
            return

        if self.energy < WORK_ENERGY_COST:
            self.feedback_label.configure(text="Not enough energy to work. Rest first.")
            self._refresh_status_ui()
            self._save_progress()
            return

        self.energy -= WORK_ENERGY_COST
        self.money += WORK_MONEY_GAIN
        self.current_game_statistics["times_worked"] += 1
        self.current_game_statistics["money_earned"] += WORK_MONEY_GAIN
        self._record_repeated_action("work")
        worsened_count = 0
        for _ in range(WORK_STATUS_TRIGGERS):
            if self._try_worsen_random_status():
                worsened_count += 1

        self.feedback_label.configure(
            text=f"Worked. +{WORK_MONEY_GAIN}¥; energy -{WORK_ENERGY_COST}; statuses worsened {worsened_count} time(s)."
        )
        self._refresh_status_ui()
        self._update_death_countdown()
        self._reset_status_roll_timer()
        self._save_progress()

    def continue_game(self) -> None:
        self._load_save()
        if self.character_dead:
            self._show_death_screen()
            return

        self._show_game()

    def new_game(self) -> None:
        if self.has_save:
            self._show_menu(show_new_game_warning=True)
            return

        self._start_new_game()

    def _show_reset_warning(self) -> None:
        self._show_menu(show_reset_warning=True)

    def _reset_progress(self) -> None:
        self.statuses = DEFAULT_STATUSES.copy()
        self.statistics = DEFAULT_STATISTICS.copy()
        self.current_game_statistics = self._new_game_statistics()
        self.last_game_statistics = None
        self.leaderboard = []
        self.energy = MAX_ENERGY
        self.money = STARTING_MONEY
        self.inventory = DEFAULT_INVENTORY.copy()
        self.character_dead = False
        self.current_character_key = None
        self.current_weather = STARTING_WEATHER
        self.current_weather_effect = self._choose_weather_effect(self.current_weather)
        self.weather_cycle_index = 0
        self.weather_animation_frame = 0
        self.death_countdown_remaining = None
        self._reset_repeated_action_streak()
        self.has_save = False
        self.game_started = False
        if SAVE_FILE.exists():
            SAVE_FILE.unlink()
        self._show_menu()

    def _start_new_game(self) -> None:
        self.statuses = DEFAULT_STATUSES.copy()
        self.current_game_statistics = self._new_game_statistics()
        self.last_game_statistics = None
        self.energy = MAX_ENERGY
        self.money = STARTING_MONEY
        self.inventory = DEFAULT_INVENTORY.copy()
        self.character_dead = False
        self.current_character_key = self._choose_new_character_key(self.current_character_key)
        self.current_weather = STARTING_WEATHER
        self.current_weather_effect = self._choose_weather_effect(self.current_weather)
        self.weather_cycle_index = 0
        self.weather_animation_frame = 0
        self.death_countdown_remaining = None
        self._reset_repeated_action_streak()
        self.statistics["games_played"] += 1
        self.has_save = True
        if SAVE_FILE.exists():
            SAVE_FILE.unlink()
        self._save_progress()
        self._show_game()

    def _save_and_show_menu(self) -> None:
        self._save_progress()
        self._show_menu()

    def _load_save(self) -> None:
        if not SAVE_FILE.exists():
            self.has_save = False
            return

        try:
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.has_save = False
            return

        saved_statuses = data.get("statuses", {})
        saved_statistics = data.get("statistics", {})
        saved_current_game_statistics = data.get("current_game", {})
        saved_last_game_statistics = data.get("last_game")
        saved_leaderboard = data.get("leaderboard", [])
        self.energy = self._load_energy(data.get("energy", MAX_ENERGY))
        self.money = self._load_money(data.get("money", STARTING_MONEY))
        self.inventory = self._load_inventory(data.get("inventory", {}))
        self.character_dead = bool(data.get("character_dead", False))
        self.current_character_key = self._load_character_key(data.get("current_character"))
        self.current_weather = self._load_weather(data.get("current_weather", data.get("current_weather_sky")))
        self.current_weather_effect = self._load_weather_effect(data.get("current_weather_effect"))
        if self.current_weather_effect not in WEATHER_EFFECT_OPTIONS.get(self.current_weather, (None,)):
            self.current_weather_effect = self._choose_weather_effect(self.current_weather)
        self.weather_cycle_index = self._load_weather_cycle_index(data.get("weather_cycle_index", 0))
        self.weather_animation_frame = 0
        self.last_repeated_action = data.get("last_repeated_action")
        if self.last_repeated_action not in {"rest", "work"}:
            self.last_repeated_action = None
        self.repeated_action_count = self._load_repeated_action_count(data.get("repeated_action_count", 0))
        if self.last_repeated_action is None:
            self.repeated_action_count = 0

        self.statuses = {
            key: self._load_status_severity(saved_statuses.get(key, default))
            for key, default in DEFAULT_STATUSES.items()
        }
        self.statistics = {
            key: int(saved_statistics.get(key, default))
            for key, default in DEFAULT_STATISTICS.items()
        }
        self.current_game_statistics = {
            key: int(saved_current_game_statistics.get(key, default))
            for key, default in self._new_game_statistics().items()
        }
        if self.current_game_statistics["started_at"] <= 0:
            self.current_game_statistics["started_at"] = int(time.time())

        self.last_game_statistics = None
        if isinstance(saved_last_game_statistics, dict):
            self.last_game_statistics = {
                "character": self._load_character_key(saved_last_game_statistics.get("character")) or DEFAULT_CHARACTER_KEY,
                "survived_minutes": int(saved_last_game_statistics.get("survived_minutes", 0)),
                "money": self._load_money(saved_last_game_statistics.get("money", 0)),
                "times_fed": int(saved_last_game_statistics.get("times_fed", 0)),
                "times_healed": int(saved_last_game_statistics.get("times_healed", 0)),
                "times_cleaned": int(saved_last_game_statistics.get("times_cleaned", 0)),
                "times_entertained": int(saved_last_game_statistics.get("times_entertained", 0)),
                "times_rested": int(saved_last_game_statistics.get("times_rested", 0)),
                "times_worked": int(saved_last_game_statistics.get("times_worked", 0)),
                "items_bought": int(saved_last_game_statistics.get("items_bought", 0)),
                "items_used": int(saved_last_game_statistics.get("items_used", 0)),
                "money_earned": self._load_money(saved_last_game_statistics.get("money_earned", 0)),
            }
            self.last_game_statistics["score"] = int(
                saved_last_game_statistics.get(
                    "score",
                    self._calculate_score(self.last_game_statistics),
                )
            )
        self.leaderboard = self._load_leaderboard(saved_leaderboard)
        self.sound_enabled = bool(data.get("sound_enabled", True))
        self.has_save = True

    def _save_progress(self) -> None:
        if not self.game_started and not self.has_save:
            return

        data = {
            "statuses": self.statuses,
            "statistics": self.statistics,
            "current_game": self.current_game_statistics,
            "last_game": self.last_game_statistics,
            "leaderboard": self.leaderboard,
            "energy": self.energy,
            "money": self.money,
            "inventory": self.inventory,
            "character_dead": self.character_dead,
            "current_character": self.current_character_key,
            "current_weather": self.current_weather,
            "current_weather_effect": self.current_weather_effect,
            "weather_cycle_index": self.weather_cycle_index,
            "last_repeated_action": self.last_repeated_action,
            "repeated_action_count": self.repeated_action_count,
            "sound_enabled": self.sound_enabled,
        }
        SAVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.has_save = True

    def _on_close(self) -> None:
        self._save_progress()
        self._close_notification_sound()
        self._close_timer_sound()
        self._close_soundtrack()
        self.destroy()

    def _current_survival_minutes(self) -> int:
        return max(0, int((time.time() - self.current_game_statistics["started_at"]) // 60))

    def _current_score(self) -> int:
        return self._calculate_score(
            {
                **self.current_game_statistics,
                "survived_minutes": self._current_survival_minutes(),
                "money": self.money,
            }
        )

    def _play_notification_sound(self) -> None:
        if not self.sound_enabled or not NOTIFICATION_SOUND_FILE.exists():
            return

        self._close_notification_sound()
        sound_path = str(NOTIFICATION_SOUND_FILE)

        if not self._mci(f'open "{sound_path}" type mpegvideo alias notification'):
            return

        self._mci(f"setaudio notification volume to {NOTIFICATION_SOUND_VOLUME}")
        if self._mci("play notification"):
            self.sound_close_job = self.after(NOTIFICATION_SOUND_CLOSE_DELAY_MS, self._close_notification_sound)
        else:
            self._close_notification_sound()

    def _play_timer_sound(self) -> None:
        if not self.sound_enabled or not TIMER_SOUND_FILE.exists():
            return

        self._close_timer_sound()
        sound_path = str(TIMER_SOUND_FILE)

        if not self._mci(f'open "{sound_path}" type mpegvideo alias death_timer'):
            return

        self._mci(f"setaudio death_timer volume to {NOTIFICATION_SOUND_VOLUME}")
        if not self._mci("play death_timer repeat"):
            self._close_timer_sound()

    def _close_notification_sound(self) -> None:
        if self.sound_close_job is not None:
            try:
                self.after_cancel(self.sound_close_job)
            except tk.TclError:
                pass
            self.sound_close_job = None

        self._mci("stop notification")
        self._mci("close notification")

    def _close_timer_sound(self) -> None:
        self._mci("stop death_timer")
        self._mci("close death_timer")

    def _play_next_soundtrack(self) -> None:
        if not self.sound_enabled:
            return

        available_tracks = [path for path in SOUNDTRACK_FILES if path.exists()]
        if not available_tracks:
            return

        choices = [
            path for path in available_tracks
            if self.current_soundtrack is None or path != self.current_soundtrack
        ]
        if not choices:
            choices = available_tracks

        track = random.choice(choices)
        self._play_soundtrack(track)

    def _ensure_soundtrack_playing(self) -> None:
        if self.soundtrack_monitor_job is not None:
            try:
                self.after_cancel(self.soundtrack_monitor_job)
            except tk.TclError:
                pass
            self.soundtrack_monitor_job = None

        if not self.sound_enabled:
            self._close_soundtrack()
            return

        if self._soundtrack_mode() != "playing":
            self._play_next_soundtrack()

        self.soundtrack_monitor_job = self.after(
            SOUNDTRACK_MONITOR_INTERVAL_MS,
            self._ensure_soundtrack_playing,
        )

    def _play_soundtrack(self, track: Path) -> None:
        self._close_soundtrack(cancel_monitor=False)
        self.current_soundtrack = track
        sound_path = str(track)

        if not self._mci(f'open "{sound_path}" type mpegvideo alias soundtrack'):
            if self._play_fallback_soundtrack(track):
                return
            self.current_soundtrack = None
            self.soundtrack_backend = None
            return

        self._mci("set soundtrack time format milliseconds")
        self._mci(f"setaudio soundtrack volume to {SOUNDTRACK_VOLUME}")
        if not self._mci("play soundtrack"):
            self._close_soundtrack(cancel_monitor=False)
            if self._play_fallback_soundtrack(track):
                return
            return

        self.soundtrack_backend = "mci"
        duration_ms = self._soundtrack_duration_ms()
        if duration_ms <= 0:
            duration_ms = SOUNDTRACK_FALLBACK_DURATION_MS
        self.soundtrack_next_job = self.after(duration_ms, self._play_next_soundtrack)

    def _play_fallback_soundtrack(self, track: Path) -> bool:
        return self._play_pygame_soundtrack(track) or self._play_powershell_soundtrack(track)

    def _play_pygame_soundtrack(self, track: Path) -> bool:
        mixer = self._get_pygame_mixer()
        if mixer is None:
            return False

        try:
            mixer.music.load(str(track))
            mixer.music.set_volume(SOUNDTRACK_VOLUME / 1000)
            mixer.music.play()
        except Exception:
            return False

        self.soundtrack_backend = "pygame"
        return True

    def _get_pygame_mixer(self):
        if self.pygame_mixer is not None:
            return self.pygame_mixer

        try:
            import pygame
        except ImportError:
            return None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            return None

        self.pygame_mixer = pygame.mixer
        return self.pygame_mixer

    def _play_powershell_soundtrack(self, track: Path) -> bool:
        self._close_powershell_soundtrack()
        volume = max(0, min(1, SOUNDTRACK_VOLUME / 1000))
        max_seconds = max(1, SOUNDTRACK_FALLBACK_DURATION_MS // 1000)
        script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([Uri]::new(@'
{track}
'@))
$player.Volume = {volume}
$player.Play()
$started = Get-Date
while ($true) {{
    Start-Sleep -Milliseconds 500
    if ($player.NaturalDuration.HasTimeSpan -and $player.Position -ge $player.NaturalDuration.TimeSpan) {{
        break
    }}
    if (((Get-Date) - $started).TotalSeconds -ge {max_seconds}) {{
        break
    }}
}}
$player.Stop()
$player.Close()
"""
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self.soundtrack_process = subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-STA",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-EncodedCommand",
                    encoded_script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
        except OSError:
            self.soundtrack_process = None
            return False

        self.soundtrack_backend = "powershell"
        return True

    def _soundtrack_duration_ms(self) -> int:
        status_buffer = ctypes.create_unicode_buffer(64)
        try:
            result = ctypes.windll.winmm.mciSendStringW(
                "status soundtrack length",
                status_buffer,
                len(status_buffer),
                None,
            )
        except AttributeError:
            return 0

        if result != 0:
            return 0

        try:
            return max(0, int(status_buffer.value))
        except ValueError:
            return 0

    def _soundtrack_mode(self) -> str:
        if self.soundtrack_backend == "pygame":
            mixer = self._get_pygame_mixer()
            if mixer is not None and mixer.music.get_busy():
                return "playing"
            return ""

        if self.soundtrack_backend == "powershell":
            if self.soundtrack_process is not None and self.soundtrack_process.poll() is None:
                return "playing"
            self.soundtrack_process = None
            return ""

        status_buffer = ctypes.create_unicode_buffer(64)
        try:
            result = ctypes.windll.winmm.mciSendStringW(
                "status soundtrack mode",
                status_buffer,
                len(status_buffer),
                None,
            )
        except AttributeError:
            return ""

        if result != 0:
            return ""

        return status_buffer.value.strip().lower()

    def _close_soundtrack(self, cancel_monitor: bool = True) -> None:
        if cancel_monitor and self.soundtrack_monitor_job is not None:
            try:
                self.after_cancel(self.soundtrack_monitor_job)
            except tk.TclError:
                pass
            self.soundtrack_monitor_job = None

        if self.soundtrack_next_job is not None:
            try:
                self.after_cancel(self.soundtrack_next_job)
            except tk.TclError:
                pass
            self.soundtrack_next_job = None

        self._mci("stop soundtrack")
        self._mci("close soundtrack")
        if self.pygame_mixer is not None:
            try:
                self.pygame_mixer.music.stop()
                self.pygame_mixer.music.unload()
            except Exception:
                pass
        self._close_powershell_soundtrack()
        self.soundtrack_backend = None

    def _close_powershell_soundtrack(self) -> None:
        if self.soundtrack_process is None:
            return

        if self.soundtrack_process.poll() is None:
            try:
                self.soundtrack_process.terminate()
            except OSError:
                pass

        self.soundtrack_process = None

    def _update_death_countdown(self) -> None:
        if self.character_dead:
            return

        if self._is_death_condition():
            if self.death_countdown_remaining is None:
                self.death_countdown_remaining = DEATH_COUNTDOWN_SECONDS
                self.feedback_label.configure(text="Everything is critical. Help Miku before time runs out.")
                self._play_timer_sound()
                self._schedule_death_countdown_tick()
        else:
            self._cancel_death_countdown()

        self._refresh_status_ui()

    def _schedule_death_countdown_tick(self) -> None:
        if self.death_countdown_job is None:
            self.death_countdown_job = self.after(1_000, self._tick_death_countdown)

    def _tick_death_countdown(self) -> None:
        self.death_countdown_job = None

        if self.character_dead or self.death_countdown_remaining is None:
            return

        if not self._is_death_condition():
            self._cancel_death_countdown()
            self._refresh_status_ui()
            self._save_progress()
            return

        self.death_countdown_remaining -= 1
        if self.death_countdown_remaining <= 0:
            self._kill_character()
            return

        self._refresh_status_ui()
        self._schedule_death_countdown_tick()

    def _cancel_death_countdown(self) -> None:
        if self.death_countdown_job is not None:
            try:
                self.after_cancel(self.death_countdown_job)
            except tk.TclError:
                pass
            self.death_countdown_job = None

        self.death_countdown_remaining = None
        self._close_timer_sound()

    def _kill_character(self) -> None:
        self.last_game_statistics = {
            "character": self._character_key(),
            "survived_minutes": self._current_survival_minutes(),
            "money": self.money,
            "times_fed": self.current_game_statistics["times_fed"],
            "times_healed": self.current_game_statistics["times_healed"],
            "times_cleaned": self.current_game_statistics["times_cleaned"],
            "times_entertained": self.current_game_statistics["times_entertained"],
            "times_rested": self.current_game_statistics["times_rested"],
            "times_worked": self.current_game_statistics["times_worked"],
            "items_bought": self.current_game_statistics["items_bought"],
            "items_used": self.current_game_statistics["items_used"],
            "money_earned": self.current_game_statistics["money_earned"],
        }
        self.last_game_statistics["score"] = self._calculate_score(self.last_game_statistics)
        self._record_leaderboard_score(self.last_game_statistics)
        self.statistics["character_deaths"] += 1
        self.character_dead = True
        self._close_timer_sound()
        self._play_notification_sound()
        self._save_progress()
        self._show_death_screen()

    def _is_death_condition(self) -> bool:
        return all(severity >= MAX_STATUS_SEVERITY for severity in self.statuses.values())

    def _current_mood(self) -> str:
        total_severity = sum(self.statuses.values())
        if total_severity >= 10:
            return "Terrible"
        if total_severity >= 7:
            return "Bad"
        if total_severity >= 4:
            return "Normal"
        if total_severity >= 1:
            return "Good"
        return "Excellent"

    def _character_state_text(self) -> str:
        if self.game_view_mode == "konbini":
            return "Seller"
        if self.game_view_mode == "inventory":
            return "Inventory"

        if self.death_countdown_remaining is not None:
            return f"{self._character_short_name()}: Critical"

        highest_severity = max(self.statuses.values())
        if highest_severity <= 0:
            return f"{self._character_short_name()}: Waiting"

        priority = ["sickness", "hunger", "dirty_room", "lazy"]
        worst_status = max(priority, key=lambda key: (self.statuses[key], -priority.index(key)))
        state = {
            "hunger": "Hungry",
            "sickness": "Sick",
            "dirty_room": "Messy",
            "lazy": "Lazy",
        }[worst_status]
        return f"{self._character_short_name()}: {state}"

    def _character_name(self) -> str:
        return CHARACTERS[self._character_key()]["name"]

    def _character_short_name(self) -> str:
        return CHARACTERS[self._character_key()]["short_name"]

    def _character_name_for(self, value: object) -> str:
        return CHARACTERS[self._load_character_key(value) or DEFAULT_CHARACTER_KEY]["name"]

    def _character_short_name_for(self, value: object) -> str:
        return CHARACTERS[self._load_character_key(value) or DEFAULT_CHARACTER_KEY]["short_name"]

    def _character_key(self) -> str:
        return self.current_character_key or DEFAULT_CHARACTER_KEY

    @staticmethod
    def _load_character_key(value: object) -> str | None:
        if isinstance(value, str) and value in CHARACTERS:
            return value

        return None

    @staticmethod
    def _choose_new_character_key(previous_key: str | None) -> str:
        choices = [key for key in CHARACTERS if key != previous_key]
        if not choices:
            choices = list(CHARACTERS)

        return random.choice(choices)

    @staticmethod
    def _choose_next_weather(current_weather: str) -> str:
        choices = [weather for weather in WEATHER_OPTIONS if weather != current_weather]
        if not choices:
            choices = list(WEATHER_OPTIONS)

        return random.choice(choices)

    @staticmethod
    def _choose_weather_effect(weather: str) -> str | None:
        return random.choice(WEATHER_EFFECT_OPTIONS.get(weather, (None,)))

    @staticmethod
    def _load_weather(value: object) -> str:
        if value == "clear":
            return "sunny"
        if value == "cloudy":
            return "cloudy"
        if value == "partly_cloudy":
            return "cloudy"
        if isinstance(value, str) and value in WEATHER_OPTIONS:
            return value

        return STARTING_WEATHER

    @staticmethod
    def _load_weather_effect(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str) and value in WEATHER_EFFECT_SPRITE_ROWS:
            return value

        return None

    @staticmethod
    def _load_weather_cycle_index(value: object) -> int:
        try:
            cycle_index = int(value)
        except (TypeError, ValueError):
            return 0

        return max(0, cycle_index)

    @staticmethod
    def _load_status_severity(value: object) -> int:
        if isinstance(value, bool):
            return MAX_STATUS_SEVERITY if value else 0

        try:
            severity = int(value)
        except (TypeError, ValueError):
            return 0

        return min(MAX_STATUS_SEVERITY, max(0, severity))

    @staticmethod
    def _load_energy(value: object) -> int:
        try:
            energy = int(value)
        except (TypeError, ValueError):
            return MAX_ENERGY

        return min(MAX_ENERGY, max(0, energy))

    @staticmethod
    def _load_money(value: object) -> int:
        try:
            money = int(value)
        except (TypeError, ValueError):
            return STARTING_MONEY

        return max(0, money)

    @staticmethod
    def _load_repeated_action_count(value: object) -> int:
        try:
            count = int(value)
        except (TypeError, ValueError):
            return 0

        return min(REPEATED_ACTION_LIMIT, max(0, count))

    @staticmethod
    def _calculate_score(stats: dict[str, object]) -> int:
        care_actions = (
            int(stats.get("times_fed", 0))
            + int(stats.get("times_healed", 0))
            + int(stats.get("times_cleaned", 0))
            + int(stats.get("times_entertained", 0))
        )
        support_actions = (
            int(stats.get("times_rested", 0)) * SCORE_PER_REST
            + int(stats.get("times_worked", 0)) * SCORE_PER_WORK
            + int(stats.get("items_bought", 0)) * SCORE_PER_ITEM
            + int(stats.get("items_used", 0)) * SCORE_PER_ITEM
        )
        money_score = int(stats.get("money_earned", 0)) // SCORE_MONEY_DIVISOR

        return max(
            0,
            int(stats.get("survived_minutes", 0)) * SCORE_PER_SURVIVAL_MINUTE
            + care_actions * SCORE_PER_CARE_ACTION
            + support_actions
            + money_score,
        )

    def _record_leaderboard_score(self, stats: dict[str, object]) -> None:
        entry = {
            "character": self._load_character_key(stats.get("character")) or DEFAULT_CHARACTER_KEY,
            "score": int(stats.get("score", self._calculate_score(stats))),
            "survived_minutes": int(stats.get("survived_minutes", 0)),
            "money": self._load_money(stats.get("money", 0)),
            "money_earned": self._load_money(stats.get("money_earned", 0)),
            "times_fed": int(stats.get("times_fed", 0)),
            "times_healed": int(stats.get("times_healed", 0)),
            "times_cleaned": int(stats.get("times_cleaned", 0)),
            "times_entertained": int(stats.get("times_entertained", 0)),
            "times_rested": int(stats.get("times_rested", 0)),
            "times_worked": int(stats.get("times_worked", 0)),
            "items_bought": int(stats.get("items_bought", 0)),
            "items_used": int(stats.get("items_used", 0)),
        }
        self.leaderboard.append(entry)
        self.leaderboard.sort(
            key=lambda score: (
                score["score"],
                score["survived_minutes"],
                score["money_earned"],
            ),
            reverse=True,
        )
        self.leaderboard = self.leaderboard[:LEADERBOARD_LIMIT]

    def _load_leaderboard(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []

        leaderboard: list[dict[str, object]] = []
        for raw_entry in value:
            if not isinstance(raw_entry, dict):
                continue

            entry = {
                "character": self._load_character_key(raw_entry.get("character")) or DEFAULT_CHARACTER_KEY,
                "survived_minutes": max(0, int(raw_entry.get("survived_minutes", 0))),
                "money": self._load_money(raw_entry.get("money", 0)),
                "money_earned": self._load_money(raw_entry.get("money_earned", 0)),
                "times_fed": max(0, int(raw_entry.get("times_fed", 0))),
                "times_healed": max(0, int(raw_entry.get("times_healed", 0))),
                "times_cleaned": max(0, int(raw_entry.get("times_cleaned", 0))),
                "times_entertained": max(0, int(raw_entry.get("times_entertained", 0))),
                "times_rested": max(0, int(raw_entry.get("times_rested", 0))),
                "times_worked": max(0, int(raw_entry.get("times_worked", 0))),
                "items_bought": max(0, int(raw_entry.get("items_bought", 0))),
                "items_used": max(0, int(raw_entry.get("items_used", 0))),
            }
            entry["score"] = max(0, int(raw_entry.get("score", self._calculate_score(entry))))
            leaderboard.append(entry)

        leaderboard.sort(
            key=lambda score: (
                score["score"],
                score["survived_minutes"],
                score["money_earned"],
            ),
            reverse=True,
        )
        return leaderboard[:LEADERBOARD_LIMIT]

    @staticmethod
    def _load_inventory(value: object) -> dict[str, int]:
        if not isinstance(value, dict):
            return DEFAULT_INVENTORY.copy()

        inventory = DEFAULT_INVENTORY.copy()
        for key in inventory:
            try:
                inventory[key] = min(INVENTORY_ITEM_LIMIT, max(0, int(value.get(key, 0))))
            except (TypeError, ValueError):
                inventory[key] = 0

        return inventory

    @staticmethod
    def _mci(command: str) -> bool:
        try:
            return ctypes.windll.winmm.mciSendStringW(command, None, 0, None) == 0
        except AttributeError:
            return False

    def _load_weather_background_frames(self) -> dict[tuple[str, str], list[ImageTk.PhotoImage]]:
        if not WEATHER_BACKGROUND_SPRITESHEET.exists():
            return {}

        try:
            sheet = Image.open(WEATHER_BACKGROUND_SPRITESHEET).convert("RGBA")
        except OSError:
            return {}

        frames: dict[tuple[str, str], list[ImageTk.PhotoImage]] = {}
        for (weather, time_name), row in WEATHER_SPRITE_ROWS.items():
            row_frames: list[ImageTk.PhotoImage] = []
            for frame in range(WEATHER_FRAME_COUNT):
                crop = sheet.crop(
                    (
                        frame * WINDOW_WIDTH,
                        row * CHARACTER_AREA_HEIGHT,
                        (frame + 1) * WINDOW_WIDTH,
                        (row + 1) * CHARACTER_AREA_HEIGHT,
                    )
                )
                row_frames.append(ImageTk.PhotoImage(crop))
            frames[(weather, time_name)] = row_frames

        return frames

    def _load_weather_effect_frames(self) -> dict[str, list[ImageTk.PhotoImage]]:
        if not WEATHER_EFFECTS_SPRITESHEET.exists():
            return {}

        try:
            sheet = Image.open(WEATHER_EFFECTS_SPRITESHEET).convert("RGBA")
        except OSError:
            return {}

        frames: dict[str, list[ImageTk.PhotoImage]] = {}
        for effect, row in WEATHER_EFFECT_SPRITE_ROWS.items():
            row_frames: list[ImageTk.PhotoImage] = []
            for frame in range(WEATHER_FRAME_COUNT):
                crop = sheet.crop(
                    (
                        frame * WINDOW_WIDTH,
                        row * CHARACTER_AREA_HEIGHT,
                        (frame + 1) * WINDOW_WIDTH,
                        (row + 1) * CHARACTER_AREA_HEIGHT,
                    )
                )
                row_frames.append(ImageTk.PhotoImage(crop))
            frames[effect] = row_frames

        return frames

    def _create_sound_images(self) -> dict[str, tk.PhotoImage]:
        return {
            "on": self._create_speaker_image(muted=False),
            "off": self._create_speaker_image(muted=True),
        }

    def _create_speaker_image(self, muted: bool) -> tk.PhotoImage:
        image = tk.PhotoImage(width=24, height=24)

        for x in range(5, 10):
            for y in range(9, 16):
                image.put("#2f3440", (x, y))

        speaker_points = [
            (10, 8),
            (11, 8),
            (10, 9),
            (11, 9),
            (12, 9),
            (10, 10),
            (11, 10),
            (12, 10),
            (13, 10),
            (10, 11),
            (11, 11),
            (12, 11),
            (13, 11),
            (10, 12),
            (11, 12),
            (12, 12),
            (13, 12),
            (10, 13),
            (11, 13),
            (12, 13),
            (13, 13),
            (10, 14),
            (11, 14),
            (12, 14),
            (10, 15),
            (11, 15),
            (10, 16),
            (11, 16),
        ]
        for point in speaker_points:
            image.put("#2f3440", point)

        if muted:
            self._draw_line(image, 16, 8, 21, 16, "#c83232")
            self._draw_line(image, 21, 8, 16, 16, "#c83232")
        else:
            self._draw_line(image, 16, 9, 17, 10, "#2f3440")
            self._draw_line(image, 17, 11, 17, 13, "#2f3440")
            self._draw_line(image, 16, 15, 17, 14, "#2f3440")
            self._draw_line(image, 19, 7, 21, 10, "#2f3440")
            self._draw_line(image, 21, 11, 21, 13, "#2f3440")
            self._draw_line(image, 21, 14, 19, 17, "#2f3440")

        return image

    @staticmethod
    def _draw_line(image: tk.PhotoImage, x1: int, y1: int, x2: int, y2: int, color: str) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        error = dx + dy

        while True:
            image.put(color, (x1, y1))
            if x1 == x2 and y1 == y2:
                break
            doubled_error = 2 * error
            if doubled_error >= dy:
                error += dy
                x1 += sx
            if doubled_error <= dx:
                error += dx
                y1 += sy

    @staticmethod
    def _new_game_statistics() -> dict[str, int]:
        statistics = DEFAULT_GAME_STATISTICS.copy()
        statistics["started_at"] = int(time.time())
        return statistics

    @staticmethod
    def _display_name(key: str) -> str:
        return {
            "hunger": "Hunger",
            "sickness": "Health",
            "dirty_room": "Dirt",
            "lazy": "Lazy",
        }[key]


if __name__ == "__main__":
    app = MikuGochiApp()
    app.mainloop()

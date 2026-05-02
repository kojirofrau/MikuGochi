import random
import ctypes
import json
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk


WINDOW_SIZE = 512
CHARACTER_AREA_HEIGHT = 340
TOP_BUTTON_SIZE = 32
MENU_BUTTON_WIDTH = 64
STATUS_CHECK_INTERVAL_MS = 20_000
STATUS_CHANGE_CHANCE = 0.6
DEATH_COUNTDOWN_SECONDS = 30
SAVE_FILE = Path(__file__).with_name("save.json")
NOTIFICATION_SOUND_FILE = Path(__file__).with_name("assets") / "audio" / "notification_1.mp3"
TIMER_SOUND_FILE = Path(__file__).with_name("assets") / "audio" / "notification_timer_1.mp3"
NOTIFICATION_SOUND_VOLUME = 500
NOTIFICATION_SOUND_CLOSE_DELAY_MS = 5_000
MAX_STATUS_SEVERITY = 3
MAX_ENERGY = 100
CARE_ACTION_ENERGY_COST = 5
REST_ENERGY_GAIN = 10
REST_STATUS_TRIGGERS = 3


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
}


class MikuGochiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("MikuGochi Prototype")
        self.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")
        self.resizable(False, False)

        self.statuses = DEFAULT_STATUSES.copy()
        self.statistics = DEFAULT_STATISTICS.copy()
        self.current_game_statistics = self._new_game_statistics()
        self.last_game_statistics: dict[str, int] | None = None
        self.energy = MAX_ENERGY
        self.has_save = SAVE_FILE.exists()
        self.game_started = False
        self.character_dead = False
        self.sound_enabled = True
        self.status_roll_job: str | None = None
        self.death_countdown_job: str | None = None
        self.death_countdown_remaining: int | None = None
        self.sound_close_job: str | None = None
        self.screen_frame: tk.Frame | ttk.Frame | None = None

        self.status_labels: dict[str, ttk.Label] = {}
        self.energy_label: ttk.Label | None = None
        self.mood_label: ttk.Label | None = None
        self.character_state_label: ttk.Label | None = None
        self.death_timer_label: ttk.Label | None = None
        self.sound_buttons: list[ttk.Button] = []
        self.sound_images = self._create_sound_images()

        self.configure(bg="#f6f7fb")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_save()
        self._show_menu()

    def _clear_screen(self) -> None:
        if self.status_roll_job is not None:
            try:
                self.after_cancel(self.status_roll_job)
            except tk.TclError:
                pass
            self.status_roll_job = None

        self._cancel_death_countdown()

        if self.screen_frame is not None:
            self.screen_frame.destroy()
            self.screen_frame = None

        self.sound_buttons = []
        self.energy_label = None
        self.mood_label = None
        self.character_state_label = None
        self.death_timer_label = None

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
        ttk.Button(frame, text="Close", command=self._on_close).pack(fill="x", pady=6, ipady=6)

    def _show_game(self) -> None:
        self._clear_screen()
        self.game_started = True
        self.status_labels = {}

        frame = tk.Frame(self, bg="#f6f7fb")
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        character_frame = tk.Frame(
            frame,
            width=WINDOW_SIZE,
            height=CHARACTER_AREA_HEIGHT,
            bg="#ffffff",
            highlightbackground="#c8ccd6",
            highlightthickness=1,
        )
        character_frame.pack_propagate(False)
        character_frame.pack(fill="x", side="top")

        self._add_menu_button(character_frame, x=-12, y=12)
        self._add_sound_button(character_frame, x=-(12 + MENU_BUTTON_WIDTH + 8), y=12)

        self.energy_label = ttk.Label(
            character_frame,
            text=f"Energy: {self.energy}/{MAX_ENERGY}",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            background="#ffffff",
        )
        self.energy_label.place(x=14, y=14, anchor="nw")

        self.character_state_label = ttk.Label(
            character_frame,
            text="Waiting",
            anchor="center",
            font=("Segoe UI", 24, "bold"),
            background="#ffffff",
        )
        self.character_state_label.place(relx=0.5, rely=0.5, anchor="center")

        self.mood_label = ttk.Label(
            character_frame,
            text="Mood: Excellent",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            background="#ffffff",
        )
        self.mood_label.place(x=14, rely=1.0, y=-18, anchor="sw")

        self.death_timer_label = ttk.Label(
            character_frame,
            text="",
            anchor="e",
            font=("Segoe UI", 11, "bold"),
            foreground="#b3261e",
            background="#ffffff",
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

        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill="x", pady=(18, 0))

        self._add_button(button_frame, "Feed", self.feed, 0)
        self._add_button(button_frame, "Heal", self.heal, 1)
        self._add_button(button_frame, "Clean", self.clean, 2)
        self._add_button(button_frame, "Entertain", self.entertain, 3)

        rest_frame = ttk.Frame(controls_frame)
        rest_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(rest_frame, text="Rest", command=self.rest).pack(fill="x")

        self.feedback_label = ttk.Label(
            controls_frame,
            text="All good for now.",
            anchor="center",
        )
        self.feedback_label.pack(fill="x", pady=(16, 0))

        self._refresh_status_ui()
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
            ("Times fed", self.statistics["times_fed"]),
            ("Times healed", self.statistics["times_healed"]),
            ("Times cleaned", self.statistics["times_cleaned"]),
            ("Times entertained", self.statistics["times_entertained"]),
        ]

        if self.last_game_statistics is not None:
            rows.extend(
                [
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
            text="Miku could not keep going.",
            anchor="center",
        ).pack(fill="x", pady=(0, 20))

        stats = self.last_game_statistics or {
            "survived_minutes": self._current_survival_minutes(),
            "times_fed": self.current_game_statistics["times_fed"],
            "times_healed": self.current_game_statistics["times_healed"],
            "times_cleaned": self.current_game_statistics["times_cleaned"],
            "times_entertained": self.current_game_statistics["times_entertained"],
        }

        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=0)

        rows = [
            ("Survived minutes", stats["survived_minutes"]),
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
        self._refresh_sound_buttons()
        self._save_progress()

    def _refresh_sound_buttons(self) -> None:
        for button in self.sound_buttons:
            button.configure(image=self._sound_button_image())

    def _sound_button_image(self) -> tk.PhotoImage:
        return self.sound_images["on" if self.sound_enabled else "off"]

    def _schedule_status_roll(self) -> None:
        self.status_roll_job = self.after(STATUS_CHECK_INTERVAL_MS, self._roll_random_status)

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
        for key, label in self.status_labels.items():
            severity = self.statuses[key]
            label.configure(text="OK" if severity == 0 else f"{severity}/{MAX_STATUS_SEVERITY}")

        if self.energy_label is not None:
            self.energy_label.configure(text=f"Energy: {self.energy}/{MAX_ENERGY}")

        if self.mood_label is not None:
            self.mood_label.configure(text=f"Mood: {self._current_mood()}")

        if self.character_state_label is not None:
            self.character_state_label.configure(text=self._character_state_text())

        if self.death_timer_label is not None:
            if self.death_countdown_remaining is None:
                self.death_timer_label.configure(text="")
            else:
                self.death_timer_label.configure(text=f"Danger: {self.death_countdown_remaining}s")

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

    def rest(self) -> None:
        self.energy = min(MAX_ENERGY, self.energy + REST_ENERGY_GAIN)
        worsened_count = 0
        for _ in range(REST_STATUS_TRIGGERS):
            if self._try_worsen_random_status():
                worsened_count += 1

        self.feedback_label.configure(
            text=f"Rested. Energy +{REST_ENERGY_GAIN}; statuses worsened {worsened_count} time(s)."
        )
        self._refresh_status_ui()
        self._update_death_countdown()
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
        self.energy = MAX_ENERGY
        self.character_dead = False
        self.death_countdown_remaining = None
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
        self.character_dead = False
        self.death_countdown_remaining = None
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
        self.energy = self._load_energy(data.get("energy", MAX_ENERGY))
        self.character_dead = bool(data.get("character_dead", False))

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
                "survived_minutes": int(saved_last_game_statistics.get("survived_minutes", 0)),
                "times_fed": int(saved_last_game_statistics.get("times_fed", 0)),
                "times_healed": int(saved_last_game_statistics.get("times_healed", 0)),
                "times_cleaned": int(saved_last_game_statistics.get("times_cleaned", 0)),
                "times_entertained": int(saved_last_game_statistics.get("times_entertained", 0)),
            }
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
            "energy": self.energy,
            "character_dead": self.character_dead,
            "sound_enabled": self.sound_enabled,
        }
        SAVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.has_save = True

    def _on_close(self) -> None:
        self._save_progress()
        self._close_notification_sound()
        self._close_timer_sound()
        self.destroy()

    def _current_survival_minutes(self) -> int:
        return max(0, int((time.time() - self.current_game_statistics["started_at"]) // 60))

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
            "survived_minutes": self._current_survival_minutes(),
            "times_fed": self.current_game_statistics["times_fed"],
            "times_healed": self.current_game_statistics["times_healed"],
            "times_cleaned": self.current_game_statistics["times_cleaned"],
            "times_entertained": self.current_game_statistics["times_entertained"],
        }
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
        if self.death_countdown_remaining is not None:
            return "Critical"

        highest_severity = max(self.statuses.values())
        if highest_severity <= 0:
            return "Waiting"

        priority = ["sickness", "hunger", "dirty_room", "lazy"]
        worst_status = max(priority, key=lambda key: (self.statuses[key], -priority.index(key)))
        return {
            "hunger": "Hungry",
            "sickness": "Sick",
            "dirty_room": "Messy",
            "lazy": "Lazy",
        }[worst_status]

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
    def _mci(command: str) -> bool:
        try:
            return ctypes.windll.winmm.mciSendStringW(command, None, 0, None) == 0
        except AttributeError:
            return False

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

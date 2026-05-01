import random
import ctypes
import json
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk


WINDOW_SIZE = 512
CHARACTER_AREA_HEIGHT = 340
STATUS_CHECK_INTERVAL_MS = 20_000
SAVE_FILE = Path(__file__).with_name("save.json")
NOTIFICATION_SOUND_FILE = Path(__file__).with_name("assets") / "audio" / "notification_1.mp3"
NOTIFICATION_SOUND_VOLUME = 500
NOTIFICATION_SOUND_CLOSE_DELAY_MS = 5_000


DEFAULT_STATUSES = {
    "hunger": False,
    "sickness": False,
    "dirty_room": False,
}


DEFAULT_STATISTICS = {
    "games_played": 0,
    "character_deaths": 0,
    "times_fed": 0,
    "times_healed": 0,
    "times_cleaned": 0,
}


DEFAULT_GAME_STATISTICS = {
    "started_at": 0,
    "times_fed": 0,
    "times_healed": 0,
    "times_cleaned": 0,
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
        self.has_save = SAVE_FILE.exists()
        self.game_started = False
        self.sound_enabled = True
        self.status_roll_job: str | None = None
        self.sound_close_job: str | None = None
        self.screen_frame: tk.Frame | ttk.Frame | None = None

        self.status_labels: dict[str, ttk.Label] = {}
        self.sound_buttons: list[ttk.Button] = []

        self.configure(bg="#f6f7fb")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_save()
        self._show_menu()

    def _clear_screen(self) -> None:
        if self.status_roll_job is not None:
            self.after_cancel(self.status_roll_job)
            self.status_roll_job = None

        if self.screen_frame is not None:
            self.screen_frame.destroy()
            self.screen_frame = None

        self.sound_buttons = []

    def _show_menu(self, show_new_game_warning: bool = False) -> None:
        self._clear_screen()

        frame = tk.Frame(self, bg="#f6f7fb", padx=44, pady=44)
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

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
        if not self.has_save:
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

        ttk.Button(frame, text="Statistics", command=self._show_statistics).pack(fill="x", pady=6, ipady=6)

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

        menu_button = ttk.Button(character_frame, text="Menu", command=self._save_and_show_menu)
        menu_button.place(relx=1.0, x=-12, y=12, anchor="ne")
        self._add_sound_button(character_frame, x=-80, y=12)

        controls_frame = ttk.Frame(frame, padding=(16, 14, 16, 12))
        controls_frame.pack(fill="both", expand=True)

        status_frame = ttk.Frame(controls_frame)
        status_frame.pack(fill="x")

        self._add_status(status_frame, "hunger", "Hunger", 0)
        self._add_status(status_frame, "sickness", "Health", 1)
        self._add_status(status_frame, "dirty_room", "Dirt", 2)

        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill="x", pady=(18, 0))

        self._add_button(button_frame, "Feed", self.feed, 0)
        self._add_button(button_frame, "Heal", self.heal, 1)
        self._add_button(button_frame, "Clean", self.clean, 2)

        self.feedback_label = ttk.Label(
            controls_frame,
            text="All good for now.",
            anchor="center",
        )
        self.feedback_label.pack(fill="x", pady=(16, 0))

        self._refresh_status_ui()
        self._schedule_status_roll()

    def _show_statistics(self) -> None:
        self._clear_screen()

        frame = tk.Frame(self, bg="#f6f7fb", padx=32, pady=24)
        frame.pack(fill="both", expand=True)
        self.screen_frame = frame

        ttk.Button(frame, text="Menu", command=self._save_and_show_menu).place(relx=1.0, x=-8, y=0, anchor="ne")
        self._add_sound_button(frame, x=-76, y=0)

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
        ]

        if self.has_save:
            rows.extend(
                [
                    ("Current survival minutes", self._current_survival_minutes()),
                    ("Current times fed", self.current_game_statistics["times_fed"]),
                    ("Current times healed", self.current_game_statistics["times_healed"]),
                    ("Current times cleaned", self.current_game_statistics["times_cleaned"]),
                ]
            )

        if self.last_game_statistics is not None:
            rows.extend(
                [
                    ("Last survival minutes", self.last_game_statistics["survived_minutes"]),
                    ("Last times fed", self.last_game_statistics["times_fed"]),
                    ("Last times healed", self.last_game_statistics["times_healed"]),
                    ("Last times cleaned", self.last_game_statistics["times_cleaned"]),
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
        button = ttk.Button(parent, text=self._sound_button_text(), command=self._toggle_sound)
        button.place(relx=1.0, x=x, y=y, anchor="ne")
        self.sound_buttons.append(button)

    def _toggle_sound(self) -> None:
        self.sound_enabled = not self.sound_enabled
        self._refresh_sound_buttons()
        self._save_progress()

    def _refresh_sound_buttons(self) -> None:
        for button in self.sound_buttons:
            button.configure(text=self._sound_button_text())

    def _sound_button_text(self) -> str:
        return "Mic On" if self.sound_enabled else "Mic Off"

    def _schedule_status_roll(self) -> None:
        self.status_roll_job = self.after(STATUS_CHECK_INTERVAL_MS, self._roll_random_status)

    def _roll_random_status(self) -> None:
        inactive_statuses = [key for key, active in self.statuses.items() if not active]

        if inactive_statuses:
            key = random.choice(inactive_statuses)
            self.statuses[key] = True
            self.feedback_label.configure(text=f"{self._display_name(key)} needs attention.")
            self._refresh_status_ui()
            self._play_notification_sound()
            self._save_progress()
        else:
            self.last_game_statistics = {
                "survived_minutes": self._current_survival_minutes(),
                "times_fed": self.current_game_statistics["times_fed"],
                "times_healed": self.current_game_statistics["times_healed"],
                "times_cleaned": self.current_game_statistics["times_cleaned"],
            }
            self.statistics["character_deaths"] += 1
            self.statistics["games_played"] += 1
            self.statuses = DEFAULT_STATUSES.copy()
            self.current_game_statistics = self._new_game_statistics()
            self.feedback_label.configure(text="Miku could not keep going. A new game has started.")
            self._refresh_status_ui()
            self._play_notification_sound()
            self._save_progress()

        self._schedule_status_roll()

    def _refresh_status_ui(self) -> None:
        for key, label in self.status_labels.items():
            label.configure(text="!" if self.statuses[key] else "OK")

    def _clear_status(
        self,
        key: str,
        statistic_key: str,
        clear_message: str,
        idle_message: str,
    ) -> None:
        if self.statuses[key]:
            self.statuses[key] = False
            self.statistics[statistic_key] += 1
            self.current_game_statistics[statistic_key] += 1
            self.feedback_label.configure(text=clear_message)
            self._refresh_status_ui()
            self._save_progress()
            return

        self.feedback_label.configure(text=idle_message)
        self._save_progress()

    def feed(self) -> None:
        self._clear_status("hunger", "times_fed", "Fed. Hunger cleared.", "Not hungry right now.")

    def heal(self) -> None:
        self._clear_status("sickness", "times_healed", "Healed. Health restored.", "Already healthy.")

    def clean(self) -> None:
        self._clear_status("dirty_room", "times_cleaned", "Cleaned. Dirt cleared.", "Room is already clean.")

    def continue_game(self) -> None:
        self._load_save()
        self._show_game()

    def new_game(self) -> None:
        if SAVE_FILE.exists():
            self._show_menu(show_new_game_warning=True)
            return

        self._start_new_game()

    def _start_new_game(self) -> None:
        self.statuses = DEFAULT_STATUSES.copy()
        self.current_game_statistics = self._new_game_statistics()
        self.last_game_statistics = None
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
            return

        try:
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        saved_statuses = data.get("statuses", {})
        saved_statistics = data.get("statistics", {})
        saved_current_game_statistics = data.get("current_game", {})
        saved_last_game_statistics = data.get("last_game")

        self.statuses = {
            key: bool(saved_statuses.get(key, default))
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
            "sound_enabled": self.sound_enabled,
        }
        SAVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.has_save = True

    def _on_close(self) -> None:
        self._save_progress()
        self._close_notification_sound()
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

    def _close_notification_sound(self) -> None:
        if self.sound_close_job is not None:
            try:
                self.after_cancel(self.sound_close_job)
            except tk.TclError:
                pass
            self.sound_close_job = None

        self._mci("stop notification")
        self._mci("close notification")

    @staticmethod
    def _mci(command: str) -> bool:
        try:
            return ctypes.windll.winmm.mciSendStringW(command, None, 0, None) == 0
        except AttributeError:
            return False

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
        }[key]


if __name__ == "__main__":
    app = MikuGochiApp()
    app.mainloop()

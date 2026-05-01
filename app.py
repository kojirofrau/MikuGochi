import random
import tkinter as tk
from tkinter import ttk


WINDOW_SIZE = 512
CHARACTER_AREA_HEIGHT = 340
STATUS_CHECK_INTERVAL_MS = 120_000


class MikuGochiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("MikuGochi Prototype")
        self.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")
        self.resizable(False, False)

        self.statuses = {
            "hunger": False,
            "sickness": False,
            "dirty_room": False,
        }

        self.status_labels: dict[str, ttk.Label] = {}

        self._build_ui()
        self._schedule_status_roll()

    def _build_ui(self) -> None:
        self.configure(bg="#f6f7fb")

        character_frame = tk.Frame(
            self,
            width=WINDOW_SIZE,
            height=CHARACTER_AREA_HEIGHT,
            bg="#ffffff",
            highlightbackground="#c8ccd6",
            highlightthickness=1,
        )
        character_frame.pack_propagate(False)
        character_frame.pack(fill="x", side="top")

        controls_frame = ttk.Frame(self, padding=(16, 14, 16, 12))
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

    def _schedule_status_roll(self) -> None:
        self.after(STATUS_CHECK_INTERVAL_MS, self._roll_random_status)

    def _roll_random_status(self) -> None:
        inactive_statuses = [key for key, active in self.statuses.items() if not active]

        if inactive_statuses:
            key = random.choice(inactive_statuses)
            self.statuses[key] = True
            self.feedback_label.configure(text=f"{self._display_name(key)} needs attention.")
            self._refresh_status_ui()
        else:
            self.feedback_label.configure(text="Everything needs attention.")

        self._schedule_status_roll()

    def _refresh_status_ui(self) -> None:
        for key, label in self.status_labels.items():
            label.configure(text="!" if self.statuses[key] else "OK")

    def _clear_status(self, key: str, clear_message: str, idle_message: str) -> None:
        if self.statuses[key]:
            self.statuses[key] = False
            self.feedback_label.configure(text=clear_message)
            self._refresh_status_ui()
            return

        self.feedback_label.configure(text=idle_message)

    def feed(self) -> None:
        self._clear_status("hunger", "Fed. Hunger cleared.", "Not hungry right now.")

    def heal(self) -> None:
        self._clear_status("sickness", "Healed. Health restored.", "Already healthy.")

    def clean(self) -> None:
        self._clear_status("dirty_room", "Cleaned. Dirt cleared.", "Room is already clean.")

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

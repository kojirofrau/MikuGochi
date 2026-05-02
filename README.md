# MikuGochi

A small native Windows desktop prototype for a Tamagotchi-like game.

## Run

Install Python 3 for Windows, then run:

```powershell
python app.py
```

Or double-click `MikuGochi.pyw` to launch it without a console window.

You can also double-click `run_mikugochi.bat`, which launches the same app through `pythonw`.

The app opens a fixed `512x512` window. The top area is reserved for the character image and is blank for now.

The app starts on a menu with:

- Continue
- New Game
- Statistics
- Close

The upper-left `Reset` button shows an in-window warning before deleting the current save and all lifetime statistics.

Continue loads the current save. New Game shows an in-window warning before deleting old progress, keeps lifetime statistics, and starts a fresh game. Statistics shows total games played, character deaths, successful feed/heal/clean/entertain counts, and the last death summary when available. Close exits the game. When the character dies, the game shows a Game Over screen with the current save's stats and buttons for starting a new game or returning to the menu.

Every 20 seconds, one status that is not already maxed can randomly worsen by one severity level:

- Hunger
- Health
- Dirt
- Lazy

Each status has severity `0-3`. Use `Feed`, `Heal`, `Clean`, and `Entertain` to reduce the matching status by one point. Each care action costs `5` energy.

The character starts with `100` energy and cannot go above `100`. Energy is shown in the upper-left corner of the character window. Use `Rest` to recover `10` energy. Resting is risky: it triggers random status worsening three times.

The character window shows a text state in the center, such as `Waiting`, `Sick`, `Hungry`, `Messy`, or `Lazy`. It also shows a mood scale in the lower-left corner:

- Terrible
- Bad
- Normal
- Good
- Excellent

Mood is calculated from the total severity of all statuses. If every status reaches severity `3`, a death countdown starts. During the countdown, `assets/audio/notification_timer_1.mp3` loops until the player clears a status or the countdown reaches zero.

Progress, lifetime statistics, current-save statistics, energy, the last death summary, and the sound toggle are saved to `save.json` when returning to the menu, closing the app, or changing care status.

When a random status change happens, the game plays `assets/audio/notification_1.mp3` at 50% app volume. Use the upper-right speaker button to turn game sound on or off.

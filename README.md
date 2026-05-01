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

Continue loads the current save. New Game shows an in-window warning before deleting old progress, keeps lifetime statistics, and starts a fresh game. Statistics shows total games played, character deaths, successful feed/heal/clean counts, current-save survival stats, and the last death summary when available.

Every 20 seconds, one inactive status can randomly activate:

- Hunger
- Health
- Dirt

Use `Feed`, `Heal`, and `Clean` to clear the matching status.

Progress, lifetime statistics, current-save statistics, the last death summary, and the sound toggle are saved to `save.json` when returning to the menu, closing the app, or changing care status.

When a random status change happens, the game plays `assets/audio/notification_1.mp3` at 50% app volume. Use the upper-right microphone button to turn game sound on or off.

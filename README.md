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

Every two minutes, one inactive status can randomly activate:

- Hunger
- Health
- Dirt

Use `Feed`, `Heal`, and `Clean` to clear the matching status.

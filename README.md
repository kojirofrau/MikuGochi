# MikuGochi

A small native Windows desktop prototype for a Tamagotchi-like game.

## Run

Install Python 3 for Windows, then run:

```powershell
python app.py
```

Or double-click `MikuGochi.pyw` to launch it without a console window.

You can also double-click `run_mikugochi.bat`, which launches the same app through `pythonw`.

The app opens a fixed `512x640` window. The top area is reserved for the character image and is blank for now.

The app starts on a menu with:

- Continue
- New Game
- Statistics
- Close

The upper-left `Reset` button shows an in-window warning before deleting the current save and all lifetime statistics.

Continue loads the current save. New Game shows an in-window warning before deleting old progress, keeps lifetime statistics, and starts a fresh game. Statistics shows total games played, character deaths, successful feed/heal/clean/entertain counts, and the last death summary when available. Close exits the game. When the character dies, the game shows a Game Over screen with the current save's stats and buttons for starting a new game or returning to the menu.

Every 20 seconds, there is a 60% chance that one status that is not already maxed will randomly worsen by one severity level:

- Hunger
- Health
- Dirt
- Lazy

Each status has severity `0-3`. Use `Feed`, `Heal`, `Clean`, and `Entertain` to reduce the matching status by one point. Each care action costs `5` energy.

The character starts with `100` energy and cannot go above `100`. Energy is shown in the upper-left corner of the character window, with money shown directly below it. Money starts at `0¥`.

Use `Rest` to recover `10` energy. Resting is risky: it performs three status checks, each with the same 60% chance to worsen one random status. Resting resets the regular 20-second status timer.

Use `Go to Work` to earn `2000¥`. Working costs `10` energy and performs three status checks, each with the same 60% chance to worsen one random status. If energy is below `10`, working is unavailable. Working resets the regular 20-second status timer.

Use `Konbini` to open the shop. The regular status timer pauses, the character text changes to `Seller`, and the care/rest/work buttons are replaced by shop items:

- Energy Drink `500¥`: restores `5` energy
- Medicine `1000¥`: removes `2` points from Disease
- Noodles `500¥`: removes `2` hunger
- Magazine `750¥`: removes `2` laziness

Shop buttons show their effect when hovered. Buying an item subtracts money immediately and adds the item to inventory. Items cannot be bought on credit. `Return` closes the shop and restarts the regular status timer.

Use `Inventory` to view saved items. The regular status timer pauses, statuses remain visible, item effects appear on hover, and clicking an item uses it. `Return` closes inventory and restarts the regular status timer.

The character window shows a text state in the center, such as `Waiting`, `Sick`, `Hungry`, `Messy`, or `Lazy`. It also shows a mood scale in the lower-left corner:

- Terrible
- Bad
- Normal
- Good
- Excellent

Mood is calculated from the total severity of all statuses. If every status reaches severity `3`, a death countdown starts. During the countdown, `assets/audio/notification_timer_1.mp3` loops until the player clears a status or the countdown reaches zero.

Progress, lifetime statistics, current-save statistics, energy, money, inventory, the last death summary, and the sound toggle are saved to `save.json` when returning to the menu, closing the app, or changing care status.

When a random status change happens, the game plays `assets/audio/notification_1.mp3` at 50% app volume. Use the upper-right speaker button to turn game sound on or off.

Background music uses the `assets/audio/soundtrack_*.mp3` tracks. Tracks are selected randomly, but the same track will not play twice in a row. Background music plays at 50% of the notification volume and follows the same sound on/off button.

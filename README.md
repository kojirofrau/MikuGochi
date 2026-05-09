# MikuGochi

MikuGochi is a small native Windows desktop pet game prototype built with Python, Tkinter, and Pillow. It runs in a fixed `512x640` window with animated character, room, shop, weather, trash, and UI layers.

## Run From Source

Install Python 3 for Windows and the Pillow dependency:

```powershell
python -m pip install pillow
```

Then run:

```powershell
python app.py
```

You can also double-click `MikuGochi.pyw` or `run_mikugochi.bat` to launch without a console window.

## Packaged App

The packaged executable is:

```text
package/MikuGochi.exe
```

The executable is built with PyInstaller and embeds the app icon from:

```text
assets/icons/mikugochi.ico
```

To rebuild the package:

```powershell
python -m PyInstaller --noconfirm --distpath package --workpath build MikuGochi.spec
```

The temporary `build/` folder can be deleted after a successful build.

## Gameplay

The main menu provides Continue, New Game, Statistics, Top Scores, and Close. The Reset button opens an in-window confirmation before deleting progress and lifetime statistics. The speaker button toggles sound.

The game tracks four statuses:

- Hunger
- Health
- Dirt
- Lazy

Each status ranges from `0` to `3`. Every 20 seconds, there is a 60% chance that one non-maxed status worsens by one point. Feed, Heal, Clean, and Entertain reduce the matching status by one point and cost `5` energy.

Energy starts at `100`. Rest restores `10` energy, while Go to Work earns `2000` yen and costs `10` energy. Resting and working both trigger extra status checks and reset the regular status timer.

If every status reaches `3`, a death countdown starts. Clearing any status cancels the countdown. If the timer reaches zero, the game records a Game Over result and adds it to the leaderboard.

## Konbini And Inventory

The Konbini screen pauses the regular status timer and shows the shop layer with an animated convenience-store worker. The worker loops a waiting animation while the shop is open and plays a one-shot thanks animation after successful purchases.

Shop items:

- Energy Drink: costs `500` yen, restores `5` energy
- Medicine: costs `1000` yen, reduces Health by `2`
- Noodles: costs `500` yen, reduces Hunger by `2`
- Magazine: costs `750` yen, reduces Lazy by `2`

The Inventory screen pauses the regular status timer and lets the player use purchased items.

## Assets

Important asset folders:

- `assets/audio`: notification sounds and background music
- `assets/characters/miku`: Miku animation sprite sheets
- `assets/characters/konbini_worker`: shop worker sprite sheet
- `assets/icons`: app icon source PNG and ICO
- `assets/locations`: room and shop background layer sprite sheet
- `assets/weather`: animated weather background and effects
- `assets/garbage`: trash layer sprite sheet

Runtime save files are named `save.json` and are intentionally not needed for a clean package. They are recreated by the game when progress is saved.

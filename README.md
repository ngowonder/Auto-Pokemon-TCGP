# Auto Pokemon TCG Pocket

Auto Pokemon TCG Pocket is designed to automate daily tasks in the Pokemon TCG Pocket using Bluestacks


## What does it do

- Open your free pack if available
- Gifts: claim your gifts
- Wonder picks: auto pick Chansey, Rare, and Bonus
- Missions: Claim and clear your missions
- Battle Solo events


## If you like the project,

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F1F21AN8FX)


## Requirements

[BlueStacks](https://www.bluestacks.com) (free Android emulator)

Python version 3.09+

## Crucial Settings

The template is sized to resolution 1600x900. The resolution and screen size has to match that.

### Bluestacks Display settings

display resolution: 1600x900

dpi: 320

interface scaling: 100% Default

### Enable "Fix Window Size"

- Menu Button (next to the Minimize button, top of player), so the BlueStack Player doesn't accidentally change size

Note: your experience may vary based on computer specs.


## Instructions to run script

Install python requirements:
- `pip install -r requirements.txt`

or
- `py -m pip install -r requirements.txt`

Run script on either Start Game screen or the Home screen
- `py auto_pokemon_tcgp.py`

or
- `py -m auto_pokemon_tcgp`

For the `desired_packs`, in the config.yaml use any readable style you like, and add/remove any strings.

If you desire 1 specific pack, remove all but that one string.

When new card packs get release, refer to `auto_pokemon_tcgp.py` for the complete list of `desired_packs`.

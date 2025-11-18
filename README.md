# Auto Pokemon TCG Pocket

<a href="https://www.buymeacoffee.com/ngowonder" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>  <a href='https://ko-fi.com/F1F21AN8FX' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

Auto Pokemon TCG Pocket is designed to automate daily tasks in the Pokemon TCG Pocket using Bluestacks and Computer Vision

## UPDATE

check branch `auto_pokemon_tcgp_0_1_0_beta`


## What does it do

- Open your free pack if available
- Gifts: claim your gifts
- Wonder picks: auto pick Chansey, Rare, and Bonus
- Missions: Claim and clear your missions
- Battle Solo events


## To get started

### Requirements

- [BlueStacks](https://www.bluestacks.com) (free Android emulator)

- Python version 3.09+

### Crucial Settings

The templates is sized to resolution 1600x900. The resolution and screen size has to match that.
The templates are in English.

#### Bluestacks Display settings

- display resolution: 1600x900

- dpi: 320

- interface scaling: 100% Default

#### Enable "Fix Window Size"

- Menu Button (next to the Minimize button, top of player), so the BlueStack Player doesn't accidentally change size

If your emulator change sizes, change it using this [solution](https://github.com/ngowonder/Auto-Pokemon-TCGP/issues/8#issuecomment-3180825665)



### Instructions to run script

Install python requirements:
- `pip install -r requirements.txt` or `py -m pip install -r requirements.txt`

Run script on either Start Game screen or the Home screen
- `py auto_pokemon_tcgp.py` or `py -m auto_pokemon_tcgp`

For the `desired_packs`, open config.yaml with a text editor or notepad, use any readable style you like, and add/remove `#` in front of strings.

- If you desire 1 specific pack, make sure there is no `#` in front of it and comment out all the rest with `#` in front of it.

- When new card packs get release, refer to top of `auto_pokemon_tcgp.py` for the complete list of `desired_packs`.

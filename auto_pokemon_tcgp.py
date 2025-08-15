"""
Auto Pokemon TCG Pocket

An OpenCV Python script designed to automate daily tasks in the Pokemon TCG Pocket using BlueStacks.

Bluestacks Display settings:
    display resolution: 1600x900
    dpi 320
    interface scaling: 100% Default

Enable "Fix Window Size"
    Menu Button (next to the Minimize button, top of player), so the BlueStack Player doesn't accidentally change size

# desired_pack choices for config.yaml:
"charizard", "mewtwo", "pikachu", "mew", "dialga", "palkia", "arceus", "shiny", "lunala", "solgaleo", "buzzwole", "eevee", "ho-oh", "lugia"
"""

from opencv_utils import match_template, get_click_location
from mss import mss
import cv2
import os
import psutil
import pyautogui
import random
import subprocess
import sys
from time import sleep
import win32gui
import numpy as np
import yaml


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Replace hardcoded values with config values
desired_pack = random.choice(config["desired_packs"])
enable_check_pack_screen = config["enable_check_pack_screen"]
enable_wonder_pick = config["enable_wonder_pick"]
enable_wonder_pick_event = config["enable_wonder_pick_event"]
enable_check_level_up = config["enable_check_level_up"]
enable_exit_app = config["enable_exit_app"]

enable_event_battle = config["enable_event_battle"]
desired_battle_diff = config["desired_battle_difficulty"]
battle_check_time = config["battle_check_time"]
enable_battle_defeat_redo = config["enable_battle_defeat_redo"]
enable_battle_victory_repeat = config["enable_battle_victory_repeat"]

EXE_PATH = r'"C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64 --cmd launchApp --package "jp.pokemon.pokemontcgp" --source desktop_shortcut'
HWND = None # Global HWND variable
PROCESS_NAME = ['BlueStacks', 'BlueStacks App Player', 'HD-Player',]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES = {
    'start_game': 'images/start_game.jpg',
    'at_home': 'images/home_1.jpg',
    'home': 'images/home_0.jpg',
    'pack': 'images/pack.jpg',
    'pack_can_open': 'images/pack_can_open.jpg',
    'pack_select_other_pack': 'images/pack_select_other_booster_packs.jpg',
    'pack_select_expansion': 'images/pack_select_expansion.jpg',
    'pack_select_pack_charizard': 'images/pack_select_pack_charizard.jpg',
    'pack_select_pack_mewtwo': 'images/pack_select_pack_mewtwo.jpg',
    'pack_select_pack_pikachu': 'images/pack_select_pack_pikachu.jpg',
    'pack_select_pack_mew': 'images/pack_select_pack_mew.jpg',
    'pack_select_pack_dialga': 'images/pack_select_pack_dialga.jpg',
    'pack_select_pack_palkia': 'images/pack_select_pack_palkia.jpg',
    'pack_select_pack_arceus': 'images/pack_select_pack_arceus.jpg',
    'pack_select_pack_shiny': 'images/pack_select_pack_shiny.jpg',
    'pack_select_pack_lunala': 'images/pack_select_pack_lunala.jpg',
    'pack_select_pack_solgaleo': 'images/pack_select_pack_solgaleo.jpg',
    'pack_select_pack_buzzwole': 'images/pack_select_pack_buzzwole.jpg',
    'pack_select_pack_eevee': 'images/pack_select_pack_eevee.jpg',
    'pack_select_pack_ho-oh': 'images/pack_select_pack_ho-oh.jpg',
    'pack_select_pack_lugia': 'images/pack_select_pack_lugia.jpg',
    'pack_select_package_0': 'images/pack_select_package_0.jpg',
    'pack_select_package_2': 'images/pack_select_package_2.jpg',
    'pack_select_package_3': 'images/pack_select_package_3.jpg',
    'pack_select_package_4': 'images/pack_select_package_4.jpg',
    'pack_select_package_6': 'images/pack_select_package_6.jpg',
    'pack_select_package_7': 'images/pack_select_package_7.jpg',
    'pack_select_package_8': 'images/pack_select_package_8.jpg',
    'pack_open': 'images/pack_open.jpg',
    'pack_open_slice': 'images/pack_open_slice.jpg',
    'new_card_dex': 'images/new_card_dex.jpg',
    'gifts': 'images/gifts.jpg',
    'gifts_screen': 'images/gifts_screen.jpg',
    'gifts_claim_all': 'images/gifts_claim_all.jpg',
    'gifts_claim_gift': 'images/gifts_claim_gift.jpg',
    'gifts_no_claim': 'images/gifts_no_claimable_items.jpg',
    'shop': 'images/shop.jpg',
    # 'shop_screen': 'images/shop_screen.jpg', # maybe this isn't needed; there's a finding in shop()
    'shop_daily_gift': 'images/shop_daily_gifts.jpg',
    'wonder_pick': 'images/wonder_pick.jpg',
    'wonder_pick_screen': 'images/wonder_pick_screen.jpg',
    'wonder_pick_bonus': 'images/wonder_pick_bonus.jpg',
    'wonder_pick_bonus_item': 'images/wonder_pick_bonus_item.jpg',
    'wonder_pick_chansey': 'images/wonder_pick_chansey.jpg',
    'wonder_pick_rare': 'images/wonder_pick_rare.jpg',
    'wonder_pick_no_stamina': 'images/wonder_pick_no_stamina.jpg',
    'wonder_pick_a_card_screen': 'images/wonder_pick_a_card_screen.jpg',
    'wonder_pick_card_back': 'images/wonder_pick_card_back.jpg',
    'missions_0': 'images/missions_0.jpg',
    'missions_1': 'images/missions_1.jpg',
    'missions_complete_all': 'images/missions_complete_all.jpg',
    'missions_complete': 'images/missions_complete.jpg',
    'missions_non_daily_complete': 'images/missions_non_daily_complete.jpg',
    'missions_claim': 'images/missions_claim.jpg',
    'missions_themed_collections': 'images/missions_themed_collections.jpg',
    'missions_themed_collections_complete': 'images/missions_themed_collections_complete.jpg',
    'battle': 'images/battle.jpg',
    'battle_solo_0': 'images/battle_solo_0.jpg',
    'battle_solo_1': 'images/battle_solo_1.jpg',
    'battle_drop_event': 'images/battle_solo_drop_event.jpg',
    'battle_solo_stamina': 'images/battle_solo_stamina.jpg',
    'battle_diff_beginner': 'images/battle_solo_diff_beginner.jpg',
    'battle_diff_intermediate': 'images/battle_solo_diff_intermediate.jpg',
    'battle_diff_advanced': 'images/battle_solo_diff_advanced.jpg',
    'battle_diff_expert': 'images/battle_solo_diff_expert.jpg',
    'battle_rules_screen': 'images/battle_rules_screen.jpg',
    'battle_rules_auto': 'images/battle_rules_auto.jpg',
    'battle_rules_go_battle': 'images/battle_rules_go_battle.jpg',
    'battle_end_defeat': 'images/battle_end_defeat.jpg',
    'battle_end_defeat_back': 'images/battle_end_defeat_back.jpg',
    'battle_end_victory': 'images/battle_end_victory.jpg',
    'battle_end_victory_proceed': 'images/battle_end_victory_proceed.jpg',
    'battle_end_victory_new_battle_unlocked': 'images/battle_end_victory_new_battle_unlocked.jpg',
    'level_up': 'images/level_up.jpg',
    'level_up_unlocked': 'images/level_up_unlocked.jpg',
    'task_click_next': 'images/task_click_next.jpg',
    'task_click_ok': 'images/task_click_ok.jpg',
    'task_click_skip': 'images/task_click_skip.jpg',
    'task_click_x': 'images/task_click_x.jpg',
    'task_click_back': 'images/task_click_back.jpg',
    'task_tap_hold': 'images/task_tap_hold.jpg',
    'task_tap_proceed': 'images/task_tap_proceed.jpg',
    'bluestacks_x': 'images/bluestacks_x.jpg',
    'bluestacks_close': 'images/bluestacks_close.jpg',
    'pokemon_tcgp_update_data': 'images/pokemon_tcgp_update_data.jpg',

    # Add more templates as needed
        # '': cv2.imread('images/.jpg'),
    # To use templates
        # template = templates.get(template_key)
}

card_pack_to_template_key = {
    'charizard': 'pack_select_pack_charizard',
    'mewtwo': 'pack_select_pack_mewtwo',
    'pikachu': 'pack_select_pack_pikachu',
    'mew': 'pack_select_pack_mew',
    'dialga': 'pack_select_pack_dialga',
    'palkia': 'pack_select_pack_palkia',
    'arceus': 'pack_select_pack_arceus',
    'shiny': 'pack_select_pack_shiny',
    'lunala': 'pack_select_pack_lunala',
    'solgaleo': 'pack_select_pack_solgaleo',
    'buzzwole': 'pack_select_pack_buzzwole',
    'eevee': 'pack_select_pack_eevee',
    'ho-oh': 'pack_select_pack_ho-oh',
    'lugia': 'pack_select_pack_lugia',
}

package_to_template_key = {
    'charizard': 'pack_select_package_0',
    'mewtwo': 'pack_select_package_0',
    'pikachu': 'pack_select_package_0',
    'mew': 'pack_select_package_0',
    'dialga': 'pack_select_package_2',
    'palkia': 'pack_select_package_2',
    'arceus': 'pack_select_package_3',
    'shiny': 'pack_select_package_4',
    'lunala': 'pack_select_package_0',
    'solgaleo': 'pack_select_package_0',
    'buzzwole': 'pack_select_package_6',
    'eevee': 'pack_select_package_7',
    'ho-oh': 'pack_select_package_8',
    'lugia': 'pack_select_package_8',
}

battle_diff_to_template_key = {
    'beginner': 'battle_diff_beginner',
    'intermediate': 'battle_diff_intermediate',
    'advanced': 'battle_diff_advanced',
    'expert': 'battle_diff_expert'
}


def main():
    print('\nStarting Auto Pokemon TCGP...\n')
    initialize_hwnd()
    with mss() as sct:
        monitor = sct.monitors[1]
        launch_game()
        start = start_game(sct, monitor)
        if start:
            have_booster_pack = check_after_start_game(sct, monitor)
            if have_booster_pack:
                open_booster_pack(sct, monitor)
        elif enable_check_pack_screen and check_at_home(sct, monitor):
            check_booster_pack_screen(sct, monitor)
        '''if enable_check_level_up:
            check_level_up(sct, monitor)'''
        have_gifts = check_gifts(sct, monitor)
        if have_gifts:
            gifts(sct, monitor)
        if enable_wonder_pick:
            wonder_pick(sct, monitor)
            '''if enable_check_level_up:
                check_level_up(sct, monitor)'''
        have_shop = check_shop(sct, monitor)
        if have_shop:
            shop(sct, monitor)
        have_missions = check_missions(sct, monitor)
        if have_missions:
            missions(sct, monitor)
        if enable_event_battle:
            battle_victory = battle_solo(sct, monitor)
            click_home(sct, monitor)
            if enable_check_level_up and battle_victory:
                check_level_up(sct, monitor)
            have_missions = check_missions(sct, monitor)
            if have_missions:
                missions(sct, monitor)
        if enable_exit_app:
            exit_bluestacks(sct, monitor)
        print('\nEnding Auto Pokemon TCGP\n')


def find_bluestacks_window():
    def enum_windows(hwnd, results):
        if 'BlueStacks' in win32gui.GetWindowText(hwnd):
            results.append(hwnd)

    hwnds = []
    win32gui.EnumWindows(enum_windows, hwnds)
    return hwnds


def initialize_hwnd():
    global HWND
    hwnds = find_bluestacks_window()
    if hwnds:
        HWND = hwnds[0]
        # print("BlueStacks window found")
    else:
        print("BlueStacks window not found")


def launch_game():
    def is_process_running():
        for proc in psutil.process_iter(['name']):
            try:
                if any(process_name.lower() in proc.info['name'].lower() for process_name in PROCESS_NAME):
                    return proc.info['name']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None

    if not is_process_running():
        print('None of the BlueStacks processes are running. Launching BlueStacks...')
        try:
            subprocess.Popen(EXE_PATH, shell=False) # launch BlueStacks
            while True:
                sleep(1)
                if is_process_running():
                    break
            sleep(3)

            '''workaround for win32gui.SetForegroundWindow() to work
            runs new py script and exit the old one'''
            restart_script()

        except PermissionError as e:
            print(f"PermissionError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print('BlueStacks is running')
        win32gui.SetForegroundWindow(HWND)


def restart_script():
    print('Restarting py script')
    python = sys.executable
    script = os.path.abspath(__file__)
    subprocess.run([python, script] + sys.argv[1:]) # run new py
    sys.exit() # exit old py


def start_game(sct, monitor):
    count = 0
    max_attempts = 120

    while count < max_attempts:
        start = check_template(sct, monitor, 'start_game')
        if start is not None and len(start) > 0:
            print('\nStarting Game')
            move_to_click(start)
            sleep(10)
            return True
        home = check_at_home(sct, monitor)
        if home:
            return False
        sleep(0.5)
        count += 1
    print(f"Error with start_game")
    if enable_exit_app:
        exit_bluestacks(sct, monitor)
    return None


def check_at_home(sct, monitor):
    return is_template_matched(sct, monitor, 'at_home', method="check")


def check_gifts(sct, monitor):
    if is_template_matched(sct, monitor, 'gifts', method="check", threshold=0.95):
        sleep(1)
        click_template(sct, monitor, 'gifts')
        sleep(1)
        return True
    return False


def check_shop(sct, monitor):
    if is_template_matched(sct, monitor, 'shop', method="check"):
        click_template(sct, monitor, 'shop')
        sleep(1)
        return True
    return False


def check_missions(sct, monitor):
    # Check for missions_0 first (special case)
    if is_template_matched(sct, monitor, 'missions_0', method="check"):
        return None
    
    # Check for missions_1
    if is_template_matched(sct, monitor, 'missions_1', method="check"):
        click_template(sct, monitor, 'missions_1')
        sleep(1)
        return True


def check_after_start_game(sct, monitor):
    count = 0
    max_attempts = 30

    while count < max_attempts:
        home = check_at_home(sct, monitor)
        if home:
            sleep(1)
            return None

        if is_template_matched(sct, monitor, 'pokemon_tcgp_update_data', method="check"):
            print('Have Pokemon TCGP update')
            click_ok(sct, monitor)
            sleep(60)
            restart_script()
            return None

        if is_template_matched(sct, monitor, 'pack_can_open', method="check"):
            print('Have booster pack')
            return True

        sleep(0.5)
        count += 1
    print(f"Error with check_after_start_game")
    return None


def check_level_up(sct, monitor):
    sleep(6)
    if is_template_matched(sct, monitor, 'level_up', method="check"):
        click_tap_to_proceed(sct, monitor)
        if is_template_matched(sct, monitor, 'level_up_unlocked', method="check"):
            click_ok(sct, monitor)
        print('Leveled up')


def check_booster_pack_screen(sct, monitor):
    print('\nOpening Booster Pack Screen')

    if not is_template_matched(sct, monitor, 'pack', method="find", max_attempts=10):
        print('Pack not found at home screen')
        return

    move_to_click(finding_template(sct, monitor, 'pack', 10))

    if not is_template_matched(sct, monitor, 'pack_select_other_pack', method="find"):
        print('Not at booster pack screen')
        click_home(sct, monitor)
        return

    print('At booster pack screen')
    sleep(1.5)

    if is_template_matched(sct, monitor, 'pack_can_open', method="check"):
        print('Can open booster pack')
        sleep(1)
        open_booster_pack(sct, monitor)
    else:
        print('No booster pack to open')

    sleep(1)
    click_home(sct, monitor)
    return


def open_booster_pack(sct, monitor):
    def select_card_pack(key):
        card_pack = card_pack_to_template_key.get(key)
        if card_pack:
            return card_pack
        else:
            print(f"Error: No card pack for '{key}'")
            return None

    def select_package(key):
        package = package_to_template_key.get(key)
        if package:
            return package
        else:
            print(f"Error: No package for '{key}'")
            return None

    print('\nOpening Pack')
    sleep(1)
    click_template(sct, monitor, 'pack_select_other_pack')

    if not is_template_matched(sct, monitor, 'pack_select_expansion', method="find"):
        print("Select expansion screen not found. Skipping pack selection.")
        click_home(sct, monitor)
        return

    desired_pack_template = select_card_pack(desired_pack)
    if not desired_pack_template:
        print(f"Desired pack '{desired_pack}' not found in template mapping.")
        click_home(sct, monitor)
        return

    scroll_attempts = 0
    max_scroll_attempts = 5
    while scroll_attempts < max_scroll_attempts:
        # Check for the desired pack on screen
        desired_pack_loc = check_template(sct, monitor, desired_pack_template, threshold=0.8)
        if desired_pack_loc is not None and len(desired_pack_loc) > 0:
            # Found desired pack
            move_to_click(desired_pack_loc)
            break
        else:
            # Scroll down to reveal more packs
            pyautogui.scroll(-1)
            sleep(1)
            scroll_attempts += 1
    else:
        print(f"Failed to find pack '{desired_pack}' after {max_scroll_attempts} attempts.")
        click_home(sct, monitor)
        return

    sleep(3)
    package = select_package(desired_pack)
    if package is not None:
        sleep(5)
        click_template(sct, monitor, package) # card package
    else:
        print('Error in select_package')
        click_home(sct, monitor)
        return

    click_template(sct, monitor, 'pack_open')
    click_skip(sct, monitor)

    open_pack(sct, monitor)

    click_home(sct, monitor)
    print('Finish opening pack')
    return


def open_pack(sct, monitor):
    # while loop for multiple card packs
    # multiple card packs is super rare occurence (happened once as gift)
    if is_template_matched(sct, monitor, 'pack_open_slice', method="find", max_attempts=30):
        while True:
            open_pack_slice(sct, monitor)
            click_tap_hold(sct, monitor)
            sleep(3)
            click_next(sct, monitor)
            sleep(6)
            if not is_template_matched(sct, monitor, 'pack_open_slice', method="check"):
                break
    else:
        print("ERROR: there is no pack to open")
        return

    if is_template_matched(sct, monitor, 'milestone_card', method="check"):  # collection milestones
        click_tap_to_proceed(sct, monitor)
        sleep(3)

    if is_template_matched(sct, monitor, 'new_card_dex', method="check"):  # if new cards, register to dex
        for _ in range(2):
            click_skip(sct, monitor)
            sleep(1)
        click_next(sct, monitor)
        sleep(1)

    if is_template_matched(sct, monitor, 'task_click_ok', method="check"):
        click_ok(sct, monitor)  # click_ok to claim shinedust
        sleep(1)


def open_pack_slice(sct, monitor): # trace line to open
    open_slice = finding_template(sct, monitor, 'pack_open_slice')
    if open_slice is not None and len(open_slice) > 0:
        # Find the bounding box with the smallest x-coordinate
        x, y, width, height = min(open_slice, key=lambda box: box[0])

        # Calculate the center of the left side of the bounding box
        x_left = x + 10
        y_left = y + height // 2
        pyautogui.moveTo(x_left, y_left, duration=0.5)
        pyautogui.drag(500, 0, 0.5, button='left')
        sleep(1)
    else:
        print('Open pack slicing not found')


def gifts(sct, monitor):
    print('\nOpening Gifts')

    if is_template_matched(sct, monitor, 'gifts_screen', method="find"):
        sleep(0.5)

        claim_all = check_template(sct, monitor, 'gifts_claim_all', threshold=0.98)
        if claim_all is not None and len(claim_all) > 0:
            move_to_click(claim_all)
            sleep(2)

            # Fallback when claim_all isn't detected properly
            if is_template_matched(sct, monitor, 'task_click_ok', method="check"):
                click_ok(sct, monitor)
                sleep(1)

        while True:
            claim_gift = check_template(sct, monitor, 'gifts_claim_gift')
            if claim_gift is not None and len(claim_gift) > 0:
                move_to_click(claim_gift)
                sleep(1)
                click_ok(sct, monitor)
                open_pack(sct, monitor)
                if is_template_matched(sct, monitor, 'gifts_screen', method="check", max_attempts=10):
                    pass  # Check if at gifts_screen before next action
            else:
                break

        if is_template_matched(sct, monitor, 'gifts_no_claim', method="check"):
            click_x(sct, monitor)
    print('Finish opening gifts')


def wonder_pick(sct, monitor):
    def pick_random_card(sct, monitor):
        template_key = 'wonder_pick_card_back'
        template_path = TEMPLATES.get(template_key)

        template = cv2.imread(os.path.join(SCRIPT_DIR, template_path))
        if template is None:
            print(f"Failed to load template '{template_key}' from {template_path}")
            return None

        image = sct.grab(monitor)
        _, cards = match_template(image, template, group_rectangles=True)
        if len(cards) > 0:
            print(f"Template '{template_key}' found")

            print(f'Found {len(cards)} card to choose')
            print(f'Cards are: {cards}')
            card = random.choice(cards)
            card_index = np.where(np.all(cards == card, axis=1))[0][0]
            print(f'Card choice is #{card_index+1}: {card}')
            move_to_click([card])
            sleep(5)
        else:
            print('No card backs found to pick')

    print('\nOpening Wonder Pick')

    wonder_pick = finding_template(sct, monitor, 'wonder_pick', max_attempts=10)
    if wonder_pick is not None and len(wonder_pick) > 0:
        sleep(1)
        move_to_click(wonder_pick)
    else:
        print('Wonder Pick not found at home screen')
        return

    if is_template_matched(sct, monitor, 'wonder_pick_screen', method="find"):
        event_picks = ['wonder_pick_chansey', 'wonder_pick_rare', 'wonder_pick_bonus']
        for pick in event_picks:
            sleep(1)
            event_pick = check_template(sct, monitor, pick)
            if event_pick is not None and len(event_pick) > 0:
                if pick in ['wonder_pick_chansey', 'wonder_pick_rare'] and not enable_wonder_pick_event:
                    print('Skipping event pick')
                    event_loc = get_click_location(event_pick)
                    pyautogui.moveTo(event_loc)
                    sleep(0.25)
                    pyautogui.scroll(-1)
                    continue
                move_to_click(event_pick)
                sleep(0.5)

                if pick in ['wonder_pick_chansey', 'wonder_pick_rare']:
                    if is_template_matched(sct, monitor, 'wonder_pick_no_stamina', method="check"):
                        print('No stamina for special wonder pick')
                        click_x(sct, monitor)
                        event_loc = get_click_location(event_pick)
                        pyautogui.moveTo(event_loc)
                        pyautogui.scroll(-1)
                        continue

                click_ok(sct, monitor)
                click_skip(sct, monitor)
                if is_template_matched(sct, monitor, 'wonder_pick_a_card_screen', method="find"):
                    pick_random_card(sct, monitor)
                    sleep(1.5)

                    if pick == "wonder_pick_bonus" and is_template_matched(sct, monitor, 'wonder_pick_bonus_item', method="check"):
                        print("Wonder pick an item")
                        for _ in range(2):
                            click_tap_to_proceed(sct, monitor)
                            sleep(0.5)
                    else:
                        print("Wonder pick a card")
                        click_tap_to_proceed(sct, monitor)
                        sleep(3)

                    if is_template_matched(sct, monitor, 'milestone_card', method="check"):  # collection milestones
                        click_tap_to_proceed(sct, monitor)
                        sleep(3)

                        if is_template_matched(sct, monitor, 'new_card_dex', method="check"):
                            for _ in range(2):
                                click_skip(sct, monitor)
                                sleep(1)
                            click_next(sct, monitor)

                        sleep(2)
                        click_tap_to_proceed(sct, monitor)
                        sleep(1)
                if is_template_matched(sct, monitor, 'wonder_pick_screen', method="find"):
                    sleep(1)
                    pass  # make sure it's at screen before click_home
            else:
                print(f"Template '{pick}' not found")

    else:
        print("Wonder Pick screen not found. Return home")
        click_home(sct, monitor)
        return

    click_home(sct, monitor)
    return


def shop(sct, monitor):
    print('\nOpening shop')

    daily_gift = finding_template(sct, monitor, 'shop_daily_gift')
    if daily_gift is not None and len(daily_gift) > 0:
        move_to_click(daily_gift)
        sleep(0.5)
        click_ok(sct, monitor)
        click_x(sct, monitor)
    else:
        print('Daily gifts button not found')
    print('Finish with shop')


def missions(sct, monitor):
    print('\nOpening Mission')

    complete_all = finding_template(sct, monitor, 'missions_complete_all', max_attempts=3, threshold=0.99)
    if complete_all is not None and len(complete_all) > 0:
        move_to_click(complete_all)
        sleep(5)
    else:
        print('Complete all missions button not found')

    if is_template_matched(sct, monitor, 'missions_non_daily_complete', method="check"):
        click_ok(sct, monitor)
        sleep(3)

    claim = check_template(sct, monitor, 'missions_claim')
    if claim is not None and len(claim) > 0:
        move_to_click(claim)
        sleep(1)
        click_ok(sct, monitor)
        sleep(1)

    themed_collection = check_template(sct, monitor, 'missions_themed_collections')
    if themed_collection is not None and len(themed_collection) > 0:
        move_to_click(themed_collection)
        complete = finding_template(sct, monitor, 'missions_complete')
        sleep(1)
        while complete:
            move_to_click(complete)
            themed_complete = finding_template(sct, monitor, 'missions_themed_collections_complete')
            move_to_click(themed_complete)
            click_ok(sct, monitor)
            sleep(3)
            complete = check_template(sct, monitor, 'missions_complete')
        click_back(sct, monitor)

    complete = check_template(sct, monitor, 'missions_complete', threshold=0.90)
    if complete is not None and len(complete) > 0:
        while complete is not None and len(complete) > 0:
            move_to_click(complete)
            final_complete = finding_template(sct, monitor, 'missions_themed_collections_complete')
            move_to_click(final_complete)
            for _ in range(2):
                sleep(1)
                click_ok(sct, monitor)
            sleep(3)
            complete = check_template(sct, monitor, 'missions_complete')

    click_x(sct, monitor)
    print('Missions clear')


def battle_solo(sct, monitor):
    print('\nOpening Battle')
    battle = finding_template(sct, monitor, 'battle')
    if battle is not None and len(battle) > 0:
        move_to_click(battle)
        sleep(3)
    else:
        print('Battle button not found')
        sleep(3)
        return False

    battle_screen_count = 0
    while battle_screen_count < 10:
        if is_template_matched(sct, monitor, 'battle_solo_0', method="check"):
            print('Solo event not found')
            sleep(1)
            return False

        solo_event = check_template(sct, monitor, 'battle_solo_1')
        if solo_event is not None and len(solo_event) > 0:
            move_to_click(solo_event)
            break
        sleep(1)
        battle_screen_count += 1

    drop_event = finding_template(sct, monitor, 'battle_drop_event', 10)
    if drop_event is not None and len(drop_event) > 0:
        move_to_click(drop_event)
    else:
        print('Drop event not found')
        sleep(3)
        return False

    battle_count = 0
    while True:
        sleep(3)
        if not is_template_matched(sct, monitor, 'battle_solo_stamina', method="check"):
            print('Solo stamina not found')
            sleep(3)
            return False

        sleep(0.5)
        diff_screen_key = battle_diff_to_template_key.get('beginner')
        diff_screen = finding_template(sct, monitor, diff_screen_key, 5)
        if diff_screen is not None and len(diff_screen) > 0:
            print('At battle difficulty screen')
            diff_screen_loc = get_click_location(diff_screen)
            pyautogui.moveTo(diff_screen_loc)
            sleep(0.25)
        else:
            print('Not at battle difficulty screen')
            sleep(3)
            return False

        diff_key = battle_diff_to_template_key.get(desired_battle_diff)
        if not diff_key:
            print(f"Invalid difficulty level: {desired_battle_diff}")
            sleep(3)
            return False
        if desired_battle_diff in ('advanced', 'expert'):
            pyautogui.scroll(-5)
            sleep(1)
        diff = finding_template(sct, monitor, diff_key)
        if diff is not None and len(diff) > 0:
            move_to_click(diff)
        else:
            print(f"Desired difficulty '{desired_battle_diff}' button not found")
            sleep(3)
            return False

        if is_template_matched(sct, monitor, 'battle_rules_screen', method="find"):
            auto_battle = finding_template(sct, monitor, 'battle_rules_auto')
            if auto_battle:
                move_to_click(auto_battle)
            else:
                print('Auto battle button not found')
                sleep(3)
                return False

            go_battle = finding_template(sct, monitor, 'battle_rules_go_battle')
            if go_battle is not None and len(go_battle) > 0:
                move_to_click(go_battle)
                battle_count += 1
                print(f'\nGo Battle #{battle_count}')
            else:
                print('Battle button not found')
                sleep(3)
                return False

        if battle_check_time != 0:
            sleep(battle_check_time)
            print('Battle sleep is over')
            win32gui.SetForegroundWindow(HWND)
            sleep(0.5)

        while True:
            if is_template_matched(sct, monitor, 'battle_end_defeat', method="check"):
                print('Battle end in defeat')
                for _ in range(2):
                    click_tap_to_proceed(sct, monitor)
                    sleep(0.5)
                battle_rewards = check_template(sct, monitor, 'task_tap_proceed') # battle task rewards
                if battle_rewards is not None and len(battle_rewards) > 0:
                    move_to_click(battle_rewards)
                    sleep(1)
                click_next(sct, monitor)
                back = check_template(sct, monitor, 'battle_end_defeat_back')
                if back:
                    move_to_click(back)
                    sleep(1)
                break

            if is_template_matched(sct, monitor, 'battle_end_victory', method="check"):
                print('Battle end in victory')
                click_template(sct, monitor, 'battle_end_victory_proceed')
                for _ in range(2):
                    click_tap_to_proceed(sct, monitor)
                    sleep(0.5)
                battle_rewards = check_template(sct, monitor, 'task_tap_proceed') # battle task rewards
                if battle_rewards is not None and len(battle_rewards) > 0:
                    move_to_click(battle_rewards)
                    sleep(1)
                click_next(sct, monitor)
                if is_template_matched(sct, monitor, 'battle_end_victory_new_battle_unlocked', method="check"):
                    click_next(sct, monitor)
                if enable_battle_victory_repeat:
                    break  # repeat with victory
                else:
                    print('Battle finish')
                    sleep(3)
                    return True  # ends with victory
            sleep(8)
            win32gui.SetForegroundWindow(HWND)
            sleep(2)

        if enable_battle_defeat_redo:
            print('Redo battle solo')
            pass
        else:
            break
    print('Battle finish')
    sleep(3)


def exit_bluestacks(sct, monitor):
    win32gui.SetForegroundWindow(HWND)
    x = finding_template(sct, monitor, 'bluestacks_x')
    if x is None or len(x) == 0:
        print('Failed to find BlueStacks X button')
        return

    print('\nExiting BlueStacks')
    move_to_click(x)
    sleep(1)
    close = finding_template(sct, monitor, 'bluestacks_close')
    if close is None or len(close) == 0:
        print('Failed to find BlueStacks close button')
        return
    move_to_click(close)
    sys.exit()


def close_bluestacks_ad(sct, monitor):
    ad_x = finding_template(sct, monitor, '')
    pass


def click_home(sct, monitor):  # click_home that adjust for ingame lag when loading home
    templates = ['home', 'at_home']
    for template in templates:
        home = check_template(sct, monitor, template)
        if home is not None and len(home) > 0:
            move_to_click(home)
            sleep(1)
            if is_template_matched(sct, monitor, 'at_home', method="find"):
                sleep(3)
                return home


def click_next(sct, monitor):
    next = finding_template(sct, monitor, 'task_click_next')
    move_to_click(next)
    sleep(1)
    return next


def click_ok(sct, monitor):
    ok = finding_template(sct, monitor, 'task_click_ok')
    move_to_click(ok)
    sleep(1)
    return ok


def click_skip(sct, monitor):
    skip = finding_template(sct, monitor, 'task_click_skip')
    move_to_click(skip)
    sleep(1)
    return skip


def click_x(sct, monitor):
    x = finding_template(sct, monitor, 'task_click_x')
    move_to_click(x)
    sleep(1)
    return x


def click_back(sct, monitor):
    back = finding_template(sct, monitor, 'task_click_back')
    move_to_click(back)
    sleep(1)
    return back


def click_tap_hold(sct, monitor):
    tap_hold = finding_template(sct, monitor, 'task_tap_hold')
    if tap_hold is not None and len(tap_hold) > 0:
        loc = get_click_location(tap_hold)
        while True:
            pyautogui.moveTo(loc)
            pyautogui.mouseDown()
            sleep(3)
            pyautogui.mouseUp()
            sleep(0.25)
            if not is_template_matched(sct, monitor, 'task_tap_hold', method="check"):
                return


def click_tap_to_proceed(sct, monitor):
    proceed = finding_template(sct, monitor, 'task_tap_proceed')
    move_to_click(proceed)
    sleep(1)
    return proceed


def click_template(sct, monitor, template_key):
    template_boxes = finding_template(sct, monitor, template_key)
    if template_boxes is not None and len(template_boxes) > 0:
        move_to_click(template_boxes)
        sleep(1)
        return True
    else:
        print(f"Template '{template_key}' not found")
        return False


def check_template(sct, monitor, template_key, threshold=0.85):
    template_path = TEMPLATES.get(template_key)
    if template_path is None:
        print(f"Template '{template_key}' not found")
        return None

    # template = cv2.imread(template)
    template = cv2.imread(os.path.join(SCRIPT_DIR, template_path))
    if template is None:
        print(f"Failed to load template '{template_key}' from {template_path}")
        return None

    image = sct.grab(monitor)
    _, boxes = match_template(image, template, threshold=threshold)
    if len(boxes) > 0:
        print(f"Template '{template_key}' found")
        return boxes
    return None


def finding_template(sct, monitor, template_key, max_attempts=60, threshold=0.85):
    count = 0
    max_attempts = 60
    sleep_duration = 0.5

    template_path = TEMPLATES.get(template_key)
    if template_path is None:
        print(f"Template '{template_key}' not found")
        return None

    # template = cv2.imread(template)
    template = cv2.imread(os.path.join(SCRIPT_DIR, template_path))
    if template is None:
        print(f"Failed to load template '{template_key}' from {template_path}")
        return None

    while count < max_attempts:
        image = sct.grab(monitor)
        _, boxes = match_template(image, template, threshold=threshold)
        if len(boxes) > 0:
            print(f"Template '{template_key}' found")
            return boxes
        sleep(sleep_duration)
        count += 1

    print(f"Error with template '{template_key}'")
    return None


def is_template_matched(sct, monitor, template, method="check", max_attempts=60, threshold=0.85) -> bool:
    if template is None or not isinstance(template, str):
        raise ValueError("Error: template cannot be None and must be a string to TEMPLATE dict.")

    if method == "check":
        found_screen = check_template(sct, monitor, template, threshold)
    elif method == "find":
        found_screen = finding_template(sct, monitor, template, max_attempts, threshold)
    else:
        print('Error: method must be "check" or "find".')
        return False

    return found_screen is not None and len(found_screen) > 0


def move_to_click(boxes):
    if len(boxes) == 0:
        print("No boxes found to click")
        return

    loc = get_click_location(boxes)
    # print(f"Click at location: {loc}")
    pyautogui.moveTo(loc, duration=0.25)
    pyautogui.click(loc)


if __name__== '__main__':
    main()

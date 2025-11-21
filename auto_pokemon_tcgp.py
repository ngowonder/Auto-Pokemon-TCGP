"""
Auto Pokemon TCG Pocket

An OpenCV Python script designed to automate daily tasks in the Pokemon TCG Pocket using BlueStacks.

Bluestacks Display settings:
    display resolution: 1600x900
    dpi 320
    interface scaling: 100% Default

Enable "Fix Window Size"
    Menu Button (next to the Minimize button, top of player), so the BlueStack Player doesn't accidentally change size

# `desired_booster_packs` choices for config.yaml:
"charizard", "mewtwo", "pikachu", "mew", "dialga", "palkia", "arceus", "shiny", "lunala", "solgaleo", "buzzwole", "eevee", "ho-oh", "lugia", "suicune", "deluxe pack ex"
"mega altaria", "mega blaziken", "mega gyarados"
"""


import cv2
import psutil
import pyautogui
import random
import subprocess
import sys
import win32gui
import numpy as np
import yaml

from datetime import datetime, timezone
from mss import mss
from pathlib import Path
from time import sleep
from typing import Literal

from mss_opencv_pyautogui_utils import *
from opencv_utils import match_template, match_template_color, get_click_location
from templates_dict import BOOSTER_PACK_TO_TEMPLATES, TEMPLATES


CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# Replace hardcoded values with config values
desired_booster_packs = random.choice(config["desired_booster_packs"]).lower()
enable_check_pack_screen = config["enable_check_pack_screen"]
enable_wonder_pick = config["enable_wonder_pick"]
enable_special_wonder_picks = config["enable_special_wonder_picks"]
enable_check_level_up = config["enable_check_level_up"]
enable_exit_app = config["enable_exit_app"]

enable_event_battle = config["enable_event_battle"]
enable_battle_difficulty_fallback = config["enable_battle_difficulty_fallback"]
desired_battle_difficulty = config["desired_battle_difficulty"].lower()
battle_check_time = config["battle_check_time"]
enable_battle_defeat_redo = config["enable_battle_defeat_redo"]
enable_battle_victory_repeat = config["enable_battle_victory_repeat"]

DEBUG: bool = config["debug"]
EXE_PATH = r'"C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64 --cmd launchApp --package "jp.pokemon.pokemontcgp" --source desktop_shortcut'
HWND = None # Global HWND variable
PROCESS_NAME = ['BlueStacks', 'BlueStacks App Player', 'HD-Player',]
SCRIPT_DIR = Path(__file__).resolve().parent

DIFFICULTIES = ["beginner", "intermediate", "advanced", "expert"]
DIFF_TO_TEMPLATE_KEY = {
    "beginner": "battle_diff_beginner",
    "intermediate": "battle_diff_intermediate",
    "advanced": "battle_diff_advanced",
    "expert": "battle_diff_expert",
}


class Bot:
    def __init__(self):
        self.booster_packs_available = None
        self.gifts_available = None
        self.wonder_pick_sneak_peeks_available = None
        self.shop_daily_gifts_available = None
        self.missions_rewards_available = None
        self.have_leveled_up = None
        self.start_run_datetime = current_datetime()

    def check_booster_pack(self, sct, monitor):
        for _ in range(6):  # 1.5s should be perfect
            if is_template_matched(sct, monitor, "pack_can_open_a_booster_pack"):
                self.booster_packs_available = True
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Booster Pack available to be open")
                return True
            sleep(0.25)

        self.booster_packs_available = False
        return False

    def check_gifts(self, sct, monitor):
        if is_template_matched(sct, monitor, "home_gifts_btn", threshold=0.95):
            print(f"[{current_datetime().strftime('%H:%M:%S')}] Gifts available")
            self.gifts_available = True
            return True

        if DEBUG:
            print(f"\n[DEBUG {current_datetime().strftime('%H:%M:%S')}] Gifts not available at Home screen")
        self.gifts_available = False
        return False

    def check_shop(self, sct, monitor):
        if is_template_matched(sct, monitor, "home_shop_btn"):
            print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Shop's Daily Gifts available")
            self.shop_daily_gifts_available = True
            return True

        self.shop_daily_gifts_available = False
        return False

    def check_missions(self, sct, monitor):
        max_attempts = 120
        for _ in range(max_attempts):
            if is_template_matched(sct, monitor, "home_missions_btn_0"):
                # self.missions_rewards_available = False
                return False

            if is_template_matched(sct, monitor, "home_missions_btn_1"):
                if DEBUG:
                    print(f"\n[DEBUG {current_datetime().strftime('%H:%M:%S')}] Missions rewards available")
                self.missions_rewards_available = True
                return True
            sleep(0.25)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Couldn't find Missions from Home screen")
            return False

    def check_level_up(self, sct, monitor):
        """NOTE TODO handle_level_up"""
        max_attempts = 7
        for _ in range(max_attempts):
            if is_template_matched(sct, monitor, "level_up"):
                click_tap_to_proceed(sct, monitor)
                if is_template_matched(sct, monitor, "level_up_unlocked"):
                    click_ok(sct, monitor)
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Leveled up")
                return True
            sleep(1)
        else:
            return False

    def start_game(self, sct, monitor):
        max_attempts = 360
        for _ in range(max_attempts):
            start = check_template(sct, monitor, "start_screen")
            if start:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Starting Game")
                move_to_click(start)
                sleep(5)

            new_app_update(sct, monitor)
            new_data_update(sct, monitor)

            if is_template_matched(sct, monitor, "home_btn_0") \
                and (not self.check_booster_pack(sct, monitor) or is_template_matched(sct, monitor, "pack_select_other_booster_packs_btn")):
                go_to_home_screen(sct, monitor)

            if check_if_home_screen(sct, monitor):
                if DEBUG:
                    print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Started at Home screen")
                self.check_gifts(sct, monitor)
                self.check_shop(sct, monitor)
                self.check_missions(sct, monitor)
                return False

            if self.check_booster_pack(sct, monitor):
                return True

            sleep(0.25)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to Start Game")
            if enable_exit_app:
                exit_bluestacks(sct, monitor)
            return

    def booster_packs(self, sct, monitor):
        # Home screen
        if (self.booster_packs_available is None or self.booster_packs_available) and check_if_home_screen(sct, monitor):
            go_to_booster_pack_screen(sct, monitor)
            self.check_booster_pack(sct, monitor)

        # Booster Pack screen
        if is_template_matched(sct, monitor, "pack_select_other_booster_packs_btn", method="find") and self.booster_packs_available:
            open_booster_packs(sct, monitor)

        self.booster_packs_available = False
        go_to_home_screen(sct, monitor)
        return

    def gifts(self, sct, monitor):
        # if not self.gifts_available and go_to_home_screen(sct, monitor):  # NOTE which is better
        if self.gifts_available is None and go_to_home_screen(sct, monitor):
            self.check_gifts(sct, monitor)

        if not self.gifts_available:
            return

        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Gifts")
        if go_to_home_screen(sct, monitor):
            click_template(sct, monitor, "home_gifts_btn", confirm_click=True)

        # Gifts screen
        if is_template_matched(sct, monitor, "gifts_screen", method="find"):
            sleep(0.5)

            claim_all = check_template(sct, monitor, "gifts_claim_all_btn", threshold=0.98)
            if claim_all:
                move_to_click(claim_all)
                sleep(2)

                # Fail-safe when claim_all isn't detected properly
                if is_template_matched(sct, monitor, "ok_btn"):
                    click_ok(sct, monitor)
                    sleep(1)

            boxes = check_template(sct, monitor, "gifts_claim_btn", color_match=False, threshold=0.95)
            if boxes and len(boxes) >= 3:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Gifts: at least {len(boxes)} gifts to claim")
            else:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Gifts: {len(boxes)} gifts to claim")

            claimed_count = 0
            while True:
                claim_btn = check_template(sct, monitor, "gifts_claim_btn")
                if not claim_btn:
                    break
                move_to_click(claim_btn)
                sleep(1)
                click_ok(sct, monitor)
                open_pack(sct, monitor)
                claimed_count += 1
                if is_template_matched(sct, monitor, "gifts_screen", method="find"):
                    pass  # wait for gifts_screen before next action

            if is_template_matched(sct, monitor, "gifts_no_claimable_items_screen"):
                self.gifts_available = False
                sleep(1)
                click_x(sct, monitor)

            print(f"[{current_datetime().strftime('%H:%M:%S')}] Gifts claimed {claimed_count} gift packs")
            return

    def shop(self, sct, monitor):
        # if not self.shop_daily_gifts_available and go_to_home_screen(sct, monitor):  # NOTE which is better
        if self.shop_daily_gifts_available is None and go_to_home_screen(sct, monitor):
            self.check_shop(sct, monitor)

        if not self.shop_daily_gifts_available:
            return

        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Shop")
        if go_to_home_screen(sct, monitor):
            click_template(sct, monitor, "home_shop_btn", confirm_click=True)

        daily_gift = finding_template(sct, monitor, "shop_daily_gift")
        if not daily_gift:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find Shop's Daily Gifts button")
            return False

        move_to_click(daily_gift)
        sleep(0.5)
        self.shop_daily_gifts_available = False
        print(f"[{current_datetime().strftime('%H:%M:%S')}] Shop's Daily Gifts claimed")
        click_ok(sct, monitor)


        """# option to buy monthly hourglasses
        if enable_shop_buy_monthly_hourglasses:
            mouse_drag_scroll(daily_gift, y_offset=-300)

            templates = ["shop_pack_hourglass", "shop_wonder_hourglass"]
            for template in templates:
                hourglass = check_template(sct, monitor, template)
                if hourglass:
                    for i in hourglass:
                        move_to_click(i)
                        sleep(1.5)

                        check_template(sct, monitor, "shop_item_max_qty_btn")

                        if is_template_matched(sct, monitor, "shop_item_max_qty_btn"):
                            click_template(sct, monitor, "shop_item_max_qty_btn")
                        click_ok(sct, monitor)

                        # what's next?
        """

        click_x(sct, monitor)
        return

    def check_wonder_pick_sneak_peeks(self, sct, monitor):
        if is_template_matched(sct, monitor, "home_wonder_pick_sneak_peeks"):
            if DEBUG:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick's Sneak Peeks available")
            self.wonder_pick_sneak_peeks_available = True
            return True
        self.wonder_pick_sneak_peeks_available = False
        return False

    def handle_wonder_pick_sneak_peeks(self, sct, monitor):
        if not self.wonder_pick_sneak_peeks_available:
            return

        max_attempts = 60
        for _ in range(max_attempts):
            if is_template_matched(sct, monitor, "wonder_pick_sneak_peek_active_icon"):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick's Sneak Peek is active")

            # wait for Sneak Peek screen
            if is_template_matched(sct, monitor, "wonder_pick_sneak_peek_take_a_peek_btn_0"):
                wonder_pick_random_card(sct, monitor)
                click_template(sct, monitor, "wonder_pick_sneak_peek_take_a_peek_btn_1", confirm_click=True)

            # normal Random Card Pick screen
            if is_template_matched(sct, monitor, "wonder_pick_pick_a_card_screen"):
                return True
            sleep(0.25)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to handle Sneak Peeks")
            return False

    def wonder_pick(self, sct, monitor):
        if self.wonder_pick_sneak_peeks_available is None and go_to_home_screen(sct, monitor):
            self.check_wonder_pick_sneak_peeks(sct, monitor)

        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick")
        if go_to_home_screen(sct, monitor):
            click_template(sct, monitor, "home_wonder_pick_btn", confirm_click=True)

        if not is_template_matched(sct, monitor, "wonder_pick_screen", method="find"):
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to get to Wonder Pick screen. Returning to Home...")
            go_to_home_screen(sct, monitor)
            return

        # Wonder Pick screen
        WONDER_PICKS = ["wonder_pick_chansey", "wonder_pick_rare", "wonder_pick_bonus"]
        SPECIAL_PICKS = ["wonder_pick_chansey", "wonder_pick_rare"]
        for pick in WONDER_PICKS:
            sleep(1)
            matched_pick = check_template(sct, monitor, pick)
            if not matched_pick:
                if DEBUG:
                    print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Wonder Pick '{pick}' not available")
                continue

            if not enable_special_wonder_picks and pick in SPECIAL_PICKS:
                if DEBUG:
                    print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Wonder Pick: skipping {pick}; 'enable_special_wonder_picks' is {enable_special_wonder_picks} in config.yaml")
                mouse_drag_scroll(matched_pick, y_offset=-220)
                continue

            move_to_click(matched_pick)
            sleep(0.5)

            if pick in SPECIAL_PICKS and is_template_matched(sct, monitor, "wonder_pick_no_stamina"):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick: no stamina for {pick}")
                click_x(sct, monitor, confirm_click=True)
                mouse_drag_scroll(matched_pick, y_offset=-250)
                continue

            # case when Chansey or Rare Pick covers "home_wonder_pick_sneak_peeks"
            ok_btns = ["ok_btn", "wonder_pick_sneak_peeks_ok_btn"]
            found_ok_btn = None
            for i in range(60):
                if found_ok_btn:
                    break
                for ok_btn in ok_btns:
                    matched_ok_btn = check_template(sct, monitor, ok_btn)
                    if matched_ok_btn:
                        found_ok_btn = True
                        if ok_btn == "wonder_pick_sneak_peeks_ok_btn":
                            self.wonder_pick_sneak_peeks_available = True
                        move_to_click(matched_ok_btn)
                        break
                    if i < 60 - 1:
                        sleep(0.25)

            print(f"[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick: '{pick}'")
            click_skip(sct, monitor)

            if self.wonder_pick_sneak_peeks_available:
                self.handle_wonder_pick_sneak_peeks(sct, monitor)

            if is_template_matched(sct, monitor, "wonder_pick_pick_a_card_screen", method="find"):
                wonder_pick_random_card(sct, monitor)

                items = ["wonder_pick_pick_item", "wonder_pick_pick_items"]
                if pick == "wonder_pick_bonus" and is_template_matched(sct, monitor, items):
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick an Item")
                else:
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Wonder Pick a Card")

                for _ in range(2):
                    click_tap_to_proceed(sct, monitor, sleep_duration=2)

                # for _ in range(120):
                while True:
                    if is_template_matched(sct, monitor, "card_milestone"):  # collection milestones
                        click_tap_to_proceed(sct, monitor)
                        sleep(3)

                    if is_template_matched(sct, monitor, "card_new_dex"):
                        for _ in range(2):
                            click_skip(sct, monitor)
                            sleep(1)
                        click_next(sct, monitor)

                    if is_template_matched(sct, monitor, "wonder_pick_results_screen"):  # Fallback catch
                        click_tap_to_proceed(sct, monitor)

                    if is_template_matched(sct, monitor, "wonder_pick_screen"):
                        sleep(1)  # wait for Wonder Pick screen
                        break

                    sleep(0.25)
        if DEBUG:
            print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Wonder Pick completed")
        go_to_home_screen(sct, monitor)
        return

    def missions(self, sct, monitor):
        if self.missions_rewards_available is None and go_to_home_screen(sct, monitor):
            self.check_missions(sct, monitor)

        if not self.missions_rewards_available:
            return

        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Missions")
        go_to_missions_screen(sct, monitor)

        while True:
            self.missions_handle_complete_all_loop(sct, monitor)
            self.missions_handle_complete_loop(sct, monitor)  # NOTE if not is_template_matched(sct, monitor, "missions_complete_all_btn")

            if not self.missions_horizontal_scroll(sct, monitor):
                break
            sleep(0.5)

            if is_template_matched(sct, monitor, "missions_tab_premium", color_match=True):
                self.missions_handle_complete_all_loop(sct, monitor)  # for case when user has premium
                break

            if check_if_home_screen(sct, monitor):
                print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Missions: unexpectedly at Home screen")
                return

        self.missions_themed_collections(sct, monitor)

        click_x(sct, monitor)
        self.missions_rewards_available = False
        print(f"[{current_datetime().strftime('%H:%M:%S')}] Missions clear")
        return

    def missions_horizontal_scroll(self, sct, monitor):
        template = "x_close_btn"
        boxes = finding_template(sct, monitor, template)
        if boxes:
            boxes = offset_boxes(boxes, x_offset=0, y_offset=-400)
            mouse_drag_scroll(boxes, x_offset=-100, duration=0.2, drag=True)
            return True
        return False

    def missions_handle_complete_all_loop(self, sct, monitor):
        """handle dex missions, bonus week, etc"""
        complete_all = check_template(sct, monitor, "missions_complete_all_btn", color_match=True)
        if complete_all:
            move_to_click(complete_all)
            sleep(5)

            for i in range(5):
                complete_all = check_template(sct, monitor, "missions_complete_all_btn", color_match=True)
                if complete_all:
                    move_to_click(complete_all)
                    click_ok(sct, monitor, sleep_duration=3, confirm_click=True)

                ok_btn = check_template(sct, monitor, "ok_btn")
                if ok_btn:
                    move_to_click(ok_btn)
                    sleep(3)

                if i > 3 and not is_template_matched(sct, monitor, "missions_complete_all_btn", color_match=True):
                    return True

                if is_template_matched(sct, monitor, "missions_claimed_all_rewards_screen"):
                    return True

                sleep(0.25)
        return False

    def missions_handle_complete_loop(self, sct, monitor):
        """handle deck missions, themed_collections"""
        while True:
            # small complete btn - shadows in background can make btn slightly darker
            small_complete = check_template(sct, monitor, "missions_small_complete_btn", color_match=True, color_space="bgr")
            if not small_complete:
                if self.missions_handle_expansions(sct, monitor):
                    continue
                return

            move_to_click(small_complete)
            sleep(2)

            big_complete = check_template(sct, monitor, "missions_big_complete_btn")
            if big_complete:
                move_to_click(big_complete)
                sleep(1)
                for _ in range(2):
                    ok_btn = check_template(sct, monitor, "ok_btn")
                    if ok_btn:
                        move_to_click(ok_btn)
                    sleep(1.5)
                sleep(4)

            """
            x_btn = check_template(sct, monitor, "x_close_btn")
            if x_btn:
                move_to_click(x_btn)
                sleep(1)
                # if not self.missions_handle_expansions(sct, monitor):
                    # return
                return
            """

            if check_if_home_screen(sct, monitor):
                return
            sleep(1)

    def missions_handle_expansions(self, sct, monitor):
        expansion_btn = check_template(sct, monitor, "missions_expansions_btn")
        if expansion_btn:
            move_to_click(expansion_btn)
            sleep(1)
            expansions_windows = ["missions_expansions_missions_window", "missions_expansions_themed_collections_window"]
            for template in expansions_windows:
                exp_window = check_template(sct, monitor, template)
                if exp_window:
                    exp_window_scroll = offset_boxes(exp_window, y_offset=450)
                    max_attempts = 10
                    for _ in range(max_attempts):
                        expansion = check_template(sct, monitor, "missions_expansions_reward_icon")
                        if expansion:
                            move_to_click(expansion)
                            sleep(1)
                            return True

                        mouse_drag_scroll(exp_window_scroll, y_offset=-450)
                        sleep(0.25)
                    else:
                        click_x(sct, monitor)
        return False

    def missions_themed_collections(self, sct, monitor):
        themed_collection = check_template(sct, monitor, "missions_themed_collections_btn")
        if not themed_collection:
            return

        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Missions: Themed Collections")
        move_to_click(themed_collection)
        sleep(1)

        self.missions_handle_complete_loop(sct, monitor)

        click_back(sct, monitor, confirm_click=True)
        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Missions: Themed Collections reward claimed")
        return

    def battle(self, sct, monitor):
        print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Battle")

        if go_to_home_screen(sct, monitor):
            go_to_battle_screen(sct, monitor)

        self.battle_solo_event(sct, monitor)

        if DEBUG:
            print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Battle finished")
        if is_template_matched(sct, monitor, "home_btn_level_up"):
            go_to_home_screen(sct, monitor)
            self.check_level_up(sct, monitor)
        else:
            go_to_home_screen(sct, monitor)
        return

    def battle_solo_event(self, sct, monitor):
        if not self.go_to_battle_solo_event(sct, monitor):
            return False

        print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle: Solo Event")

        battle_count = 0
        while True:
            sleep(1.5)  # use is_template_matched(sct, monitor, screen, method="find") for screen instead of sleep
            if not is_template_matched(sct, monitor, "battle_solo_event_stamina"):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle: Solo Event: no stamina available")
                # sleep(3)  # NOTE commented for now
                return False

            if not self.select_battle_difficulty(sct, monitor):
                return False

            battle_count += 1
            print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Battle #{battle_count}")
            battle_result = self.handle_battle_loop(sct, monitor)
            if battle_result and not self.gifts_available:
                self.gifts_available = True

            if (battle_result and enable_battle_victory_repeat) \
                   or (not battle_result and enable_battle_defeat_redo):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle: continuing after {'Victory' if battle_result else 'Defeat'}")
                continue

            if battle_result:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle: finished after Victory")
                return True
            else:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle: finished after Defeat")
                return False

    def go_to_battle_solo_event(self, sct, monitor):
        max_attempts = 15
        for _ in range(max_attempts):
            if is_template_matched(sct, monitor, "battle_solo_btn"):
                if DEBUG:
                    print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Battle: Solo Event not available")
                sleep(1)
                return False

            templates = ["battle_solo_event_btn_0",]  # "battle_solo_event_btn_1"
            for template in templates:
                solo_event = check_template(sct, monitor, template)
                if solo_event:
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle: Solo Event available")
                    move_to_click(solo_event)

                    # After clicking the solo event, check for drop event immediately
                    drop_event = finding_template(sct, monitor, "battle_solo_event_drop_event_btn")
                    if drop_event:
                        move_to_click(drop_event)
                        return True
                    else:
                        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find Drop Event")
                        return False
            sleep(1)

        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find Solo Event after {max_attempts} attempts")
        return False

    def select_battle_difficulty(self, sct, monitor):
        def find_battle_difficulty_screen(sct, monitor, max_attempts: int = 5):
            """Find Battle Difficulty screen and return the difficulty boxes for scrolling"""
            # cases where there's no "beginner" like PROMO reissue drop event
            for i in range(max_attempts):
                for diff in DIFFICULTIES:
                    diff_key = DIFF_TO_TEMPLATE_KEY.get(diff)
                    diff_boxes = check_template(sct, monitor, diff_key)
                    if diff_boxes:
                        return diff_boxes
                sleep(1)
            return False

        diff_screen = find_battle_difficulty_screen(sct, monitor)
        if not diff_screen:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to get to Battle Difficulty screen")
            return False

        if DEBUG:
            print(f"[{current_datetime().strftime('%H:%M:%S')}] Selecting Battle Difficulty")

        try:
            desired_diff_idx = DIFFICULTIES.index(desired_battle_difficulty)
        except ValueError:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Invalid difficulty: {desired_battle_difficulty}")
            return False

        # Create fallback order: start with desired difficulty and try lower difficulties
        fallback_order = DIFFICULTIES[desired_diff_idx::-1] # From desired down to beginner

        # Split difficulties into two groups: those requiring scroll and those not
        high_diffs = []  # advanced, expert
        low_diffs = []   # beginner, intermediate

        for diff in fallback_order:
            if diff in ("advanced", "expert"):
                high_diffs.append(diff)
            else:
                low_diffs.append(diff)

        # First, try high difficulties (scroll down)
        if high_diffs:
            mouse_drag_scroll(diff_screen, y_offset=-250)
            sleep(0.5)

            for diff in high_diffs:
                diff_key = DIFF_TO_TEMPLATE_KEY.get(diff)
                desired_diff = check_template(sct, monitor, diff_key)

                if desired_diff is not None and len(desired_diff) >= 2:
                    print(f"{current_datetime().strftime('%H:%M:%S')}] There is {len(desired_diff)} {diff} on screen\n\
                        The function to do or select multiple {diff} is not available. Exiting Battle")
                    return False

                if desired_diff:
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Selected difficulty: {diff}")
                    move_to_click(desired_diff)
                    return True
                elif not enable_battle_difficulty_fallback:
                    print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Desired difficulty '{desired_battle_difficulty}' not found")
                    sleep(3)
                    return False
                else:
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Difficulty '{diff}' not available, trying fallback...")

        # If high difficulties not found or not applicable, try low difficulties (scroll back up)
        if low_diffs:
            # Only scroll up if we previously scrolled down
            if high_diffs:
                mouse_drag_scroll(diff_screen, y_offset=250)  # Scroll back up
                sleep(0.5)

            for diff in low_diffs:
                diff_key = DIFF_TO_TEMPLATE_KEY.get(diff)
                desired_diff = check_template(sct, monitor, diff_key)

                if desired_diff is not None and len(desired_diff) >= 2:
                    print(f"{current_datetime().strftime('%H:%M:%S')}] There is {len(desired_diff)} {diff} on screen\n\
                        The function to do or select multiple {diff} is not available. Exiting Battle")
                    return False

                if desired_diff:
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Selected difficulty: {diff}")
                    move_to_click(desired_diff)
                    return True
                elif not enable_battle_difficulty_fallback:
                    print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Desired difficulty '{desired_battle_difficulty}' not found")
                    sleep(3)
                    return False
                else:
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] Difficulty '{diff}' not available, trying fallback...")

        # If we get here, all fallback options were tried and failed
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] No battle difficulties available after fallback attempts")
        sleep(3)
        return False

    def handle_battle_loop(self, sct, monitor):
        if not is_template_matched(sct, monitor, "battle_rules_screen", method="find"):
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find Battle Rules screen")
            return

        click_template(sct, monitor, "battle_rules_auto_btn", confirm_click=True)
        click_template(sct, monitor, "battle_rules_battle_btn", confirm_click=True)

        battle_duration = battle_check_time if battle_check_time is not None else 0
        if battle_check_time:
            sleep(battle_check_time)
            if DEBUG:
                print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Battle sleep is over")
            win32gui.SetForegroundWindow(HWND)
            sleep(0.5)

        while True:
            if is_template_matched(sct, monitor, "battle_end_defeat"):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle ended in Defeat")
                for _ in range(2):
                    click_tap_to_proceed(sct, monitor, sleep_duration=1.5)

                """
                rewards = check_template(sct, monitor, "battle_end_victory_rewards")  # NOTE TODO get screenshot of battle task rewards
                if rewards:
                    click_tap_to_proceed(sct, monitor)
                """
                rewards = check_template(sct, monitor, "tap_to_proceed_btn")  # battle task rewards
                if rewards:
                    move_to_click(rewards)
                    sleep(1)
                click_next(sct, monitor)
                back = check_template(sct, monitor, "battle_end_defeat_back_btn")  # randomly appear: shows recommended deck to play
                if back:
                    move_to_click(back)
                    sleep(1)
                return False  # defeat

            if is_template_matched(sct, monitor, "battle_end_victory"):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Battle ended in Victory")
                click_template(sct, monitor, "battle_end_victory_tap_to_proceed_btn")
                for _ in range(2):
                    click_tap_to_proceed(sct, monitor, sleep_duration=1.5)

                """
                rewards = check_template(sct, monitor, "battle_end_victory_rewards")  # NOTE TODO get screenshot of battle task rewards
                if rewards:
                    click_tap_to_proceed(sct, monitor)
                """
                rewards = check_template(sct, monitor, "tap_to_proceed_btn")  # battle task rewards
                if rewards:
                    move_to_click(rewards)
                    sleep(1)

                click_next(sct, monitor)  # player exp and first-time rewards

                if is_template_matched(sct, monitor, "battle_end_victory_new_battle_unlocked"):
                    click_ok(sct, monitor)

                # sleep(3)
                return True  # victory

            if battle_duration >= 600:  # if >= 10 mins
                print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Battle time exceeded 10 mins")
                return

            i = 8 if battle_duration < 360 else (3 if battle_duration < 600 else 0)
            battle_duration += i
            sleep(i)

            win32gui.SetForegroundWindow(HWND)
            battle_duration += 2
            sleep(2)


def new_app_update(sct, monitor):
    if is_template_matched(sct, monitor, "pokemon_tcgp_update_app"):
        print(f"[{current_datetime().strftime('%H:%M:%S')}] new Pokemon TCGP app version - Updating...")
        click_template(sct, monitor, "pokemon_tcgp_go_to_store_btn", confirm_click=True)

        # Google Play store
        if is_template_matched(sct, monitor, "google_play_screen", method="find"):
            click_template(sct, monitor, "google_play_update_btn", confirm_click=True)
            sleep(17.5)

            max_attempts = 120
            for _ in range(max_attempts):
                play_btn = check_template(sct, monitor, "google_play_play_btn")
                if play_btn:
                    move_to_click(play_btn)
                    print(f"[{current_datetime().strftime('%H:%M:%S')}] new Pokemon TCGP app updated")
                    return
                sleep(1)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to update Pokemon TCGP app")
            if enable_exit_app:
                exit_bluestacks(sct, monitor)
            else:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Quitting Auto Pokemon TCGP")
                sys.exit()


def new_data_update(sct, monitor):
    if is_template_matched(sct, monitor, "pokemon_tcgp_update_data"):
        print(f"[{current_datetime().strftime('%H:%M:%S')}] new Pokemon TCGP data update - Downloading...")
        click_ok(sct, monitor)
        sleep(17.5)

        max_attempts = 120
        for _ in range(max_attempts):
            if is_template_matched(sct, monitor, "start_screen") or go_to_home_screen(sct, monitor):
                print(f"[{current_datetime().strftime('%H:%M:%S')}] new Pokemon TCGP data downloaded")
                return
            sleep(1)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to download Pokemon TCGP data")
            if enable_exit_app:
                exit_bluestacks(sct, monitor)
            else:
                print(f"[{current_datetime().strftime('%H:%M:%S')}] Quitting Auto Pokemon TCGP")
                sys.exit()


def open_booster_packs(sct, monitor, booster_pack: str = desired_booster_packs):
    print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Booster Pack: opening '{booster_pack}' pack")

    select_booster_packs(sct, monitor, booster_pack=booster_pack)
    sleep(1)
    if is_template_matched(sct, monitor, "pack_can_open_a_booster_pack"):
        sleep(4)

    found_package = None
    select_packages = ["pack_select_package_0", "pack_select_package_1"]
    while not found_package:
        for package in select_packages:
            pack = check_template(sct, monitor, package)
            if pack:
                move_to_click(pack)
                sleep(0.5)
                if is_template_matched(sct, monitor, "pack_open_btn"):
                    found_package = True
                break

    click_template(sct, monitor, "pack_open_btn")
    click_skip(sct, monitor)
    open_pack(sct, monitor)

    print(f"[{current_datetime().strftime('%H:%M:%S')}] Booster Pack: finish opening '{booster_pack}'")
    return


def select_booster_packs(sct, monitor, booster_pack: str = desired_booster_packs):
    """Select Desired Pack from Select Expansion window"""
    series_name, booster_pack_key = find_pack_in_series(booster_pack=booster_pack)
    if not booster_pack_key:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find Desired Pack '{booster_pack}' in template dict")
        click_x(sct, monitor)
        return

    if DEBUG:
        print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Booster Pack: selecting '{series_name}': '{booster_pack}'")

    click_template(sct, monitor, "pack_select_other_booster_packs_btn", confirm_click=True)

    # Select Expansion window
    select_expansion = finding_template(sct, monitor, "pack_select_expansion_window")
    select_expansion = offset_boxes(select_expansion, y_offset=375)

    click_template(sct, monitor, series_name, color_match=False)

    max_scroll_attempts = 10
    for i in range(max_scroll_attempts):
        booster_pack_loc = check_template(sct, monitor, booster_pack_key, threshold=0.8)
        if booster_pack_loc:
            move_to_click(booster_pack_loc)
            sleep(1)
            if is_template_matched(sct, monitor, "pack_select_other_booster_packs_btn", method="find"):
                return True
        else:
            # scroll down to reveal more packs
            mouse_drag_scroll(select_expansion, y_offset=-350, duration=0.5)
            if i > max_scroll_attempts-3:
                sleep(0.50)
    else:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find Pack '{booster_pack}' in {series_name} after {max_scroll_attempts} attempts")
        click_x(sct, monitor)
        return


def find_pack_in_series(booster_pack: str = desired_booster_packs):
    """Find which series a pack belongs to and return the template key"""
    for series_name, series_packs in BOOSTER_PACK_TO_TEMPLATES.items():
        if booster_pack in series_packs:
            return series_name, series_packs[booster_pack]
    return None, None


def open_pack(sct, monitor):
    # while loop for multiple card packs
    # multiple card packs is super rare occurrence (happened once as gift)
    if not is_template_matched(sct, monitor, "pack_open_slice", method="find", max_attempts=30):
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] No pack found to slices open")
        return

    for _ in range(10):
        open_pack_slice(sct, monitor)
        click_template_nonstop_until(sct, monitor, click_template="tap_and_hold_btn", stop_templates="next_btn", click_hold=True, click_hold_duration=2.0)
        click_next(sct, monitor)
        sleep(6)
        if not is_template_matched(sct, monitor, "pack_open_slice"):
            break

    if is_template_matched(sct, monitor, "card_milestone"):  # collection milestones
        click_tap_to_proceed(sct, monitor)
        sleep(3)

    if is_template_matched(sct, monitor, "card_new_dex"):  # if new cards, register to dex
        for _ in range(2):
            click_skip(sct, monitor)
            sleep(1)
        click_next(sct, monitor)
        sleep(1)

    if is_template_matched(sct, monitor, "ok_btn"):
        click_ok(sct, monitor)  # claim shinedust
        sleep(1)
    return


def open_pack_slice(sct, monitor):
    """Trace line to open Pack"""
    for i in range(20):
        open_slice = check_template(sct, monitor, "pack_open_slice", color_match=False, threshold=0.85)
        if not open_slice:
            return True

        # Find the bounding box with the smallest x-coordinate
        boxes = min(open_slice, key=lambda box: box[0])

        boxes = offset_boxes(boxes, zero_w_h=True)
        mouse_drag_scroll(boxes, x_offset=500, duration=0.5, drag=True)
        # pyautogui.moveTo(x_left, y_left, duration=0.5)
        # pyautogui.drag(xOffset=500, yOffset=0, duration=0.5, button='left')
        sleep(0.25)
    else:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to slice open pack")
    return


def wonder_pick_random_card(sct, monitor):
    cards = finding_template(sct, monitor, "wonder_pick_pick_a_card_back", group_rectangles=True)
    if len(cards) > 0:
        if DEBUG:
            print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Found {len(cards)} card backs to randomly choose")
            # print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] Cards are: {cards}")
        card = random.choice(cards)
        card_index = cards.index(card)
        print(f"[{current_datetime().strftime('%H:%M:%S')}] Random card choice is #{card_index+1}: {card}")
        move_to_click(card)
        sleep(7.5)
    else:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find card backs to randomly pick")
    return


def check_if_home_screen(sct, monitor):
    templates = ["home_missions_btn_0", "home_missions_btn_1"]
    if is_template_matched(sct, monitor, "home_btn_1") \
        and is_template_matched(sct, monitor, templates):
        return True
    return False


def go_to_home_screen(sct, monitor):
    if check_if_home_screen(sct, monitor):
        return True

    templates = ["home_btn_0", "home_btn_1", "home_btn_level_up"]
    max_attempts = 120
    for _ in range(max_attempts):
        for template in templates:
            home = check_template(sct, monitor, template)
            if home:
                move_to_click(home)
                for _ in range(10):
                    if check_if_home_screen(sct, monitor):
                        sleep(1.5)  # TEST cut to 1.5 from 3
                        return True
                    sleep(0.1)
        sleep(0.25)
    else:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Couldn't get to Home screen")
        return False


def go_to_booster_pack_screen(sct, monitor):
    if is_template_matched(sct, monitor, "pack_select_other_booster_packs_btn"):
        return True

    go_to_home_screen(sct, monitor)

    if DEBUG:
        print(f"\n[DEBUG {current_datetime().strftime('%H:%M:%S')}] Opening Booster Pack screen")

    # different approach to "home_pack" template, which gets updated constantly
    home_pack_btn = "home_pack_expansion_btn"
    home_pack = check_template(sct, monitor, home_pack_btn)
    if home_pack:
        home_pack_loc = offset_boxes(home_pack, x_offset=-200, y_offset=150)
        while True:
            move_to_click(home_pack_loc)
            sleep(1)
            if not check_template(sct, monitor, "home_wonder_pick_btn"):
                break
    else:
        print(f"\n[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find {home_pack_btn} at Home screen")
        return False

    templates = ["pack_can_open_a_booster_pack", "pack_select_other_booster_packs_btn"]
    max_attempts = 40
    for _ in range(max_attempts):
        for template in templates:
            pack_screen = check_template(sct, monitor, template)
            if pack_screen:
                if DEBUG and template == "pack_can_open_a_booster_pack":
                    print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] can open a Booster Pack")
                elif DEBUG:
                    print(f"[DEBUG {current_datetime().strftime('%H:%M:%S')}] at Booster Pack screen")
                return True
        sleep(0.25)
    else:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to get to Booster Pack screen")
        return False


def go_to_battle_screen(sct, monitor):
    if go_to_home_screen(sct, monitor):
        templates = ["home_battle_btn_0", "home_battle_btn_0_dot"]
        max_attempts = 120
        for _ in range(max_attempts):
            for template in templates:
                battle = check_template(sct, monitor, template)
                if battle:
                    move_to_click(battle)
                    for _ in range(10):
                        if not is_template_matched(sct, monitor, template):
                            sleep(3)
                            return True
                        sleep(0.1)
            sleep(0.25)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Couldn't get to Battle screen")
            return False


def go_to_missions_screen(sct, monitor):
    if go_to_home_screen(sct, monitor):
        templates = ["home_missions_btn_0", "home_missions_btn_1"]
        max_attempts = 120
        for _ in range(max_attempts):
            for template in templates:
                missions = check_template(sct, monitor, template)
                if missions:
                    move_to_click(missions)
                    for _ in range(10):
                        if not is_template_matched(sct, monitor, template):
                            sleep(5)
                            return True
                        sleep(0.1)
            sleep(0.25)
        else:
            print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Couldn't get to Home screen")
            return False


def click_next(sct, monitor, sleep_duration: float = 1.0, confirm_click: bool = True):
    boxes = finding_template(sct, monitor, "next_btn")
    if boxes:
        move_to_click(boxes)
        sleep(sleep_duration)
        if confirm_click:
            max_attempts = 120
            for _ in range(max_attempts):
                matched = check_template(sct, monitor, template="next_btn")
                if matched:
                    move_to_click(boxes)
                if not matched:
                    break
                sleep(sleep_duration/4)
        return


def click_ok(sct, monitor, sleep_duration: float = 1.0, confirm_click: bool = True):
    boxes = finding_template(sct, monitor, "ok_btn")
    if boxes:
        move_to_click(boxes)
        sleep(sleep_duration)
        if confirm_click:
            max_attempts = 120
            for _ in range(max_attempts):
                matched = check_template(sct, monitor, template="ok_btn")
                if matched:
                    move_to_click(boxes)
                if not matched:
                    break
                sleep(sleep_duration/4)
        return


def click_skip(sct, monitor, sleep_duration: float = 1.0, confirm_click: bool = False):
    boxes = finding_template(sct, monitor, "skip_btn")
    if boxes:
        move_to_click(boxes)
        sleep(sleep_duration)
        if confirm_click:
            max_attempts = 120
            for _ in range(max_attempts):
                matched = check_template(sct, monitor, template="skip_btn")
                if matched:
                    move_to_click(boxes)
                if not matched:
                    break
                sleep(sleep_duration/4)
        return


def click_x(sct, monitor, sleep_duration: float = 1.0, confirm_click: bool = True):
    boxes = finding_template(sct, monitor, "x_close_btn")
    if boxes:
        move_to_click(boxes)
        sleep(sleep_duration)
        if confirm_click:
            max_attempts = 120
            for _ in range(max_attempts):
                matched = check_template(sct, monitor, template="x_close_btn")
                if matched:
                    move_to_click(boxes)
                if not matched:
                    break
                sleep(sleep_duration/4)
        return


def click_back(sct, monitor, sleep_duration: float = 1.0, confirm_click: bool = True):
    boxes = finding_template(sct, monitor, "back_arrow_btn")
    if boxes:
        move_to_click(boxes)
        sleep(sleep_duration)
        if confirm_click:
            max_attempts = 120
            for _ in range(max_attempts):
                matched = check_template(sct, monitor, template="back_arrow_btn")
                if matched:
                    move_to_click(boxes)
                if not matched:
                    break
                sleep(sleep_duration/4)
        return


def click_tap_and_hold(sct, monitor):
    tap_hold = finding_template(sct, monitor, "tap_and_hold_btn")
    if tap_hold:
        loc = get_click_location(tap_hold)
        while True:
            pyautogui.moveTo(loc)
            pyautogui.mouseDown()
            sleep(3)
            pyautogui.mouseUp()
            sleep(0.5)
            if not is_template_matched(sct, monitor, "tap_and_hold_btn"):
                return


def click_tap_to_proceed(sct, monitor, sleep_duration: float = 1.0, confirm_click: bool = False):
    boxes = finding_template(sct, monitor, "tap_to_proceed_btn")
    if boxes:
        move_to_click(boxes)
        sleep(sleep_duration)
        if confirm_click:
            max_attempts = 120
            for _ in range(max_attempts):
                matched = check_template(sct, monitor, template="tap_to_proceed_btn")
                if matched:
                    move_to_click(boxes)
                if not matched:
                    break
                sleep(sleep_duration/4)
        return


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
    else:
        print(f"[{current_datetime().strftime('%H:%M:%S')}] BlueStacks window not found")


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
        print(f"[{current_datetime().strftime('%H:%M:%S')}] None of the BlueStacks processes are running. Launching BlueStacks...")
        try:
            subprocess.Popen(EXE_PATH, shell=False)  # launch BlueStacks
            while True:
                sleep(1)
                if is_process_running():
                    break
            sleep(3)

            '''workaround for win32gui.SetForegroundWindow() to work'''
            # runs new py script and exit the old one
            restart_script()

        except PermissionError as e:
            print(f"PermissionError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print(f"[{current_datetime().strftime('%H:%M:%S')}] BlueStacks is running")
        win32gui.SetForegroundWindow(HWND)


def restart_script():
    print(f"[{current_datetime().strftime('%H:%M:%S')}] Restarting py script")
    python = sys.executable
    script = Path(__file__).resolve()
    subprocess.run([python, script] + sys.argv[1:])  # run new py
    sys.exit()  # exit old py


def exit_bluestacks(sct, monitor):
    win32gui.SetForegroundWindow(HWND)
    x = finding_template(sct, monitor, "bluestacks_x")
    if not x:
        print(f"[{current_datetime().strftime('%H:%M:%S')}] Failed to find BlueStacks X button")
        return

    print(f"\n[{current_datetime().strftime('%H:%M:%S')}] Exiting BlueStacks")
    move_to_click(x)
    sleep(1)
    close = finding_template(sct, monitor, "bluestacks_close")
    if not close:
        print(f"[ERROR {current_datetime().strftime('%H:%M:%S')}] Failed to find BlueStacks close button")
        return

    move_to_click(close)
    sys.exit()
    return


def main():
    print(f"\n[{current_datetime().strftime('%Y-%m-%d %H:%M:%S UTC')}] Starting Auto Pokemon TCGP...\n")
    initialize_hwnd()
    with mss() as sct:
        monitor = sct.monitors[1]
        launch_game()
        bot = Bot()

        bot.start_game(sct, monitor)
        bot.booster_packs(sct, monitor)
        bot.gifts(sct, monitor)
        bot.wonder_pick(sct, monitor)
        bot.shop(sct, monitor)
        bot.missions(sct, monitor)
        bot.battle(sct, monitor)

        if enable_exit_app:
            exit_bluestacks(sct, monitor)
        print(f"\n[{current_datetime().strftime('%Y-%m-%d %H:%M:%S UTC')}] Ending Auto Pokemon TCGP\n")


if __name__== "__main__":
    main()

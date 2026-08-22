"""
Auto Pokemon TCG Pocket

An OpenCV Python script designed to automate daily tasks in the Pokemon TCG Pocket using BlueStacks.

Bluestacks Display settings:
    display resolution: 1600x900
    dpi 320
    interface scaling: 100% Default

Enable "Fix Window Size"
    Menu Button (next to the Minimize button, top of player), so the BlueStack Player doesn't accidentally change size

# `DESIRED_BOOSTER_PACKS` choices for config.yaml:
"charizard", "mewtwo", "pikachu", "mew", "dialga", "palkia", "arceus", "shiny", "lunala", "solgaleo", "buzzwole", "eevee", "ho-oh", "lugia", "suicune", "deluxe pack ex"
"mega altaria", "mega blaziken", "mega gyarados", "crimson blaze", "fantastical parade", "paldean wonders", "mega shine", "pulsing aura"
"""


import logging
import psutil
import random
import subprocess
import sys
import win32gui
import win32process
import yaml

from mss import mss
from pathlib import Path
from time import monotonic, sleep

from mss_opencv_pyautogui import MSSOpenCV
from opencv import Match
from templates_dict import BOOSTER_PACK_TO_TEMPLATES, TEMPLATES

logger = logging.getLogger(__name__)


CONFIG_PATH = Path(__file__).parent / "config.yaml"
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

DESIRED_BOOSTER_PACKS: list[str] = [p.lower() for p in CONFIG["desired_booster_packs"]]
ENABLE_CHECK_PACK_SCREEN = CONFIG["enable_check_pack_screen"]
ENABLE_SHOP_BUY_MONTHLY_HOURGLASSES = CONFIG["enable_shop_buy_monthly_hourglasses"]
ENABLE_WONDER_PICK = CONFIG["enable_wonder_pick"]
ENABLE_SPECIAL_WONDER_PICKS = CONFIG["enable_special_wonder_picks"]
ENABLE_EXIT_APP = CONFIG["enable_exit_app"]

ENABLE_EVENT_BATTLE = CONFIG["enable_event_battle"]
ENABLE_BATTLE_DIFFICULTY_FALLBACK = CONFIG["enable_battle_difficulty_fallback"]
DESIRED_BATTLE_DIFFICULTY: str = CONFIG["desired_battle_difficulty"].lower()
BATTLE_CHECK_TIME = CONFIG["battle_check_time"]
ENABLE_BATTLE_DEFEAT_REDO = CONFIG["enable_battle_defeat_redo"]
ENABLE_BATTLE_VICTORY_REPEAT = CONFIG["enable_battle_victory_repeat"]

DEBUG: bool = CONFIG["debug"]
EXE_PATH = r'"C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64 --cmd launchApp --package "jp.pokemon.pokemontcgp" --source desktop_shortcut'
BLUESTACKS_EXE = r"C:\Program Files\BlueStacks_nxt\HD-Player.exe"
BLUESTACKS_ARGS = [
    "--instance", "Pie64",
    "--cmd", "launchApp",
    "--package", "jp.pokemon.pokemontcgp",
    "--source", "desktop_shortcut",
]
HWND = None
PROCESS_NAME = ["BlueStacks", "BlueStacks App Player", "HD-Player", ]
EXE_NAME = "HD-Player.exe"
SCRIPT_DIR = Path(__file__).resolve().parent

DIFFICULTIES = ["beginner", "intermediate", "advanced", "expert"]
DIFF_TO_TEMPLATE_KEY = {
    "beginner": "battle_diff_beginner",
    "intermediate": "battle_diff_intermediate",
    "advanced": "battle_diff_advanced",
    "expert": "battle_diff_expert",
}


class Bot:
    def __init__(self, sct, monitor):
        self.utils = MSSOpenCV(
            sct=sct,
            search_region=monitor,
            templates=TEMPLATES,
            debug=DEBUG,
            color_match=False,
            color_space="bgr",
            script_dir=SCRIPT_DIR,
        )
        self.booster_packs_available = None
        self.gifts_available = None
        self.wonder_pick_sneak_peeks_available = None
        self.shop_daily_gifts_available = None
        self.missions_rewards_available = None
        self.have_leveled_up = None
        self.battle_count = 0
        self.battle_defeat_count = 0
        self.battle_victory_count = 0
        self.battle_tie_count = 0

    def check_booster_pack(self):
        if self.booster_packs_available:
            return True

        if self.utils.wait_for_match("pack_can_open_a_booster_pack", timeout=1.5):
            self.booster_packs_available = True
            logger.info("Booster Pack available to be open")
            return True

        self.booster_packs_available = False
        return False

    def check_gifts(self):
        if self.gifts_available:
            return True

        if self.utils.check_match("home_gifts_btn", threshold=0.95):
            logger.debug("Gifts available")
            self.gifts_available = True
            return True

        logger.debug("Gifts not available")
        self.gifts_available = False
        return False

    def check_shop(self):
        if self.shop_daily_gifts_available:
            return True

        if self.utils.check_match("home_shop_btn"):
            logger.debug("Shop's Daily Gifts available")
            self.shop_daily_gifts_available = True
            return True

        logger.debug("Shop's Daily Gifts not available")
        self.shop_daily_gifts_available = False
        return False

    def check_missions(self):
        if self.missions_rewards_available:
            return True

        timeout = 15.0
        start = monotonic()
        while monotonic() - start < timeout:
            if self.utils.check_match(["home_missions_btn_0", "home_missions_btn_0_mark"]):
                logger.debug("Missions rewards not available")
                return False
            if self.utils.check_match("home_missions_btn_1"):
                logger.debug("Missions rewards available")
                self.missions_rewards_available = True
                return True

        self.missions_rewards_available = False
        logger.error("Failed to find Missions at Home screen")
        return False

    def check_news(self):
        if self.utils.wait_for_match("news_window", timeout=1.5):
            logger.info("Fresh News available")
            self.click_x()
            return True
        return False

    def check_level_up(self):
        if self.have_leveled_up:
            return True

        if self.utils.check_match("home_btn_level_up", color_match=True):
            self.have_leveled_up = True
            logger.debug("Level Up available")
            return True

        self.have_leveled_up = False
        return False

    def _handle_level_up(self):
        if self.have_leveled_up:
            if self.utils.wait_for_match("level_up", timeout=7.0):
                self.click_tap_to_proceed()
                if self.utils.wait_for_match("level_up_unlocked", timeout=2.0):
                    self.click_ok()
                logger.info("Leveled up!")
                return True
            return False

    def new_app_update(self):
        if not self.utils.check_match("pokemon_tcgp_update_app"):
            return False

        logger.info("New Pokemon TCGP app version - Updating...")
        self.utils.click_template("pokemon_tcgp_go_to_store_btn", confirm_click=True)

        # Google Play store
        if self.utils.wait_for_match("google_play_screen", timeout=10.0):
            self.utils.click_template("google_play_update_btn", confirm_click=True)
            sleep(17.5)

            play_btn = self.utils.wait_for_match("google_play_play_btn", timeout=120.0)
            if play_btn:
                self.utils.move_to_click(play_btn)
                logger.info("New Pokemon TCGP app updated")
                return True
        else:
            logger.error("Failed to update Pokemon TCGP app")
            if ENABLE_EXIT_APP:
                exit_bluestacks(self)
            else:
                logger.info("Quitting Auto Pokemon TCGP")
                sys.exit()

    def new_data_update(self):
        if self.utils.check_match("pokemon_tcgp_update_data"):
            logger.info("New Pokemon TCGP data update - Downloading...")
            self.click_ok()
            sleep(17.5)

            if self.utils.wait_for_match("start_screen", timeout=60.0):
                logger.info("New Pokemon TCGP data downloaded")
                return
            if self.go_to_home_screen():
                logger.info("New Pokemon TCGP data downloaded")
                return

            logger.error("Failed to download Pokemon TCGP data")
            if ENABLE_EXIT_APP:
                exit_bluestacks(self)
            else:
                logger.info("Quitting Auto Pokemon TCGP")
                sys.exit()

    def new_privacy_update(self):
        if not self.utils.check_match("pokemon_tcgp_update_privacy_notice"):
            return False

        logger.info("New Privacy update")
        self.click_ok()
        self.utils.click_template("pokemon_tcgp_update_privacy_notice_btn")
        self.click_x()
        if self.utils.wait_for_match("pokemon_tcgp_update_checked_agree_to", timeout=10.0):
            self.click_ok()
        return True

    def new_terms_of_use_update(self):
        if not self.utils.check_match("pokemon_tcgp_update_terms_of_use"):
            return False

        logger.info("New Terms of Use update")
        self.click_ok()
        self.utils.click_template("pokemon_tcgp_update_terms_of_use_btn")
        self.click_x()
        if self.utils.wait_for_match("pokemon_tcgp_update_checked_agree_to", timeout=10.0):
            self.click_ok()
        return True

    def start_game(self):
        timeout = 180.0
        start_time = monotonic()
        while monotonic() - start_time < timeout:
            start_screen = self.utils.check_match("start_screen")
            if start_screen:
                logger.info("Starting Game")
                self.utils.click_template(start_screen)
                self.utils.wait_for_match(["home_btn_0", "home_btn_1"], timeout=10.0)

            bluestacks_enter_pokemon_tcgp(self)
            self.new_app_update()
            self.new_data_update()
            self.new_privacy_update()
            self.new_terms_of_use_update()

            # Go to Home screen if start elsewhere in-game
            if self.utils.check_match("home_btn_0") \
                and (not self.check_booster_pack() \
                    or self.utils.check_match("pack_select_other_booster_packs_btn")):
                self.go_to_home_screen()
                self.booster_packs_available = None

            self.check_news()

            if self.check_if_home_screen():
                logger.debug("Started at Home screen")
                self.utils.wait_for_match("home_missions_btn_1", timeout=5.0)
                self.check_gifts()
                self.check_shop()
                self.check_missions()
                return False

            if self.check_booster_pack():
                return True
        else:
            logger.error("Failed to Start Game")
            if ENABLE_EXIT_APP:
                exit_bluestacks(self)
            return False

    def check_if_home_screen(self):
        templates = ["home_missions_btn_0", "home_missions_btn_0_mark", "home_missions_btn_1"]
        if self.utils.check_match("home_btn_1") \
            and self.utils.check_match(templates):
            return True
        return False

    def go_to_home_screen(self):
        if self.check_if_home_screen():
            return True

        self.check_level_up()

        templates = ["home_btn_0", "home_btn_1", "home_btn_level_up"]
        timeout = 15.0
        start = monotonic()
        while monotonic() - start < timeout:
            for template in templates:
                home = self.utils.check_match(template)
                if home:
                    self.utils.click_template(home)
                    if self.utils.wait_for_match("home_btn_1", timeout=5.0):
                        sleep(4.5)
                        if self.have_leveled_up:
                            self._handle_level_up()
                        return True
        else:
            logger.error("Couldn't get to Home screen")
            return False

    def go_to_booster_pack_screen(self):
        if self.utils.check_match("pack_select_other_booster_packs_btn"):
            return True

        self.go_to_home_screen()

        logger.debug("Opening Booster Pack screen")

        home_pack_btn = "home_pack_expansion_btn"
        home_pack = self.utils.check_match(home_pack_btn)
        if home_pack:
            home_pack_loc = [b.offset(-200, 150) for b in home_pack]
            while True:
                self.utils.move_to_click(home_pack_loc)
                if self.utils.wait_for_unmatch("home_wonder_pick_btn", timeout=5.0):
                    break
        else:
            logger.error(f"Failed to find {home_pack_btn} at Home screen")
            return False

        templates = ["pack_can_open_a_booster_pack", "pack_select_other_booster_packs_btn"]
        max_attempts = 40
        for _ in range(max_attempts):
            for template in templates:
                pack_screen = self.utils.check_match(template)
                if pack_screen:
                    if template == "pack_can_open_a_booster_pack":
                        logger.debug("can open a Booster Pack")
                    else:
                        logger.debug("at Booster Pack screen")
                    return True
            sleep(0.5)
        else:
            logger.error("Failed to get to Booster Pack screen")
            return False

    def booster_packs(self):
        if self.booster_packs_available is False:
            return

        # Home screen
        if (self.booster_packs_available is None or self.booster_packs_available) \
            and self.check_if_home_screen():
            self.go_to_booster_pack_screen()
            self.check_booster_pack()

        # Booster Pack screen
        if self.booster_packs_available and self.utils.wait_for_match("pack_select_other_booster_packs_btn"):
            self._open_booster_packs()

        self.booster_packs_available = False
        self.go_to_home_screen()
        self.utils.wait_for_match("home_missions_btn_1", timeout=5.0)
        self.check_news()
        return

    def _open_booster_packs(self, booster_pack: str | None = None):
        if booster_pack is None:
            booster_pack = random.choice(DESIRED_BOOSTER_PACKS)
        logger.info(f"Booster Pack: opening '{booster_pack}' pack")

        self._select_booster_packs(booster_pack)
        if self.utils.wait_for_match("pack_can_open_a_booster_pack", timeout=5.0):
            self.utils.wait_for_match("pack_open_btn", timeout=5.0)

        found_package = None
        select_packages = ["pack_select_package_0", "pack_select_package_1"]
        while not found_package:
            for package in select_packages:
                pack = self.utils.check_match(package)
                if pack:
                    self.utils.click_template(pack)
                    if self.utils.wait_for_match("pack_open_btn", timeout=3.0):
                        found_package = True
                    break

        self.utils.click_template("pack_open_btn", confirm_click=True)
        self.click_skip()
        self.open_pack()

        logger.info(f"Booster Pack: finish opening '{booster_pack}'")
        return

    def _select_booster_packs(self, booster_pack: str):
        """Select Desired Pack from Select Expansion window"""
        series_name, booster_pack_key = self._find_pack_in_series(booster_pack)
        if not booster_pack_key:
            logger.error(f"Failed to find Desired Pack '{booster_pack}' in template dict")
            self.click_x()
            return False

        logger.debug(f"Booster Pack: selecting '{series_name}': '{booster_pack}'")

        self.utils.click_template("pack_select_other_booster_packs_btn", confirm_click=True)

        # Select Expansion window
        select_expansion = self.utils.wait_for_match("pack_select_expansion_window", timeout=15.0)
        if not select_expansion:
            logger.error(f"Failed to find Desired Pack '{booster_pack}'")
            self.click_x()
            return False

        select_expansion = [b.offset(0, 375) for b in select_expansion]

        self.utils.click_template(series_name, color_match=False)

        max_scroll_attempts = 10
        for i in range(max_scroll_attempts):
            booster_pack_loc = self.utils.check_match(booster_pack_key, threshold=0.8)
            if booster_pack_loc:
                self.utils.click_template(booster_pack_loc)
                self.utils.wait_for_match("pack_select_other_booster_packs_btn", timeout=3.0)
                if not self.utils.check_match("pack_cannot_be_obtained"):
                    return True
                else:
                    logger.warning(f"Pack '{booster_pack}' not found, trying random pack as fallback")
                    random_pack = random.choice(DESIRED_BOOSTER_PACKS)
                    if random_pack != booster_pack:
                        return self._select_booster_packs(random_pack)

                    return False
            else:
                # scroll down to reveal more packs
                self.utils.mouse_scroll(select_expansion, y_offset=-350, duration=0.5)
                if i > max_scroll_attempts - 3:
                    sleep(0.50)
        else:
            logger.error(f"Failed to find Pack '{booster_pack}' in {series_name} after {max_scroll_attempts} attempts")
            self.click_x()
            return False

    def _find_pack_in_series(self, booster_pack: str):
        """Find which series a pack belongs to and return the template key"""
        for series_name, series_packs in BOOSTER_PACK_TO_TEMPLATES.items():
            if booster_pack in series_packs:
                return series_name, series_packs[booster_pack]
        return None, None

    def open_pack(self):
        if not self.utils.wait_for_match("pack_open_slice", timeout=2.5):
            logger.error("No pack found to slices open")
            return False

        # while loop for multiple card packs
        for _ in range(10):
            self._open_pack_slice()
            self.utils.click_template_nonstop_until(
                target_template="tap_and_hold_btn",
                stop_templates="next_btn",
                click_hold=True,
                click_hold_duration=2.0,
            )
            self.click_next()
            if not self.utils.wait_for_match("pack_open_slice", timeout=10.0):
                break

        temp = ["card_milestone", "card_new_dex", "ok_btn"]
        everything = self.utils.wait_for_match(temp)
        if not everything:
            return False

        self._handle_card_collection_milestone()
        self._handle_card_new_dex()

        if self.utils.wait_for_match("ok_btn", timeout=2.5):
            self.click_ok()  # claim shinedust
        return

    def _open_pack_slice(self):
        """Trace line to open Pack"""
        stop_templates = ["tap_and_hold_btn", "next_btn"]
        for i in range(60):
            if self.utils.check_match(stop_templates):
                return True

            open_slice = self.utils.check_match("pack_open_slice", color_match=False, threshold=0.85)
            if open_slice:
                # Find the bounding box with the smallest x-coordinate (leftmost slice)
                leftmost = min(open_slice, key=lambda box: box.x)

                boxes = [Match(leftmost.x, leftmost.y, 0, 0)]
                self.utils.mouse_scroll(boxes, x_offset=500, duration=0.5, drag=True)
            sleep(0.5)
        else:
            logger.error("Failed to slice open pack")
        return

    def _handle_card_collection_milestone(self):
        if not self.utils.wait_for_match("card_milestone", timeout=2.5):  # card collection milestone
            return False

        logger.info("Card Collection Milestone reached!")
        self.click_tap_to_proceed()
        sleep(3)
        return True


    def _handle_card_new_dex(self):
        if not self.utils.wait_for_match("card_new_dex", timeout=2.5):  # if new cards, register to dex
            return False

        logger.info("New Card added to the Dex!")
        for _ in range(2):
            self.click_skip()
        self.click_next()
        return True

    def _handle_card_mission_reward(self):
        # NOTE TODO
        """
        if not self.utils.wait_for_match("", timeout=1.0):
            return False
        logger.info("Card mission reward collected")
        self.click_skip()
        """

    def _handle_item_acquired(self):
        # NOTE TODO
        """
        if not self.utils.wait_for_match("item_acquired_window", timeout=2.5):
            return False
        logger.info("Item Acquired")
        self.click_ok()
        """

    def gifts(self):
        if not self.gifts_available and self.go_to_home_screen():
            self.check_gifts()

        if not self.gifts_available:
            return False

        logger.info("Gifts")
        if self.go_to_home_screen():
            self.utils.click_template("home_gifts_btn", confirm_click=True)

        # Gifts screen
        if self.utils.wait_for_match("gifts_screen", timeout=15.0):
            sleep(1.0)

            claim_count = self.utils.wait_for_match("gifts_claim_btn", color_match=False, threshold=0.95)
            if claim_count is not None:
                if len(claim_count) >= 3:
                    logger.info(f"Gifts: at least {len(claim_count)} gifts to claim")
                else:
                    logger.info(f"Gifts: {len(claim_count)} gifts to claim")

            claim_all = self.utils.wait_for_match("gifts_claim_all_btn", timeout=1.0, threshold=0.98, color_match=True)
            if claim_all:
                self.utils.click_template("gifts_claim_all_btn", confirm_click=True)
                # Fail-safe when claim_all click didn't register / OK pops up
                if self.utils.wait_for_match("ok_btn", timeout=1.5):
                    self.click_ok()
                    self.open_pack()
                self.utils.wait_for_match("gifts_screen")
                self.utils.wait_for_unmatch("gifts_claim_all_btn", timeout=5.0, threshold=0.98, color_match=True)

            claimed_count = 0
            while True:
                claim_btn = self.utils.check_match("gifts_claim_btn")
                if not claim_btn:
                    break
                self.utils.click_template("gifts_claim_btn", confirm_click=True)
                self.click_ok()
                self.open_pack()
                claimed_count += 1
                self.utils.wait_for_match("gifts_screen")  # wait for gifts_screen before next action

            if self.utils.check_match("gifts_no_claimable_items_screen"):
                self.gifts_available = False
                self.click_x()

            if claim_count is not None and claimed_count != len(claim_count):
                logger.info(f"Gifts: claimed {claimed_count} gift packs")
            return True

    def shop(self):
        if self.shop_daily_gifts_available is None and self.go_to_home_screen():
            self.check_shop()

        if not self.shop_daily_gifts_available:
            return False

        logger.info("Shop")
        if self.go_to_home_screen():
            self.utils.click_template("home_shop_btn", confirm_click=True)

        daily_gift = self.utils.wait_for_match("shop_daily_gift", timeout=15.0)
        if not daily_gift:
            logger.error("Failed to find Shop's Daily Gifts button")
            return False

        self.utils.click_template("shop_daily_gift", confirm_click=True)
        self.shop_daily_gifts_available = False
        logger.info("Shop's Daily Gifts claimed")
        self.click_ok()

        # Option to buy monthly hourglasses (2nd and 28th of month)
        if ENABLE_SHOP_BUY_MONTHLY_HOURGLASSES:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            JST = ZoneInfo("Asia/Tokyo")
            is_monthly_day = datetime.now(JST).day in (2, 28)

            if is_monthly_day:
                logger.info("Shop: checking for monthly hourglasses")
                self.utils.mouse_scroll(daily_gift, y_offset=-300)

                templates = ["shop_pack_hourglass", "shop_wonder_hourglass"]
                for template in templates:
                    hourglass = self.utils.check_match(template, color_match=True)
                    if hourglass:
                        for i in hourglass:
                            self.utils.click_template(i, confirm_click=True)

                            max_qty_btn = self.utils.check_match("shop_max_qty_btn_1", color_match=True)
                            if max_qty_btn:
                                self.utils.click_template(max_qty_btn)

                            self.click_ok()  # Buy
                            self.click_ok(confirm_click=True)  # Received
                logger.debug("Shop: Monthly Hourglasses purchased")

        self.click_x(sleep_duration=3.0)

        for _ in range(20):  # Wait for Home screen
            if self.check_if_home_screen():
                break
            sleep(0.5)
        return True

    def _check_wonder_pick_sneak_peeks(self):
        if not self.utils.check_match("home_wonder_pick_sneak_peeks"):
            self.wonder_pick_sneak_peeks_available = False
            return False
        logger.debug("Wonder Pick's Sneak Peeks available")
        self.wonder_pick_sneak_peeks_available = True
        return True

    def _handle_wonder_pick_sneak_peeks(self):
        if not self.wonder_pick_sneak_peeks_available:
            return

        timeout = 15.0
        start = monotonic()
        while monotonic() - start < timeout:
            if self.utils.check_match("wonder_pick_sneak_peek_active_icon"):
                logger.info("Wonder Pick's Sneak Peek is active")

            # wait for Sneak Peek screen
            if self.utils.check_match("wonder_pick_sneak_peek_take_a_peek_btn_0"):
                self._wonder_pick_random_card()
                self.utils.click_template("wonder_pick_sneak_peek_take_a_peek_btn_1", confirm_click=True)

            # normal Random Card Pick screen
            if self.utils.check_match("wonder_pick_pick_a_card_screen"):
                return True
        else:
            logger.error("Failed to handle Sneak Peeks")
            return False

    def wonder_pick(self):
        if self.wonder_pick_sneak_peeks_available is None and self.go_to_home_screen():
            self._check_wonder_pick_sneak_peeks()

        logger.info("Wonder Pick")
        if self.go_to_home_screen():
            self.utils.click_template("home_wonder_pick_btn", confirm_click=True)

        if not self.utils.wait_for_match("wonder_pick_screen", timeout=15.0):
            logger.error("Failed to get to Wonder Pick screen. Returning to Home...")
            self.go_to_home_screen()
            return

        # Wonder Pick screen
        WONDER_PICKS = ["wonder_pick_chansey", "wonder_pick_rare", "wonder_pick_bonus"]
        SPECIAL_PICKS = ["wonder_pick_chansey", "wonder_pick_rare"]
        for pick in WONDER_PICKS:
            matched_pick = self.utils.wait_for_match(pick, timeout=0.75)
            if not matched_pick:
                logger.debug(f"Wonder Pick '{pick}' not available")
                continue

            if not ENABLE_SPECIAL_WONDER_PICKS and pick in SPECIAL_PICKS:
                logger.debug(f"Wonder Pick: skipping {pick}; 'ENABLE_SPECIAL_WONDER_PICKS' is {ENABLE_SPECIAL_WONDER_PICKS} in config.yaml")
                self.utils.mouse_scroll(matched_pick, y_offset=-220)
                continue

            self.utils.click_template(pick, confirm_click=True)

            if pick in SPECIAL_PICKS and self.utils.check_match("wonder_pick_no_stamina"):
                logger.info(f"Wonder Pick: no stamina for '{pick}'")
                self.click_x()
                self.utils.mouse_scroll(matched_pick, y_offset=-250)
                continue

            # case when Chansey or Rare Pick covers "home_wonder_pick_sneak_peeks"
            ok_btns = ["ok_btn", "wonder_pick_sneak_peek_ok_btn"]
            timeout = 15.0
            start = monotonic()
            found_ok_btn = False
            while monotonic() - start < timeout:
                for ok_btn in ok_btns:
                    matched_ok_btn = self.utils.check_match(ok_btn)
                    if matched_ok_btn:
                        if ok_btn == "wonder_pick_sneak_peek_ok_btn":
                            self.wonder_pick_sneak_peeks_available = True
                        self.utils.click_template(ok_btn, confirm_click=True)
                        found_ok_btn = True
                        break
                if found_ok_btn:
                    break
                sleep(0.5)

            logger.info(f"Wonder Pick: '{pick}'")
            self.click_skip()

            if self.wonder_pick_sneak_peeks_available:
                self._handle_wonder_pick_sneak_peeks()

            if self.utils.wait_for_match("wonder_pick_pick_a_card_screen", timeout=5.0):
                self._wonder_pick_random_card()

                items = ["wonder_pick_pick_item", "wonder_pick_pick_items"]
                if pick == "wonder_pick_bonus" and self.utils.check_match(items):
                    logger.info("Wonder Pick an Item")
                    for _ in range(2):
                        self.click_tap_to_proceed(sleep_duration=2.0)
                else:
                    logger.info("Wonder Pick a Card")
                    self.click_tap_to_proceed(sleep_duration=2.0)

                while True:
                    self._handle_card_collection_milestone()
                    self._handle_card_new_dex()

                    if self.utils.check_match("wonder_pick_results_screen"):  # Fallback catch
                        self.click_tap_to_proceed()

                    if self.utils.wait_for_match("wonder_pick_screen", timeout=1.0):
                        break

        logger.debug("Wonder Pick completed")
        self.go_to_home_screen()
        return

    def _wonder_pick_random_card(self):
        cards = self.utils.wait_for_match("wonder_pick_pick_a_card_back", timeout=10.0, group_rectangles=True)
        if len(cards) > 0:
            logger.debug(f"Found {len(cards)} card backs to randomly choose")
            # logger.debug(f"Cards are: {cards}")
            card = random.choice(cards)
            card_index = cards.index(card)
            logger.info(f"Wonder Pick: random card choice: #{card_index + 1} {card}")
            self.utils.click_template(card)
            self.utils.wait_for_match("wonder_pick_results_screen", timeout=10.0)
        else:
            logger.error("Failed to find card backs to randomly pick")
        return

    def go_to_missions_screen(self):
        if not self.go_to_home_screen():
            return False

        templates = ["home_missions_btn_0", "home_missions_btn_0_mark", "home_missions_btn_1"]
        timeout = 15.0
        start = monotonic()
        while monotonic() - start < timeout:
            missions = self.utils.check_match(templates)
            if missions:
                self.utils.click_template(missions, confirm_click=True)
            if self.utils.wait_for_match("x_close_btn"):
                sleep(7.5)
                return True
            sleep(1)
        else:
            logger.error("Couldn't get to Missions screen")
            return False

    def missions(self):
        if not self.missions_rewards_available and self.go_to_home_screen():
            self.check_missions()

        if not self.missions_rewards_available:
            return False

        logger.info("Missions")
        self.go_to_missions_screen()
        # self.utils.wait_for_match(["missions_complete_all_btn", "missions_complete_btn", "missions_themed_collections_btn"]) 
        if not self.utils.wait_for_match(["missions_complete_all_btn", "missions_complete_btn", "missions_themed_collections_btn"]):
            logger.error("Unexpectedly went to Missions with no completed missions")
            return False

        while True:
            self._missions_handle_complete_all_loop()
            self._missions_handle_complete_loop()

            if not self._missions_horizontal_scroll():
                break
            sleep(0.75)

            if self.utils.check_match("missions_tab_premium", color_match=True):
                self._missions_handle_complete_all_loop()  # for case when user has premium
                break

            if self.check_if_home_screen():
                logger.error("Missions: unexpectedly at Home screen")
                return True

        self.missions_themed_collections()

        self.missions_rewards_available = False
        logger.info("Missions clear")
        self.click_x()

        for _ in range(20):  # Wait for Home screen
            if self.check_if_home_screen():
                break
            sleep(0.5)
        return True

    def _missions_horizontal_scroll(self):
        template = "x_close_btn"
        boxes = self.utils.wait_for_match(template, timeout=15.0)
        if boxes:
            boxes = [b.offset(0, -400) for b in boxes]
            self.utils.mouse_scroll(boxes, x_offset=-100, duration=0.2, drag=True)
            return True
        logger.error("Error during Missions horizontal scroll")
        return False

    def _missions_handle_complete_all_loop(self):
        """handle dex missions, bonus week, etc"""
        complete_all = self.utils.check_match("missions_complete_all_btn", threshold=0.95, color_match=True)
        if not complete_all:
            return False

        logger.debug("Handling Missions complete all loop")
        self.utils.click_template(complete_all)
        sleep(7.5)

        break_templates = ["card_new_dex", "ok_btn"]
        for _ in range(5):
            complete_all = self.utils.check_match("missions_complete_all_btn", threshold=0.95, color_match=True)
            if complete_all:
                self.utils.click_template(complete_all)
                self.utils.wait_for_match("ok_btn", timeout=10.0)
                # sleep(6.5)

            ok_btn = self.utils.check_match("ok_btn")
            if ok_btn:
                self.utils.click_template(ok_btn)
                self.utils.wait_for_match("x_close_btn", timeout=10.0)
                self.utils.wait_for_unmatch("missions_complete_all_btn", timeout=2.5)
                # sleep(5)

            # Missions reward: single cards
            if self.utils.check_match("tap_to_proceed_btn"):
                while True:
                    self.click_tap_to_proceed()  # single card reward
                    if self.utils.check_match(break_templates):
                        break
                self._handle_card_new_dex()
                for _ in range(2):
                    ok_btn = self.utils.check_match("ok_btn")
                    if ok_btn:
                        self.utils.click_template(ok_btn, sleep_duration=3.0)

            # Return if at the Missions screen and no complete_all
            if self.utils.check_match("x_close_btn") \
                and not self.utils.check_match("missions_complete_all_btn", color_match=True):
                logger.debug("Finished Missions complete all loop")
                return True

            if self.check_if_home_screen():
                logger.error("Unexpectedly at Home screen")
                return False

            sleep(1)

    def _missions_handle_complete_loop(self):
        """handle deck missions, themed_collections"""
        small_complete = self.utils.check_match("missions_small_complete_btn", color_match=True, color_space="bgr")
        if not small_complete:
            return

        small_complete_ctn: int = 1
        logger.debug("Handling Missions complete loop")
        self.utils.click_template("missions_small_complete_btn", confirm_click=True)

        exit_templates = ["x_close_btn", "back_arrow_btn"]

        while True:
            # small complete btn - shadows in background can make btn slightly darker
            small_complete = self.utils.check_match("missions_small_complete_btn", color_match=True, color_space="bgr")
            if small_complete:
                small_complete_ctn += 1
                logger.info(f"Missions: Handling small complete #{small_complete_ctn}")
                self.utils.click_template("missions_small_complete_btn", confirm_click=True)

            big_complete = self.utils.check_match("missions_big_complete_btn")
            if big_complete:
                self.utils.click_template("missions_big_complete_btn", confirm_click=True)
                for _ in range(2):

                    # we use two check_match over click_ok for missions_themed_collections()
                    ok_btn = self.utils.check_match("ok_btn")
                    if ok_btn:
                        self.click_ok()

                # make sure we're at the missions screen before continuing
                for _ in range(60):
                    # x_close_btn for usual complete loop, back_arrow_btn for themed_collection
                    if self.utils.check_match(exit_templates):
                        break
                    sleep(0.5)
                sleep(1)
                continue

            if self.utils.check_match(exit_templates) \
                and not self.utils.check_match("missions_small_complete_btn", color_match=True, color_space="bgr"):
                if self._missions_handle_expansions():
                    continue
                logger.debug("Finished Missions complete loop")
                return

            if self.check_if_home_screen():
                logger.error("Unexpectedly at Home screen")
                return False

            sleep(1)

    def _missions_handle_expansions(self):
        templates = ["missions_expansions_btn", "missions_expansions_view_more_btn"]
        expansion_btn = None
        for template in templates:
            expansion_btn = self.utils.check_match(template, color_match=True)
            if expansion_btn:
                logger.debug("Missions: Expansions btn detected")
                break

        if expansion_btn:
            self.utils.click_template(expansion_btn)
            if not self.utils.wait_for_match(["missions_expansions_missions_window", "missions_expansions_themed_collections_window"], timeout=5.0):
                return False

            expansions_windows = ["missions_expansions_missions_window", "missions_expansions_themed_collections_window"]
            for template in expansions_windows:
                exp_window = self.utils.check_match(template)
                if exp_window:
                    exp_window_scroll = [b.offset(0, 400) for b in exp_window]
                    max_attempts = 10
                    for _ in range(max_attempts):
                        expansion = self.utils.check_match("missions_expansions_reward_icon")
                        if expansion:
                            self.utils.click_template("missions_expansions_reward_icon", confirm_click=True)
                            return True

                        self.utils.mouse_scroll(exp_window_scroll, y_offset=-450)
                        sleep(0.5)
                    else:
                        self.click_x()
        return False

    def missions_themed_collections(self):
        themed_collection = self.utils.check_match("missions_themed_collections_btn")
        if not themed_collection:
            return

        logger.info("Missions: Themed Collections")
        self.utils.click_template("missions_themed_collections_btn", confirm_click=True)

        self._missions_handle_complete_loop()

        self.utils.click_template("back_arrow_btn", confirm_click=True)
        logger.info("Missions: Themed Collections reward claimed")
        return

    def go_to_battle_screen(self):
        if not self.go_to_home_screen():
            return False

        templates = ["home_battle_btn_0", "home_battle_btn_0_dot"]
        timeout = 15.0
        start = monotonic()
        while monotonic() - start < timeout:
            for template in templates:
                battle = self.utils.check_match(template)
                if battle:
                    self.utils.click_template(battle)
                    if self.utils.wait_for_unmatch(template, timeout=5.0):
                        return True
        else:
            logger.error("Couldn't get to Battle screen")
            return False

    def battle(self):
        if not self.go_to_home_screen():
            logger.error("Failed to go to start Battle")
            return False

        logger.info("Battle")

        self.go_to_battle_screen()

        self.battle_solo_event()

        if self.battle_count >= 1:
            parts = [f"Battle: {self.battle_count} total"]
            if self.battle_victory_count >= 1:
                parts.append(f"{self.battle_victory_count} victories")
            if self.battle_defeat_count >= 1:
                parts.append(f"{self.battle_defeat_count} defeats")
            if self.battle_tie_count >= 1:
                parts.append(f"{self.battle_tie_count} ties")
            logger.info(" | ".join(parts))

            logger.debug("Battle finished")
        self.go_to_home_screen()
        return

    def battle_solo_event(self):
        if not self.go_to_battle_solo_event():
            return False

        logger.info("Battle: Solo Event")

        while True:
            if self.utils.wait_for_match("battle_solo_drop_event_screen", timeout=5.0):
                sleep(1)
                if not self.utils.check_match("battle_solo_event_stamina"):
                    logger.info("Battle: Solo Event: no stamina available")
                    return False
                if not self.select_battle_difficulty():
                    return False
            elif self.utils.wait_for_match(["battle_rules_screen_1", "battle_rules_screen"]):
                logger.debug("Battle ended in Defeat, back at Battle Rules screen")
            else:
                logger.warning("Failed to get to Drop Event screen")
                return False

            self.battle_count += 1
            logger.info(f"Battle #{self.battle_count}")
            battle_result = self._handle_battle_loop()
            if battle_result and not self.gifts_available:
                self.gifts_available = True

            # Wait for Battle screen / handle New Battle Unlocked
            stop_templates = ["battle_solo_drop_event_screen", "back_arrow_btn"]
            for _ in range(15):
                if self.utils.check_match("battle_end_victory_new_battle_unlocked"):
                    logger.info("Battle: New Battle Unlocked")
                    self.click_ok()
                if self.utils.check_match(stop_templates):
                    break
                sleep(1.0)

            if (battle_result and ENABLE_BATTLE_VICTORY_REPEAT) \
                or (not battle_result and ENABLE_BATTLE_DEFEAT_REDO):
                logger.info(f"Battle: continuing after {'Victory' if battle_result else 'Defeat'}")
                continue

            if battle_result:
                logger.info("Battle: finished after Victory")
                return True
            else:
                logger.info("Battle: finished after Defeat")
                return False

    def go_to_battle_solo_event(self):
        timeout = 15.0
        start = monotonic()
        while monotonic() - start < timeout:
            if self.utils.check_match("battle_solo_btn_0"):
                logger.debug("Battle: Solo Event not available")
                sleep(1)
                return False

            # Battle screen
            templates = ["battle_solo_btn_1", ]
            for template in templates:
                solo_btn = self.utils.check_match(template)
                if solo_btn:
                    logger.info("Battle: Solo Event available")
                    self.utils.click_template(solo_btn)

                    # Battle Solo screen
                    if not self.utils.wait_for_match("battle_solo_screen", timeout=0.5):
                        logger.error("Failed to find Battle Solo screen")
                        return False

                    # Check for Drop Event btn or Event btn
                    templates = ["battle_solo_drop_event_btn", "battle_solo_event_btn"]
                    if self.utils.wait_for_match(templates, timeout=0.5):
                        event_btn = self.utils.check_match(templates)
                        if event_btn:
                            self.utils.click_template(event_btn)
                            return True
                    logger.warning("Failed to find Drop Event")
                    return False
            sleep(1)

        else:
            logger.error(f"Failed to find Solo Event after {timeout}s")
            return False

    def select_battle_difficulty(self):
        def find_battle_difficulty_screen(max_attempts: int = 5):
            """Find Battle Difficulty screen and return the difficulty boxes for scrolling"""
            diff_templates = [DIFF_TO_TEMPLATE_KEY[d] for d in DIFFICULTIES]
            return self.utils.wait_for_match(diff_templates, timeout=max_attempts)

        diff_screen = find_battle_difficulty_screen()
        if not diff_screen:
            logger.error("Failed to get to Battle Difficulty screen")
            return False

        logger.debug("Selecting Battle Difficulty")

        try:
            desired_diff_idx = DIFFICULTIES.index(DESIRED_BATTLE_DIFFICULTY)
        except ValueError:
            logger.error(f"Invalid difficulty: {DESIRED_BATTLE_DIFFICULTY}")
            return False

        # Create fallback order: start with desired difficulty and try lower difficulties
        fallback_order = DIFFICULTIES[desired_diff_idx::-1]  # From desired down to beginner

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
            self.utils.mouse_scroll(diff_screen, y_offset=-250)
            sleep(0.5)

            for diff in high_diffs:
                diff_key = DIFF_TO_TEMPLATE_KEY.get(diff)
                desired_diff = self.utils.check_match(diff_key)

                if desired_diff is not None and len(desired_diff) > 1:
                    logger.warning(f"Multiple {diff} instances found on screen, using first match")

                if desired_diff:
                    logger.info(f"Selected difficulty: {diff}")
                    self.utils.move_to_click(desired_diff)
                    return True
                elif not ENABLE_BATTLE_DIFFICULTY_FALLBACK:
                    logger.error(f"Desired difficulty '{DESIRED_BATTLE_DIFFICULTY}' not found")
                    sleep(3)
                    return False
                else:
                    logger.debug(f"Difficulty '{diff}' not available, trying fallback...")

        # If high diffs not found or not applicable, try low difficulties (scroll back up)
        if low_diffs:
            # Only scroll up if we previously scrolled down
            if high_diffs:
                self.utils.mouse_scroll(diff_screen, y_offset=250)  # Scroll back up
                sleep(0.5)

            for diff in low_diffs:
                diff_key = DIFF_TO_TEMPLATE_KEY.get(diff)
                desired_diff = self.utils.check_match(diff_key)

                if desired_diff is not None and len(desired_diff) > 1:
                    logger.warning(f"Multiple {diff} instances found on screen, using first match")

                if desired_diff:
                    logger.info(f"Selected difficulty: {diff}")
                    self.utils.move_to_click(desired_diff)
                    return True
                elif not ENABLE_BATTLE_DIFFICULTY_FALLBACK:
                    logger.error(f"Desired difficulty '{DESIRED_BATTLE_DIFFICULTY}' not found")
                    sleep(3)
                    return False
                else:
                    logger.debug(f"Difficulty '{diff}' not available, trying fallback...")

        logger.error("No battle difficulties available after fallback attempts")
        sleep(3)
        return False

    def _handle_battle_loop(self):
        if not self.utils.wait_for_match(["battle_rules_screen_1", "battle_rules_screen"], timeout=10.0):
            logger.error("Failed to find Battle Rules screen")
            return False

        self.utils.click_template("battle_rules_auto_btn", confirm_click=True)
        self.utils.click_template("battle_rules_battle_btn", confirm_click=True)

        battle_duration = BATTLE_CHECK_TIME or 0
        if battle_duration:
            sleep(battle_duration)
            logger.debug("Battle sleep is over")
            win32gui.SetForegroundWindow(HWND)
            sleep(0.5)

        while True:
            if self.utils.check_match(["battle_end_defeat", "battle_end_tie"]):
                if self.utils.check_match("battle_end_defeat"):
                    logger.info("Battle ended in Defeat")
                    self.battle_defeat_count += 1
                elif self.utils.check_match("battle_end_tie"):
                    logger.info("Battle ended in Tie")
                    self.battle_tie_count += 1
                for _ in range(2):
                    self.click_tap_to_proceed(sleep_duration=1.25, confirm_click=False)

                rewards = self.utils.check_match("tap_to_proceed_btn")  # battle task rewards
                if rewards:
                    self.utils.click_template(rewards)
                self.click_next(sleep_duration=3.0)

                # "type/deck is recommended" window
                templates = ["battle_end_defeat_deck_recommended_window_1", "battle_end_defeat_deck_recommended_window_0"]
                for template in templates:
                    deck_recommended_window = self.utils.check_match(template, threshold=0.6)
                    if deck_recommended_window:
                        logger.debug("Battle ended: Deck is recommended")
                        back_btn = self.utils.check_match("battle_end_defeat_back_btn")
                        if back_btn:
                            self.utils.click_template(back_btn)
                        x_btn = self.utils.check_match("x_close_btn")
                        if x_btn:
                            self.utils.click_template(x_btn)
                        sleep(1)

                return False  # defeat/tie

            if self.utils.check_match("battle_end_victory"):
                logger.info("Battle ended in Victory")
                self.battle_victory_count += 1
                self.utils.click_template("battle_end_victory_tap_to_proceed_btn")
                for _ in range(2):
                    self.click_tap_to_proceed(sleep_duration=1.5)

                rewards = self.utils.check_match("tap_to_proceed_btn")  # battle task rewards
                if rewards:
                    self.utils.click_template(rewards)

                self.click_next()  # player exp and first-time rewards

                return True  # victory

            if battle_duration >= 600:
                logger.error("Battle time exceeded 10 mins")
                return False

            i = 8 if battle_duration < 360 else (3 if battle_duration < 600 else 0)
            battle_duration += i
            sleep(i)

            win32gui.SetForegroundWindow(HWND)
            battle_duration += 2
            sleep(2)

    def click_next(self, sleep_duration: float = 1.0, confirm_click: bool = True):
        return self.utils.click_template(
            "next_btn",
            sleep_duration=sleep_duration,
            confirm_click=confirm_click,
        )

    def click_ok(self, sleep_duration: float = 1.0, confirm_click: bool = True):
        return self.utils.click_template(
            "ok_btn",
            sleep_duration=sleep_duration,
            confirm_click=confirm_click,
        )

    def click_skip(self, sleep_duration: float = 1.0, confirm_click: bool = True):
        return self.utils.click_template(
            "skip_btn",
            sleep_duration=sleep_duration,
            confirm_click=confirm_click,
        )

    def click_x(self, sleep_duration: float = 1.0, confirm_click: bool = True):
        """x_close_btn"""
        return self.utils.click_template(
            "x_close_btn",
            sleep_duration=sleep_duration,
            confirm_click=confirm_click,
        )

    def click_tap_to_proceed(self, sleep_duration: float = 1.0, confirm_click: bool = True):
        return self.utils.click_template(
            "tap_to_proceed_btn",
            sleep_duration=sleep_duration,
            confirm_click=confirm_click,
        )


def find_my_program_windows():
    def _enum_cb(hwnd, hwnds):
        title = win32gui.GetWindowText(hwnd) or ""
        names = [PROCESS_NAME] if isinstance(PROCESS_NAME, str) else PROCESS_NAME
        if not any(name in title for name in names):
            return

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            if proc.name().lower() == EXE_NAME.lower():
                hwnds.append(hwnd)
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            logger.debug(f"psutil failed for PID {pid}, falling back to title match")

        hwnds.append(hwnd)

    hwnd_list = []
    win32gui.EnumWindows(_enum_cb, hwnd_list)
    return hwnd_list


def initialize_hwnd():
    global HWND

    hwnds = find_my_program_windows()
    if hwnds:
        HWND = hwnds[0]
        logger.debug(f"Found program window: {HWND}")
        return True

    logger.error("hwnd window not found")
    HWND = None
    return False


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
        logger.info("None of the BlueStacks processes are running. Launching BlueStacks...")
        try:
            subprocess.Popen([BLUESTACKS_EXE] + BLUESTACKS_ARGS, shell=False)  # launch BlueStacks
            while True:
                sleep(1)
                if is_process_running():
                    break
            sleep(3)

            # workaround for win32gui.SetForegroundWindow() to work
            # runs new py script and exit the old one
            restart_script()

        except PermissionError as e:
            logger.error(f"PermissionError: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
    else:
        max_attempts = 5
        for i in range(max_attempts):
            try:
                win32gui.SetForegroundWindow(HWND)

                # Check if the window is actually the foreground window
                current_foreground = win32gui.GetForegroundWindow()
                if current_foreground == HWND:
                    logger.info("BlueStacks is running")
                    break
            except Exception as e:
                if i == max_attempts - 1:  # Last iteration
                    logger.error(f"Failed setting foreground window: {e}. Exiting Auto Pokemon TCGP")
                    sys.exit()
            sleep(1)


def restart_script():
    logger.info("Restarting py script")
    python = sys.executable
    script = Path(__file__).resolve()
    subprocess.run([python, script] + sys.argv[1:])  # run new py
    sys.exit()  # exit old py


def bluestacks_enter_pokemon_tcgp(Bot=None):
    """Enter Pokemon TCGP from BlueStacks homescreen"""
    if Bot is None:
        # raise # NOTE may need to raise error
        logger.error("Failed to find Bot instance; may")

    pokemon_tcgp_icon = Bot.utils.check_match("bluestacks_pokemon_tcgp_icon")
    if pokemon_tcgp_icon:
        logger.debug("Entering Pokemon TCGP from BlueStacks homescreen")
        Bot.utils.move_to_click(pokemon_tcgp_icon)
        return True
    return False


def exit_bluestacks(Bot=None):
    if Bot is None:
        logger.error("Cannot exit Bluestacks. Failed to find Bot instance; quitting Bot.")
        sys.exit()

    win32gui.SetForegroundWindow(HWND)
    x = Bot.utils.wait_for_match("bluestacks_x_btn", timeout=10.0)
    if not x:
        logger.warning("Failed to find BlueStacks X button")
        return

    logger.info("Exiting BlueStacks")
    Bot.utils.move_to_click(x)

    close = Bot.utils.wait_for_match("bluestacks_close_btn", timeout=5.0)
    if not close:
        logger.error("Failed to find BlueStacks close button")
        return

    Bot.utils.move_to_click(close)
    sys.exit()


def main():
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    logger.debug(f"{Path(__file__).name}")
    logger.info("Starting Auto Pokemon TCGP...\n")
    initialize_hwnd()
    with mss() as sct:
        monitor = sct.monitors[1]
        launch_game()
        bot = Bot(sct, monitor)

        bot.start_game()
        bot.booster_packs()
        bot.gifts()
        bot.wonder_pick()
        bot.shop()
        bot.missions()
        bot.battle()

        if ENABLE_EXIT_APP:
            exit_bluestacks(bot)
    logger.info("\nEnding Auto Pokemon TCGP")


if __name__ == "__main__":
    main()

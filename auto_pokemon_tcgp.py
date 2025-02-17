'''
Auto Pokemon TCG Pocket

A Python script designed to automate daily tasks in the Pokemon TCG Pocket using Bluestacks.

Bluestacks settings:
    display resolution: 1600x900
    dpi 320


# NOTE changelog:
0.0.3:
    open_pack_slice is global function; can slice
    check_at_screen()
    battle_diff_to_template_key
    check_level_up
    import win32gui and win32gui.SetForegroundWindow(hwnd)
0.0.4:
    simplify templates, and update check_template and finding_template.
    fix all bool check 
        if VAR is not None and len(VAR) > 0:
        if VAR is None or len(VAR) == 0:
0.0.5:
    refining main logic and bugfixes.
0.0.6:
    replacing with click_template.
    wonder_pick_event and pick_random_card.
    move_to_click(claim_card[0])
0.0.7:
    launch_game: if cannot find Bluestacks App Player, launch app.
    check_have_booster_pack, open_pack: fix logic.
    open_booster_pack_screen # shows the home_1 button, but no missions. starting script from here is the bug.
    wonder_pick_event: fix pick_random_card. if chansey_pick, print('Found Chansey pick)
    check_missions: update.
0.0.8:
    at start_game, if game not loaded correctly, exit the program
    open_packs: add sleep before wait see click 'pack_select_other_pack'.
    gifts: fix click_x to go home.
    missions: add time to finding_template('missions_complete_all').
0.0.9:
    battle_solo: add while loop
        after 4 mins, every 10 sec win32gui.SetForegroundWindow(HWND) and watch for defeat.
            enable_defeat_redo, create a loop until victory.
        victory_tap_to_proceed - different from the other
        if not solo_event, return.
        if no solo_stamina, return
    click_tap_hold. in open_gift_pack
    check_level_up everytime at home after booster_pack, wonder_pick, battle_solo. if True, click Proceed
0.0.10:
    wonder_pick_card_back
    check_booster_pack_screen: simplify and remove check_have_booster_pack
    check_have_booster_pack: remove 'select_other_booster_pack'
    open_booster_packs: add click_tap_hold, congrats_screen, and click_skip
    open_packs: 'task_tap_hold'
    click_tap_hold: real mouseDown and Up
0.0.11:
    wonder_pick: adjust to add wonder_pick_chansey
    battle_solo
0.0.12:
    open_booster_packs.
    wonder_pick: add no_stamina for chansey pick
    gifts, shop, missions: moves move_to_click from it and into check home stuff
    click_home: new version that adjust for ingame lag when loading home
    desired_pack = random.choice[]
0.0.13:
    wonder_pick: new pick_random_card with group_rectangles=True
    gifts.claim_all: better code but still need screenshot
    card_pack_to_template_key: added the rest of pack_select and desired_pack
0.0.14
    missions: non_daily_complete
    wonder_pick: pick_random_card: [card]
    battle_solo: if battle_rewards, 3rd tap_proceed
0.0.15
    click_tap_hold: sleep(5) # does it need to be 10s?
    enable_wonder_pick_chansey
    cleanup
0.0.16
    launch_game: BUG win32gui.SetForegroundWindow(HWND) doesn't work after launch; works otherwise.
    select_package: sleep(3) from 1s, may need to go 5s.
0.0.17
    check_gifts: higher threshold

# NOTE
    'at_home' can also be seen in booster_pack_screen and wonder_pick
    'pack_select_package' works genetic apex bc it's apex; idk about the rest of expansion packs.
    game notes: level xp from open booster pack, solo battle, win vs battle, wonder pick.
    relative file paths for templates works via cmd; not with VS code because the code execute from somewhere else.

# TODO
    screenshots needed: level_up_unlocked, gifts_claim_all, pokemon_tcgp_update screen
        # need gifts_claim_all or else will lead to bug from normal claim gift

    if pokemon_tcgp_update, start update and quit py?
    test script without using vscode

battle_solo_normal: # non-event; a lot of images without the clear check mark background
bluestacks_close_ad: HOW?? it can show any anytime and hard to fit; prob place it everywhere.
    close_ad = check_template(sct, monitor, 'bluestacks_close_ad')
    if close_ad is not None and len(close_ad) > 0:
        move_to_click(close_ad)
        # sleep(1)
'''

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


enable_check_pack_screen = True
# desired_pack = 'mew' # charizard, mewtwo, pikachu, mew, dialga, palkia
desired_pack = random.choice(['mew', 'dialga', 'palkia']) # charizard, mewtwo, pikachu, mew, dialga, palkia
enable_wonder_pick = True
enable_wonder_pick_chansey = False
enable_check_level_up = False

enable_battle = True
desired_battle_diff = 'expert' # beginner, intermediate, advanced, expert
battle_check_time = 270 # sleep time before battle_check; only 0 is False.
enable_battle_defeat_redo = True
enable_battle_victory_repeat = False

enable_exit_app = False

EXE_PATH = r'"C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64 --cmd launchApp --package "jp.pokemon.pokemontcgp" --source desktop_shortcut'
HWND = win32gui.FindWindow(None, 'BlueStacks App Player')
PROCESS_NAME = ['BlueStacks', 'BlueStacks App Player', 'HD-Player',]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

templates = {
    'start_game': 'images/start_game.jpg',
    'at_home': 'images/home_1.jpg',
    'home': 'images/home_0.jpg',
    'pack': 'images/pack.jpg',
    'pack_can_open': 'images/pack_can_open.jpg',
    'pack_select_other_pack': 'images/pack_select_other_booster_packs.jpg',
    'pack_select_package': 'images/pack_select_package.jpg',
    'pack_select_pack_charizard': 'images/pack_select_pack_charizard.jpg',
    'pack_select_pack_mewtwo': 'images/pack_select_pack_mewtwo.jpg',
    'pack_select_pack_pikachu': 'images/pack_select_pack_pikachu.jpg',
    'pack_select_pack_mew': 'images/pack_select_pack_mew.jpg',
    'pack_select_pack_dialga': 'images/pack_select_pack_dialga.jpg',
    'pack_select_pack_palkia': 'images/pack_select_pack_palkia.jpg',
    'pack_open': 'images/pack_open.jpg',
    'pack_open_slice': 'images/pack_open_slice.jpg',
    'gifts': 'images/gifts.jpg',
    'gifts_screen': 'images/gifts_screen.jpg',
    'gifts_claim_all': 'images/gifts_claim_all.jpg',
    'gifts_claim_card': 'images/gifts_claim_card.jpg',
    'gifts_no_claim': 'images/gifts_no_claimable_items.jpg',
    'shop': 'images/shop.jpg',
    # 'shop_screen': 'images/shop_screen.jpg', # maybe this isn't needed; there's a finding in shop()
    'shop_daily_gift': 'images/shop_daily_gifts.jpg',
    'wonder_pick': 'images/wonder_pick.jpg',
    'wonder_pick_screen': 'images/wonder_pick_screen.jpg',
    'wonder_pick_chansey': 'images/wonder_pick_chansey.jpg',
    'wonder_pick_chansey_no_stamina': 'images/wonder_pick_chansey_no_stamina.jpg',
    'wonder_pick_bonus': 'images/wonder_pick_bonus.jpg',
    'wonder_pick_a_card_screen': 'images/wonder_pick_a_card_screen.jpg',
    'wonder_pick_card_back': 'images/wonder_pick_card_back.jpg',
    'missions_0': 'images/missions_0.jpg',
    'missions_1': 'images/missions_1.jpg',
    'missions_complete_all': 'images/missions_complete_all.jpg',
    'missions_non_daily_complete': 'images/missions_non_daily_complete.jpg',
    'missions_claim': 'images/missions_claim.jpg',
    'battle': 'images/battle.jpg',
    #'battle_solo_0': 'images/battle_solo_0.jpg',
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
    'bluestacks_x': 'images/bluestacks_x.jpg',
    'bluestacks_close': 'images/bluestacks_close.jpg',
    'task_click_next': 'images/task_click_next.jpg',
    'task_click_ok': 'images/task_click_ok.jpg',
    'task_click_skip': 'images/task_click_skip.jpg',
    'task_click_x': 'images/task_click_x.jpg',
    'task_tap_hold': 'images/task_tap_hold.jpg',
    'task_tap_proceed': 'images/task_tap_proceed.jpg',

    # Add more templates as needed
        # '': cv2.imread('images/.jpg'),
    # To use templates
        # template = templates.get(template_key)
}
card_pack_to_template_key = {
    'charizard':'pack_select_pack_charizard',
    'mewtwo':'pack_select_pack_mewtwo',
    'pikachu':'pack_select_pack_pikachu',
    'mew':'pack_select_pack_mew',
    'dialga':'pack_select_pack_dialga',
    'palkia':'pack_select_pack_palkia',
}

battle_diff_to_template_key = {
    'beginner': 'battle_diff_beginner',
    'intermediate': 'battle_diff_intermediate',
    'advanced': 'battle_diff_advanced',
    'expert': 'battle_diff_expert'
}


def main():
    print('\nStarting Auto Pokemon TCGP...\n')
    with mss() as sct:
        monitor = sct.monitors[1]
        launch_game()
        # win32gui.SetForegroundWindow(HWND)
        start = start_game(sct, monitor)
        if start:
            have_booster_pack = check_have_booster_pack(sct, monitor)
            if have_booster_pack is not None and len(have_booster_pack) > 0:
                open_booster_packs(sct, monitor)
        elif enable_check_pack_screen and check_at_home(sct, monitor):
            check_booster_pack_screen(sct, monitor)
        if enable_check_level_up:
            check_level_up(sct, monitor)
        have_gifts = check_gifts(sct, monitor)
        if have_gifts:
            gifts(sct, monitor)
        have_shop = check_shop(sct, monitor)
        if have_shop:
            shop(sct, monitor)
        if enable_wonder_pick:
            wonder_pick(sct, monitor)
            if enable_check_level_up:
                check_level_up(sct, monitor)
        have_missions = check_missions(sct, monitor)
        if have_missions:
            missions(sct, monitor)
        if enable_battle:
            battle_solo(sct, monitor)
            click_home(sct, monitor)
            if enable_check_level_up:
                check_level_up(sct, monitor)
        if enable_exit_app:
            exit_bluestacks(sct, monitor)
        print('\nEnding Auto Pokemon TCGP\n')


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
        print('None of the BlueStacks processes are running. Launching...')
        try:
            subprocess.Popen(EXE_PATH, shell=False) # launch BlueStacks
            while True:
                sleep(1)
                if is_process_running():
                    break
            sleep(1)
            win32gui.SetForegroundWindow(HWND)
            '''
            # workaround for win32gui.SetForegroundWindow() to work
            # runs new py script and exit the old one

            python = sys.executable
            script = os.path.abspath(__file__)
            subprocess.run([python, script] + sys.argv[1:]) # run new py
            sys.exit() # exit old py
            '''
        except PermissionError as e:
            print(f"PermissionError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print('BlueStacks is running')
        win32gui.SetForegroundWindow(HWND)


def start_game(sct, monitor):
    print('Starting game')
    count = 0
    max_attempts = 120

    while count < max_attempts:
        start = check_template(sct, monitor, 'start_game')
        if start is not None and len(start) > 0:
            move_to_click(start)
            sleep(10)
            return True
        home = check_at_home(sct, monitor)
        if home is not None and len(home) > 0:
            return False
        sleep(0.5)
        count += 1
    print(f"Error with start_game")
    if enable_exit_app:
        exit_bluestacks(sct, monitor)
    return None


def check_at_home(sct, monitor):
    return check_template(sct, monitor, 'at_home')

'''
def check_at_home(sct, monitor):
    templates = ['home', 'at_home']
    for template in templates:
        at_home = check_template(sct, monitor, template)
        if at_home is not None and len(at_home) > 0:
            if template = 'home'
                return False
            return True
'''

def check_gifts(sct, monitor):
    template_key = 'gifts'
    template_path = templates.get(template_key)
    template = cv2.imread(os.path.join(SCRIPT_DIR, template_path))

    image = sct.grab(monitor)
    matched_image, have_gifts = match_template(image, template, threshold=0.95)
    if len(have_gifts) > 0:
        move_to_click(have_gifts)
        sleep(1)
        return True
    else:
        return False


def check_shop(sct, monitor):
    have_shop = check_template(sct, monitor, 'shop')
    if have_shop is not None and len(have_shop) > 0:
        move_to_click(have_shop)
        sleep(1)
        return True
    else:
        False


def check_missions(sct, monitor):
    templates = ['missions_0', 'missions_1']

    for template in templates:
        have_missions = check_template(sct, monitor, template)
        if have_missions is not None and len(have_missions) > 0:
            if template == 'missions_0':
                return None
            move_to_click(have_missions)
            sleep(1)
            return True


def check_have_booster_pack(sct, monitor):
    count = 0
    max_attempts = 30

    while count < max_attempts:
        home = check_at_home(sct, monitor)
        if home is not None and len(home) > 0:
            return None

        booster_pack = check_template(sct, monitor, 'pack_can_open')
        if booster_pack is not None and len(booster_pack) > 0:
            print('Have booster pack')
            return booster_pack

        sleep(0.5)
        count += 1
    print(f"Error with check_have_booster_pack")
    return None


def check_level_up(sct, monitor):
    sleep(5)
    level_up = check_template(sct, monitor, 'level_up')
    if level_up is not None and len(level_up) > 0:
        click_tap_to_proceed(sct, monitor)
        level_up_unlocked = check_template(sct, monitor, 'level_up_unlocked')
        if level_up_unlocked is not None and len(level_up_unlocked) > 0:
            click_ok(sct, monitor)
        print('Leveled up')


def check_booster_pack_screen(sct, monitor):
    print('Opening booster pack screen')

    pack = finding_template(sct, monitor, 'pack', 10)
    if pack is not None and len(pack) > 0:
        move_to_click(pack)

    pack_screen = finding_template(sct, monitor, 'pack_select_other_pack')
    if pack_screen is not None and len(pack_screen) > 0:
        print('At booster pack screen')
        sleep(1.5)
    else:
        print('Not at booster pack screen')
        click_home(sct, monitor)
        return

    can_open_pack = check_template(sct, monitor, 'pack_can_open')
    if can_open_pack is not None and len(can_open_pack) > 0:
        print('Can open booster pack')
        sleep(1)
        open_booster_packs(sct, monitor)
    else:
        print('No booster pack to open')

    sleep(1)
    click_home(sct, monitor)
    return


def open_booster_packs(sct, monitor):
    print('Opening pack')

    sleep(1)
    click_template(sct, monitor, 'pack_select_other_pack')
    pack_select = card_pack_to_template_key.get(desired_pack)
    click_template(sct, monitor, pack_select) # from expansion pack screen
    sleep(3)
    click_template(sct, monitor, 'pack_select_package') # card package
    click_template(sct, monitor, 'pack_open')
    click_skip(sct, monitor)

    open_pack_slice(sct, monitor)

    click_tap_hold(sct, monitor) # opening cards
    click_next(sct, monitor) # opening result
    sleep(5)

    congrat_screen = check_template(sct, monitor, 'task_tap_proceed') # collection milestones
    if congrat_screen is not None and len(congrat_screen) > 0:
        click_tap_to_proceed(sct, monitor)
        sleep(3)

    new_cards = check_template(sct, monitor, 'task_click_skip') # if new card, register to dex
    if new_cards is not None and len(new_cards) > 0:
        for _ in range(2):
            click_skip(sct, monitor)
            sleep(1)

    click_next(sct, monitor)
    sleep(1)

    click_home(sct, monitor)
    print('Finish opening pack')
    return


def open_gift_pack(sct, monitor):
    open_pack_slice(sct, monitor)
    click_tap_hold(sct, monitor)
    click_next(sct, monitor)
    click_ok(sct, monitor) # only in gift pack

    new_card = check_template(sct, monitor, 'task_click_skip') # if new card, register to dex
    if new_card is not None and len(new_card) > 0:
        for _ in range(2):
            click_skip(sct, monitor)


def open_pack_slice(sct, monitor):
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
    print('Opening gifts')

    gifts_screen =  finding_template(sct, monitor, 'gifts_screen', 10)
    if gifts_screen is not None and len(gifts_screen) > 0:
        sleep(0.5)

        ''' # comment until we get 'gifts_claim_all' screenshot
        claim_all = check_template(sct, monitor, 'gifts_claim_all') # NOTE doesn't work for now; hard to discern 'gifts_claim_all'
        if claim_all is not None and len(claim_all) > 0:
            move_to_click(claim_all)
            sleep(1)
            click_ok(sct, monitor)
            sleep(1)
        '''

        while True:
            claim_card = check_template(sct, monitor, 'gifts_claim_card')
            if claim_card is not None and len(claim_card) > 0:
                move_to_click(claim_card)
                sleep(1)
                click_ok(sct, monitor)
                open_gift_pack(sct, monitor)
            elif claim_card is None or len(claim_card) == 0:
                break

        no_claim = check_template(sct, monitor, 'gifts_no_claim')
        if no_claim is not None and len(no_claim) > 0:
            click_x(sct, monitor)
    print('Finish opening gifts')


def shop(sct, monitor):
    print('Opening shop')

    daily_gift = finding_template(sct, monitor, 'shop_daily_gift')
    if daily_gift is not None and len(daily_gift) > 0:
        move_to_click(daily_gift)
        sleep(0.5)
        click_ok(sct, monitor)
        click_x(sct, monitor)
    else:
        print('Daily gifts button not found')
    print('Finish with shop')


def wonder_pick(sct, monitor):
    def pick_random_card(sct, monitor):
        template_key = 'wonder_pick_card_back'
        template_path = templates.get(template_key)

        # template = cv2.imread(template)
        template = cv2.imread(os.path.join(SCRIPT_DIR, template_path))
        if template is None:
            print(f"Failed to load template '{template_key}' from {template_path}")
            return None

        image = sct.grab(monitor)
        matched_image, cards = match_template(image, template, group_rectangles=True)
        if len(cards) > 0:
            print(f"Template '{template_key}' found")

            print(f'Found {len(cards)} card to choose')
            print(f'Cards are: {cards}')
            card = random.choice(cards)
            print(f'Card choice is {card}')
            move_to_click([card])
            sleep(5)
        else:
            print('No card backs found to pick')

    click_template(sct, monitor, 'wonder_pick')

    wonder_pick_screen = finding_template(sct, monitor, 'wonder_pick_screen')
    if wonder_pick_screen is not None and len(wonder_pick_screen) > 0:

        event_picks = ['wonder_pick_chansey', 'wonder_pick_bonus']

        for pick in event_picks:
            sleep(1)
            event_pick = check_template(sct, monitor, pick)
            if event_pick is not None and len(event_pick) > 0:
                print(f'Template {pick} found')

                if pick == 'wonder_pick_chansey' and not enable_wonder_pick_chansey:
                    print('Skipping Chansey pick')
                    chansey_loc = get_click_location(event_pick)
                    pyautogui.moveTo(chansey_loc)
                    pyautogui.scroll(-1)
                    continue
                move_to_click(event_pick)
                sleep(0.5)

                if pick == 'wonder_pick_chansey':
                    no_stamina = check_template(sct, monitor, 'wonder_pick_chansey_no_stamina')
                    if no_stamina is not None and len(no_stamina) > 0:
                        print('No stamina for Chansey pick')
                        click_x(sct, monitor)
                        chansey_loc = get_click_location(event_pick)
                        pyautogui.moveTo(chansey_loc)
                        pyautogui.scroll(-1)
                        continue

                click_ok(sct, monitor)
                click_skip(sct, monitor)
                wonder_pick_a_card_screen = finding_template(sct, monitor, 'wonder_pick_a_card_screen')
                if wonder_pick_a_card_screen is not None and len(wonder_pick_a_card_screen) > 0:
                    pick_random_card(sct, monitor)
                    for _ in range(2):
                        click_tap_to_proceed(sct, monitor)
                        sleep(1.5)
                wonder_pick_screen = finding_template(sct, monitor, 'wonder_pick_screen')
                if wonder_pick_screen is not None and len(wonder_pick_screen) > 0:
                    pass # make sure it's at screen before click_home
            else:
                print(f'Template {pick} not found')

    click_home(sct, monitor)
    return


def missions(sct, monitor):
    print('Starting mission clear')

    complete_all = finding_template(sct, monitor, 'missions_complete_all', 5)
    if complete_all is not None and len(complete_all) > 0:
        move_to_click(complete_all)
        sleep(3)
    else:
        print('Complete all missions button not found')

    non_daily_complete = check_template(sct, monitor, 'missions_non_daily_complete')
    if non_daily_complete is not None and len(non_daily_complete) > 0:
        click_ok(sct, monitor)

    claim = check_template(sct, monitor, 'missions_claim')
    if claim is not None and len(claim) > 0:
        move_to_click(claim)
        sleep(1)
        click_ok(sct, monitor)
    click_x(sct, monitor)
    print('Missions clear')


def battle_solo(sct, monitor):
    print('Starting battle')
    battle = finding_template(sct, monitor, 'battle')
    if battle is not None and len(battle) > 0:
        move_to_click(battle)
    else:
        print('Battle button not found')
        sleep(3)
        return

    solo_event = finding_template(sct, monitor, 'battle_solo_1', 10)
    if solo_event is not None and len(solo_event) > 0:
        move_to_click(solo_event)
    else:
        print('Solo event not found')
        sleep(3)
        return

    drop_event = finding_template(sct, monitor, 'battle_drop_event', 10)
    if drop_event is not None and len(drop_event) > 0:
        move_to_click(drop_event)
    else:
        print('Drop event not found')
        sleep(3)
        return

    battle_count = 0
    while True:
        sleep(1.5)
        event_stamina = check_template(sct, monitor, 'battle_solo_stamina')
        if event_stamina is not None and len(event_stamina) > 0:
            pass
        else:
            print('Solo stamina not found')
            sleep(3)
            return

        sleep(0.5)
        diff_screen_key = battle_diff_to_template_key.get('beginner')
        diff_screen = finding_template(sct, monitor, diff_screen_key, 5)
        if diff_screen is not None and len(diff_screen) > 0:
            print('At battle difficulty screen')
            diff_screen_loc = get_click_location(diff_screen)
            pyautogui.moveTo(diff_screen_loc)
        else:
            print('Not at battle difficulty screen')
            sleep(3)
            return

        diff_key = battle_diff_to_template_key.get(desired_battle_diff)
        if not diff_key:
            print(f"Invalid difficulty level: {desired_battle_diff}")
            sleep(3)
            return
        if desired_battle_diff in ('advanced', 'expert'):
            pyautogui.scroll(-5)
            sleep(1)
        diff = finding_template(sct, monitor, diff_key)
        if diff is not None and len(diff) > 0:
            move_to_click(diff)
        else:
            print(f"Desired difficulty '{desired_battle_diff}' button not found")
            sleep(3)
            return

        battle_rules_screen = finding_template(sct, monitor, 'battle_rules_screen')
        if battle_rules_screen is not None and len(battle_rules_screen) > 0:
            auto_battle = finding_template(sct, monitor, 'battle_rules_auto')
            if auto_battle:
                move_to_click(auto_battle)
            else:
                print('Auto battle button not found')
                sleep(3)
                return

            go_battle = finding_template(sct, monitor, 'battle_rules_go_battle')
            if go_battle is not None and len(go_battle) > 0:
                move_to_click(go_battle)
                battle_count += 1
                print(f'Go battle #{battle_count}')
            else:
                print('Battle button not found')
                sleep(3)
                return

        if battle_check_time != 0:
            sleep(battle_check_time)
            win32gui.SetForegroundWindow(HWND)
            sleep(0.5)

        while True:
            defeat = check_template(sct, monitor, 'battle_end_defeat')
            if defeat is not None and len(defeat) > 0:
                print('Battle end in defeat')
                for _ in range(2):
                    click_tap_to_proceed(sct, monitor)
                    sleep(1.5)
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
            victory = check_template(sct, monitor, 'battle_end_victory')
            if victory is not None and len(victory) > 0:
                print('Battle end in victory')
                click_template(sct, monitor, 'battle_end_victory_proceed')
                for _ in range(2):
                    click_tap_to_proceed(sct, monitor)
                    sleep(1.5)
                battle_rewards = check_template(sct, monitor, 'task_tap_proceed') # battle task rewards
                if battle_rewards is not None and len(battle_rewards) > 0:
                    move_to_click(battle_rewards)
                    sleep(1)
                click_next(sct, monitor)
                new_battle_unlocked = check_template(sct, monitor, 'battle_end_victory_new_battle_unlocked')
                if new_battle_unlocked is not None and len(new_battle_unlocked) > 0:
                    click_next(sct, monitor)
                if enable_battle_victory_repeat:
                    break # repeat with victory
                else:
                    print('Battle finish')
                    sleep(3)
                    return # ends with victory
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
    print('Exiting BlueStacks')
    move_to_click(x)
    sleep(1)
    close = finding_template(sct, monitor, 'bluestacks_close')
    if close is None or len(close) == 0:
        print('Failed to find BlueStacks close button')
        return
    move_to_click(close)


def close_bluestacks_ad(sct, monitor):
    ad_x = finding_template(sct, monitor, '')
    pass


# click_home that adjust for ingame lag when loading home
def click_home(sct, monitor):
    templates = ['home', 'at_home']

    for template in templates:
        home = check_template(sct, monitor, template)
        if home is not None and len(home) > 0:
            move_to_click(home)
            sleep(1)
            at_home = finding_template(sct, monitor, 'at_home')
            if at_home is not None and len(at_home) > 0:
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


def click_tap_hold(sct, monitor):
    tap_hold = finding_template(sct, monitor, 'task_tap_hold')
    if tap_hold is not None and len(tap_hold) > 0:
        loc = get_click_location(tap_hold)
        pyautogui.moveTo(loc)
        pyautogui.mouseDown()
        sleep(5)
        pyautogui.mouseUp()
    return tap_hold


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


def check_template(sct, monitor, template_key):
    template_path = templates.get(template_key)
    if template_path is None:
        print(f"Template '{template_key}' not found")
        return None

    # template = cv2.imread(template)
    template = cv2.imread(os.path.join(SCRIPT_DIR, template_path))
    if template is None:
        print(f"Failed to load template '{template_key}' from {template_path}")
        return None

    image = sct.grab(monitor)
    matched_image, boxes = match_template(image, template)
    if len(boxes) > 0:
        print(f"Template '{template_key}' found")
        return boxes
    return None


def finding_template(sct, monitor, template_key, max_attempts=60):
    count = 0
    max_attempts = 60
    sleep_duration = 0.5

    template_path = templates.get(template_key)
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
        matched_image, boxes = match_template(image, template)
        if len(boxes) > 0:
            print(f"Template '{template_key}' found")
            return boxes
        sleep(sleep_duration)
        count += 1

    print(f"Error with template '{template_key}'")
    return None


def move_to_click(boxes):
    if len(boxes) == 0:
        print("No boxes found to click")
        return

    loc = get_click_location(boxes)
    print(f"Click at location: {loc}")
    pyautogui.moveTo(loc, duration=0.25)
    pyautogui.click(loc)


if __name__== '__main__':
    main()
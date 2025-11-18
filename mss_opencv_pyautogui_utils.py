# import mss
import cv2
import numpy as np
import pyautogui
import random

from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Literal

from opencv_utils import match_template, match_template_color, get_click_location
from templates_dict import TEMPLATES

random_move_to_click: bool = False
DEBUG: bool = False
SCREENSHOT_OUTPUT_DIR = Path.home() / "Desktop"
SCRIPT_DIR = Path(__file__).resolve().parent


def current_datetime() -> datetime:
    return datetime.now(timezone.utc)


def mss_screenshot(sct, monitor, output_name = None, output_dir=SCREENSHOT_OUTPUT_DIR):
    """mss screenshot function

    Arg:
        output_name: name appended after current datetime. If None, 'screenshot' will be appended.
        output_dir: Default is "Desktop". If None, the SCRIPT_DIR will be used.
    """
    monitor = sct.monitors[1] if monitor is None else monitor
    sct_img = sct.grab(monitor)

    output_dir = Path(SCRIPT_DIR if output_dir is None else output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not output_name:
        output_name = "screenshot"
    output_path = output_dir / f"{current_datetime().strftime('%Y-%m-%d_%H-%M-%S')}_{output_name}.png"

    from mss.tools import to_png
    to_png(sct_img.rgb, sct_img.size, output=str(output_path))
    print(f"[{current_datetime().strftime('%H:%M:%S')}] Screenshot saved: {output_path}")


def click_template_nonstop_until(sct, monitor, click_template, stop_templates, sleep_duration: float = 0.1, click_hold: bool = False, click_hold_duration: float = 0.5):
    boxes = finding_template(sct, monitor, click_template)
    if not boxes:
        print(f"Click template '{click_template}' not found")
        return False

    if not isinstance(stop_templates, (list, tuple, set)):
        stop_templates = [stop_templates]

    loc = get_click_location(boxes)

    max_attempts = 240
    for i in range(max_attempts):
        for stop in stop_templates:
            if is_template_matched(sct, monitor, stop):
                return True

        pyautogui.moveTo(loc)
        if click_hold:
            pyautogui.mouseDown()
            sleep(click_hold_duration)
            pyautogui.mouseUp
        else:
            pyautogui.click()
        if i < max_attempts - 1:
            sleep(sleep_duration)
    return False


def click_all_template(sct, monitor, template, sleep_duration = 0.0):
    template_path = TEMPLATES.get(template)

    tmpl = cv2.imread(str(SCRIPT_DIR / template_path))
    if tmpl is None:
        print(f"Failed to load template '{template}' from {template_path}")
        return None

    image = sct.grab(monitor)
    boxes = match_template(image, tmpl, group_rectangles=True)

    for i in boxes:
        # if DEBUG:
            # print(f"i: {i}")
        move_to_click([i])
        sleep(sleep_duration)
    return


def click_template(sct, monitor, template, color_match: bool = False, color_space: Literal["bgr", "hsv"] = "hsv", threshold: float = 0.90, sleep_duration: float = 1.0, confirm_click: bool = False):
    boxes = finding_template(sct, monitor, template=template, threshold=threshold)
    if not boxes:
        print(f"Template '{template}' not found")
        return False

    move_to_click(boxes)
    sleep(sleep_duration)
    if confirm_click:
        max_attempts = 120
        for _ in range(max_attempts):
            boxes = check_template(sct, monitor, template=template, color_match=color_match, color_space=color_space, threshold=threshold)
            if not boxes:  # Template is no longer present - confirmed
                return True

            # Template still present, click again and wait
            move_to_click(boxes)
            sleep(sleep_duration/4)

        print(f"Template '{template}' did not disappear after clicking")
        return False
    return True


def dbl_click_template(sct, monitor, template, color_match: bool = False, color_space: Literal["bgr", "hsv"] = "hsv", threshold: float = 0.90, sleep_duration: float = 1.0, confirm_click: bool = False):
    boxes = finding_template(sct, monitor, template, threshold=threshold)
    if not boxes:
        print(f"Template '{template}' not found")
        return False

    loc = get_click_location(boxes)
    pyautogui.moveTo(loc, duration=0.25)
    pyautogui.doubleClick(loc)
    sleep(sleep_duration)
    if confirm_click:
        max_attempts = 120
        for _ in range(max_attempts):
            boxes = check_template(sct, monitor, template=template, color_match=color_match, color_space=color_space, threshold=threshold)
            if not boxes:
                return True

            loc = get_click_location(boxes)
            pyautogui.moveTo(loc, duration=0.25)
            pyautogui.doubleClick(loc)
            sleep(sleep_duration/4)

        print(f"Template '{template}' did not disappear after clicking")
        return False
    return True


def check_template(sct, monitor, template, color_match: bool = False, color_space: Literal["bgr", "hsv"] = "hsv", threshold=0.90, group_rectangles: bool = False):
    if isinstance(template, str):
        template_path = TEMPLATES.get(template)
        if template_path is None:
            print(f"Template '{template}' not found")
            return None

        # template = cv2.imread(template)
        tmpl = cv2.imread(str(SCRIPT_DIR / template_path))
        if tmpl is None:
            print(f"Failed to load template '{template}' from {template_path}")
            return None
    elif isinstance(template, np.ndarray):
        tmpl = template

    image = sct.grab(monitor)
    if color_match:
        boxes = match_template_color(image, tmpl, color_space=color_space, threshold=threshold, group_rectangles=group_rectangles)
    else:
        boxes = match_template(image, tmpl, threshold=threshold, group_rectangles=group_rectangles)
    if boxes:
        if DEBUG:
            print(f"Template '{template}' found")
        return boxes
    return None


def finding_template(sct, monitor, template, max_attempts = 120, color_match: bool = False, color_space: Literal["bgr", "hsv"] = "hsv", threshold=0.90, group_rectangles: bool = False):
    if isinstance(template, str):
        template_path = TEMPLATES.get(template)
        if template_path is None:
            print(f"Template '{template}' not found")
            return None

        # template = cv2.imread(template)
        tmpl = cv2.imread(str(SCRIPT_DIR / template_path))
        if tmpl is None:
            print(f"Failed to load template '{template}' from {template_path}")
            return None
    elif isinstance(template, np.ndarray):
        tmpl = template

    for _ in range(max_attempts):
        image = sct.grab(monitor)
        if color_match:
            boxes = match_template_color(image, tmpl, color_space=color_space, threshold=threshold, group_rectangles=group_rectangles)
        else:
            boxes = match_template(image, tmpl, threshold=threshold, group_rectangles=group_rectangles)
        if boxes:
            if DEBUG:
                print(f"Template '{template}' found")
            return boxes
        sleep(0.25)
    print(f"Error with template '{template}'")
    return None


def is_template_matched(sct, monitor, template, method: Literal["check", "find"] = "check", max_attempts: int = 120, color_match: bool = False, color_space: Literal["bgr", "hsv"] = "hsv", threshold=0.90) -> bool:
    """When a list of templates is provided, the function returns True if ANY template in the list matches (OR logic), and not if ALL templates match (AND logic)."""
    # Convert single template to list
    if isinstance(template, (str, np.ndarray)):
        templates = [template]
    elif isinstance(template, (list, tuple)):
        templates = template
        if not template:  # Empty list should return False
            print("Error: template should not be an empty list")
            return False
    else:
        raise ValueError("Error: template must be a string to TEMPLATE dict, np.ndarray, or a list/tuple of them")

    if method == "check":
        for tmpl in templates:
            template_matched = check_template(sct, monitor, tmpl, color_match=color_match, color_space=color_space, threshold=threshold)
            if template_matched:
                return True
    elif method == "find":
        for _ in range(max_attempts):
            for tmpl in templates:
                template_matched = check_template(sct, monitor, tmpl, color_match=color_match, color_space=color_space, threshold=threshold)
                if template_matched:
                    return True
            sleep(0.25)
    else:
        print("Error: method must be 'check' or 'find'")
        return False
    return False


def test_templates(sct, monitor, templates, color_match: bool = False, color_space: Literal["bgr", "hsv"] = "hsv", threshold: float = 0.95):
    if isinstance(templates, str):
        templates = [templates]
    while True:
        for template in templates:
            tmpl = check_template(sct, monitor, template, color_match=color_match, color_space=color_space, threshold=threshold)
            if tmpl:
                print(f"Template '{template}' detected")
            else:
                print(f"Cannot detect template '{template}'")
            sleep(0.25)


def get_second_template_relative(
    sct,
    monitor,
    first_template,
    second_template,
    rel_region,
    anchor: Literal["top-left", "top-right"] = "top-left",
    method: Literal["check", "find"] = "find",
    color_match: bool = False,
    color_space: Literal["bgr", "hsv"] = "hsv",
    threshold = 0.85,
    max_attempts = 1,
):
    """
    Search for a second template inside a region defined relative to each match of a first template.

    Args:
        sct: mss screenshot instance used for grabbing regions.
        monitor: monitor region passed to sct.grab (full-screen or cropped).
        first_key: key/name of the first template to find.
        second_key: key/name of the template to search for relative to each first-template match.
        rel_region: (dx, dy, w, h) — rectangle relative to the top-left of each found first-template box.
                    dx/dy are offsets in pixels (right/down positive);
                    w/h are the width and height in pixels of the search region.
        anchor: 'top-left' (default) or 'top-right'. rel_region (dx, dy, w, h) is applied relative to the chosen anchor point.
        method: "check" (single grab) or "find" (retries inside finding_template).
        color_match: Whether to use color matching for both template.
        color_space: Color space to use for color matching ('bgr' or 'hsv').
        threshold: template matching threshold.
        max_attempts: max_attempts: number of grabs/tries per anchor when using "find".

    Returns:
        List of boxes for second template in screen coordinates (x, y, w, h),
        or None if not found.
    """
    if not (isinstance(rel_region, (tuple, list)) and len(rel_region) == 4):
        raise ValueError("rel_region must be (dx, dy, w, h) with integer pixels")

    # locate first templates
    if method == "check":
        first_boxes = check_template(sct, monitor, first_template, color_match=color_match, color_space=color_space, threshold=threshold)
    elif method == "find":
        first_boxes = finding_template(sct, monitor, first_template, color_match=color_match, color_space=color_space, threshold=threshold)
    else:
        first_boxes = check_template(sct, monitor, first_template, color_match=color_match, color_space=color_space, threshold=threshold)

    if not first_boxes:
        return []

    # load second template
    second_path = TEMPLATES.get(second_template)
    if second_path is None:
        print(f"Template '{second_template}' not found")
        return [None for _ in first_boxes]

    second_img = cv2.imread(str(SCRIPT_DIR / second_path))
    if second_img is None:
        print(f"Failed to load template '{second_template}' from {second_path}")
        return [None for _ in first_boxes]

    # determine monitor bounds
    if isinstance(monitor, (tuple, list)) and len(monitor) >= 4:
        # m_left, m_top, m_width, m_height = int(monitor[0]), int(monitor[1]), int(monitor[2]), int(monitor[3])
        m_left, m_top, m_width, m_height = map(int, monitor[:4])
    elif isinstance(monitor, dict) and {"left","top","width","height"} <= monitor.keys():
        m_left = int(monitor["left"]); m_top = int(monitor["top"])
        m_width = int(monitor["width"]); m_height = int(monitor["height"])
    elif hasattr(monitor, "left") and hasattr(monitor, "top") and hasattr(monitor, "width") and hasattr(monitor, "height"):
        m_left = int(monitor.left); m_top = int(monitor.top)
        m_width = int(monitor.width); m_height = int(monitor.height)
    elif hasattr(monitor, "width") and hasattr(monitor, "height"):
        m_left, m_top = 0, 0
        m_width = int(monitor.width); m_height = int(monitor.height)
    else:
        # fallback to common 1080p
        m_left, m_top, m_width, m_height = 0, 0, 1920, 1080

    dx, dy, sw, sh = map(int, rel_region)

    results = []
    for fb in first_boxes:
        fx, fy, fw, fh = fb

        if anchor == "top-right":
            anchor_x = fx + fw
            anchor_y = fy
        else:  # "top-left"
            anchor_x = fx
            anchor_y = fy
        sx = anchor_x + dx
        sy = anchor_y + dy

        # clamp search region to monitor bounds (ensure ints)
        abs_x = int(max(m_left, sx))
        abs_y = int(max(m_top, sy))

        # compute remaining width/height inside monitor
        abs_w = int(min(sw, m_left + m_width - abs_x))
        abs_h = int(min(sh, m_top + m_height - abs_y))

        left, top, w, h = map(int, (abs_x, abs_y, abs_w, abs_h))

        # if region has no area, skip with None
        if w <= 0 or h <= 0:
            results.append(None)
            continue

        # search_region = (left, top, left + w, top + h)  # (left, top, right, bottom) PIL bbox style
        search_region = {"left": left, "top": top, "width": w, "height": h}

        # try matching with retries
        count = 0
        found_box = None
        while count < max_attempts:
            try:
                img = sct.grab(search_region)
            except (TypeError, ValueError, RuntimeError):
                # invalid region for MSS — skip this region
                found_box = None
                break

            # Use color matching if specified, otherwise use regular template matching
            if color_match:
                boxes = match_template_color(img, second_img, color_space=color_space, threshold=threshold)
            else:
                boxes = match_template(img, second_img, threshold=threshold)

            if boxes:
                # pick the best (largest) within this region and convert to screen coords
                best = max(boxes, key=lambda b: b[2] * b[3])
                bx, by, bw, bh = best
                found_box = (abs_x + int(bx), abs_y + int(by), int(bw), int(bh))
                break

            count += 1
            if count < max_attempts:
                sleep(0.25)

        results.append(found_box)

    return results


def mouse_drag_scroll(boxes, x_offset: int = 0, y_offset: int = 0, duration=0.5, drag: bool = False):
    """
    Args:
        x_offset: offset to apply to x mouse direction (positive = right, negative = left)
        y_offset: offset to apply to y mouse direction (positive = down, negative = up)
        drag: uses pyautogui.drag(); otherwise uses pyautogui.move for precision
    """
    if boxes is None or len(boxes) == 0:
        print("No boxes found to drag")
        return

    loc = get_click_location(boxes)
    pyautogui.moveTo(loc, duration=0.25)
    if drag:
        pyautogui.dragRel(x_offset, y_offset, duration=duration, button='left')
        sleep(duration)
    else:
        pyautogui.mouseDown()
        pyautogui.moveRel(x_offset, y_offset, duration=duration)
        pyautogui.sleep(0.25)
        pyautogui.mouseUp()


def offset_boxes(boxes, x_offset=0, y_offset=0, zero_w_h: bool = False):
    """
    Applies x_offset and y_offset to boxes (x, y, w, h).

    Args:
        x_offset: offset to apply to x coordinates (positive = right, negative = left)
        y_offset: offset to apply to y coordinates (positive = down, negative = up)

    Returns:
        List of adjusted boxes (x, y, w, h) with offsets applied, or None if no boxes found
    """
    if not boxes:
        return None

    if isinstance(boxes, tuple) and len(boxes) == 4:
        boxes = [boxes]

    adjusted_boxes = []
    for box in boxes:
        x, y, w, h = box
        if zero_w_h:
            adjusted_box = (x + x_offset, y + y_offset, 0, 0)
        else:
            adjusted_box = (x + x_offset, y + y_offset, w, h)
        adjusted_boxes.append(adjusted_box)

    return adjusted_boxes


def move_to_click(boxes, add_random: bool=random_move_to_click, random_int: int = 0):
    if boxes is None or len(boxes) == 0:
        print("No boxes found to click")
        return

    if add_random and (random_int is not None or random_int != 0):
        x_offset = random.randint(-random_int, random_int)
        y_offset = random.randint(-random_int, random_int)
        boxes = offset_boxes(boxes, x_offset=x_offset, y_offset=y_offset)

    x, y = get_click_location(boxes)

    if DEBUG:
        print(f"Click at location: {(x, y)}")
    pyautogui.moveTo((x, y), duration=0.25)
    pyautogui.click((x, y))


def click_center_screen(left_screen: bool = True):
    # Get screen size (width, height)
    screen_width, screen_height = pyautogui.size()

    # Compute the center coordinates
    if left_screen:
        center_x = screen_width // 4  # center left screen
    else:
        center_x = screen_width // 2

    center_y = screen_height // 2

    # Move the mouse to the center and click
    pyautogui.moveTo(center_x, center_y)
    pyautogui.click()

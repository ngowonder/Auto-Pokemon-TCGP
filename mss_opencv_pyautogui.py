"""
MSS + OpenCV + PyAutoGUI automation utilities.

High-level API built on top of low-level template matching.
Set default matching parameters in __init__, then override per-call
using optional keyword arguments on each method.

Example usage:

    from mss import mss
    from mss_opencv_pyautogui import MSSOpenCV

    with mss() as sct:
        utils = MSSOpenCV(
            sct,
            search_region={"left": 0, "top": 0, "width": 1600, "height": 900},
            debug=True,
            threshold=0.90,
        )

        # Wait for a template to appear
        boxes = utils.wait_for_match("home_btn_0", timeout=10.0)
        if boxes:
            utils.move_to_click(boxes)
            utils.click_template("ok_btn", confirm_click=True)

        # Quick boolean check (override threshold per-call)
        if utils.check_match("pack_can_open_a_booster_pack", threshold=0.95):
            logger.info("Booster pack available")

        # Click with color matching
        utils.click_template("home_gifts_btn", color_match=True, threshold=0.95)

        # Wait for something to disappear
        disappeared = utils.wait_for_unmatch("news_window", timeout=5.0)
"""

import cv2
import numpy as np
import pyautogui
import random
import logging

from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep
from typing import Literal, Optional, List, Union, Tuple, Dict

from opencv import Match, _normalize_boxes, match_template, match_template_color, get_click_location

logger = logging.getLogger(__name__)


class MSSOpenCV:
    def __init__(
        self,
        sct,
        search_region: Optional[Union[dict, tuple, list, Match]] = None,
        templates: Optional[Dict[str, Union[str, Path]]] = None,

        threshold: float = 0.85,
        color_match: bool = False,
        color_space: Literal["bgr", "hsv"] = "hsv",
        group_rectangles: bool = False,
        sort_by_score: bool = False,
        cache: bool = True,

        screenshot_output_dir: Optional[Path] = None,
        debug: bool = False,
        random_move_to_click: bool = False,
        script_dir: Optional[Path] = None,
    ):
        self.sct = sct
        self.search_region = search_region
        self.templates = templates or {}

        self._threshold = threshold
        self._color_match = color_match
        self._color_space = color_space
        self._group_rectangles = group_rectangles
        self._sort_by_score = sort_by_score
        self._cache = cache

        self.debug = debug
        self.random_move_to_click = random_move_to_click
        self.screenshot_output_dir = screenshot_output_dir or Path.home() / "Desktop"
        self.script_dir = script_dir or Path(__file__).resolve().parent
        self._template_cache: Dict[str, np.ndarray] = {}

        if self.debug:
            logger.setLevel(logging.DEBUG)

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def current_datetime() -> datetime:
        return datetime.now(timezone.utc)

    def _resolve_params(self, **kwargs) -> dict:
        """Resolve matching params from kwargs, falling back to instance defaults."""
        return {
            "threshold": kwargs.get("threshold") if kwargs.get("threshold") is not None else self._threshold,
            "color_match": kwargs.get("color_match") if kwargs.get("color_match") is not None else self._color_match,
            "color_space": kwargs.get("color_space") if kwargs.get("color_space") is not None else self._color_space,
            "group_rectangles": kwargs.get("group_rectangles") if kwargs.get("group_rectangles") is not None else self._group_rectangles,
            "sort_by_score": kwargs.get("sort_by_score") if kwargs.get("sort_by_score") is not None else self._sort_by_score,
            "cache": kwargs.get("cache") if kwargs.get("cache") is not None else self._cache,
        }

    @staticmethod
    def _template_str(template: Union[str, np.ndarray, Match]) -> str:
        if isinstance(template, np.ndarray):
            return f"array{template.shape}"
        if isinstance(template, Match):
            name_part = f"'{template.name}'" if template.name else ""
            # Include coords to prevent collisions in dictionary keys
            return f"Match({name_part}@{template.x},{template.y})"
        return str(template)

    def _get_search_region(self, region: Optional[Union[dict, tuple, list, Match]] = None) -> Match:
        """
        Consolidate normalization and fallback logic for regions.
        Returns a Match object representing the search area.
        """
        boxes = _normalize_boxes(region or self.search_region)
        if boxes:
            return boxes[0]

        # Fallback to primary monitor
        mon = self.sct.monitors[1]
        return Match(mon["left"], mon["top"], mon["width"], mon["height"])

    def load_template_image(self, template: Union[str, np.ndarray, Match], cache: bool = True, template_cache: Optional[Dict[str, np.ndarray]] = None) -> Optional[np.ndarray]:
        """Resolve a template name, array, or Match to a numpy image."""
        if isinstance(template, Match):
            return template.template

        if isinstance(template, np.ndarray):
            return template

        if isinstance(template, str):
            # 1. Check provided temporary cache
            if template_cache is not None and template in template_cache:
                return template_cache[template]

            # 2. Check persistent instance cache
            if template in self._template_cache:
                return self._template_cache[template]

            template_path = self.templates.get(template)
            if template_path is None:
                logger.error(f"Template '{template}' not found in templates dictionary")
                return None

            full_path = self.script_dir / template_path
            try:
                tmpl = cv2.imread(str(full_path))
            except Exception as e:
                logger.error(f"Exception loading template '{template}' from {full_path}: {e}")
                return None

            if tmpl is None:
                logger.error(f"Failed to load template image from {full_path}")
                return None

            # Save to persistent cache if enabled
            if cache:
                self._template_cache[template] = tmpl
            
            # Also save to temporary cache if provided
            if template_cache is not None:
                template_cache[template] = tmpl

            return tmpl

        logger.error(f"Invalid template type: {type(template)}. Expected str, np.ndarray, or Match")
        return None

    def save_to_cache(self, templates: Union[str, np.ndarray, Match, List[Union[str, np.ndarray, Match]]]) -> Dict[str, bool]:
        """Explicitly load and cache template images."""
        if isinstance(templates, (str, np.ndarray, Match)):
            templates = [templates]

        results: Dict[str, bool] = {}
        for t in templates:
            if isinstance(t, Match):
                if t.template is not None:
                    key = t.name or f"__match_{id(t)}__"
                    self._template_cache[key] = t.template
                    results[key] = True
                else:
                    results[str(t)] = False
            elif isinstance(t, str):
                if t in self._template_cache:
                    results[t] = True
                    continue
                img = self.load_template_image(t, cache=True)
                if img is not None:
                    # self.load_template_image already saves to self._template_cache
                    results[t] = True
                else:
                    results[t] = False
            elif isinstance(t, np.ndarray):
                key = f"__array_{id(t)}__"
                self._template_cache[key] = t
                results[key] = True
            else:
                results[str(type(t))] = False

        return results

    def clear_template_cache(self) -> int:
        """Clear the template cache."""
        count = len(self._template_cache)
        self._template_cache.clear()
        return count

    def grab_img(self, region: Union[Match, dict, tuple, list, None] = None) -> np.ndarray:
        """Take a screenshot and return as numpy array."""
        target = region if isinstance(region, Match) else self._get_search_region(region)
        image = self.sct.grab(target.dict)
        return np.asarray(image)

    def mss_screenshot(
        self,
        output_name: Optional[str] = None,
        output_suffix: Optional[str] = None,
        output_dir: Optional[Path] = None,
        region: Optional[Union[dict, tuple, list, Match]] = None,
    ) -> None:
        """Capture and save a screenshot."""
        target = self._get_search_region(region)
        sct_img = self.sct.grab(target.dict)

        target_dir = Path(output_dir if output_dir is not None else self.screenshot_output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        if not output_name:
            output_name = "screenshot"
        timestamp = self.current_datetime().strftime('%Y-%m-%d_%H-%M-%S')
        suffix = f"_{output_suffix}" if output_suffix else ""
        output_path = target_dir / f"{output_name}_{timestamp}{suffix}.png"

        from mss.tools import to_png
        to_png(sct_img.rgb, sct_img.size, output=str(output_path))
        logger.info(f"Screenshot saved: {output_path}")

    # -- low level -------------------------------------------------------------

    def _match_template(
        self,
        template: Union[str, np.ndarray, Match],
        region: Optional[Union[dict, tuple, list, Match]] = None,
        image: Optional[np.ndarray] = None,
        template_cache: Optional[Dict[str, np.ndarray]] = None,
        cache: Optional[bool] = None,
        **kwargs
    ) -> Optional[List[Match]]:
        """
        Grab screen once and check for a single template match.
        Coordinates are automatically adjusted to screen space.

        Args:
            template: Template name (str key), numpy array, or existing Match.
            region: Optional search region override.
            image: Optional pre-grabbed image.
            template_cache: Optional temporary cache to use/populate.
            cache: Whether to save loaded templates to persistent cache.
            **kwargs: Matching parameter overrides.
        """
        if isinstance(template, Match):
            return [template]

        # Resolve parameters
        params = self._resolve_params(cache=cache, **kwargs)
        resolved_cache = params.pop("cache")

        tmpl_img = self.load_template_image(template, cache=resolved_cache, template_cache=template_cache)
        if tmpl_img is None:
            return None

        # Resolve name for metadata
        name = template if isinstance(template, str) else None

        # Resolve region once
        target_reg = region if isinstance(region, Match) else self._get_search_region(region)

        if image is None:
            image = self.grab_img(target_reg)

        color_match = params.pop("color_match")

        if color_match:
            boxes = match_template_color(image, tmpl_img, name=name, **params)
        else:
            # Grayscale doesn't use color_space
            params.pop("color_space", None)
            boxes = match_template(image, tmpl_img, name=name, **params)

        if not boxes:
            return None

        # Globalization: Adjust coordinates to screen space
        if target_reg.x != 0 or target_reg.y != 0:
            boxes = [b.offset(target_reg.x, target_reg.y) for b in boxes]

        return boxes

    def check_match(
        self,
        template: Union[str, np.ndarray, Match, List[Union[str, np.ndarray, Match]], Tuple[Union[str, np.ndarray, Match], ...]],
        region: Optional[Union[dict, tuple, list, Match]] = None,
        logic: Literal["any", "all"] = "any",
        cache: Optional[bool] = None,
        **kwargs
    ) -> Optional[Union[List[Match], Dict[str, List[Match]]]]:
        """
        Check match for template(s) on screen.
        """
        if isinstance(template, (str, np.ndarray, Match)):
            templates_to_check = [(self._template_str(template), template)]
        else:
            templates_to_check = [(self._template_str(t), t) for t in template]

        target_reg = self._get_search_region(region)
        image = self.grab_img(target_reg)

        all_matches: Dict[str, List[Match]] = {}
        for key, tmpl_val in templates_to_check:
            boxes = self._match_template(tmpl_val, region=target_reg, image=image, cache=cache, **kwargs)
            if boxes:
                if self.debug:
                    best_match = max(boxes, key=lambda b: b.score)
                    count_str = f"{len(boxes)} matches, " if len(boxes) > 1 else ""
                    logger.debug(f"[MATCH] '{key}' ({count_str}best score: {best_match.score:.4f}) at screen: ({best_match.x}, {best_match.y})")
                if logic == "any":
                    return boxes
                all_matches[key] = boxes
            else:
                if self.debug:
                    logger.debug(f"[NO MATCH] '{key}'")

        if logic == "all" and len(all_matches) == len(templates_to_check):
            return all_matches

        return None

    # -- polling / waiting -----------------------------------------------------

    def wait_for_match(
        self,
        template: Union[str, np.ndarray, Match, List[Union[str, np.ndarray, Match]], Tuple[Union[str, np.ndarray, Match], ...]],
        timeout: float = 10.0,
        interval: float = 0.25,
        logic: Literal["any", "all"] = "any",
        region: Optional[Union[dict, tuple, list, Match]] = None,
        cache: Optional[bool] = None,
        **kwargs
    ) -> Optional[Union[List[Match], Dict[str, List[Match]]]]:
        """Poll for template(s) to appear on screen."""
        start_time = monotonic()

        if isinstance(template, (str, np.ndarray, Match)):
            templates_to_check = [(self._template_str(template), template)]
        else:
            templates_to_check = [(self._template_str(t), t) for t in template]

        # Resolve cache once
        params = self._resolve_params(cache=cache, **kwargs)
        resolved_cache = params.get("cache")

        # Temporary cache preparation
        temp_cache = self._template_cache.copy()
        for _, tmpl_val in templates_to_check:
            if not isinstance(tmpl_val, Match):
                self.load_template_image(tmpl_val, cache=resolved_cache, template_cache=temp_cache)

        # Resolve region once for the whole loop
        target_reg = self._get_search_region(region)

        while True:
            image = self.grab_img(target_reg)
            all_matches: Dict[str, List[Match]] = {}

            for key, tmpl_val in templates_to_check:
                boxes = self._match_template(tmpl_val, region=target_reg, image=image, template_cache=temp_cache, cache=resolved_cache, **kwargs)
                if boxes:
                    if self.debug:
                        best_match = max(boxes, key=lambda b: b.score)
                        count_str = f"{len(boxes)} matches, " if len(boxes) > 1 else ""
                        logger.debug(f"[WAIT MATCH] '{key}' ({count_str}best score: {best_match.score:.4f}) after {monotonic() - start_time:.2f}s at screen: ({best_match.x}, {best_match.y})")
                    if logic == "any":
                        return boxes
                    all_matches[key] = boxes

            if logic == "all" and len(all_matches) == len(templates_to_check):
                return all_matches

            if monotonic() - start_time >= timeout:
                break

            sleep(interval)

        if self.debug:
            logger.warning(f"[WAIT MATCH] '{self._template_str(template)}' not found after {timeout}s")
        return None

    def wait_for_unmatch(
        self,
        template: Union[str, np.ndarray, Match, List[Union[str, np.ndarray, Match]], Tuple[Union[str, np.ndarray, Match], ...]],
        timeout: float = 10.0,
        interval: float = 0.25,
        logic: Literal["any", "all"] = "any",
        region: Optional[Union[dict, tuple, list, Match]] = None,
        cache: Optional[bool] = None,
        **kwargs
    ) -> bool:
        """Poll for template(s) to disappear from screen."""
        start_time = monotonic()

        if isinstance(template, (str, np.ndarray, Match)):
            templates_to_check = [(self._template_str(template), template)]
        else:
            templates_to_check = [(self._template_str(t), t) for t in template]

        # Resolve cache once
        params = self._resolve_params(cache=cache, **kwargs)
        resolved_cache = params.get("cache")

        # Temporary cache preparation
        temp_cache = self._template_cache.copy()
        for _, t_val in templates_to_check:
            if isinstance(t_val, Match):
                if t_val.template is None:
                    logger.error(f"Cannot wait for unmatch of Match object without template data: {t_val}")
                    return True # Assume it's "unmatched" if we can't search for it? Or return False?
            else:
                self.load_template_image(t_val, cache=resolved_cache, template_cache=temp_cache)

        target_reg = self._get_search_region(region)

        while True:
            image = self.grab_img(target_reg)

            # Check all templates in the current image frame
            matches = []
            for _, t_val in templates_to_check:
                search_val = t_val.template if isinstance(t_val, Match) else t_val
                if search_val is None:
                    matches.append(False)
                    continue

                boxes = self._match_template(search_val, region=target_reg, image=image, template_cache=temp_cache, cache=resolved_cache, **kwargs)
                matches.append(boxes is not None)

            if logic == "any":
                # logic="any" gone -> True if at least one is NOT matched.
                if not all(matches):
                    if self.debug:
                        logger.debug(f"[WAIT UNMATCH] '{self._template_str(template)}' disappeared after {monotonic() - start_time:.2f}s")
                    return True
            else: # logic="all" gone
                # logic="all" gone -> True if NONE are matched.
                if not any(matches):
                    if self.debug:
                        logger.debug(f"[WAIT UNMATCH] '{self._template_str(template)}' disappeared after {monotonic() - start_time:.2f}s")
                    return True

            if monotonic() - start_time >= timeout:
                break

            sleep(interval)

        if self.debug:
            logger.warning(f"[WAIT UNMATCH] '{self._template_str(template)}' failed to disappear after {timeout}s")
        return False

    # -- actions ---------------------------------------------------------------

    def move_to_click(
        self,
        boxes: Optional[Union[Match, List[Match], dict, tuple]],
        add_random: Optional[bool] = None,
        random_int: int = 5,
        dbl_click: bool = False,
    ) -> None:
        """
        Move the mouse to a specific location (box, point, or Match) and click.

        Args:
            boxes: The target(s) to click.
            add_random: Whether to add a small random offset. Defaults to instance setting.
            random_int: Max pixel offset for randomness.
            dbl_click: Whether to perform a double click.
        """
        matches = _normalize_boxes(boxes)
        if not matches:
            logger.error("No boxes found to click")
            return

        use_random = add_random if add_random is not None else self.random_move_to_click
        if use_random and random_int != 0:
            rx = random.randint(-random_int, random_int)
            ry = random.randint(-random_int, random_int)
            matches = [b.offset(rx, ry) for b in matches]

        loc = get_click_location(matches)
        if not loc:
            return

        x, y = loc
        if self.debug:
            best_match = max(matches, key=lambda b: b.score)
            name_str = f"'{best_match.name}'" if best_match.name else ""
            logger.debug(f"[CLICK] {name_str} at {(x, y)}")

        pyautogui.moveTo(x, y, duration=0.25)
        if dbl_click:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.click(x, y)

    def click_template(
        self,
        template: Union[str, np.ndarray, Match],
        region: Optional[Union[dict, tuple, list, Match]] = None,
        timeout: float = 10.0,
        dbl_click: bool = False,
        sleep_duration: float = 1.0,
        confirm_click: bool = False,
        confirm_timeout: float = 30.0,
        cache: Optional[bool] = None,
        **kwargs
    ) -> bool:
        """Find a template and click it."""
        boxes = self.wait_for_match(template, region=region, timeout=timeout, cache=cache, **kwargs)
        if not boxes:
            logger.error(f"Template '{self._template_str(template)}' not found")
            return False

        self.move_to_click(boxes, dbl_click=dbl_click)
        sleep(sleep_duration)

        if confirm_click:
            # If template was a Match, we use its internal template for confirmation
            confirm_target = template
            if isinstance(template, Match) and template.template is None:
                logger.warning("confirm_click requested for Match without template; skipping confirmation")
                return True

            start_time = monotonic()
            while monotonic() - start_time < confirm_timeout:
                if self.wait_for_unmatch(confirm_target, region=region, timeout=sleep_duration, cache=cache, **kwargs):
                    return True
                self.move_to_click(boxes, dbl_click=dbl_click, add_random=False)

            logger.error(f"Template '{self._template_str(template)}' did not disappear after {confirm_timeout}s")
            return False

        return True

    def click_template_nonstop_until(
        self,
        target_template: Union[str, np.ndarray, Match],
        stop_templates: Union[str, np.ndarray, Match, List[Union[str, np.ndarray, Match]], Tuple[Union[str, np.ndarray, Match], ...]],
        timeout: float = 5.0,
        click_hold: bool = False,
        click_hold_duration: float = 0.5,
        sleep_duration: float = 0.1,
        region: Optional[Union[dict, tuple, list, Match]] = None,
        cache: Optional[bool] = None,

        max_attempts: int = 240,
        **kwargs
    ) -> bool:
        """Click target_template repeatedly until stop_templates appear."""
        boxes = self.wait_for_match(target_template, region=region, timeout=timeout, cache=cache, **kwargs)
        if not boxes:
            logger.error(f"Click template '{self._template_str(target_template)}' not found")
            return False

        loc = get_click_location(boxes)
        if not loc:
            return False

        screen_width, screen_height = pyautogui.size()
        center_x, center_y = screen_width // 2, screen_height // 2

        for i in range(max_attempts):
            if self.check_match(stop_templates, region=region, cache=cache, **kwargs):
                return True

            pyautogui.moveTo(loc, duration=0.25)
            if click_hold:
                pyautogui.mouseDown()
                sleep(click_hold_duration)
                pyautogui.mouseUp()
            else:
                pyautogui.click()

            if i > 20:
                pyautogui.moveTo(center_x, center_y)
            if i < max_attempts - 1:
                sleep(sleep_duration)
        return False

    def click_all_template(
        self,
        template: Union[str, np.ndarray, Match, List[Match]],
        sleep_duration: float = 0.0,
        region: Optional[Union[dict, tuple, list, Match]] = None,
        cache: Optional[bool] = None,
        **kwargs
    ) -> None:
        """Click every occurrence of a template on screen."""
        if isinstance(template, (Match, list)):
            boxes = _normalize_boxes(template)
        else:
            boxes = self._match_template(template, region=region, cache=cache, **kwargs)

        if not boxes:
            return

        for match in boxes:
            self.move_to_click(match)
            sleep(sleep_duration)

    # -- other utilities -------------------------------------------------------

    def get_second_template_relative(
        self,
        first_template: Union[str, np.ndarray, Match],
        second_template: Union[str, np.ndarray],
        rel_region: Tuple[int, int, int, int],
        anchor: Literal["top-left", "top-right"] = "top-left",
        method: Literal["check", "wait"] = "wait",
        timeout: float = 10.0,
        region: Optional[Union[dict, tuple, list, Match]] = None,
        max_attempts: int = 1,
        cache: Optional[bool] = None,
        **kwargs
    ) -> List[Match]:
        """Find a template in a region relative to another template."""
        if not (isinstance(rel_region, (tuple, list)) and len(rel_region) == 4):
            raise ValueError("rel_region must be (dx, dy, w, h)")

        # Resolve cache
        params = self._resolve_params(cache=cache, **kwargs)
        resolved_cache = params.get("cache")

        first_boxes = _normalize_boxes(first_template)
        if not first_boxes:
            if method == "check":
                first_boxes = self._match_template(first_template, region=region, cache=resolved_cache, **kwargs)
            else:
                first_boxes = self.wait_for_match(first_template, region=region, timeout=timeout, cache=resolved_cache, **kwargs)

        matches = _normalize_boxes(first_boxes)
        if not matches:
            if self.debug:
                logger.debug(f"[RELATIVE] Anchor template '{self._template_str(first_template)}' not found")
            return []

        if self.debug:
            logger.debug(f"[RELATIVE] Found {len(matches)} anchor(s) for '{self._template_str(first_template)}'")

        dx, dy, sw, sh = map(int, rel_region)
        results: List[Optional[Match]] = []

        for i, fb in enumerate(matches):
            anchor_pt = fb.top_right if anchor == "top-right" else fb.top_left
            base_x, base_y = anchor_pt

            search_x, search_y = base_x + dx, base_y + dy
            # We wrap the relative search region in a Match object for consistent globalization
            search_region_match = Match(search_x, search_y, sw, sh)

            found_box = None
            for attempt in range(max_attempts):
                boxes = self._match_template(second_template, region=search_region_match, cache=resolved_cache, **kwargs)
                if boxes:
                    found_box = max(boxes, key=lambda b: b.score)
                    if self.debug:
                        logger.debug(f"[RELATIVE] Match found for '{self._template_str(second_template)}' relative to anchor {i+1} (score: {found_box.score:.4f})")
                    break
                if max_attempts > 1:
                    sleep(0.25)

            if not found_box and self.debug:
                logger.debug(f"[RELATIVE] No match for '{self._template_str(second_template)}' relative to anchor {i+1}")

            results.append(found_box)

        return [r for r in results if r is not None]

    def test_templates(
        self, templates: Union[str, Match, List[Union[str, Match]]],
        max_iterations: int = 0,
        cache: Optional[bool] = None,
        **kwargs
    ) -> bool:
        """Continuously test templates in a loop (for debugging)."""
        if isinstance(templates, (str, Match)):
            templates = [templates]

        # Resolve cache
        params = self._resolve_params(cache=cache, **kwargs)
        resolved_cache = params.get("cache")

        # Temporary cache preparation
        temp_cache = self._template_cache.copy()
        for t in templates:
            self.load_template_image(t, cache=resolved_cache, template_cache=temp_cache)

        any_match = False
        iteration = 0
        while max_iterations == 0 or iteration < max_iterations:
            for template in templates:
                boxes = self._match_template(template, template_cache=temp_cache, cache=resolved_cache, **kwargs)
                if boxes:
                    count = len(boxes)
                    best_match = max(boxes, key=lambda b: b.score)
                    logger.info(f"Template '{self._template_str(template)}' detected — {count} matches (best score: {best_match.score:.4f} at screen: ({best_match.x}, {best_match.y})")
                    any_match = True
                else:
                    logger.info(f"Template '{self._template_str(template)}' not detected")
                sleep(0.25)
            iteration += 1
        return any_match

    def test_templates_time(
        self,
        template_a: Union[str, np.ndarray, Match],
        template_b: Union[str, np.ndarray, Match],
        timeout: float = 60.0,
        interval: float = 0.5,
        region: Optional[Union[dict, tuple, list, Match]] = None,
        cache: Optional[bool] = None,
        **kwargs
    ) -> Optional[Dict[str, float]]:
        """Measure elapsed time between template events: A exists -> A disappears -> B exists."""
        start_time = monotonic()
        a_exists_time = a_disappears_time = b_exists_time = None
        a_found = b_found = False

        # Resolve cache
        params = self._resolve_params(cache=cache, **kwargs)
        resolved_cache = params.get("cache")

        # Temporary cache preparation
        temp_cache = self._template_cache.copy()
        self.load_template_image(template_a, cache=resolved_cache, template_cache=temp_cache)
        self.load_template_image(template_b, cache=resolved_cache, template_cache=temp_cache)

        while monotonic() - start_time < timeout:
            elapsed = monotonic() - start_time
            a_exists = self.check_match(template_a, region=region, cache=resolved_cache, **kwargs)
            b_exists = self.check_match(template_b, region=region, cache=resolved_cache, **kwargs)

            if not a_found and a_exists:
                a_found = True
                a_exists_time = elapsed
                logger.info(f"[test_templates_time] Template A ({self._template_str(template_a)}) found at t={elapsed:.2f}s")

            if a_found and a_disappears_time is None and not a_exists:
                a_disappears_time = elapsed
                logger.info(f"[test_templates_time] Template A ({self._template_str(template_a)}) disappeared at t={elapsed:.2f}s")

            if a_disappears_time is not None and not b_found and b_exists:
                b_found = True
                b_exists_time = elapsed
                logger.info(f"[test_templates_time] Template B ({self._template_str(template_b)}) found at t={elapsed:.2f}s")

            if a_exists_time is not None and a_disappears_time is not None and b_exists_time is not None:
                return {
                    "a_exists_to_disappears": round(a_disappears_time - a_exists_time, 4),
                    "disappears_to_b_exists": round(b_exists_time - a_disappears_time, 4),
                    "total": round(b_exists_time - a_exists_time, 4),
                }

            sleep(interval)

        logger.warning(f"[test_templates_time] Timeout after {timeout}s")
        return None

    # -- mouse helpers ---------------------------------------------------------

    @staticmethod
    def mouse_scroll(
        boxes: Optional[Union[Match, List[Match], dict, tuple]],
        x_offset: int = 0, y_offset: int = 0,
        duration: float = 0.5,
        drag: bool = False,
    ) -> None:
        matches = _normalize_boxes(boxes)
        if not matches:
            logger.error("No boxes found to drag")
            return

        loc = get_click_location(matches)
        if not loc:
            return
            
        pyautogui.moveTo(loc, duration=0.25)
        if drag:
            pyautogui.dragRel(x_offset, y_offset, duration=duration, button='left')
            sleep(duration)
        else:
            pyautogui.mouseDown()
            pyautogui.moveRel(x_offset, y_offset, duration=duration)
            sleep(0.25)
            pyautogui.mouseUp()

    def click_center_screen(self, clicks: int = 1, region: Optional[Union[dict, tuple, list, Match]] = None) -> None:
        """Move mouse to the center of a region and click."""
        target = self._get_search_region(region)
        for _ in range(clicks):
            pyautogui.click(target.center)

"""
OpenCV template matching utilities.

Provides low-level functions for template matching with optional color
matching and rectangle grouping.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union, Optional


@dataclass(frozen=True)
class Match:
    """Represents a detected template match with position, size, and confidence."""
    x: int
    y: int
    w: int
    h: int
    score: float = 0.0
    name: Optional[str] = None
    template: Optional[np.ndarray] = field(default=None, compare=False, hash=False, repr=False)

    @property
    def area(self) -> int:
        """Width x height of the match."""
        return self.w * self.h

    @property
    def center(self) -> Tuple[int, int]:
        """Center point (x, y) of the match."""
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def top_left(self) -> Tuple[int, int]:
        """(x, y) coordinates of the top-left corner."""
        return (self.x, self.y)

    @property
    def top_right(self) -> Tuple[int, int]:
        """(x+w, y) coordinates of the top-right corner."""
        return (self.x + self.w, self.y)

    @property
    def bottom_left(self) -> Tuple[int, int]:
        """(x, y+h) coordinates of the bottom-left corner."""
        return (self.x, self.y + self.h)

    @property
    def bottom_right(self) -> Tuple[int, int]:
        """(x+w, y+h) coordinates of the bottom-right corner."""
        return (self.x + self.w, self.y + self.h)

    @property
    def tuple(self) -> Tuple[int, int, int, int]:
        """Return (x, y, w, h) as a plain tuple."""
        return (self.x, self.y, self.w, self.h)

    @property
    def dict(self) -> Dict[str, int]:
        """Return format compatible with MSS: {'left', 'top', 'width', 'height'}."""
        return {"left": self.x, "top": self.y, "width": self.w, "height": self.h}

    def offset(self, dx: int, dy: int) -> 'Match':
        """Return a new Match object shifted by (dx, dy)."""
        return Match(self.x + dx, self.y + dy, self.w, self.h, self.score, self.name, self.template)

    def __iter__(self):
        """Allows unpacking: x, y, w, h = match"""
        yield from (self.x, self.y, self.w, self.h)

    def __getitem__(self, index):
        """Allows index access: match[0]"""
        return (self.x, self.y, self.w, self.h, self.score)[index]


def _ensure_3ch(img: np.ndarray) -> np.ndarray:
    """Convert a 2-channel (grayscale) image to 3-channel BGR."""
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def _create_boxes(result: np.ndarray, template: np.ndarray, threshold: float, name: Optional[str] = None) -> List[Match]:
    """Find all locations above threshold and create Match objects."""
    h, w = template.shape[:2]
    locations = np.where(result >= threshold)
    boxes: List[Match] = []
    for x, y in zip(locations[1], locations[0]):
        score = float(np.min(result[y, x])) if result.ndim > 2 else float(result[y, x])
        boxes.append(Match(int(x), int(y), int(w), int(h), score, name, template))
    return boxes


def _group_boxes(boxes: List[Match]) -> List[Match]:
    """Group overlapping rectangles and keep the highest score per group."""
    if not boxes:
        return []
    rects_only = [(b.x, b.y, b.w, b.h) for b in boxes]
    grouped, _ = cv2.groupRectangles(rects_only, groupThreshold=1, eps=0.5)

    # Metadata from original matches (all matches in this list should share name/template)
    name = boxes[0].name
    template = boxes[0].template

    result: List[Match] = []
    for gx, gy, gw, gh in grouped:
        max_score = 0.0
        for ob in boxes:
            # Check overlap
            if not (ob.x + ob.w < gx or ob.x > gx + gw or ob.y + ob.h < gy or ob.y > gy + gh):
                if ob.score > max_score:
                    max_score = ob.score
        result.append(Match(int(gx), int(gy), int(gw), int(gh), float(max_score), name, template))
    return result


def _normalize_boxes(boxes: Union[None, Match, dict, tuple, list]) -> List[Match]:
    """
    Normalize any boxes input to a flat List[Match].
    Prevents nesting and handles various coordinate formats.
    """
    if boxes is None:
        return []

    # 1. Handle single objects
    if isinstance(boxes, Match):
        return [boxes]

    if isinstance(boxes, dict):
        if {"left", "top", "width", "height"}.issubset(boxes.keys()):
            return [Match(
                int(boxes["left"]), int(boxes["top"]), 
                int(boxes["width"]), int(boxes["height"]),
                name=boxes.get("name")
            )]
        return []

    # 2. Handle sequences (tuples or lists)
    if isinstance(boxes, (tuple, list)):
        if not boxes:
            return []

        # Is it a single box sequence? (e.g. (x, y, w, h) or (x, y))
        if all(isinstance(v, (int, float)) for v in boxes):
            if len(boxes) == 4:
                return [Match(int(boxes[0]), int(boxes[1]), int(boxes[2]), int(boxes[3]))]
            if len(boxes) == 2:
                return [Match(int(boxes[0]), int(boxes[1]), 0, 0)]
            return []

        # It's a collection of boxes
        result: List[Match] = []
        for b in boxes:
            if isinstance(b, Match):
                result.append(b)
            elif isinstance(b, dict):
                normalized = _normalize_boxes(b)
                if normalized: result.append(normalized[0])
            elif isinstance(b, (tuple, list)):
                if len(b) == 4:
                    result.append(Match(int(b[0]), int(b[1]), int(b[2]), int(b[3])))
                elif len(b) == 2:
                    result.append(Match(int(b[0]), int(b[1]), 0, 0))
        return result

    return []


def draw_bounding_boxes(
    image: np.ndarray, 
    boxes: Optional[List[Match]] = None, 
    color: Tuple[int, int, int] = (0, 255, 0), 
    thickness: int = 2,
    draw_labels: bool = True
) -> np.ndarray:
    """
    Draw bounding boxes on an image.

    Args:
        image: The image to draw on.
        boxes: A list of Match objects or anything normalizable to a Match list.
        color: The color of the bounding box (BGR format).
        thickness: The thickness of the lines.
        draw_labels: Whether to draw the Match name above the box.

    Returns:
        The image with bounding boxes drawn.
    """
    if boxes is None:
        return image

    for box in _normalize_boxes(boxes):
        # Draw the rectangle
        cv2.rectangle(image, (box.x, box.y), (box.x + box.w, box.y + box.h), color, thickness)
        
        # Draw the label if requested and present
        if draw_labels and box.name:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_thickness = 1
            label = f"{box.name} ({box.score:.2f})"
            
            # Get text size for background rectangle
            (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            # Draw background for text to make it readable
            label_y = max(box.y, label_h + 10) # Ensure label isn't off-screen top
            cv2.rectangle(image, (box.x, label_y - label_h - 5), (box.x + label_w, label_y + baseline - 5), color, -1)
            
            # Draw text in white or black depending on color brightness
            text_color = (0, 0, 0) if (color[0] + color[1] + color[2]) / 3 > 128 else (255, 255, 255)
            cv2.putText(image, label, (box.x, label_y - 5), font, font_scale, text_color, font_thickness)
            
    return image


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert an image to grayscale if it isn't already."""
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def match_template(
    image: np.ndarray,
    template: np.ndarray,
    method: int = cv2.TM_CCOEFF_NORMED,
    threshold: float = 0.85,
    group_rectangles: bool = False,
    sort_by_score: bool = False,
    name: Optional[str] = None,
) -> List[Match]:
    """
    Match a template within an image using grayscale comparison.

    Args:
        image: The larger image to search within.
        template: The template image to search for.
        method: OpenCV template matching method.
        threshold: Minimum confidence to count as a match.
        group_rectangles: Merge overlapping detections into single boxes.
        sort_by_score: Sort results by confidence score descending.
        name: Optional semantic name for the template.

    Returns:
        List of Match objects.
    """
    image_gray = to_grayscale(image)
    template_gray = to_grayscale(template)
    result = cv2.matchTemplate(image_gray, template_gray, method)
    boxes = _create_boxes(result, template_gray, threshold, name=name)
    if not boxes:
        return []
    if group_rectangles:
        boxes = _group_boxes(boxes)
    if sort_by_score:
        boxes.sort(key=lambda b: b.score, reverse=True)
    return boxes


def match_template_color(
    image: np.ndarray,
    template: np.ndarray,
    method: int = cv2.TM_CCOEFF_NORMED,
    color_space: str = "bgr",
    threshold: float = 0.85,
    group_rectangles: bool = False,
    sort_by_score: bool = False,
    name: Optional[str] = None,
) -> List[Match]:
    """
    Match a template within an image using per-channel color comparison.

    Each channel is matched independently; the final score is the minimum
    across all channels, making this stricter than grayscale matching.

    Args:
        image: The larger image to search within.
        template: The template image to search for.
        method: OpenCV template matching method.
        color_space: "bgr" or "hsv".
        threshold: Minimum confidence to count as a match.
        group_rectangles: Merge overlapping detections into single boxes.
        sort_by_score: Sort results by confidence score descending.
        name: Optional semantic name for the template.

    Returns:
        List of Match objects.
    """
    image = _ensure_3ch(image)
    template = _ensure_3ch(template)

    if color_space.lower() == "hsv":
        image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        template = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)

    img_ch = cv2.split(image)
    tmpl_ch = cv2.split(template)

    combined = np.min(
        np.stack([cv2.matchTemplate(ic, tc, method) for ic, tc in zip(img_ch, tmpl_ch)], axis=-1),
        axis=-1,
    )
    boxes = _create_boxes(combined, template, threshold, name=name)
    if not boxes:
        return []
    if group_rectangles:
        boxes = _group_boxes(boxes)
    if sort_by_score:
        boxes.sort(key=lambda b: b.score, reverse=True)
    return boxes


def get_click_location(boxes: Union[List[Match], Match, dict, tuple]) -> Optional[Tuple[int, int]]:
    """
    Determine a single click location from the detected bounding boxes.
    Returns the center of the largest detected box.

    Args:
        boxes: A Match object, a list of Match objects, or anything normalizable 
               (tuple, dict) to boxes.

    Returns:
        (x, y) center coordinates, or None if no valid boxes are provided.
    """
    match_list = _normalize_boxes(boxes)
    if not match_list:
        return None

    # Find largest by area, fallback to first if areas are zero (points)
    largest = max(match_list, key=lambda b: b.area)
    return largest.center

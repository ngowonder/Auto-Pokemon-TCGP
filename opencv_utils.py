'''
opencv-python utils
'''

import cv2
import numpy as np

from typing import Literal


def to_grayscale(image):
    """
    Convert an image to grayscale.

    Args:
        image: The image to convert.
    """
    # if len(image.shape) == 2:  # Already grayscale
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def draw_bounding_boxes(image, boxes=None, color=(0, 255, 0), thickness=2):
    """
    Draw bounding boxes on an image.

    Args:
        image: The image to draw on.
        boxes: A list of bounding boxes (x, y, w, h) or None to draw all.
        color: The color of the bounding box (BGR format).
        thickness: The thickness of the bounding box lines.
    """
    if boxes is None:
        return image

    for (x, y, w, h) in boxes:
        cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
    return image


def match_template(image, template, method=cv2.TM_CCOEFF_NORMED, threshold=0.85, group_rectangles=False):
    """
    Match a template within an image.

    Args:
        image: The larger image to search within.
        template: The template image to search for.
        method: Template matching method.
        threshold: Match threshold to determine if a match is valid.
        group_rectangles: Whether to group overlapping rectangles.

    Return:
        List of boxes (x, y, w, h).
    """
    # Ensure image and template is a NumPy array
    if not isinstance(image, np.ndarray):
        image = np.array(image)

    if not isinstance(template, np.ndarray):
        template = np.array(template)

    # Convert to grayscale
    image_gray = to_grayscale(image)
    template_gray = to_grayscale(template)

    # Perform template matching
    result = cv2.matchTemplate(image_gray, template_gray, method)

    # Find locations above threshold
    locations = np.where(result >= threshold)

    # Get template dimensions
    h, w = template.shape[:2]

    # Create boxes from locations
    boxes = [(int(x), int(y), int(w), int(h)) for x, y in zip(locations[1], locations[0])]

    # Group rectangles if the option is enabled
    if group_rectangles and boxes:
        grouped, _ = cv2.groupRectangles(boxes, groupThreshold=1, eps=0.5)
        boxes = [tuple(int(val) for val in b) for b in grouped]

    return boxes


def match_template_color(image, template, method=cv2.TM_CCOEFF_NORMED, color_space: Literal["bgr", "hsv"]="bgr", 
                        threshold=0.85, group_rectangles=False):
    """
    Match a template within an image using color information (per-channel matching).

    Args:
        image: The larger image to search within.
        template: The template image to search for.
        method: Template matching method.
        threshold: Match threshold to determine if a match is valid.
        group_rectangles: Whether to group overlapping rectangles.

    Return:
        List of boxes (x, y, w, h).
    """
    if not isinstance(image, np.ndarray):
        image = np.array(image)
    if not isinstance(template, np.ndarray):
        template = np.array(template)

    # Ensure both are 3-channel, convert grayscale to BGR (OpenCV format)
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if template.ndim == 2:
        template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)

    # Convert to the specified color space
    if color_space.lower() == "hsv":
        image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        template = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    else:  # Default to BGR
        image = image
        template = template

    # Split channels
    image_channels = cv2.split(image)
    template_channels = cv2.split(template)

    # Match each channel
    results = []
    for img_ch, tmpl_ch in zip(image_channels, template_channels):
        res = cv2.matchTemplate(img_ch, tmpl_ch, method)
        results.append(res)

    # Stack results and take the minimum across all channels
    stacked_results = np.stack(results, axis=-1)
    combined_result = np.min(stacked_results, axis=-1)

    # Find locations above threshold
    locations = np.where(combined_result >= threshold)

    # Get template dimensions
    h, w = template.shape[:2]

    # Create boxes (x, y, w, h)
    boxes = [(int(x), int(y), int(w), int(h)) for x, y in zip(locations[1], locations[0])]

    # Group overlapping rectangles if requested
    if group_rectangles and boxes:
        grouped, _ = cv2.groupRectangles(boxes, groupThreshold=1, eps=0.5)
        boxes = [tuple(int(val) for val in b) for b in grouped]

    return boxes


def get_click_location(boxes):
    """
    Determine a single click location from the detected bounding boxes.

    Args:
        boxes: A list of bounding boxes (x, y, w, h).

    Return:
        Tuple (x, y) representing the click location or None.
    """
    if not boxes:
        print('No boxes detected')
        return None

    if isinstance(boxes, tuple) and len(boxes) == 2:
        x, y = boxes
        return (x, y)
    elif isinstance(boxes, tuple) and len(boxes) == 4:
        boxes = [tuple(boxes)]

    # Find the largest bounding box
    largest_box = max(boxes, key=lambda box: box[2] * box[3])

    # Calculate the center of the largest bounding box
    x, y, w, h = largest_box
    click_x = x + w // 2
    click_y = y + h // 2

    return (click_x, click_y)

'''
opencv-python utils
'''

import cv2
import numpy as np


def draw_bounding_boxes(image, boxes, color=(0, 255, 0), thickness=2):
    """
    Draw bounding boxes on an image.

    :param image: The image to draw on.
    :param boxes: A list of bounding boxes (x, y, w, h).
    :param color: The color of the bounding box (BGR).
    :param thickness: The thickness of the bounding box lines.
    :return: The image with bounding boxes drawn.
    """
    for (x, y, w, h) in boxes:
        cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
    return image


def match_template(image, template, method=cv2.TM_CCOEFF_NORMED, threshold=0.85, group_rectangles=False):
    """
    Match a template image within a larger image using OpenCV's matchTemplate function.

    :param image: The larger image to search within.
    :param template: The template image to search for.
    :param method: The method to use for template matching.
    :param threshold: The threshold to determine if a match is valid.
    :return: The image with bounding boxes drawn around detected matches.
    """
    # Ensure image and template is a NumPy array
    if not isinstance(image, np.ndarray):
        image = np.array(image)

    if not isinstance(template, np.ndarray):
        template = np.array(template)

    # Convert images to grayscale if they are not already
    if len(image.shape) == 3:
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image

    if len(template.shape) == 3:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template

    # Get the dimensions of the template
    template_height, template_width = template_gray.shape

    # Perform template matching
    result = cv2.matchTemplate(image_gray, template_gray, method)

    # Find the locations where the match value is above the threshold
    locations = np.where(result >= threshold)

    # Extract the coordinates of the bounding boxes
    boxes = []
    for (x, y) in zip(*locations[::-1]):
        boxes.append((x, y, template_width, template_height))

    # Group rectangles if the option is enabled
    if group_rectangles:
        boxes, _ = cv2.groupRectangles([list(box) for box in boxes], groupThreshold=1, eps=0.5)
        # Ensure boxes is always a list
        if isinstance(boxes, tuple) and len(boxes) == 1:
            boxes = [boxes[0]]

    # Draw bounding boxes on the original image
    image_with_boxes = draw_bounding_boxes(image.copy(), boxes, color=(0, 255, 0), thickness=2)

    return image_with_boxes, boxes


def get_click_location(boxes):
    """
    Determine a single click location from the detected bounding boxes.

    :param boxes: A list of bounding boxes (x, y, w, h).
    :return: A tuple (x, y) representing the click location.
    """
    if len(boxes) == 0:
        print('Error with get_click_location')
        return None
    elif len(boxes) == 1:
        largest_box = boxes[0]
    else:
        # Find the largest bounding box
        largest_box = max(boxes, key=lambda box: box[2] * box[3])

    # Calculate the center of the largest bounding box
    x, y, w, h = largest_box
    click_x = x + w // 2
    click_y = y + h // 2

    return (click_x, click_y)

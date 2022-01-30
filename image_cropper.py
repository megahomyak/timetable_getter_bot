from typing import Iterable

import PIL.Image


def color_looks_like(first_color: Iterable[int], second_color: Iterable[int]):
    return all(
        abs(first_channel - second_channel) < 20
        for first_channel, second_channel in zip(first_color, second_color)
    )


def crop_white_margins(image: PIL.Image.Image):
    """
    Crops white margins at the bottom and on the right of the given image.
    Image should be in RGB mode.
    """
    content_end_y = 0
    content_end_x = 0
    #   ########^^
    #   ####^###^^
    #   ^^##^###^^
    # > ^^^^^^^^^^
    #
    #   ^
    # Go from bottom to top, and if one non-white pixel was encountered, it
    # means that the content for this column ends here. Just take a
    # maximum value of these numbers and here it is, the content's real end
    for x in range(image.width):
        y = image.height - 1
        # Go until we meet some non-white pixel
        while not color_looks_like(image.getpixel((x, y)), (0, 0, 0)):
            if y == 0:
                # All of the pixels in this column were white, so this column is
                # empty
                break
            y -= 1
        else:
            # Non-white pixel was found in this column, so this column
            # definitely has some content
            content_end_x = x
            if y > content_end_y:
                content_end_y = y
    return image.crop((
        0,  # Left border
        0,  # Upper border
        content_end_x,  # Right border
        content_end_y  # Lower border
    ))

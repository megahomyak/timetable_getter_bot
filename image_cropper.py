import functools

from PIL import Image as PILImageModule

BLACK = (0, 0, 0)


def color_looks_like(first_color, second_color):
    return all(
        abs(first_channel - second_channel) < 20
        for first_channel, second_channel in zip(first_color, second_color)
    )


class _NowhereToGo(Exception):
    pass


def _increment_y(coordinates, image):
    coordinates[1] += 1
    if coordinates[1] == image.width:
        coordinates[1] -= 1
        raise _NowhereToGo


def _increment_x(coordinates, image):
    coordinates[0] += 1
    if coordinates[0] == image.height:
        coordinates[0] -= 1
        raise _NowhereToGo


# noinspection PyUnusedLocal
def _decrement_y(coordinates, image):
    if coordinates[1] == 0:
        raise _NowhereToGo
    else:
        coordinates[1] -= 1


# noinspection PyUnusedLocal
def _decrement_x(coordinates, image):
    if coordinates[0] == 0:
        raise _NowhereToGo
    else:
        coordinates[0] -= 1


class ImageCropper:

    def __init__(self, image: PILImageModule.Image):
        if image.mode != "RGB":
            image = image.convert("RGB")
        self.image = image
        self.coordinates = [5, image.height - 1]
        (
            self.go_up_while_color_is_black,
            self.go_up_until_color_is_black,
            self.go_left_while_color_is_black,
            self.go_left_until_color_is_black,
            self.go_down_while_color_is_black,
            self.go_down_until_color_is_black,
            self.go_right_while_color_is_black,
            self.go_right_until_color_is_black
        ) = (
            functools.partial(fn, functools.partial(action))
            for fn, action in (
                (self._go_while_black, _decrement_y),
                (self._go_until_black, _decrement_y),
                (self._go_while_black, _decrement_x),
                (self._go_until_black, _decrement_x),
                (self._go_while_black, _increment_y),
                (self._go_until_black, _increment_y),
                (self._go_while_black, _increment_x),
                (self._go_until_black, _increment_x)
            )
        )

    def _go_while_black(self, action):
        try:
            while color_looks_like(self._get_current_pixel(), BLACK):
                action(self.coordinates, self.image)
        except _NowhereToGo:
            pass

    def _get_current_pixel(self):
        return self.image.getpixel(tuple(self.coordinates))

    def _go_until_black(self, action):
        try:
            while not color_looks_like(self._get_current_pixel(), BLACK):
                action(self.coordinates, self.image)
        except _NowhereToGo:
            pass

    def _go_one_row_up_and_get_row_height(self):
        row_lower_border = self.coordinates[1]
        self.go_up_until_color_is_black()
        row_upper_border = self.coordinates[1] + 1
        return row_lower_border - row_upper_border

    def crop(self):
        self.go_up_until_color_is_black()
        self.go_up_while_color_is_black()
        lower_border = self.coordinates[1]
        self.go_right_until_color_is_black()
        self.go_right_while_color_is_black()
        max_common_row_height = self._go_one_row_up_and_get_row_height() * 2
        self.go_up_while_color_is_black()
        while self._go_one_row_up_and_get_row_height() < max_common_row_height:
            self.go_up_while_color_is_black()
        old_coordinates = self.coordinates.copy()
        self.go_left_while_color_is_black()
        left_border = self.coordinates[0] + 1
        self.coordinates = old_coordinates
        self.coordinates[1] += 1
        upper_border = self.coordinates[1]
        for _ in range(3):
            self.go_right_until_color_is_black()
            self.go_right_while_color_is_black()
        self.go_right_until_color_is_black()
        right_border = self.coordinates[0] - 1
        return self.image.crop((
            left_border,
            upper_border,
            right_border,
            lower_border
        ))

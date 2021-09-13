import functools

from PIL import Image as PILImageModule

BLACK = (0, 0, 0)


def color_looks_like(first_color, second_color):
    return all(
        abs(first_channel - second_channel) < 20
        for first_channel, second_channel in zip(first_color, second_color)
    )


def _increment_y(coordinates):
    coordinates[1] += 1


def _increment_x(coordinates):
    coordinates[0] += 1


def _decrement_y(coordinates):
    coordinates[1] -= 1


def _decrement_x(coordinates):
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
            functools.partial(fn, functools.partial(action, self.coordinates))
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
        while color_looks_like(self._get_current_pixel(), BLACK):
            action()

    def _get_current_pixel(self):
        return self.image.getpixel(tuple(self.coordinates))

    def _go_until_black(self, action):
        while not color_looks_like(self._get_current_pixel(), BLACK):
            action()

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
        self.go_right_until_color_is_black()
        self.coordinates[0] -= 1
        right_border = self.coordinates[0]
        max_common_row_height = self._go_one_row_up_and_get_row_height() * 2
        while self._go_one_row_up_and_get_row_height() < max_common_row_height:
            self.go_up_while_color_is_black()
        upper_border = self.coordinates[1] + 1
        self.go_left_while_color_is_black()
        left_border = self.coordinates[0] + 1
        return self.image.crop((
            left_border,
            upper_border,
            right_border,
            lower_border
        ))

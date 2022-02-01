from collections.abc import Iterator


class LoopedTwoWaysIterator(Iterator):

    def __init__(self, initial_list: list):
        self.initial_list = initial_list
        self.list_index = 0

    def __next__(self):
        self.list_index += 1
        try:
            return self.initial_list[self.list_index]
        except IndexError:
            self.list_index = 0
            return self.initial_list[self.list_index]

    def step_back(self):
        self.list_index -= 1

    def step_forward(self):
        self.list_index += 1
        try:
            return self.initial_list[self.list_index]
        except IndexError:
            raise StopIteration from None

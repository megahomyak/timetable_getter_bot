def reversed_range(end: int):
    # end - 1 as a start makes it start at end - 1,
    # -1 as an end makes it stop at 0,
    # -1 as a step makes it go backwards (that's what we need)
    return range(end - 1, -1, -1)

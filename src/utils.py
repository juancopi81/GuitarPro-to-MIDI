def get_duration_name(value):
    duration_mapping = {
        1: "whole",
        2: "half",
        4: "quarter",
        8: "eighth",
        16: "sixteenth",
        32: "thirtySecond",
        64: "sixtyFourth",
        128: "hundredTwentyEighth",
    }
    return duration_mapping.get(value)

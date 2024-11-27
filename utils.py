# helper function to convert from Metaculus internal scale to actual scale
def internal_to_actual(x, zero_point, lower_bound, upper_bound, is_linear=True):
    actual_range = upper_bound - lower_bound
    if is_linear:
        return lower_bound + actual_range * x
    dr = (upper_bound - zero_point) / (lower_bound - zero_point)
    return lower_bound + actual_range * (dr**x - 1) / (dr - 1)

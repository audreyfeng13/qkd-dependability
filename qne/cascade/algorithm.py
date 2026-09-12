import math

def original_block_size_function(iteration_nr, estimated_bit_error_rate, key_size):
    """Block size formula for the 'original' Cascade algorithm variant."""
    min_ber = 0.00001
    if estimated_bit_error_rate < min_ber:
        estimated_bit_error_rate = min_ber
    if iteration_nr == 1:
        return math.ceil(0.73 / estimated_bit_error_rate)
    return 2 * original_block_size_function(iteration_nr - 1, estimated_bit_error_rate, key_size)


class Algorithm:
    def __init__(self, name, nr_cascade_iterations, block_size_function):
        self.name = name
        self.nr_cascade_iterations = nr_cascade_iterations
        self.block_size_function = block_size_function


ORIGINAL = Algorithm("original", nr_cascade_iterations=4,
                      block_size_function=original_block_size_function)
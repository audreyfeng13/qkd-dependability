class Block:
    """A contiguous range of bits within one cascade iteration's shuffled key,
    used for the parity bisection search."""

    UNKNOWN_PARITY = -1

    def __init__(self, iteration, start_bit_nr, end_bit_nr, parent_block=None, block_nr=0):
        self.iteration = iteration
        self.shuffled_key = iteration.shuffled_key
        self.start_bit_nr = start_bit_nr
        self.end_bit_nr = end_bit_nr
        self.current_parity = Block.UNKNOWN_PARITY
        self.correct_parity = Block.UNKNOWN_PARITY
        self.parent_block = parent_block
        self.block_nr = block_nr
        self.left_sub_block = None
        self.right_sub_block = None

    def get_nr_bits(self):
        return self.end_bit_nr - self.start_bit_nr + 1

    def get_or_compute_current_parity(self):
        if self.current_parity == Block.UNKNOWN_PARITY:
            self.current_parity = self.shuffled_key.compute_range_parity(
                self.start_bit_nr, self.end_bit_nr)
        return self.current_parity

    def flip_current_parity(self):
        if self.current_parity == Block.UNKNOWN_PARITY:
            return
        self.current_parity = 1 - self.current_parity

    def set_correct_parity(self, parity):
        self.correct_parity = parity

    def correct_parity_is_known(self):
        return self.correct_parity != Block.UNKNOWN_PARITY

    def try_to_infer_correct_parity(self):
        """If both the parent's and sibling's correct parity are known, the
        correct parity of this block can be derived without asking Alice."""
        if self.parent_block is None:
            return False
        sibling = (self.parent_block.right_sub_block
                   if self.parent_block.left_sub_block is self
                   else self.parent_block.left_sub_block)
        if sibling is None:
            return False
        if self.parent_block.correct_parity == Block.UNKNOWN_PARITY:
            return False
        if sibling.correct_parity == Block.UNKNOWN_PARITY:
            return False
        if self.parent_block.correct_parity == 1:
            self.correct_parity = 1 - sibling.correct_parity
        else:
            self.correct_parity = sibling.correct_parity
        return True

    def get_error_parity(self):
        assert self.correct_parity != Block.UNKNOWN_PARITY
        current = self.get_or_compute_current_parity()
        return 0 if self.correct_parity == current else 1

    def create_left_sub_block(self):
        if self.left_sub_block is not None:
            return self.left_sub_block
        mid = self.start_bit_nr + (self.get_nr_bits() // 2) - 1
        block = Block(self.iteration, self.start_bit_nr, mid, self, 0)
        self.left_sub_block = block
        return block

    def create_right_sub_block(self):
        if self.right_sub_block is not None:
            return self.right_sub_block
        mid = self.start_bit_nr + (self.get_nr_bits() // 2)
        block = Block(self.iteration, mid, self.end_bit_nr, self, 1)
        self.right_sub_block = block
        return block
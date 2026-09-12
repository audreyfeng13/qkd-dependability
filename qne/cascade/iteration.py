from .shuffle import Shuffle, ShuffledKey
from .block import Block

class Iteration:
    """One full pass of the Cascade algorithm."""

    def __init__(self, reconciliation, iteration_nr, seed=None):
        self.reconciliation = reconciliation
        self.iteration_nr = iteration_nr
        self.nr_key_bits = reconciliation.nr_key_bits

        self.shuffle_seed = seed
        self.shuffle = Shuffle(self.nr_key_bits, seed=seed)
        self.shuffled_key = ShuffledKey(reconciliation.reconciled_key, self.shuffle)

        self.block_size = reconciliation.algorithm.block_size_function(
            iteration_nr, reconciliation.estimated_bit_error_rate, self.nr_key_bits)

        self.top_blocks = []

    def schedule_initial_work(self):
        block_nr = 0
        start_bit_nr = 0
        while start_bit_nr < self.nr_key_bits:
            end_bit_nr = min(start_bit_nr + self.block_size, self.nr_key_bits) - 1
            block = Block(self, start_bit_nr, end_bit_nr, None, block_nr)
            self.top_blocks.append(block)
            self.reconciliation.schedule_ask_correct_parity(block, False)
            block_nr += 1
            start_bit_nr += self.block_size

    def try_correct_block(self, block, correct_right_sibling, cascade, _depth=0):
        if _depth > 50:
            raise RuntimeError(f"try_correct_block recursion exceeded 50 levels -- "
                                f"likely fault-induced desync causing pathological bisection")

        if not block.correct_parity_is_known():
            if not block.try_to_infer_correct_parity():
                self.reconciliation.schedule_ask_correct_parity(block, correct_right_sibling)
                return 0

        error_parity = block.get_error_parity()

        if error_parity == 0:
            if correct_right_sibling:
                return self._try_correct_right_sibling(block, cascade, _depth + 1)
            return 0

        if block.get_nr_bits() == 1:
            orig_bit_nr = self.shuffle.shuffle_to_orig(block.start_bit_nr)
            self.reconciliation.correct_orig_key_bit(orig_bit_nr, self.iteration_nr, cascade)
            return 1

        left = block.left_sub_block or block.create_left_sub_block()
        return self.try_correct_block(left, True, cascade, _depth + 1)

    def _try_correct_right_sibling(self, block, cascade, _depth=0):
        parent = block.parent_block
        right = parent.right_sub_block or parent.create_right_sub_block()
        return self.try_correct_block(right, False, cascade, _depth + 1)

    def get_cascade_block(self, orig_key_bit_nr):
        shuffled_bit_nr = self.shuffle.orig_to_shuffle(orig_key_bit_nr)
        block_nr = shuffled_bit_nr // self.block_size
        if block_nr < len(self.top_blocks):
            return self.top_blocks[block_nr]
        return None

    def flip_parity_in_all_blocks_containing_bit(self, orig_key_bit_nr):
        shuffled_bit_nr = self.shuffle.orig_to_shuffle(orig_key_bit_nr)
        block_nr = shuffled_bit_nr // self.block_size
        if block_nr >= len(self.top_blocks):
            return
        block = self.top_blocks[block_nr]
        block.flip_current_parity()
        while True:
            sub = block.left_sub_block
            if sub is None:
                break
            if shuffled_bit_nr <= sub.end_bit_nr:
                sub.flip_current_parity()
                block = sub
                continue
            sub = block.right_sub_block
            if sub is None:
                break
            sub.flip_current_parity()
            block = sub
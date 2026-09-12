from .shuffle import ShuffledKey

class MockClassicalSession:
    """In-memory session for isolated/offline testing."""
    def __init__(self, correct_key):
        self.correct_key = correct_key
        self.total_leaked_bits = 0  # running tally of bits communicated Alice -> Bob

    def ask_correct_parities(self, blocks):
        # Each block's parity is a single bit that Alice would send to Bob
        # in the real protocol -- this IS the leakage.
        self.total_leaked_bits += len(blocks)
        for block in blocks:
            iteration = block.iteration
            shuffle = iteration.shuffle
            shuffled_correct_key = ShuffledKey(self.correct_key, shuffle)
            parity = shuffled_correct_key.compute_range_parity(
                block.start_bit_nr, block.end_bit_nr)
            block.set_correct_parity(parity)


class QFabricClassicalSession:
    """Real classical-session implementation using QFabric's existing
    ClassicalClient/ClassicalServer channel. Sends the iteration number
    and shuffle seed alongside each block range, so Alice can reconstruct
    the SAME shuffle Bob's blocks are expressed in before computing parity."""

    def __init__(self, channel):
        self.channel = channel

    def ask_correct_parities(self, blocks):
        self.channel.send_message({
            "type": "cascade_ask_parities",
            "blocks": [
                (b.start_bit_nr, b.end_bit_nr, b.iteration.iteration_nr, b.iteration.shuffle_seed)
                for b in blocks
            ],
        })
        response = self.channel.recv_message()
        for block, parity in zip(blocks, response["parities"]):
            block.set_correct_parity(parity)


def alice_handle_ask_parities(channel, alice_key):
    """Alice-side handler: reconstructs the correct Shuffle for each
    requested block's iteration before computing parity, matching Bob's
    shuffled coordinate space exactly."""
    from .shuffle import Shuffle, ShuffledKey

    msg = channel.recv_message()
    assert msg["type"] == "cascade_ask_parities"

    shuffle_cache = {}  # iteration_nr -> Shuffle object, reused across blocks in this request
    parities = []
    for start, end, iteration_nr, shuffle_seed in msg["blocks"]:
        if iteration_nr not in shuffle_cache:
            shuffle_cache[iteration_nr] = Shuffle(alice_key.get_nr_bits(), seed=shuffle_seed)
        shuffle = shuffle_cache[iteration_nr]
        shuffled_alice_key = ShuffledKey(alice_key, shuffle)
        parity = shuffled_alice_key.compute_range_parity(start, end)
        parities.append(parity)

    channel.send_message({"type": "cascade_parities_result", "parities": parities})
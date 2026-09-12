from collections import deque
from .iteration import Iteration

class Reconciliation:
    """Top-level Cascade orchestrator."""

    def __init__(self, algorithm, classical_session, noisy_key, estimated_bit_error_rate,
                 correct_key=None, seed=None, fault_injector=None):
        self.algorithm = algorithm
        self.classical_session = classical_session
        self.reconciled_key = noisy_key.copy()
        self.estimated_bit_error_rate = estimated_bit_error_rate
        self.correct_key = correct_key
        self.nr_key_bits = noisy_key.get_nr_bits()
        self.seed = seed
        self.fault_injector = fault_injector

        self.iterations = []
        self.pending_ask_correct_parity_blocks = deque()
        self.pending_try_correct_blocks = deque()
        self.corrected_bit_positions = set()

    def reconcile(self):
        for i in range(self.algorithm.nr_cascade_iterations):
            iteration_nr = i + 1
            iter_seed = None if self.seed is None else self.seed + iteration_nr
            iteration = Iteration(self, iteration_nr, seed=iter_seed)
            self.iterations.append(iteration)
            iteration.schedule_initial_work()
            self._service_all_pending_work(cascade=True)
        return self.reconciled_key

    def schedule_ask_correct_parity(self, block, correct_right_sibling):
        self.pending_ask_correct_parity_blocks.append((block, correct_right_sibling))

    def schedule_try_correct(self, block, correct_right_sibling):
        self.pending_try_correct_blocks.append((block, correct_right_sibling))

    def correct_orig_key_bit(self, orig_key_bit_nr, triggering_iteration_nr, cascade):
        if orig_key_bit_nr in self.corrected_bit_positions:
            return
        self.corrected_bit_positions.add(orig_key_bit_nr)

        self.reconciled_key.flip_bit(orig_key_bit_nr)

        if self.fault_injector is not None:
            self.fault_injector.maybe_flip_reconciliation_state_bit(
                self.reconciled_key, orig_key_bit_nr, context=f"iter{triggering_iteration_nr}")

        for iteration in self.iterations:
            iteration.flip_parity_in_all_blocks_containing_bit(orig_key_bit_nr)
        if cascade:
            self._cascade_effect(orig_key_bit_nr, triggering_iteration_nr)

    def _cascade_effect(self, orig_key_bit_nr, triggering_iteration_nr):
        for iteration in self.iterations:
            if iteration.iteration_nr != triggering_iteration_nr:
                block = iteration.get_cascade_block(orig_key_bit_nr)
                if block is not None:
                    self.schedule_try_correct(block, False)

    def _service_all_pending_work(self, cascade, max_loops=10000):
        errors_corrected = 0
        loop_count = 0
        while self.pending_ask_correct_parity_blocks or self.pending_try_correct_blocks:
            loop_count += 1
            if loop_count > max_loops:
                raise RuntimeError(
                    f"Reconciliation did not converge after {max_loops} loops -- "
                    f"likely fault-induced parity desync"
                )
            errors_corrected += self._service_pending_try_correct(cascade)
            self._service_pending_ask_correct_parity()
        return errors_corrected

    def _service_pending_try_correct(self, cascade, max_inner_loops=2000):
        errors_corrected = 0
        inner_count = 0
        while self.pending_try_correct_blocks:
            inner_count += 1
            if inner_count > max_inner_loops:
                raise RuntimeError(
                    f"_service_pending_try_correct did not drain after {max_inner_loops} "
                    f"iterations -- likely fault-induced runaway cascade-effect scheduling"
                )
            block, correct_right_sibling = self.pending_try_correct_blocks.popleft()
            iteration = block.iteration
            errors_corrected += iteration.try_correct_block(block, correct_right_sibling, cascade)
        return errors_corrected

    def _service_pending_ask_correct_parity(self):
        if not self.pending_ask_correct_parity_blocks:
            return
        blocks = list(self.pending_ask_correct_parity_blocks)
        self.pending_ask_correct_parity_blocks.clear()
        self.classical_session.ask_correct_parities([b for b, _ in blocks])
        for block, correct_right_sibling in blocks:
            self.schedule_try_correct(block, correct_right_sibling)
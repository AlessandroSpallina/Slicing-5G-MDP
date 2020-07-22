import mdptoolbox
import numpy as np
import utils


class State:
    def __init__(self, k, n):
        self._k = k  # k jobs
        self._n = n  # n servers

    @property
    def k(self):
        return self._k

    @property
    def n(self):
        return self._n

    def __str__(self):
        return "(" + str(self._k) + "," + str(self._n) + ")"

    def __sub__(self, other):
        k = self.k - other.k
        n = self.n - other.n
        return State(k, n)


class SliceMDP:
    def __init__(self, arrivals_histogram, departures_histogram, queue_size, max_server_num,
                 c_job=1, c_server=1, alpha=0.5, verbose=True):

        self._verbose = verbose

        self._arrivals_histogram = arrivals_histogram
        self._departures_histogram = departures_histogram
        self._queue_size = queue_size
        self._max_server_num = max_server_num

        # trans matrix stuff
        self._transition_matrix = self._generate_transition_matrix()

        # reward stuff
        self._c_job = c_job
        self._c_server = c_server
        self._alpha = alpha
        self._current_reward = self._calculate_reward()

    """
    es. b=2; s=1
    
    (k job, n server)
    S0: (0,0)
    S1: (1,0)
    S2: (2,0)
    S3: (0,1)
    S4: (1,1)
    S5: (2,1)
    """
    def _generate_states(self):
        states = []  # state at pos 0 -> S0, etc..
        for i in range(self._max_server_num + 1):
            for j in range(self._queue_size + 1):
                states.append(State(j, i))
        return states

    def _calculate_alloc_dealloc_probability(self, state):
        p_alloc = 1.
        p_dealloc = 1.
        if state.n == 0:
            p_dealloc = 0.
        elif state.n == self._max_server_num:
            p_alloc = 0.
        return p_alloc, p_dealloc

    def _calculate_h_p(self, state):
        # le probabilità di departure hanno senso solo per server_num > 0
        # in caso di server_num > 0, H_p per il sistema = H_p convuluto H_p nel caso di due server
        # perchè H_p_nserver = [P(s1:0)*P(s2:0), P(s1:0)*P(s2:1) + P(s1:1)*P(s2:0), P(s1:1)*P(s2:1)]
        # NB: la convoluzione è associativa, quindi farla a due a due per n volte è ok
        h_p = self._departures_histogram
        for i in range(1, state.n):
            h_p = np.convolve(h_p, self._departures_histogram)
        return h_p

    # old calculate_transition_prob https://0bin.net/paste/myC+f0f5d6CoKF79#4nJw-dt4IhQxddw6D4EjbiG0aWeUhzdYniWC3i0DWjm
    def _calculate_transition_probability(self, from_state, to_state, action_id):
        transition_probability = 0
        diff = to_state - from_state

        # prima valuto le transizioni "orizzontali"
        if from_state.n == 0:
            if diff.k == 0 and to_state.k == self._queue_size:
                transition_probability = 1.
            elif diff.k >= 0:
                try:
                    transition_probability = self._arrivals_histogram[diff.k]
                except IndexError:
                    pass
        else:
            if diff.k == 0 and to_state.k == 0:
                tmp = 0
                for i in range(1, len(self._departures_histogram)):
                    try:
                        tmp += self._arrivals_histogram[i] * self._departures_histogram[i]
                    except IndexError:
                        pass
                transition_probability = self._arrivals_histogram[0] + tmp

            elif diff.k >= 0:
                if to_state.k < self._queue_size:
                    tmp = 0
                    tmp2 = 0
                    for i in range(diff.k, self._queue_size):
                        try:
                            tmp += self._arrivals_histogram[i] * self._departures_histogram[i - diff.k]
                        except IndexError:
                            pass
                    for i in range(len(self._arrivals_histogram) - self._queue_size):
                        try:
                            tmp2 += self._arrivals_histogram[self._queue_size + i] * self._departures_histogram[self._queue_size - to_state.k]
                        except IndexError:
                            pass
                    transition_probability = tmp + tmp2
                elif to_state.k == self._queue_size:
                    for i in range(diff.k, len(self._arrivals_histogram)):
                        try:
                            transition_probability += self._arrivals_histogram[i] * self._departures_histogram[0]
                        except IndexError:
                            pass

            elif diff.k < 0:
                for i in range(-diff.k, len(self._departures_histogram)):
                    try:
                        transition_probability += self._arrivals_histogram[diff.k + i] * self._departures_histogram[i]
                    except IndexError:
                        pass
                if self._queue_size <= len(self._departures_histogram) - 1 or from_state.k == self._queue_size and -diff.k <= len(self._departures_histogram) - 1:
                    for i in range(len(self._departures_histogram) - 1, len(self._arrivals_histogram)):
                        try:
                            transition_probability += self._arrivals_histogram[i] * self._departures_histogram[len(self._departures_histogram) - 1]
                        except IndexError:
                            pass

        p_alloc, p_dealloc = self._calculate_alloc_dealloc_probability(from_state)

        # adesso valuto le eventuali transizioni "verticali"
        if action_id == 0:  # do nothing
            if to_state.n != from_state.n:
                return 0.

        elif action_id == 1:  # allocate 1 server
            if to_state.n != from_state.n + 1:
                return 0.
            else:
                transition_probability *= p_alloc

        elif action_id == 2:  # deallocate 1 server
            if to_state.n != from_state.n - 1:
                return 0.
            else:
                transition_probability *= p_dealloc




        return transition_probability

    """
    The transition matrix is of dim action_num * states_num * states_num
    Q[0] -> transition matrix related action 0 (do nothing)
    Q[1] -> transition matrix related action 0 (allocate 1)
    Q[2] -> transition matrix related action 0 (deallocate 1)
    """
    def _generate_transition_matrix(self):
        self._states = self._generate_states()

        if self._verbose:
            for i in range(len(self._states)):
                print(f"S{i}: {self._states[i]}")

        self._transition_matrix = np.zeros((3, len(self._states), len(self._states)))

        # lets iterate the trans matrix and fill with correct probabilities
        for a in range(len(self._transition_matrix)):
            for i in range(len(self._states)):
                for j in range(len(self._states)):
                    self._transition_matrix[a][i][j] = self._calculate_transition_probability(self._states[i], self._states[j], a)

        return self._transition_matrix

    def _calculate_reward(self):
        pass

    def allocate_server(self, count=1):
        pass

    def deallocate_server(self, count=1):
        pass

    def run_value_iteration(self):
        pass


if __name__ == '__main__':
    # generate histogram of arrivals
    # this means: Pr(0 job incoming in this timeslot) = 0.5; Pr(1 job incoming in this timeslot) = 0.5
    arrivals = [0.5, 0.5]

    # generate histogram of arrivals
    # this means: Pr(0 job processed in this timeslot) = 0.6; Pr(1 job processed in this timeslot) = 0.4
    departures = [0.6, 0.4]

    # @findme : generare grafico partenze e arrivi

    slice_mdp = SliceMDP(arrivals, departures, 2, 2)

    #print(slice_mdp._transition_matrix[0])
    utils.export_markov_chain("toy", "a0-do-nothing", slice_mdp._states, slice_mdp._transition_matrix[0], view=True)
    utils.export_markov_chain("toy", "a1-alloc1", slice_mdp._states, slice_mdp._transition_matrix[1], view=True)
    #utils.export_markov_chain("toy", "a2-dealloc1", slice_mdp._states, slice_mdp._transition_matrix[2], view=True)





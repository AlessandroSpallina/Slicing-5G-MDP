class SingleSliceState:
    def __init__(self, k, n):
        self._k = k  # k jobs
        self._n = n  # n servers

    @property
    def k(self):
        return self._k

    @k.setter
    def k(self, k):
        self._k = k

    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, n):
        self._n = n

    @property
    def json(self):
        return {'k': self._k, 'n': self._n}

    def __str__(self):
        return "(" + str(self._k) + "," + str(self._n) + ")"

    def __add__(self, other):
        k = self.k + other.k
        n = self.n + other.n
        return SingleSliceState(k, n)

    def __sub__(self, other):
        k = self.k - other.k
        n = self.n - other.n
        return SingleSliceState(k, n)

    def __eq__(self, other):
        # if isinstance(other, SingleSliceState):
        #     return self._k == other._k and self._n == other._n
        return self._k == other._k and self._n == other._n
        # return False

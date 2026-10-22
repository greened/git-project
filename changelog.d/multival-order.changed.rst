Reading a key with several values as an attribute now gives a
``tuple`` instead of a ``frozenset``. Code that compares the value
with a set, or uses set operations on it, needs ``set(...)``.

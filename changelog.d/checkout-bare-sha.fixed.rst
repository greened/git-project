``Git.checkout`` given a SHA, or any other committish with no ref, now
detaches HEAD at its commit as ``git checkout`` does.
``Git.update_symbolic_ref`` given one now raises ``GitProjectError``, since a
symbolic ref can only point at another ref. Both raised an ``AttributeError``
before.

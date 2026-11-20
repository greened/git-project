``Git.add_worktree`` given a committish that is not a local branch, such as a
SHA or a tag, now raises ``GitProjectError`` before it creates anything. It
raised a ``TypeError`` or ``GitError`` before, after creating the worktree's
parent directory.

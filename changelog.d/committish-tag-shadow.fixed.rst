``Git.checkout``, ``Git.add_worktree``, ``Git.update_symbolic_ref`` and
``Git.committish_is_pushed`` now take a short name that is both a branch and
a tag as the branch, and so do ``Project.branch_is_merged``,
``Project.branch_is_merged_remotely`` and ``Project.branch_is_pushed``. The
tag was taken in its place. A checkout or a symbolic ref could then land on
the tag, a worktree add failed, and a branch could be reported merged,
unmerged, pushed or unpushed by the tag's commit. The new
``Git.branch_or_committish_ref`` does the lookup. An unmerged SHA given to
``Project.branch_is_merged`` or ``Project.branch_is_pushed`` now gives False
instead of an ``AttributeError``.

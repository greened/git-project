``Git.refname_is_merged`` now resolves a target given as a short branch
name to that branch, and ``Project.branch_is_merged`` and
``Project.branch_is_pushed`` look up each project branch as a branch. A tag
with the same name, such as a tag ``master``, was taken in its place. A
branch could then be reported merged when only the tag contained it, or
unmerged or unpushed when the project branch contained it.

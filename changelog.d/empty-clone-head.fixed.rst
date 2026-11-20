``Git.clone`` of an empty repository now points HEAD at the branch the
remote's HEAD names, as ``git clone`` does, and without ``bare`` that
branch tracks origin. Before, the clone got ``master`` or the local
``init.defaultBranch``. It still gets ``init.defaultBranch``, else
``master``, with a warning, for a url that may carry a credential or a
remote that cannot be asked.

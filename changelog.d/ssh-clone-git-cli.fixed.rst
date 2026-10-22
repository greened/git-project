``Git.clone`` and ``Git.fetch_remote`` run the git CLI for an ssh url
without a password, so they use the ssh agent, ``~/.ssh/config`` and
``known_hosts`` as plain git does, and a Host alias now resolves. An ssh
clone has the same branches, upstream config and remote ``HEAD`` as a
libgit2 clone. A failure is a one-line ``GitProjectError`` that carries
git's error. ssh sends keepalives, so a link that stops answering fails in
about a minute. ``GIT_SSH_COMMAND`` turns that off, and so do
``GIT_SSH`` and ``core.sshCommand`` when ``ssh.id`` is unset. An ssh clone
or fetch through git gives up after six hours. A libgit2 clone or fetch
that reached an ssh server with no key to offer died with ``TypeError:
credential does not implement interface``, and now fails with a one-line
error.

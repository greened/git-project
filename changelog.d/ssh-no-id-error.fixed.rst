A clone, or a fetch through ``Git.fetch_remote``, of an ssh url with no
key to offer died with a traceback ending in ``TypeError: credential does
not implement interface``. It now fails with a one-line error. A fetch
offers the key ``ssh.id`` names; a clone offers none.

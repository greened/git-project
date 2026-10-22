A key with several values now gives them in the same order on every
run, the order git reads them from the config files. Before, the order
changed from one run to the next, so choices and ``--menu=json`` built
from such a key were reordered.

``--menu`` now reports whether an option takes a value from the action
argparse builds for it. An option added with ``action="append"``,
``action="extend"`` or a custom action class and no ``nargs`` was listed
as taking no value, and one with a custom action and ``nargs=0`` as taking
one.

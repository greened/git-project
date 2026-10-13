Loading a config object no longer writes the values it loaded into the
repository's local config. Every command loads the project this way, so a
single-valued key set in the project's section of the global or system config
was copied into the local config on each run, even by a command that changes
nothing. Removing a key that has no value in the local config no longer fails.
Any value it has in another config file, such as the global or system config,
stays in place.

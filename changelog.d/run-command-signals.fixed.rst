``run_command_with_shell`` no longer dies on a Ctrl-C or a SIGTERM while
its command runs. It waits for the command and returns its status. A
SIGTERM is sent on to the command, and so is a SIGINT when git-project is
not in the terminal's foreground group. Before, git-project exited and left
the command running. When the command dies of a signal, git-project now
exits by the same signal, so a shell loop running it stops on a Ctrl-C.

import git_project

import argparse
from pathlib import Path
import sys

def main_impl(args=None):
    """The main entry point for the git-config tools."""

    if not args:
        args = sys.argv[1:]

    git = git_project.Git()

    project_name = Path(sys.argv[0]).name

    prefix = 'git-'
    if project_name.startswith(prefix):
        project_name = project_name[len(prefix):]

    plugin_manager = git_project.PluginManager()

    plugin_manager.load_plugins(git)

    # Now that class hooks have been added, instantiate objects.
    gp = git_project.GitProject.get(git)

    project = git_project.Project.get(git, project_name)

    clargs = git_project.parse_arguments(git, gp, project, plugin_manager, args)

    plugin_manager.initialize_plugins(git, gp, project)

    clargs.func(git, gp, project, clargs)

def main(args=None):
    try:
        main_impl(args)
    except git_project.GitProjectException as exception:
        print(f'{exception.message}')
        raise SystemExit(-1)

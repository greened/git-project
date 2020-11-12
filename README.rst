***********
git-project
***********

The extensible stupid project manager

Setup
=====

``pip3 install git-project``

Description
===========

git-project is a git extension to manage development of a project hosted in a
git repository.  By itself git-project does almost nothing.  Its functionality
is enhanced by plugins.

`git-project-core-plugins
<http://www.github.com/greened/git-project-core-plugins>`_ provides a set of
basic functionality and should almost always be installed alongside git-project.

Conventions
===========

Symlinks identiy projects to the ``git-project`` command.  For example, if
``git-fizzbin`` is symlinked to ``git-project``, then ``git fizzbin <command>``
will invoke ``git-project`` with ``fizzbin`` as the "active project."  To
emphasize this, we show git-project commands with a generic ``<project>``
identifier::

  git <project> --help

Discussion
==========

With git-project and its core plugins you can:

* Initialize a development environment at clone time (or after clone time)
* Manage branches
* Manage worktrees
* Set and invoke configuration, build and install action

git-project is intended to make switching between active 'tasks' in a repository
simple and fast, without losing the progress context of existing tasks.  For
example the core plugins set up build environments such that switching among
projects and worktrees does not result in "rebuilding the world."  Builds can be
configured to invoke complex commands via a convenient name (e.g. ``git
<project> build debug``)

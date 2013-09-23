=============
gforge2github
=============

Migration script for moving a project's tracker / tickets / issues from GForge to GitHub.

This script was initially developed to help with moving multiple repositories from RENCI's (http://www.renci.org) hosted GForge instance to GitHub in the Fall of 2013.  Uses the GForge SOAP API and the GitHub RESTful OAuth API.

Inspiration came from the similar script for migrating from GoogleCode to Github (https://github.com/arthur-debert/google-code-issues-migrator).

This version:

 - always keeps trackeritem numbers and newly created issue numbers in sync to keep commit messages that reference particular bug or feature requests consistent through the migration
 - checks the username mapping for consistency before creating any issues at GitHub

Dependencies
============

 * [PyGithub](https://github.com/jacquev6/PyGithub/) -- `pip install PyGithub` -- v1.8.0+ required

 Or a simple subdirectory without requiring installation: `git clone https://github.com/jacquev6/PyGithub.git`

Usage
=====

1. Copy config.py.template to config.py and fill in the appropriate values.
2. Run with: ```python gforge2github.py```

Release History
===============

0.1 **Initial Release**
-----------------------

Works with 800+ trackeritems across 9 owners / commenters / assignees.

Should be run against a new clean GitHub repository with no existing issues.

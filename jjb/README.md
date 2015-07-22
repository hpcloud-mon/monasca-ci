# Jenkins Job Builder job definitions for Monasca
Jenkins Job Builder 1.2.0 is the version used.

*build* - Contains jobs for building the various projects and run unit tests. These watch for git changes and build as needed.
  - Most build jobs have two version one that builds master and another with '-dev' at the end that builds branches. This allows the system
    job to pull in all the master builds except for the one that triggered it and in that way test each change against the current master builds.

*system* - Includes jobs that build and test the entire Monasca System. These jobs are triggered by the various build jobs.

# Known issues
- Projects hosted in gerrit have no branches and so the only way to test changesets is full integration with gerrit, ie a user with ssh access.
  This effectively makes it unusable for an immutable system like this.

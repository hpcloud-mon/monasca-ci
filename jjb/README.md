# Jenkins Job Builder job definitions for Monasca
Jenkins Job Builder 1.2.0 is the version used.

*build* - Contains jobs for building the various projects and run unit tests. These watch for git changes and build as needed.
*system* - Includes jobs that build and test the entire Monasca System. These jobs are triggered by the various build jobs.


# Known issues
- The build jobs hosted in stackforge only build on changes to master. The problem is that changesets in gerrit don't use branches and
  so no new review builds are triggered. It is possible to integrate fully with gerrit and have it trigger the jobs based on gerrit events.
  Though that would work it requires a special account on gerrit which is a server we don't administer. An alternative is to setup
  a job that watches refs/changes in git but this will trigger a build for all changes in the entire repository rather than just new ones.
  A workaround would be to setup a special job that watched that refspec but only reacted when a new one appeared and in that
  case it would trigger the build job specifying the exact ref to run against.

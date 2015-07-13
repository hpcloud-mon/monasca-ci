# Monasca CI
A continuous integration build environment with automatic and regular testing is a necessity for modern projects. With Monasca
we are not shipping only a single project but rather are shipping a group of projects tightly coupled together as a single system.
This means that CI for the system as a whole is more important than that for individual projects, though it isn't a replacement for
simpler project based CI. This Docker image is a Monasca CI environment that is our solution for testing Monasca as a whole.

## Goals
The goals for our Monasca CI overlap but differ a bit from those of standard project level CI. The primary goals are:

  - Tests the integrated Monasca system not just individual components.
  - Easy Maintenance.
    - Fully automated.
    - Easy to incrementally improve. Most importantly this should apply to the tests run but also the the CI system as a whole.
    - Easy to replicate in different environments.
  - Flexible test configuration.
    - Should be easy to test various configurations, ie different components in our system, ssl or not, fully clustered, large cluster, standalone, etc.
    - Able to simultaneously run multiple environments enabling multiple test configurations and long running tests.
  - Improves team Velocity. The tool needs to improve velocity by enabling fast fail not slow the rate of change as we wait for tests.
    - CI tools that trigger long runs for minor changes then gate on these can slow down team velocity.
      An asynchronous model triggered by checkins and/or a schedule without gating rather with notification of failures
      is used for long running tests to improve velocity.
  - Execution speed.
    - Though it is expected that tests take time a fair amount of optimization work should be done.

As with most CI systems there are number of capabilities it should have including:
  - Notifies the team on any failures.
  - Includes a dashboard with status and build history.
  - Builds the code directly from any branch. Any checkin from master should build, branch checkins optionally.
  - The ability to be running multiple instances at one time so multiple configurations can be tested simultaneously.

There are few things to note that aren't goals:
  - This doesn't require reference production hardware. 
    - Our software should be exactly what is run in production but the hardware this runs on need not be.
    - Relative performance testing can be done but it shouldn't be considered the load production will run.

## Running
A Docker image with a customized Jenkins is available from the Docker registry as 'monasca/ci' the build scripts for it are
[here](https://github.com/hpcloud-mon/monasca-docker/tree/master/ci).

### Implementation Notes
- The system jobs uses a local pip cache so on the jenkins box to avoid repeated downloads.
- Most other remote packages are downloaded over http including apt in many cases. Downloads of these can be mitigated by a local caching proxy
  for example, https://github.com/jpetazzo/squid-in-a-can

## Code structure
- `jjb` - Contains the (Jenkins Job Builder)[http://docs.openstack.org/infra/jenkins-job-builder/] job definitions.
- `system` - Contains the scripts used by Jenkins to build the Monasca system. Various configurations are supported and run by different Jenkins jobs.
- `tests` - Various test scripts. Some tests using larger frameworks such as Tempest are in different git repos and pulled in by Jenkins as needed.

## Todo
- Can I watch gerrit patchsets and trigger builds based on them like I could for branches?
- There is an official docker repo for sonarqube, consider adding that to the mix.

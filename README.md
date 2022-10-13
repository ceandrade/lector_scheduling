Lector scheduler - V1.0
================================================================================

<table>
<tr>
  <td>License</td>
  <td>
    <a href="https://github.com/ceandrade/lector_scheduling/blob/master/LICENSE.md">
    <img src="https://img.shields.io/badge/license-BSD--like-blue" alt="License" />
    </a>
  </td>
</tr>
</table>

:speech_balloon: Introduction
--------------------------------------------------------------------------------

This is a simple lector scheduler for readings in a regular mass. It tries to
load balancing the lector among the readings and days so that each reading is
done by a unique lector every day, rotating the lectures between the readings,
and guaranteeing that the number of readings per lector is the closest as
possible.

We optimize the schedule following these constraints:

  1) For each day, each reading can be done for only one person;
  2) For each day, each lector does only one reading;
  3) Each lector must participate in all readings eventually.

Also, it is possible to pass blocked dates for each lector, indicating that
he/she is unavailable.

Finally, we maximize the minimum number of readings per lector. Such an
objective function pushes for a load balancing between the lectors.

Note that if we don't have enough days, Constraint 3 may be violated, and the
model will be infeasible. Therefore, for only a few days, you may need to
change the code and relax Constraint 3 or give extra "fake" days to ensure the
constraint.

:computer: Installation
--------------------------------------------------------------------------------

This is a single Python script that doesn't need installation. Just download it
and use it directly. However, you need the following dependencies:

- [Python >= 3.9](https://www.python.org);
- [docopt >= 0.6.2](http://docopt.org);
- [Google OR-Tools >= 9.4.1874](https://developers.google.com/optimization).

:zap: Usage
--------------------------------------------------------------------------------

See examples in this
[:open_file_folder: folder.](https://github.com/ceandrade/lector_scheduling/tree/master/examples)

:construction_worker: TODO
--------------------------------------------------------------------------------

- Handle dates as actual datetime objects;

- Implement some safe mechanisms like deduplication.
# Requirements: the made-up customer directory

**Made up.** The directory, its customers and its two plans are invented. No rule here is any real company's. The
directory is the small demo in `participant/tests/playwright/demo-app/server.mjs`, which runs on this computer only.

These were written for the test inventory, so that each test has a requirement to name as its source. They say what
the directory is to do, in the words of someone who uses it.

## Importance

| Word | Meaning |
|---|---|
| must | The directory cannot be used without it. If it is broken, the release is stopped |
| should | Expected by the people who use it. If it is broken, the release may go out with a date for the repair |
| could | Wanted. If it is broken, it waits its turn |

## The requirements

| ID | Importance | Requirement |
|---|---|---|
| DIR-01 | must | The page and the data interface list every customer that exists, each with its name and its plan |
| DIR-02 | must | A customer added with a name and a plan is stored with exactly that name and that plan |
| DIR-03 | must | A name already in use, capitals aside, is refused, and no second customer is stored |
| DIR-04 | must | Upgrading a customer changes that customer's plan to plus, and changes no other customer |
| DIR-05 | must | Removing a customer removes that customer, and no other |
| DIR-06 | should | A request about a customer that does not exist is answered with "not found" and changes nothing |
| DIR-07 | should | The form for adding a customer has a labelled name, a choice of the two plans, and a button |
| DIR-08 | could | Sixty customers added one after another are all stored and all listed |
| DIR-09 | could | The data interface gives the number of customers on each plan |

## Withdrawn

A requirement that was dropped keeps its number, so that a test still naming it can be found.

| ID | Withdrawn because |
|---|---|
| DIR-10 | Downgrading a customer from plus to basic. Dropped: the directory has no way to do it and none is planned |

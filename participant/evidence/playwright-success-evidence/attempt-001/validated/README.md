# Evidence captured at the validation points of one passing run

The folder is named `validated` by the quest. The name claims nothing: what each item shows, and what it does not, is in the item.

Evidence captured by one passing run of `participant/tests/playwright/meaningful-evidence.spec.ts`, against a made-up checkout on this computer.
Written by `participant/tests/playwright/tools/success-evidence-check.ts`, which empties this folder and fills it again each time it runs.

- `R1-discount.md` to `R4-charge.md`: one record for each business rule. Each says what the rule is, the value the test asserted, the value read
  from the page at that moment, what that value follows from, and where in the test it was asserted.
- `R1-discount.png` to `R4-charge.png`: a picture of the part of the page that rule is about, taken at the same moment. The record gives its checksum.
- `run-output.txt`: every step of the run in order, marked NAVIGATION, PRECONDITION or PROOF, and whether anything was captured at it. It is
  written by the test's own helper, so it is the test's word.
- `runner-output.txt`: what Playwright itself reported: each test, whether it passed, and the files attached to it.

There is one record and one picture for each rule, and no other capture. The checkout has one basket, so each item shows its rule's figure
for that basket and for no other. The run that broke each rule on purpose is `../logs/contrast-run.txt`.

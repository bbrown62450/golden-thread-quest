/*
 * The tag vocabulary for the playwright-tagging quest. This file is the one place it is written down.
 *
 * tools/tagging-check.ts reads it to check the tests, and writes participant/context/playwright/tag-scheme.md from it.
 * So the document a person reads and the rules the check applies cannot drift apart.
 *
 * A tag belongs to exactly one dimension. A test carries exactly one tag from each of the five.
 */

export type Tag = { tag: string; means: string; limitMs?: number };
export type Dimension = { key: string; name: string; question: string; rule: string; tags: Tag[] };

export const DIMENSIONS: Dimension[] = [
  {
    key: "feature",
    name: "Feature",
    question: "Which of the directory's four functions is the test about?",
    rule: "The last thing the test itself does before its assertions: add, upgrade or remove. Set-up does not count, so a test that adds a customer only to upgrade it is an upgrade test. A test that only looks is a list test, unless all it looks at is the controls of one function.",
    tags: [
      { tag: "@feature-list", means: "The test only looks at the customers that exist" },
      { tag: "@feature-add", means: "The test adds a customer, or tries to, or looks only at the form for adding one" },
      { tag: "@feature-upgrade", means: "The test changes a customer's plan to plus" },
      { tag: "@feature-remove", means: "The test removes a customer, or tries to" },
    ],
  },
  {
    key: "risk",
    name: "Risk",
    question: "What could this test catch going wrong?",
    rule: "Decided by what the test does and asserts, not by a guess at the cause. Take the first of the three that fits, from the top.",
    tags: [
      { tag: "@risk-high", means: "A change went wrong. The test sends an add, an upgrade or a remove, and then asserts which customers exist or what plan one has" },
      { tag: "@risk-medium", means: "What is there is shown or returned wrongly. The test changes nothing, and asserts which customers exist or what plan one has" },
      { tag: "@risk-low", means: "Anything else: the test asserts only controls, labels or the status of an answer" },
    ],
  },
  {
    key: "access",
    name: "Read or write",
    question: "Does running the test send the application anything but a read?",
    rule: "Counted over every request the test sends, set-up and clean-up included. The check watches the requests.",
    tags: [
      { tag: "@read", means: "Every request is a GET or a HEAD. The test changes nothing. It can still fail if someone else changes the data it reads" },
      { tag: "@write", means: "At least one request is a POST, PUT, PATCH or DELETE. Not for a shared environment" },
    ],
  },
  {
    key: "layer",
    name: "Layer",
    question: "Does the test open the page in a browser?",
    rule: "The check tells the two apart by what sent each request.",
    tags: [
      { tag: "@layer-api", means: "No browser: every request comes from the test runner's own request client" },
      { tag: "@layer-ui", means: "A browser opens the page at least once" },
    ],
  },
  {
    key: "duration",
    name: "Duration",
    question: "How long does the test take, run on its own?",
    rule: "The slowest of three runs, each alone, by the time Playwright reports for the test. The limits are written once, as numbers, and the check measures against them.",
    tags: [
      { tag: "@fast", means: "Quick enough to run on every change", limitMs: 2000 },
      { tag: "@slow", means: "Too slow for @fast. A test over this limit gets no tag: it is split or rewritten", limitMs: 10000 },
    ],
  },
];

/** Every tag of the vocabulary, with the dimension it belongs to. */
export const TAGS = new Map(DIMENSIONS.flatMap((dimension) => dimension.tags.map((tag) => [tag.tag, dimension.key] as const)));

/** Selections that used to be tags, and are now combinations of tags. */
export const SELECTIONS = [
  { name: "smoke", grep: "(?=.*@risk-high)(?=.*@fast)", means: "High risk and fast: what must hold before anything else is worth running" },
  { name: "changes nothing", grep: "@read", means: "Every test that only reads. None of the smoke tests is among them: each of those writes" },
];

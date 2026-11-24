# R4 · The confirmation says the customer was charged the total they were shown

- Result: HELD, for the one basket this test uses
- Asserted: the amount beside "Total charged" on the confirmation has exactly the text `£43.20`
- Read from the page at that moment: `£43.20`
- Given, the total shown on the checkout page, read by the test before the order: `£43.20`
- Why that value: it is the total that was on the checkout page before "Buy now" was pressed. The test read it then and compares the confirmation with it
- What this does not show: that any money was taken, or how much. The application takes none. This is what the confirmation page says, set against what the checkout page said. Nor does it show the total was the right one: that is R3
- Asserted at: `meaningful-evidence.spec.ts, line 121`, in the test "R4 · the confirmation says the customer was charged the total they were shown"
- Picture: `R4-charge.png`, of that part of the page and no more. sha256 `5702cff5e9b744bb2c4dce04af9d5a4330c02933a1745411349d984ce31b925e`
- Text inside the picture: `Total charged £43.20`
- Taken at: 2026-11-24T23:07:17.972Z, from a made-up checkout running on this computer only

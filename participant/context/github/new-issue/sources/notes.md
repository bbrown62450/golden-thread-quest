# Notes from a made-up support call, 23 November

Made-up notes. Nobody and nothing in them is real.

Caller: the finance team, during the month-end reconciliation.

The export writes dates in two different formats in the same file.
In `orders-march.csv` the column order_date is 2026-03-04 in some rows and 04/03/2026 in others.
They ran `export.py` from `v2.3.1`. No error is shown. The file is written and looks complete.
They expected every date in the file to be written the same way, as 2026-03-04.
It is a bug in the export. Robin said to assign it to robin-fixture.
It should go in Sprint 13.

Second call, the same morning: the nightly job.

Saving the March orders ran out of memory and the job was killed.
They ran `export.py` on `orders-march.csv` with `v2.3.1`. It stopped with MemoryError: cannot allocate 2147483648 bytes.
It looks as if the whole orders file is loaded into memory before anything is written.
They expected the export to finish, as it does for smaller files.
It is a bug in the export.

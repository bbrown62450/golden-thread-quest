---
title: "Out of memory when saving the March orders"
repository: "acme-fixture/tracker"
labels: ["bug", "export"]
---
Saving the March orders ran out of memory this morning and the job was killed.

I ran `export.py` on `orders-march.csv` with `v2.3.1`. After a few minutes it stopped:

```
MemoryError: cannot allocate 2147483648 bytes
```

The orders file is large this month. It looks as if the whole file is loaded into memory before anything is written.

"""People - People & Finance > Teachers & Staff: one roster, two views.

`teachers` is the teaching view (which subject in which class-section, workload,
performance) and `staff` is the employment view (employee code, lifecycle, salary).
Both read the same `Employee` row; the router is `api.py`, and each feature carries
its own prefix, so `/teachers` and `/staff` stay exactly what the frontend calls.
"""

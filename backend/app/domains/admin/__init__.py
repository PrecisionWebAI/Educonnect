"""Admin - Insights & Admin > Settings, plus the cross-school console.

`users` is the sign-in list and `settings` the school's own details; `platform`
holds the school itself (`School`) and is the only place that may look across
schools (see `tests/test_structure.py`'s tenancy allow-list).

The router is `api.py`: `auth.roles` imports `admin.users.models`, and if this
package built routes on import that model import would come back through `auth`
as a circular import - the one cycle this layout exists to prevent.
"""

"""Operations: the school's own paperwork - admission, staff hiring, fees, salary.

This package is the group's home; the router is `api.py`, so importing a model
module (`operations.admission.models`) never builds routes. Feature routers carry
their own prefixes and tags; paths stay exactly what the frontend calls.

Everything else that used to live here has its own home now: the Classroom cards
are `academic/classroom/`, notifications and the copilot are `main/`, reports are
`insights/reports/`, settings are `admin/settings/`, and the day-to-day services
(library, transport, meetings, tickets, leave) are the `services/` group.
"""


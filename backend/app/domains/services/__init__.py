"""Services - the everyday school services: library, transport, meetings, tickets, leave.

These are the screens under the frontend's **Services** group. They have no shared
parent screen (unlike Classroom), so each one is its own feature folder and the
group only mounts them:

    /library/books        /transport/routes      /meetings
    /library/issues       /transport/buses       /tickets
    /leave/applications   /leave/staff-requests

The router is `api.py` (not this file), so importing a model module never builds
routes; each feature carries its own prefix, so every path stays exactly what the
frontend already calls.
"""

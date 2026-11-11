"""Main - the front door of the product: dashboard, chat, notifications, copilot.

These are the screens every role lands on. The router is `api.py`, so importing a
model module (`main.chat.models`) never builds routes; each feature carries its own
prefix, so `/dashboard`, `/chat`, `/notifications` and `/copilot` stay exactly what
the frontend calls.
"""

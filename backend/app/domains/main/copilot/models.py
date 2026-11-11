"""The copilot's own rows: scheduled automations, prompt suggestions, palette entries.

All three are plain lists the assistant reads; keeping them as tables means the
school can tune what the assistant offers without a code change.
"""

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class CopilotAutomationBase(SQLModel):
    title: str
    schedule: str
    last_run: str
    active: bool = True


class CopilotAutomation(CopilotAutomationBase, TenantMixin, UUIDMixin, table=True):
    pass


class CopilotSuggestionBase(SQLModel):
    prompt: str
    tag: str


class CopilotSuggestion(CopilotSuggestionBase, TenantMixin, UUIDMixin, table=True):
    pass


class PaletteCommandBase(SQLModel):
    label: str
    shortcut: str
    category: str


class PaletteCommand(PaletteCommandBase, TenantMixin, UUIDMixin, table=True):
    pass

from uuid import UUID

from pydantic import BaseModel


class CopilotAutomation(BaseModel):
    id: UUID
    title: str
    schedule: str
    lastRun: str
    active: bool


class CopilotSuggestion(BaseModel):
    id: UUID
    prompt: str
    tag: str


class PaletteCommand(BaseModel):
    id: UUID
    label: str
    shortcut: str
    category: str

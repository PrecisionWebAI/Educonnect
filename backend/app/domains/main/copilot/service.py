"""Copilot reads: automations, prompt suggestions and the command palette.

`/copilot/*` used to answer with invented rows; the three tables hold them, so
these read the school's own configuration.
"""

from sqlmodel import Session, select

from .models import CopilotAutomation as CopilotAutomationModel
from .models import CopilotSuggestion as CopilotSuggestionModel
from .models import PaletteCommand as PaletteCommandModel
from .schemas import CopilotAutomation, CopilotSuggestion, PaletteCommand


def list_copilot_automations(session: Session) -> list[CopilotAutomation]:
    """The scheduled automations the assistant runs."""
    return [
        CopilotAutomation(
            id=automation.id,  # type: ignore[arg-type]
            title=automation.title,
            schedule=automation.schedule,
            lastRun=automation.last_run,
            active=automation.active,
        )
        for automation in session.exec(select(CopilotAutomationModel)).all()
    ]


def list_copilot_suggestions(session: Session) -> list[CopilotSuggestion]:
    """The prompts the assistant offers as a starting point."""
    return [
        CopilotSuggestion(
            id=suggestion.id,  # type: ignore[arg-type]
            prompt=suggestion.prompt,
            tag=suggestion.tag,
        )
        for suggestion in session.exec(select(CopilotSuggestionModel)).all()
    ]


def list_palette_commands(session: Session) -> list[PaletteCommand]:
    """The command-palette entries (Ctrl+K menu)."""
    return [
        PaletteCommand(
            id=command.id,  # type: ignore[arg-type]
            label=command.label,
            shortcut=command.shortcut,
            category=command.category,
        )
        for command in session.exec(select(PaletteCommandModel)).all()
    ]

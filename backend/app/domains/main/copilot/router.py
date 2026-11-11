from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import CopilotAutomation, CopilotSuggestion, PaletteCommand

router = APIRouter()

_can_use = RequirePermission("ai_copilot.use")


@router.get("/automations", response_model=list[CopilotAutomation])
def read_copilot_automations(
    session: Session = Depends(get_session),
    current_user=Depends(_can_use),
):
    """The scheduled automations the assistant runs."""
    return service.list_copilot_automations(session=session)


@router.get("/suggestions", response_model=list[CopilotSuggestion])
def read_copilot_suggestions(
    session: Session = Depends(get_session),
    current_user=Depends(_can_use),
):
    """The prompts the assistant offers as a starting point."""
    return service.list_copilot_suggestions(session=session)


@router.get("/commands", response_model=list[PaletteCommand])
def read_palette_commands(
    session: Session = Depends(get_session),
    current_user=Depends(_can_use),
):
    """The command-palette entries."""
    return service.list_palette_commands(session=session)

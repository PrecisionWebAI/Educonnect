"""04 - the class catalog (15 classes + sections) and each school's subjects."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlmodel import Session

from app.core.db import engine
from app.domains.academics.seed import seed_academics


def main() -> None:
    with Session(engine) as session:
        classes, sections = seed_academics(session)
    print(f"[seed] 04_academics_seed: {classes} class(es), {sections} section(s)")


if __name__ == "__main__":
    main()

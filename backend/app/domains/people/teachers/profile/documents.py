"""Where a staff document lives on disk, and how it is found again.

One module owns the disk, for the same reason `labels` owns the words: the rules
are the kind that must not be re-invented per endpoint.

* **per-school, per-person folders** - `UPLOAD_DIR/staff-docs/<school>/<employee>/`.
  A dossier folder can then be copied, archived or erased school by school, and a
  mis-scoped query cannot serve somebody else's scan across the tenant boundary.
* **an allow-list of extensions** and `UPLOAD_MAX_MB`, the hiring-resume rules.
  The upload is read into memory once to measure it, so a 400 MB "degree" is
  refused before it touches the disk.
* **the stored key is relative**, and the path is rebuilt on the way out. The
  database never holds `/app/.uploads/...`, so a moved volume is not a data
  migration, and no response can ever contain the server's layout.
* **the file is looked up by basename inside the employee's own folder**, then the
  resolved path is checked to be inside that folder. A tampered key
  (`../../etc/passwd`) resolves to nothing - the guard the exams extractor uses,
  for the same reason: a user-supplied path opened as-is is an arbitrary read.

Nothing here commits a row or raises a `403`: it either writes a file and answers
where it went, or raises the same `404` an unknown id would.
"""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

from .. import labels

#: The folder under `UPLOAD_DIR` that belongs to this feature.
FOLDER = "staff-docs"


def _root() -> Path:
    return Path(settings.UPLOAD_DIR) / FOLDER


def _folder(school_id: UUID | None, employee_id: UUID) -> Path:
    """This employee's own folder. `unscoped` only for a caller with no school
    (the platform admin acting before a school is chosen) - still a folder, so
    the read-side guard is the same code path."""
    return _root() / (str(school_id) if school_id else "unscoped") / str(employee_id)


def save(
    *, school_id: UUID | None, employee_id: UUID, file: UploadFile
) -> tuple[str, str | None, int]:
    """Write the upload, answering `(storage_key, content_type, size_bytes)`.

    The filename on disk is a fresh uuid, not the uploaded name: two people can
    file "scan.pdf", and one of them must not overwrite the other. The uploaded
    name is kept in the row (`file_name`) because that is what a download has to
    be called.
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="A document file is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in labels.DOC_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail="A document must be a PDF, Word document or image.",
        )

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=422, detail="That file is empty.")
    if len(data) > settings.UPLOAD_MAX_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Document exceeds the {settings.UPLOAD_MAX_MB} MB limit.",
        )

    folder = _folder(school_id, employee_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid4().hex}{suffix}"
    (folder / stored).write_bytes(data)

    key = "/".join([FOLDER, folder.parent.name, str(employee_id), stored])
    return key, file.content_type, len(data)


def path_of(storage_key: str, *, school_id: UUID | None, employee_id: UUID) -> Path:
    """The file behind a stored key - `404` unless it is inside the folder above.

    Only `Path(...).name` of the key is used, and the resolved candidate must sit
    directly in this employee's folder, so no key can walk out of it.
    """
    folder = _folder(school_id, employee_id).resolve()
    candidate = (folder / Path(storage_key).name).resolve()
    if folder not in candidate.parents or not candidate.is_file():
        raise HTTPException(
            status_code=404, detail="That document file is no longer on the server."
        )
    return candidate


def remove(storage_key: str, *, school_id: UUID | None, employee_id: UUID) -> bool:
    """Delete the file, answering whether it was there.

    A missing file is **not** an error on the way out: the row is the record, and
    a dossier folder restored from a backup that predates the upload must still
    let the row be deleted. The caller writes the audit line either way.
    """
    try:
        path = path_of(storage_key, school_id=school_id, employee_id=employee_id)
    except HTTPException:
        return False
    path.unlink(missing_ok=True)
    return True

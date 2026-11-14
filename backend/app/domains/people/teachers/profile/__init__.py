"""Everything the profile drawer shows about one member of staff.

The hub (`people/teachers/`) answers "who is on the roll". This sub-feature
answers "what does the school know about this one person": the degrees they hold,
where they taught before, the certificates they keep, the events that explain
their seniority - and the post itself (designation, employment type, probation,
who they report to).

Two rules keep it honest:

* **each list is its own table**, never a numbered column family. A teacher with
  four degrees is four rows, and "the second degree" is not a slot a form has to
  guess at;
* **nothing here is derived from the file system**. Documents are Phase 3
  (`staffdocument`), where the size, extension and folder rules live once.

`models.py` is registered in `app/core/schema.py`, so the tables are created with
everything else.
"""

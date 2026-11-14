"""Leave - Services > Leave & Applications: the requests, the policy, the balances.

Three tables (`models.py`) and three layers of logic:

* `service.py` - the reads: both screens' rows, the policy table, the balance
  register. A balance is **derived** (entitled - approved - pending), never stored,
  so a cancelled leave gives its days back with no reconciliation;
* `workflow.py` - the writes: apply (with the clash and balance checks), approve /
  reject / cancel (idempotent, one state each), and the school's policy;
* `scope.py` - who may decide whose request, and who may write the policy.

`student_id` on a request says which screen it belongs to; a staff request has none.
"""

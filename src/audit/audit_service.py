"""
Audit service placeholder.

Future responsibility:
- record every meaningful workflow event
- capture policy evaluation, approval, execution attempt, retry, reconciliation, and manual recovery events
- preserve actor, timestamp, entity, and structured event details
- support investigation of failed or duplicated execution attempts

Important product boundary:
Every money-impacting workflow step should be explainable after the fact.
"""
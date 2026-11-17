# Actual dispatch record
2026-11-17. Internal workers, fork_turns=none; model configuration inherited by service, no explicit model override and no pinned model version/seed.
Study root 08-goal-driven-ontology. Workers were told to read only named contract/questions/material files and their own draft, not gold, results of others, network, or agents.
For every variant:
- one pass: “Based solely on packet answer all questions/cases in contract format … One pass, no later revision … Do actual semantic reasoning, not programmatically infer labels from tests.”
- batch initial: supplied *_first.json only, asked to “Answer questions/cases with currently supplied evidence in contract format and list unresolved gaps separately in final reply.” Saved *_batch_pass1.json.
- batch followup: supplied *_second.json, told “Retain earlier material and revise answers using both batches; may reread first, questions and contract and your own draft only.” Saved *_batch.json.
- strong initial: full packet, same task, “This is a draft and later you will receive a self-review pass.” Saved *_strong_pass1.json.
- strong followup: “Review your draft against same complete [packet], questions and contract. Check logic direction, scope/version/alternatives, unknowns and citation support; revise if needed.” Saved *_strong.json.

Outputs were file writes, not simulated model calls. Separate workers were used per variant-arm cell; first and second passes reused only that cell’s worker.

Long-condition dispatches additionally instructed: “Read all packet paragraphs fully, not a truncated tool display (use bounded chunks as needed).” This delivery safeguard was applied to all long arms. Short packets fit ordinary display. Thus delivery guidance is not byte-identical across lengths; semantic task and within-length arm inputs are paired.

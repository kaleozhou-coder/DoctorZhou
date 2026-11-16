# Common output contract, frozen before extraction
Read all supplied materials and questions. Return JSON with `facts` and `decisions` arrays. No actual business actions. Every row has `id`, `answer`, `sources` (array of exact Dn.paragraph references), `reason` (short explanation), and `status`: `proposed`. One row per Q01-Q12 and C01-C16, with no duplicates or omissions. Q rows are in facts; C rows in decisions.

Use these answer vocabularies exactly (they define output syntax, not correct answers):
Q01: NECESSARY_ONLY / SUFFICIENT_ONLY / BOTH / NEITHER
Q02: SUFFICIENT / NOT_SUFFICIENT
Q03: ALL / ROUTINE_ONLY / NONE
Q04: WAIVER_AND_AUDIT / WAIVER_AND_INSPECTION / WAIVER_AND_EITHER_AUDIT_OR_INSPECTION / WAIVER_AND_BOTH_AUDIT_AND_INSPECTION / OTHER
Q05, Q08, Q09, Q10, Q11, Q12: YES / NO / UNKNOWN
Q06, Q07: DEFINED / UNKNOWN
All C rows: ALLOW / BLOCKED / UNKNOWN.

Sources must support the answer and reasoning. Cite superseding documents as well as unchanged prerequisites when needed. UNKNOWN must not be inferred as false. No external sources are needed. Do not read gold, scoring, other arms, run records, or reports. This bounded classification contract is not a claim to have generated a general executable ontology.

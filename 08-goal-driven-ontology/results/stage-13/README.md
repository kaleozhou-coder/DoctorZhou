# Stage 13 observation directory

Input/key hashes are frozen in freeze.json. Raw generation will be supplied by independent workers. No inference results are implied by engineering-tests.txt.

Run `python src/stage13_artifacts.py --output /tmp/stage13-replay-unique` from the project root to replay frozen expressions. Check schema_errors before interpreting results: absent or invalid candidates yield unknown predictions but never count as a successful run. This replay does not judge natural-language entailment or source-citation sufficiency.

layout-measurements.json contains whitespace-delimited word counts, not model token measurements. The material has 883 source words per layout, plus instructions and questions. N41 position is first/middle/last of nine blocks; rotating the same blocks also changes positions of the exception and dictionary. Batch splits at four blocks change arrival order as well. Each cell must use a fresh worker to avoid preceding layout exposure.

The separate reviewer should score Q1–Q5 semantic_ok, citation_ok, wrong_applicable_citation (Booleans), and note, plus whether model sources actually support the extracted expression. Gold required citations are a minimum conceptual source checklist, not blind lexical citation matching. Rejected comparator citations are not false applicable citations. Preserve reviewer identity masking/reveal and all initial/revised raw outputs.

# Public source and license verification

Verified 2026-11-06 UTC via official sites. These are specification examples, NOT enterprise transactions, and not a validated end-to-end business case. No customer data is used. XML source bytes are preserved. No Git commit is claimed; release-path pin plus SHA256 is used. Current unversioned sites are not reproducibility pins.

## OpenPeppol Billing

- Version selected: BIS Billing 3.0, May 2025 release / 2025-Q2. Deliberately pinned, not claimed latest.
- Official landing: https://docs.peppol.eu/poacc/billing/3.0/2025-Q2/
- Example archive: https://docs.peppol.eu/poacc/billing/3.0/2025-Q2/files/BIS-Billing3-Examples.zip (17,739 bytes at retrieval).
- Permission source: https://docs.peppol.eu/poacc/billing/3.0/2025-Q2/bis/#examples
- Appendix E explicitly says users may freely use the example files. This is an express example-use permission, NOT an inferred MIT/Apache/CC license. The BIS copyright statement belongs to OpenPeppol; underlying EN 16931 copyright belongs to CEN/members. Do not apply the Asciidoctor stylesheet's MIT license to the document.
- Three unmodified XML members selected; archive member paths and SHA256 are in manifest.json. Archive itself is not retained.

## OASIS UBL

- Release: UBL 2.1, OASIS Standard, 4 November 2013.
- Specification: https://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.html
- Official examples directory: https://docs.oasis-open.org/ubl/os-UBL-2.1/xml/
- Four exact example URLs are in manifest.json. They reside in the UBL 2.1 release but have `2.0` in their filename and declare UBLVersionID 2.0. Do not relabel them Peppol BIS 3 compliant or native UBL 2.1 examples.
- Notice terms permit copying/distribution and explanatory/implementation derivatives with notices retained; the specification itself may not be modified except stated exceptions. This is OASIS notice permission, NOT a generic open-source license. Full notices retained separately in OASIS-NOTICES.txt. Preserve them when redistributing this subset. Source bytes are unmodified; any future synthetic changes belong in a separate directory and must be labeled.
- The full 55 MB UBL release zip was not downloaded.

## Peppol Despatch / Receipt: metadata and links only

- Post-award Despatch Advice BIS 3.1, archived 2024-Q4 profile: https://docs.peppol.eu/poacc/upgrade-3/2024-Q4/profiles/30-despatchadvice/
- Archived syntax: https://docs.peppol.eu/poacc/upgrade-3/2024-Q4/syntax/DespatchAdvice/
- Logistics live landing: https://docs.peppol.eu/logistics/ (title observed: Release 1.3.1 Hotfix; individual transaction versions differ).
- Receipt Advice profile: https://docs.peppol.eu/logistics/profiles/67-advanceddespatchadvice_w_receiptadvice/ (profile 1.1 at landing).
- Official example archive link: https://docs.peppol.eu/logistics/files/Examples.zip
- Copyright notice in this BIS says the BIS document may not be modified, redistributed, sold or repackaged without prior consent. We have NOT established an explicit redistribution license for the logistics XML example archive, so it was NOT downloaded or vendored. Public access is not a permissive license. Use links and original analysis for now, or clarify the example license before adding it.
- Live page titles/version numbers are not immutable release identifiers. Do not silently treat this as a pinned experiment corpus.

## Business limits

Invoice content is a supplier claim; it is not proof of delivery, inspection, acceptance, payment approval or payment. Despatch/shipping is not acceptance. A receiving-advice reference is a pointer, not the referenced document or its verified conclusion. Absence of evidence in this corpus is not evidence that the event never occurred in the business.

The Logistics Receipt Advice profile distinguishes document-receipt/validation (type D, AB/AP/RE) from goods/service-receipt response (type S), and allows later reports of shortage/quality issues after unpacking. Even a receipt without claims is not automatically final contractual acceptance or authorization to pay.

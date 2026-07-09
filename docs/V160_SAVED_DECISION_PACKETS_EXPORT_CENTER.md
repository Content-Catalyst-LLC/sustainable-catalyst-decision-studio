# Decision Studio v1.7.0 — Saved Decision Packets and Export Center

Decision Studio v1.7.0 adds a persistence and export layer around the Decision Packet workflow.

## Added

- Saved Decision Packet structure.
- Browser/local save and reload controls in the public UI.
- Export Center tab inside Decision Studio.
- Export bundle generation for complete review packets.
- Backend export-center endpoints.
- WordPress REST endpoints for packet storage templates, export bundles, and admin packet storage.
- Admin Export Center upgrade for saved packets and export bundle documentation.

## Export bundle contents

- Decision Packet JSON.
- Inputs JSON.
- Results JSON.
- Integrated Brief JSON.
- Integrated Brief Markdown.
- Integrated Brief HTML.
- Audit and Provenance JSON.
- Readiness JSON.
- Scenario Comparison JSON.
- Workbench Handoff JSON.

## Boundaries

Saved packets and export bundles are working review records. They are not approvals, certifications, assurance reports, or professional advice. Review sensitive information before sharing exported files.

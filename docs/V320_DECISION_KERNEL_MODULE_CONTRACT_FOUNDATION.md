# Decision Studio v3.2.0 — Decision Kernel & Module Contract Foundation

## Purpose
Define one shared Decision Studio kernel and formal module contracts before persistence authority moves to PostgreSQL.

## Shared kernel
The kernel owns decision identity/lifecycle plus alternatives, criteria, evidence references, assumptions, scenarios, recommendations, review/challenge, outcomes, artifact references, and provenance references.

## First-class modules
- Canvas — general decision architecture.
- Finance — financial/economic decision context; Workbench remains compute authority.
- Narrative Risk — qualitative, narrative, reputational, and emerging-risk context.
- Global Impact Catalyst — sustainability, SDG, environmental, social, economic, carbon, resource, geographic, and distributional impact context.

## Architectural boundaries
Modules extend shared kernel objects rather than forking identity. Model/AI output never becomes final decision authority. The final decision authority remains human-governed. v3.2.0 performs no database migration and does not change WordPress persistence authority.

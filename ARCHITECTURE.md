# TowerOps architecture

```mermaid
flowchart LR
    A[Synthetic aircraft/world state] --> B[Conflict prediction]
    B --> C[Strands agent advisory boundary]
    C --> D[Deterministic safety + freshness gate]
    D --> E[Human approval fixture / authority boundary]
    E --> F[Acknowledgement binding]
    F --> G[Simulated state transition]
    G --> H[Hash-chained audit + replay]
    H --> A
```

The agent may propose an advisory, but the deterministic gate decides whether the proposal is admissible. The published demo uses only synthetic state and fixture approvals/acknowledgements.

**Scope:** research simulation only. No live surveillance feed, real clearance issuance, aircraft integration, operational separation assurance, or aviation certification.

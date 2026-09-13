# Deploy Decision Studio backend v2.8.0

Run the Mac wrapper after GitHub and WordPress have been updated:

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v2_8_0_from_macos.sh
./deploy_decision_studio_v2_8_0_from_macos.sh
```

The guarded upgrader backs up `/opt/sustainable-catalyst/decision-studio`, preserves backend environment files, deploys image `sustainable-catalyst-decision-studio:2.8.0`, and verifies:

- internal/public health identity;
- Decision Dependency Graph contracts;
- explicit and structural dependency mapping;
- non-causal edge semantics;
- change-impact review queue without automatic invalidation;
- graph fingerprint tamper rejection;
- Decision Object / Decision Packet attachment;
- v2.7 Site Intelligence context preservation;
- v2.6 native Lab/Workbench handoffs;
- v2.5 Scenario/Stress contracts;
- Energy Runtime Consumer v2.3.0.

Expected public identity:

- version `2.8.0`
- build fingerprint `scds-v2.8.0-decision-graph-dependency-mapping`
- source commit `release-v2.8.0`

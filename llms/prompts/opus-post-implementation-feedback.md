# Post-Implementation: Feedback Setup

After hardening is complete, establish the observation 
framework for the next cycle.

### 1. Deferred Items

Identify and categorize:

- **Technical debt**: Known shortcuts, TODOs, suboptimal 
  implementations chosen for expediency.
  For each: severity (acceptable | degrading | blocking), 
  trigger condition for revisiting.

- **Open questions**: Design decisions deferred due to 
  insufficient information.
  For each: what observation or data would resolve it.

### 2. Decay Triggers

Document conditions under which the current implementation 
becomes inappropriate:
- Scale thresholds (data volume, user count, request rate)
- Structural shifts (new requirements that break current abstractions)
- Dependency changes (upstream API changes, library deprecations)

For each: the symptom you'd observe, and the response.

### 3. Success Criteria

Define what "working" means beyond "not broken":
- What behavior confirms the design is correct?
- What usage pattern indicates it's achieving its purpose?
- What absence of signal is concerning vs. expected?

### 4. Metrics and Instrumentation

For each metric, specify:
- What to measure
- The decision it informs: "If X, then I would Y"
- How to measure it (log line, counter, manual observation)
- Review cadence (on every use | weekly | on next revisit)

Only include metrics tied to decisions. No vanity measurements.

### 5. Predicted Friction

Based on implementation experience, identify:
- Where will the next user (or future you) get confused?
- What error messages are unhelpful?
- What workflows are clunky but were out of scope to fix?
- What documentation gaps remain?

For each: expected symptom, and whether to address now 
(if trivial) or track for later.

### Output

Collect into a single tracking document or file 
(e.g., FEEDBACK.md, .dev/tracking.md) with sections 
matching the above. This becomes the input artifact 
for the next design phase.

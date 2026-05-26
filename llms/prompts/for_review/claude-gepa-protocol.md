# GEPA (Genetic-Pareto) Optimization Protocol
A prompt optimizer that uses natural language reflection to learn from trial and error. GEPA samples system trajectories (reasoning, tool calls, outputs), diagnoses problems, proposes updates, and combines successful approaches from multiple attempts.
## APPLICATION TEMPLATE
**Target System**: Generalize the prompt to be able to handle any user background, and any topic they want to learn.
**Current Prompt/Text**: 
[insert here]

**Optimization Goals**: [e.g., clarity, token efficiency, robustness, specific capabilities]
---
## GEPA PROCESS
### 1. SAMPLE & DIAGNOSE
Analyze the current prompt by simulating its use:
- What problems would this create in practice?
- Where is it unclear, redundant, or contradictory?
- What's missing or excessive?
- How does it perform across different scenarios?
### 2. REFLECT & PROPOSE
Generate natural language insights:
- Root causes of identified problems
- High-level principles for improvement
- Specific updates to test
- Trade-offs to consider
### 3. ITERATE & COMBINE
Create optimized variant(s):
- Apply proposed improvements
- Preserve what works well
- Combine complementary strengths
- Test against edge cases
### 4. VERIFY
Compare old vs new:
- Measure token efficiency
- Check clarity and usability
- Validate completeness
- Document improvements
---
**Expected Output**: Optimized version with explanation of key improvements and rationale.

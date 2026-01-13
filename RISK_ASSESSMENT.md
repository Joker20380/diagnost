# ⚖️ AI RISK ASSESSMENT — AI-Diagnostics

## 1. Purpose of this Document

This document provides a structured assessment of risks associated with the
use of Artificial Intelligence in the **AI-Diagnostics** system and describes
the mitigation measures implemented by design.

It supports:
- internal governance;
- partner due diligence;
- regulatory transparency under the EU AI Act.

---

## 2. System Context

AI-Diagnostics is a **Decision-Support System** used in automotive diagnostics.
The system provides **recommendations and explanatory insights**, while all
decisions remain under **human control**.

The system:
- does not control vehicles;
- does not execute actions;
- does not make autonomous decisions.

---

## 3. Risk Classification Summary

| Risk Category              | Risk Level | Notes |
|---------------------------|------------|-------|
| Autonomous decision risk  | Low        | No autonomous actions |
| Over-reliance by users    | Medium     | Mitigated by UX + policy |
| Misinterpretation risk    | Medium     | Mitigated by explainability |
| Safety-critical control   | None       | Not applicable |
| Manipulative behavior     | None       | Explicitly excluded |
| Data hallucination (LLM)  | Medium     | Mitigated by scope limits |

---

## 4. Identified Risks and Mitigations

### 4.1 Risk: Over-reliance on System Recommendations

**Description**  
Users may interpret recommendations as mandatory decisions.

**Mitigation Measures**
- All outputs are explicitly labeled as *recommendations*.
- No automatic actions are triggered by the system.
- Critical decisions require manual confirmation.
- Documentation clearly states decision responsibility.

**Residual Risk**  
Low to Medium (human factors dependent).

---

### 4.2 Risk: Implicit Automation Bias

**Description**  
Users may trust system outputs over their own judgment.

**Mitigation Measures**
- Human-in-the-Loop architecture enforced in backend logic.
- UI elements do not auto-select repair decisions.
- Conflicts between recommendations and user choices are allowed.
- System avoids authoritative language.

**Residual Risk**  
Low.

---

### 4.3 Risk: Incorrect Recommendations Due to Threshold Logic

**Description**  
Rule-based thresholds (e.g., wear percentages) may not reflect real-world context.

**Mitigation Measures**
- Thresholds are treated as advisory indicators.
- Recommendations do not enforce outcomes.
- Specialist may override any recommendation.
- Conflicts are logged via QA mechanisms for review.

**Residual Risk**  
Low.

---

### 4.4 Risk: Lack of Explainability (“Black Box” Risk)

**Description**  
Users may not understand why a recommendation was generated.

**Mitigation Measures**
- Recommendations are derived from explicit rules.
- Factors influencing recommendations are visible.
- No opaque or self-learning decision logic is used.
- Language model outputs are explanatory, not prescriptive.

**Residual Risk**  
Low.

---

### 4.5 Risk: Misuse of Language Models (LLMs)

**Description**  
LLMs may produce inaccurate or misleading text.

**Mitigation Measures**
- LLMs operate only on provided data.
- No direct access to vehicle state or sensors.
- Outputs are non-binding and informational.
- LLMs are not used for decision authorization.

**Residual Risk**  
Medium (controlled by scope limitation).

---

### 4.6 Risk: Safety-Critical Misuse

**Description**  
System could be interpreted as a safety certification tool.

**Mitigation Measures**
- System is explicitly not certified.
- Not a substitute for manufacturer diagnostics.
- Safety disclaimers are present in documentation and UI.
- Final responsibility remains with the user.

**Residual Risk**  
Low.

---

## 5. QA and Monitoring

AI-Diagnostics implements **soft Quality Assurance mechanisms**:

- Conflicts between system recommendations and human decisions
  are logged as QA events.
- QA events do not affect system behavior.
- Logs are used for:
  - internal review;
  - threshold calibration;
  - diagnostic quality analysis.

---

## 6. High-Risk AI Determination (EU AI Act)

Based on Article 6 of the EU AI Act:

AI-Diagnostics:
- does not perform biometric identification;
- does not control critical infrastructure;
- does not autonomously decide safety outcomes;
- does not operate in regulated high-risk domains.

**Conclusion**  
AI-Diagnostics is **not classified as High-Risk AI**.

---

## 7. Continuous Risk Review

Risk assessment is:
- revisited periodically;
- updated with system evolution;
- aligned with regulatory updates.

---

## 8. Final Assessment

AI-Diagnostics maintains a **controlled risk profile** by design.

The system:
- supports decision-making;
- enforces human oversight;
- avoids autonomous behavior;
- prioritizes transparency and accountability.

> **AI-Diagnostics reduces uncertainty — it does not replace responsibility.**

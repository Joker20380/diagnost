# 🇪🇺 EU AI ACT — SELF-ASSESSMENT
## AI-Diagnostics

## 1. Purpose of this Assessment

This document provides a self-assessment of **AI-Diagnostics**
with regard to the **EU Artificial Intelligence Act (EU AI Act)**.

It aims to:
- classify the system correctly;
- identify applicable obligations;
- demonstrate compliance by design.

---

## 2. System Overview

**System name:** AI-Diagnostics  
**Domain:** Automotive diagnostics  
**Function:** Decision-support and explanatory assistance  
**Deployment context:** Professional use by specialists

AI-Diagnostics provides **recommendations and explanations**
based on diagnostic data.  
It does **not** make autonomous decisions and does **not** execute actions.

---

## 3. AI System Classification

According to Article 3 of the EU AI Act, AI-Diagnostics qualifies as:

> **Decision-Support System (DSS)**  
> **Human-in-the-Loop, Non-Autonomous**

The system is **not**:
- an autonomous AI agent;
- a safety-critical control system;
- a real-time operational decision-maker.

---

## 4. High-Risk AI Determination (Article 6)

AI-Diagnostics was assessed against the criteria for **High-Risk AI**.

### 4.1 High-Risk Use Cases (Annex III)

| Annex III Category | Applicable | Reason |
|--------------------|------------|--------|
| Biometric identification | ❌ No | No biometric processing |
| Critical infrastructure | ❌ No | No infrastructure control |
| Education & training | ❌ No | Not applicable |
| Employment & HR | ❌ No | Not applicable |
| Law enforcement | ❌ No | Not applicable |
| Migration & border control | ❌ No | Not applicable |
| Administration of justice | ❌ No | Not applicable |

### 4.2 Safety Component Assessment

AI-Diagnostics:
- does not control vehicles;
- does not activate mechanical systems;
- does not certify safety or roadworthiness.

**Conclusion:**  
AI-Diagnostics is **not classified as High-Risk AI** under Article 6.

---

## 5. Transparency Obligations

AI-Diagnostics complies with transparency principles by design:

- system outputs are clearly labeled as *recommendations*;
- users are informed that AI assistance is being used;
- decision authority remains with the human specialist;
- system logic avoids opaque or self-learning enforcement.

---

## 6. Human Oversight (Article 14)

Human oversight is implemented through:

- mandatory Human-in-the-Loop architecture;
- no automatic execution of actions;
- no auto-selection of repair decisions;
- explicit user confirmation for finalization (signing);
- backend enforcement preventing override of user choices.

Oversight is:
- continuous;
- non-bypassable;
- enforced at both UI and backend levels.

---

## 7. Risk Management and Mitigation

Key risks identified:
- over-reliance on recommendations;
- misinterpretation of advisory outputs;
- contextual limitations of AI models.

Mitigation measures include:
- non-authoritative language;
- explainable, rule-based recommendations;
- QA logging of conflicts without enforcement;
- explicit responsibility disclaimers.

---

## 8. Use of Language Models (LLMs)

If language models are used:
- they operate only on provided data;
- they do not access vehicles or sensors;
- they generate non-binding explanatory text;
- outputs require human validation.

LLMs are not used for:
- decision authorization;
- safety certification;
- autonomous reasoning.

---

## 9. Prohibited AI Practices (Article 5)

AI-Diagnostics does **not**:
- manipulate user behavior;
- exploit vulnerabilities;
- apply subliminal techniques;
- deceive users about system authority.

No prohibited practices under Article 5 are present.

---

## 10. Final Classification and Statement

Based on this assessment:

- AI-Diagnostics is a **Decision-Support Tool**;
- it is **not High-Risk AI**;
- it complies with the core principles of the EU AI Act:
  - transparency;
  - human oversight;
  - limitation of scope;
  - accountability.

> **AI-Diagnostics reduces uncertainty.  
> Responsibility remains human.**

---

## 11. Review and Versioning

This self-assessment:
- is reviewed periodically;
- is updated alongside system evolution;
- is versioned in the repository.

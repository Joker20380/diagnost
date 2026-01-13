# 🛡 AI POLICY — AI-Diagnostics

## 1. Purpose of this Document

This document defines the **policy, boundaries, and governance principles**
for the use of Artificial Intelligence within the **AI-Diagnostics** system.

It serves as:
- an internal governance document;
- a public declaration of system boundaries;
- a compliance-oriented reference for partners, auditors, and regulators.

This policy is aligned with the principles of the **EU AI Act** and
international best practices for **Decision-Support Systems**.

---

## 2. System Classification

AI-Diagnostics is classified as a:

> **Decision-Support System (DSS)**  
> **Non-autonomous, Human-in-the-Loop**

The system does **not** qualify as:
- an autonomous AI agent;
- a safety-critical control system;
- a real-time decision-making engine.

---

## 3. Core Principles

### 3.1 Human-in-the-Loop (Mandatory)

- All system outputs are **recommendations**, not decisions.
- A human specialist always:
  - reviews outputs;
  - interprets context;
  - makes final decisions.
- The system cannot execute actions independently.

---

### 3.2 No Autonomous Decisions

AI-Diagnostics:
- does not automatically authorize repairs;
- does not enforce technical actions;
- does not override human judgment;
- does not block alternative interpretations.

Any interface element suggesting a decision is:
- explicitly marked as a *recommendation*;
- reversible;
- user-confirmed.

---

### 3.3 Explainability by Design

The system avoids “black-box decisions”.

Each recommendation is:
- derived from observable inputs (e.g., wear thresholds);
- explainable through explicit rules or logic;
- traceable to its source data.

---

## 4. Scope of AI Usage

Artificial Intelligence within AI-Diagnostics may be used for:

- structuring diagnostic data;
- highlighting correlations and patterns;
- generating explanatory text;
- assisting navigation through technical information.

AI is **not** used for:
- direct mechanical control;
- safety-critical decisions;
- automated authorization of actions.

---

## 5. Role of Language Models (LLMs)

When Language Models are used:

- they operate on **provided textual data only**;
- they have no direct access to vehicles or sensors;
- they do not possess real-world context;
- they are treated as interpretive tools.

LLM outputs are always:
- advisory;
- non-binding;
- subject to human validation.

---

## 6. Quality Assurance and Conflict Handling

AI-Diagnostics implements **soft QA mechanisms**:

- If system recommendations conflict with human decisions,
  the conflict may be logged for analysis.
- No automatic correction or enforcement occurs.
- QA logs are used for:
  - system improvement;
  - threshold calibration;
  - diagnostic quality analytics.

---

## 7. Responsibility and Liability

AI-Diagnostics does **not** assume responsibility for:
- diagnostic outcomes;
- repair decisions;
- vehicle safety;
- regulatory compliance of the vehicle.

Responsibility remains with:
- the professional using the system;
- the organization deploying it.

---

## 8. Regulatory Alignment (EU AI Act)

AI-Diagnostics is designed to comply with:
- transparency requirements;
- human oversight requirements;
- limitation of scope;
- avoidance of manipulative practices.

The system is **not classified as high-risk AI**
under Article 6 of the EU AI Act.

---

## 9. Continuous Review

This policy is:
- reviewed periodically;
- updated alongside system evolution;
- versioned within the repository.

---

## 10. Final Statement

AI-Diagnostics is built on one fundamental rule:

> **AI supports thinking.  
> Humans make decisions.**

Any deviation from this principle is considered a system defect,
not a feature.

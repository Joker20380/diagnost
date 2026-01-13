# 🧑‍🔧 HUMAN OVERSIGHT — AI-Diagnostics

## 1. Purpose

This document defines how **human oversight** is implemented in AI-Diagnostics.

Goal:
- ensure that AI-Diagnostics remains a **Decision-Support System**;
- prevent autonomous decision-making;
- guarantee that all critical actions require **human confirmation**.

---

## 2. Oversight Model

AI-Diagnostics follows a mandatory:

> **Human-in-the-Loop (HITL)** oversight model

Meaning:
- the system can generate recommendations;
- the human specialist validates and decides;
- no action is executed automatically.

---

## 3. Roles and Responsibilities

### 3.1 User / Specialist
Responsible for:
- interpreting diagnostic data;
- making repair / эксплуатационные decisions;
- confirming any final conclusions.

### 3.2 System (AI-Diagnostics)
Responsible for:
- aggregating and structuring data;
- generating explainable recommendations;
- surfacing QA signals for review.

The system is **not responsible** for:
- safety certification;
- repair authorization;
- decision enforcement.

---

## 4. Oversight Mechanisms in the Product

### 4.1 Recommendations Are Non-Binding
- Recommendations are displayed as advisory hints (e.g., "Recommended: replace").
- They never automatically trigger:
  - repair approval;
  - cost estimation commitments;
  - work orders.

### 4.2 No Auto-Selection of Repair Decisions
- UI controls that represent final decisions (e.g., “Needs replacement?”) are:
  - manually selected by the specialist;
  - never auto-checked by the system.

This prevents automation bias and preserves accountability.

### 4.3 Explicit Human Confirmation for Completion
When inspection results are finalized:
- the user explicitly triggers signing / confirmation actions;
- once signed, editing is blocked to preserve integrity.

### 4.4 Backend Enforcement of Human Authority
Human oversight is enforced not only in UI, but in backend logic:
- system-generated recommendations do not overwrite user choices;
- backend stores user decisions as authoritative.

---

## 5. QA Oversight (Non-Blocking)

### 5.1 Conflict Logging
If system recommendations conflict with user decisions:
- the conflict is logged as a QA event;
- the system does not enforce changes.

Example:
- wear ≥ threshold triggers “recommend replace”
- user chooses “no replacement”
- system logs QA mismatch for review.

### 5.2 Purpose of QA
QA events are used for:
- calibration of thresholds and rules;
- identifying ambiguous cases;
- improving explainability and UX.

QA events are **not** used to:
- penalize users;
- override specialist decisions.

---

## 6. Transparency and User Control

AI-Diagnostics ensures:
- user control over final outputs;
- traceability of recommendations;
- non-authoritative language in system outputs.

The specialist can always:
- override recommendations;
- interpret context not visible to the system;
- choose alternative actions.

---

## 7. Integrity Controls

When inspections are finalized (signed):
- editing is blocked;
- the signed state indicates completion and accountability;
- auditability is improved.

---

## 8. Summary Statement

AI-Diagnostics is designed so that:

- the system **cannot** execute decisions;
- the system **cannot** enforce repairs;
- the system **cannot** replace professional responsibility.

> **AI supports thinking. Humans make decisions.**

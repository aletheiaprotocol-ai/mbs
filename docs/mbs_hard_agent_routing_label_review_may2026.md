# Hard Agent Routing Label Review — May 2026

This note documents the expected-label methodology for
`examples/hard_agent_routing/cases.jsonl`. It exists to keep MBS benchmark
claims evidence-safe: a low semantic score is useful only if the labels are
reviewable and policy precedence is explicit.

## Policy Precedence

When a customer message contains multiple intents, expected labels follow this
priority order:

1. Active credential compromise, account takeover, token leakage, unknown access,
   tenant data exposure, or payment-destination anomaly → `ESCALATE_SECURITY`,
   usually `CRITICAL`, human required, not customer-visible by default.
2. Legal/privacy/regulatory threats without immediate compromise →
   `CREATE_TICKET`, usually `HIGH`, human required.
3. Refund/billing reversal requests without security or legal escalation →
   `REFUND_REQUEST`.
4. Account lookup/invoice explanation without requested change →
   `SEARCH_ACCOUNT`.
5. Explicit close/no-reply/no-change messages with no active risk → `NO_ACTION`.

Security overrides refund and lookup. Legal/privacy workflow usually overrides
simple refund because it requires human/policy review. No-action applies only
when no unresolved risk remains.

## Cases Worth Reviewer Attention

The following labels are intentionally debatable or policy-sensitive. They are
kept because hard cases must be able to fail, but claims should acknowledge that
these are benchmark-policy labels, not universal support policy.

| case | current expected action | rationale | review note |
| --- | --- | --- | --- |
| `hard_006` | `CREATE_TICKET` | Vague account unease without concrete compromise. | Could become `ESCALATE_SECURITY` under a very conservative security policy. |
| `hard_008` | `CREATE_TICKET` | Data access request needs privacy/support workflow. | Not `SEARCH_ACCOUNT`; it requests a data export workflow. |
| `hard_012` | `CREATE_TICKET` | Refund plus deletion plus unauthorized child purchase needs policy review. | Refund is present but not the only or safest route. |
| `hard_023` | `CREATE_TICKET` | Multiple legal/security/billing keywords without details; gather facts and route to human. | Could become security escalation if stolen-card claim is treated as sufficient. |
| `hard_029` | `CREATE_TICKET` | User asks for account-history review with ambiguous travel context. | Could be `SEARCH_ACCOUNT` if history lookup is considered read-only. |
| `hard_034` | `CREATE_TICKET` | Former-employer account merge requires human authorization review. | Security-adjacent but no active compromise alleged. |
| `hard_036` | `CREATE_TICKET` | Password reset email concern without click/access loss; needs human advice. | Could be security escalation under strict phishing policy. |
| `hard_040` | `NO_ACTION` | User cancels deletion and refund requests and asks to keep account active. | Assumes prior request can be closed without additional workflow. |

## Methodology Rules

- Report semantic correctness as correctness against this documented policy, not
  as universal truth.
- Do not treat schema-valid outputs as behavior success unless all expected
  semantic fields match.
- Preserve infra failures separately from model behavior.
- Re-run label review before making external claims, especially for security,
  privacy, and legal cases.
- Prefer adding policy notes over silently changing labels after observing model
  failures.
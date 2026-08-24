# MCE Agent Skills (source of truth)

Jason's MCE agent skills currently live in Claude's synced skills area (uploaded via
claude.ai), not in git — which means there's no version history, no review, and no
backup of them. Skills committed here are the versioned copies.

## What's here

| Skill | Purpose |
|---|---|
| `rep-network-builder/` | Maps CPM's/Bliss's existing sales representatives nationally and internationally, identifies which ones lost their parts business when CPM consolidated aftermarket parts into Jacobs Global, and produces a prioritized rep-recruitment register. Research and drafting only — never contacts a rep. |

## Installing a skill

Upload the skill folder (`SKILL.md` plus its `references/` directory) through
claude.ai → Settings → Capabilities → Skills. Keep the folder structure intact —
`SKILL.md` refers to files in `references/` by relative path.

## One manual step after installing `rep-network-builder`

The `mce-leadership-team` router skill lists every agent on the team, and it doesn't
know about this one yet. Add this entry to its "The team" section so generic requests
("who handles finding reps?") route correctly:

> **Rep Network Builder** (`rep-network-builder`) — Builds the independent
> sales-representative channel for parts: maps CPM/Bliss reps nationally and
> internationally, identifies reps who lost their parts business to the Jacobs Global
> consolidation, qualifies and ranks them, and drafts the approach. Trigger: "who are
> CPM's reps," "build a rep network," "find representatives," "territory coverage,"
> "international reps." Researches and drafts only — never contacts a rep, never sets
> commission or territory terms. Distinct from Parts Growth Agent: that skill targets
> **mills** directly, this one targets **the reps who already sell to those mills**.

While editing the router, note that its "Not yet built" section is now out of date —
it says the Engineering Manager agent doesn't exist, but `engineering-manager` and
`senior-engineer` are both installed.

## Stale references to fix in the installed skills

**Ron Dominguez no longer works for MCE (as of Aug 2026), and two installed skills
still treat him as active staff:**

- `parts-growth-agent` names him in the daily calling roster ("Paula, Ron Dominguez,
  Magda, and Jason") in both its description and its "calling team" section, and
  points at the Salesperson Scorecard tab where all four are listed. It will keep
  producing call lists assigned to someone who has left.
- `mce-leadership-team` repeats the same roster in its Parts Growth Agent entry.

Both need Ron removed and the remaining callers' capacity re-planned — three people,
not four, with Jason's share still temporary until the next sales hire. The Midwest OS
`Salesperson Scorecard` tab needs the same correction, or the activity targets will
silently under-report against a roster that no longer exists.

Separately, Ron owned the rep agreement and its exhibits. `rep-network-builder` flags
that as unowned rather than reassigning it — see its "Still genuinely open" section.

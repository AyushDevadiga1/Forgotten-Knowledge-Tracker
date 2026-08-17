## 1. Encode the policy in project rules

- [x] 1.1 Broaden the AGENTS.v2.md rule from behavior-changing fixes to every modification

## 2. Broaden the audit pipeline to require an OpenSpec change for every confirmed fix

- [x] 2.1 audit-orchestrator.md: change gate 7 and workflow step I to require an OpenSpec change for every confirmed fix
- [x] 2.2 patch-engineer.md: create an OpenSpec change before every fix
- [x] 2.3 audit-patch/SKILL.md: capture every fix in an OpenSpec change before editing
- [x] 2.4 /audit command: require an OpenSpec change for every confirmed fix

## 3. Seed the workflow

- [x] 3.1 Create the OpenSpec change for this policy change (done via openspec CLI)
- [x] 3.2 Commit the policy change together with its OpenSpec change
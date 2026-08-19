# Migration Map — command-engine

**Installed:** 2026-08-19
**Mode:** migrate
**Profile:** platform

## Existing structure preserved

All existing root directories and files declared in REPO.yaml.

## Special handling

- Active MO§ES runtime — preserve relationship to MOS2ES / moses-governance lineage
- Supersedes MOS2ES, moses-governance, Command

## Canon context

- Authority role: implementation
- Canon contexts: moses
- Authority owner: search_authority
- Note: active MO§ES runtime, supersedes MOS2ES/moses-governance/Command

## Migration steps (before enforce)

1. [ ] Run `repo_check.py --ci` until clean
2. [ ] Verify GitHub ruleset application (solo-fast)
3. [ ] Switch REPO.yaml mode from `migrate` → `enforce`

## Enforce readiness

See repo_check output for current state.

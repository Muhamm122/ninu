# User-Provided Skill Zip — Comparison Protocol

When a user sends a zip file containing skills they built, follow this protocol before installing.

## Protocol

1. **Extract** to `/tmp/user-skill-name/`
2. **Compare** against existing installed skill with the same name:
   ```bash
   diff -rq /tmp/user-skill-name/skill-name/ ~/.hermes/skills/superagent/skill-name/
   ```
3. **Analyze differences**:
   - If installed version is **more complete** (more files, more recent features): inform user, do NOT overwrite
   - If user version has **new content** not in installed: merge the new files
   - If versions are **identical**: inform user, no action needed
4. **Report** findings to user before making any changes

## Key Principle

Never blindly overwrite an installed skill with a user-provided zip. Always compare first. The installed version may have been updated with more features (e.g., SUPERAGENT v4.0 hermes-crypto-agent has MEV protection, governor, browser automation that older versions lack).

## Example from Session

User sent `hermes-crypto-agent.zip`. Comparison showed:
- Installed version (from SUPERAGENT v4.0): 15 references + 15 scripts + DISPATCH.md
- User zip version: 9 references + 9 scripts, no DISPATCH.md, no governor/mev/browser files
- Decision: Keep installed version, inform user it's already more complete

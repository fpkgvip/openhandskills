# Pack design research and provenance
Checked 2026-10-25. The bundle's skills/helper implementations are original. No OpenHands public skill bodies or other third-party code are redistributed.

## OpenHands compatibility
1. https://docs.openhands.dev/overview/skills
   Recommended `.agents/skills/<name>/SKILL.md`; names/descriptions first, body on invocation; legacy paths supported. Skills do not themselves grant tools/permissions.
2. https://docs.openhands.dev/overview/plugins
   `.plugin/plugin.json` and compatible `.claude-plugin` metadata; plugin `skills/` directories; GitHub and local-source loading.
3. https://docs.openhands.dev/sdk/guides/skill
   Progressive disclosure and unique names; avoid large always-loaded legacy context; script/resource paths resolved from skill location.
4. https://docs.openhands.dev/overview/skills/creating
   AgentSkills frontmatter, focused workflows, references and deterministic scripts.
5. https://docs.openhands.dev/overview/skills/adding
   Per-skill GitHub import and filesystem alternatives.
6. https://docs.openhands.dev/cookbook/upload-skills
   User skills can be seeded before a new conversation; running conversations may not rescan; fresh sandboxes do not inherit arbitrary old files.
7. https://docs.openhands.dev/cookbook/per-conversation-secrets
   Conversation secrets can be exposed as named shell environment variables; plugin MCP substitution timing differs. No platform secret-store API integration is assumed by this kit.
8. https://docs.openhands.dev/enterprise/skills-and-plugins
   Git repository marketplace import in settings; availability/UI depends on deployment.

## Built-in/registry inspection
- https://github.com/OpenHands/extensions
- https://github.com/OpenHands/extensions/blob/main/marketplaces/openhands-extensions.json
- https://github.com/OpenHands/extensions/blob/main/skills/code-review/.plugin/plugin.json
- https://github.com/OpenHands/extensions/blob/main/skills/evidence-based-citations/SKILL.md
- https://github.com/OpenHands/extensions/blob/main/skills/research-brief/SKILL.md

Read via authenticated GitHub read tools where public HTML retrieval failed. Observed marketplace uses `name`, `owner`, `metadata`, and `plugins` with local `source` paths; built-in registry has a `.plugin/marketplace.json` symlink. This pack uses real mirrored files, not symlinks, for ZIP portability. The existing `research-brief` uses Tavily+Notion and is not a fit for Brave-only access. Generic citation formatting should not erase practitioner evidence.

## Brave
- https://api-dashboard.search.brave.com/api-reference/web/search/get
- https://api-dashboard.search.brave.com/documentation/guides/rate-limiting

Verified fixed GET endpoint, subscription-token header, q/count/offset/freshness/extra-snippet parameters and rate/quota response headers. No live key was supplied or used while creating this kit. Account pricing/access is not inferred from general documentation.

## Evidence limits
Static structures were checked against current docs and inspected examples. Offline mocks do not prove a deployed OpenHands UI imports the package, nor that a particular secret is exposed. Runtime registration, UI labels, registry contents and provider quotas can change.

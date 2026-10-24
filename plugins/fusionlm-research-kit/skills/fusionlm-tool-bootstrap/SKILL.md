---
name: fusionlm-tool-bootstrap
description: "Use to autonomously choose, install, test and replace research tools or optional MCP servers in the disposable Linux sandbox."
license: MIT
compatibility: "OpenHands with terminal and file tools; Python 3.10+ for bundled helpers"
metadata:
  version: "1.0.0"
---

# Tool autonomy without an installation maze

Inspect available host terminal/file/browser tools and loaded skills before installing duplicates. Public-registry availability does not mean a skill is loaded or authenticated. See `references/BUILTINS_AND_MCP.md`.

Within an authorised research task, ordinary free research-tool installation inside the disposable workspace is a routine decision, not a reason to ask William for permission.

1. Check OS, interpreter/tool versions, disk/RAM, writable paths, network and built-in capabilities. Record names/versions, never secret values or an environment dump.
2. Choose the minimum useful addition. Prefer Python stdlib, existing git/browser tools, isolated virtual environments and maintained public packages. Add PDF parsing/rendered browsing only when needed.
3. Inspect provenance, installation scripts and required permissions. Pin a version/commit for important tools. Install under a workspace/.venv or user-owned directory rather than changing global host configuration.
4. Run a small smoke test and record success/failure and removal path. If broken, try a bounded alternative and continue unaffected work.
5. Keep third-party subprocess environments free of Brave/LLM/platform credentials unless that exact tool needs the exact credential for its legitimate service. A disposable filesystem does not make token exfiltration or credit loss disposable.

For MCP: establish the missing capability, inspect source/permissions/egress/licence, use local stdio where practical, and verify actual host registration/discovery. Downloading a server does not register tools. Do not expose an unauthenticated public listener. Do not route the Brave key to a service merely because it calls itself a Twitter/search server.

No purchases, GPU rental, account creation, CAPTCHA/access bypass, unlimited weights/downloads, platform-policy disabling or production actions. No hidden autorun, cron/Stop hooks or persistent background agents just to avoid finishing. Use supported continuation, documented separately.

Do not run `curl | sh` blindly with secrets present. Do not “fix” access by changing remote permissions. Missing Claude/GitHub credentials cannot be downloaded; record the bounded gap and continue source/offline work.

# blind-mcp → payband-mcp

**This package was renamed. It is now [`payband-mcp`](https://pypi.org/project/payband-mcp/).**

```bash
pip install payband-mcp     # or: uvx payband-mcp
```

Installing `blind-mcp` still works — this final version depends on
`payband-mcp` and re-exports it, so existing installs and the `blind-mcp`
command keep running. Nothing further will be published under this name.

Why the rename: the project reads published salary bands off public job-board
APIs (Greenhouse, Ashby, Lever, Workday), per seniority and per currency. The
Blind tools it started as are still in the codebase but are no longer
registered by default, because Blind has returned 403 to every automated
request since around September 2026. The old name described the part that
does not work.

Source, issues and docs: https://github.com/dheerajjha/payband-mcp

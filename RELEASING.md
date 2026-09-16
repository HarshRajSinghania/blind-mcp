# Releasing

Two steps, in order. The second depends on the first.

## 1. PyPI

Publishing is not a manual step. Pushing a `v*` tag runs
[`release.yml`](.github/workflows/release.yml), which publishes to PyPI over
Trusted Publishing — GitHub's OIDC identity, no API token stored anywhere.
The job refuses to publish unless the tests pass **and** the tag matches the
version in the package, so a mistyped tag fails loudly rather than shipping
the wrong thing.

```bash
git tag v0.4.0
git push origin v0.4.0
gh run watch          # or: gh run list --workflow=release.yml
```

Bump `version` in **three** places or the registry will reject the submission:
`pyproject.toml`, `src/payband_mcp/__init__.py`, and `server.json` (twice — the
top-level `version` and `packages[0].version`). See
[#7](https://github.com/dheerajjha/payband-mcp/issues/7) — the version is
currently duplicated rather than derived, which is exactly the kind of thing
that goes stale.

## 2. The official MCP registry

[registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io) is
how MCP clients discover servers. It validates ownership by matching the
`mcp-name:` marker in our README against the `name` in
[`server.json`](server.json) — both say `io.github.dheerajjha/payband-mcp`, so
this is already set up.

```bash
# https://github.com/modelcontextprotocol/registry
mcp-publisher login github
mcp-publisher publish
```

GitHub auth proves ownership of the `io.github.dheerajjha/*` namespace, so no
extra secret is needed beyond being signed in as the repo owner.

## 3. Where else to list it

Not automated, and each wants a PR to someone else's repo:

- [`punkpeye/awesome-mcp-servers`](https://github.com/punkpeye/awesome-mcp-servers)
- [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers) — community list
- [Glama](https://glama.ai/mcp/servers) and [Smithery](https://smithery.ai) — both index public GitHub repos, often without a submission

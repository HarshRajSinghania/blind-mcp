# Good first issues

Everything here is real, reproduced, and small. Each issue says where the code
is, what the fix probably looks like, and how to test it. `mentored` means ask
questions in the thread and you'll get walked through it — that's not a
formality, it's the point.

Comment on the issue to claim it. No need to wait for a reply to start.

## Under 30 minutes (`size: XS`)

| # | What's wrong | Why it matters |
| --- | --- | --- |
| [#1](https://github.com/dheerajjha/payband-mcp/issues/1) | `"what is the rto policy"` produces **zero** search keywords | The single most common question this server exists to answer falls back to "whatever was posted this week" |
| [#2](https://github.com/dheerajjha/payband-mcp/issues/2) | The noise filter drops `"16 weeks now"` and `"4 days mandatory"` | Those are the *answers*. Anything under 26 characters is discarded as spam |
| [#5](https://github.com/dheerajjha/payband-mcp/issues/5) | `read_post` truncates silently | You can't tell a 12-comment thread from a 137-comment one |
| [#6](https://github.com/dheerajjha/payband-mcp/issues/6) | Every multi-word company fails (`Goldman Sachs`, `Morgan Stanley`) | Blind uses hyphens; we only try capitalisations |
| [#7](https://github.com/dheerajjha/payband-mcp/issues/7) | The server reports an empty version to every client | Two files, no Blind knowledge needed at all |

## About an hour (`size: S`)

| # | What's wrong |
| --- | --- |
| [#3](https://github.com/dheerajjha/payband-mcp/issues/3) | `find` says "272 matches", returns 30, mentions nothing |
| [#8](https://github.com/dheerajjha/payband-mcp/issues/8) | The cache never evicts — 61MB after casual use |

## An afternoon (`size: M`)

| # | What's wrong |
| --- | --- |
| [#4](https://github.com/dheerajjha/payband-mcp/issues/4) | Ranking ignores thread age, so 2021 policy gets reported as current |

## Not on this list?

The most valuable contribution isn't any of the above — it's a **keyword gap**.
Ask `research` a real question about a company you know, and when it returns the
wrong threads, open a [keyword gap issue](https://github.com/dheerajjha/payband-mcp/issues/new?template=keyword_gap.md)
with what you asked and what came back. Usually one line in `_TOPIC_ALIASES`
fixes it, and you can send that as the same PR.

## Setup

```bash
git clone https://github.com/dheerajjha/payband-mcp && cd payband-mcp
uv sync
uv run pytest -q     # 12 tests, all offline, ~0.5s
```

Tests never touch the network. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the
two hard rules (don't commit captured Blind pages; don't weaken
robots/cache/throttle).

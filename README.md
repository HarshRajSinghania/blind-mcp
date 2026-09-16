# blind-mcp

[![tests](https://github.com/dheerajjha/blind-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/dheerajjha/blind-mcp/actions/workflows/test.yml)
[![good first issues](https://img.shields.io/github/issues/dheerajjha/blind-mcp/good%20first%20issue?label=good%20first%20issues&color=7057ff)](https://github.com/dheerajjha/blind-mcp/issues?q=is%3Aopen+label%3A%22good+first+issue%22)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/dheerajjha/blind-mcp/blob/main/pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](https://github.com/dheerajjha/blind-mcp/blob/main/LICENSE)

**Find out what a role actually pays — including in markets where the employer
publishes nothing.**

Colorado, California, New York, Washington and Illinois require a salary range
on covered job postings. India, Singapore and most of the EU require none. So
the same title, at the same company, in the same week, is posted with a band in
Denver and without one in Bengaluru.

The band is still there. It is just attached to a different listing.

```
pay_bands(company="Databricks", role="forward deployed")

  101 matching openings · 68 publish a range
  USD 140,400 – 320,200   (median 182,000 – 250,208)

  PUBLISHES A RANGE                      PUBLISHES NOTHING (same title)
    $152,900–210,155  United States        Remote - India
    $182,000–250,208  MD; VA; D.C.         Seoul, South Korea
    $211,800–291,300  Remote - D.C.        London, United Kingdom
    $178,800–245,850  Central - US         Berlin; Munich
```

That is the same employer, the same title, the same moment — a far better
anchor for an unpublished number than any salary survey, and it takes one call.

Reads the **public job-board APIs** (Greenhouse, Ashby, Lever). Documented,
intended for machines, and stable — not scraping.

## Tools

### Pay


### Culture — currently blocked

| Tool | What it does |
| --- | --- |
| `find(company, keyword, limit=, page=)` | Search a company's [Blind](https://www.teamblind.com) posts by keyword |
| `research(company, question, max_posts=)` | Pick the topic, rank threads against the question, return them in full |
| `company_topics` / `company_posts` / `read_post` | Listings and single threads |

> ⚠️ **Blind began returning 403 to all automated requests around September 2026.**
> This is site-wide bot protection, not a block on this project: `curl` and an
> empty User-Agent are refused too, and only a browser User-Agent gets through.
> `robots.txt` still permits `/company/`, but the WAF does not.
>
> We do not spoof a browser to get around it — that would be circumventing an
> access control, and it is the first thing their next escalation defeats. The
> Blind tools now raise `BlindBlocked` with an explanation rather than
> returning empty results that would read as "no discussion found".
>
> The pay tools are unaffected. See [#12](https://github.com/dheerajjha/blind-mcp/issues/12).

## Coverage

Measured, not estimated:

| Company | Board | Open roles | With a published range |
| --- | --- | --- | --- |
| Databricks | Greenhouse | 880 | 464 (52%) |
| Anthropic | Greenhouse | 595 | 470 (78%) |
| Ramp | Ashby | 148 | 141 (95%) |
| Figma | Greenhouse | 158 | 101 (63%) |
| Notion | Ashby | 127 | 71 (55%) |
| Stripe | Greenhouse | 647 | 21 (3%) |

**Not covered:** employers who self-host their careers site — Google, Meta,
Amazon, Apple, Atlassian, Canva — and most Indian-headquartered companies.
`fetch_postings` raises `BoardNotFound` and says so rather than returning
nothing. Adding an adapter is [#13](https://github.com/dheerajjha/blind-mcp/issues/13).

## Install

```bash
uv sync
```

Register with Claude Code:

```bash
uv tool install --editable .          # puts `blind-mcp` on PATH
claude mcp add --scope user blind -- blind-mcp
```

Or in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "blind": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/blind-mcp", "blind-mcp"]
    }
  }
}
```

## Do I need to log in?

**No — and you probably shouldn't.** This was measured, not assumed:

- Post bodies, full comment threads, Blind's AI comment summaries, company
  listings, topic pages, reviews and salary pages **all return HTTP 200
  anonymously**, with no gating.
- Driving an authenticated session with automation tripped Blind's anomaly
  detection after roughly six navigations: `Automatic Logout — we noticed a
  login from a new device or location (code 2009)`, with a redirect to
  `/session-out`.

So a cookie buys no extra read access and costs you session stability. The only
thing it would unlock is company-internal channels, which are gated to verified
employees of that company.

If you still want it, set `BLIND_COOKIE` to your session cookie header (copy it
from a logged-in browser request in DevTools). There is no login flow — the
server only replays a cookie you supply, read once at startup and attached to
each request. It is off by default, and the client raises immediately if Blind
invalidates it rather than silently returning logged-out HTML.

The cookie itself is never written to disk, but responses fetched with it are
cached under a separate `auth/` directory so authenticated and anonymous
results can never be served for each other. Don't commit the cookie.

## Being a good citizen

Blind's `robots.txt` disallows `/search/` for every user-agent, so **this server
has no search tool** and refuses to fetch that path. It also:

- sends an honest `User-Agent` (no browser impersonation — Blind serves it a 200 anyway)
- caches every response on disk for 6h, so repeat questions cost zero requests
- spaces requests ~1.5s apart
- fetches `robots.txt` first and fails closed if it can't be read

Configure via `BLIND_MCP_CACHE_DIR`, `BLIND_MCP_CACHE_TTL`,
`BLIND_MCP_MIN_INTERVAL`, `BLIND_MCP_USER_AGENT`.

Blind's Terms of Service restrict automated access. This reads public pages at
human pace for personal research; bulk crawling is both a ToS problem and, given
that Blind's value rests on anonymity, a privacy one. Don't build a dataset of
posts joined to employers and nicknames.

## Reading the output

Blind is anonymous and unverified. Weight claims by the commenter's employer
(`company` on each comment) and treat a single loud voice as one data point. In
testing, the Roku India RTO answer was corroborated by two independent
commenters *and* an unrelated Glassdoor review — that's when it's worth trusting.

## Contributing

Small project, easy to contribute to. The cheapest useful change is a **keyword
alias** — one dict entry plus a test — and it's the change that most improves
answers, because `research` only finds threads whose words match yours.

Start with [**good first issues**](https://github.com/dheerajjha/blind-mcp/blob/main/.github/GOOD_FIRST_ISSUES.md) — nine open,
all real and reproduced, each one saying where the code is and how to test the
fix — then [CONTRIBUTING.md](https://github.com/dheerajjha/blind-mcp/blob/main/CONTRIBUTING.md). Issues are labelled by size (`size: XS`
is under 30 minutes) and `mentored` means ask questions in the thread and
you'll get walked through it. First review within 48 hours.

Two hard rules, both explained in CONTRIBUTING: **don't commit captured Blind
pages** (fixtures are generated), and **don't weaken robots/cache/throttle** for
speed.

## Publishing

`mcp-name: io.github.dheerajjha/blind-mcp`

See [RELEASING.md](https://github.com/dheerajjha/blind-mcp/blob/main/RELEASING.md).

## License

MIT

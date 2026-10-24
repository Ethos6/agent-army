# Competitor Watch Agent

Give it your URL and your competitors' URLs. It fetches every page and writes a snapshot table (positioning in their own words, target customer, exact pricing, recent changes), then where you win, where you are exposed, and three moves for this quarter, each tied to evidence from the pages.

```bash
army run competitor-watch "We are https://ourco.com; rivals: https://a.com/pricing https://b.com" -v
```

It reports only pricing it actually saw on the page and writes "not published" otherwise. Run it weekly as a scheduled job to track changes.

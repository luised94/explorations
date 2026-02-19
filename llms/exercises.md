## Exercises

**Exercise tasks to stress-test the tool across all three commands:**

1. "Find that conversation where I designed the database schema" - tests search with a vague memory, will you find it in the first query or need to refine?
2. "What were my 5 longest conversations about?" - `list --sort messages --limit 5` then `show` each one. Tests the listshow flow.
3. "Find every conversation where I discussed Python packaging" - tests whether 20 results is enough, whether you want pagination.
4. "Find a specific code snippet I know an assistant wrote" - tests the known limitation that artifact content isn't indexed. How much does this hurt?
5. "Browse everything from last week" - tests whether list needs a date filter.
6. "Find a conversation and share the key insight with someone" - tests whether `show` output is copy-pasteable, or if you want a `--raw`/`--markdown` flag.
7. Pipe test: `uv run llm.py search "something" | grep "keyword"` - tests whether colors break grep, whether the output format works for unix pipeline composition.

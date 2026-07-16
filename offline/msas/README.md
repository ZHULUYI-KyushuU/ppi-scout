# Optional local receptor MSA files

Put optional receptor A3M files here using this exact filename:

```text
<sha256-of-normalized-receptor-sequence>.a3m
```

PPI Scout validates that the first/query A3M sequence exactly matches the
receptor before use. Peptide chains always remain `msa: empty`. A missing exact
match safely falls back to offline single-sequence mode.

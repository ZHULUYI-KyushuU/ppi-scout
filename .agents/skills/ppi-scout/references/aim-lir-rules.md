# AIM/LIR candidate and peptide-panel rules

Apply these rules only to an Atg8-family receptor and a candidate AIM/LIR-bearing protein. Treat the output as a testable motif hypothesis, not a binding call.

## Recognize candidates

Use the canonical core as a first-pass pattern:

```text
Φ-X-X-Ψ
Φ = W, F, or Y
Ψ = L, I, or V
```

Do not rank candidates by this regular expression alone. Noncanonical motifs exist, and many canonical-looking matches are incidental.

The local scanner is an optional first pass and is disabled unless the user
opts in. When enabled, it must report every canonical `[WFY]xx[LIV]` match,
assign stable candidate IDs, and expose the sequence-only features and scoring
used for ranking. It cannot infer solvent accessibility, disorder, membrane
topology, folded structure, or biological function. Those require independent
evidence and review. Candidate IDs follow sequence position and are not ranks;
use the separate rank and reasons when discussing priority.

Prioritize a match when several independent features agree:

- the partner is Atg8, LC3, or GABARAP and its AIM/LIR-binding pocket is relevant;
- the core is in a predicted or observed disordered region, exposed loop, or accessible terminus;
- acidic or regulatable flanking residues, conservation, prior mutagenesis, or biological localization support the site;
- the match is outside a transmembrane helix, signal peptide, buried folded core, and unrelated low-complexity artifact.

Route a core in a transmembrane segment to `needs_review`. Route a core in a defined folded domain to `domain` unless there is evidence that the isolated loop behaves as a linear motif.

## Preserve coordinates

Use 1-based inclusive coordinates in user input, job files, filenames, and reports. For example, residues W412 through L415 are `412:415`. If implementation code uses zero-based slicing, convert at the boundary and emit both `start_1based` and `end_1based`. Verify that the extracted core exactly matches the source sequence before planning.

## Generate nested WT windows

Default to 16, 24, and 34 residues around the four-residue core. Center the core where possible, clamp at protein termini, and report the actual coordinates and length of every peptide. Keep biologically important asymmetric flanks when known; do not force centering at the expense of context.

Never model only the four-residue core as the primary peptide. Treat the three window sizes as a context-sensitivity panel rather than claiming one universal optimal length.

## Generate matched controls

For every selected window, generate under identical settings:

- `WT`;
- `anchor1_A`: replace the aromatic Φ anchor with alanine;
- `anchor2_A`: replace the hydrophobic Ψ anchor with alanine;
- `double_anchor_A`: replace both anchors with alanine;
- `core_AAAA`: replace all four core residues with alanine when composition changes are acceptable;
- `flank_scramble`: retain the core but shuffle flanks;
- at least three deterministic, seeded scrambles matched as closely as possible for length, composition, and net charge.

Record the seed and exact mutated positions. A reversed core or peptide may be included as a stress-test decoy, but never label it a strict negative control.

## Plan candidate selection

When the user specifies one motif, test it directly and state any contextual warnings. When scanning a protein, report all matches, features, exclusions, and ranking rationale; do not silently select the first or highest regex match. If evidence is weak, plan a small candidate panel and label it exploratory.

After displaying the complete candidate table, ask for comma-separated
candidate IDs. A blank response means design none. Use
`ppi-scout scan --fasta PROTEIN.fasta` to inspect candidates, and add
`--design-candidate CANDIDATE_ID` only after explicit selection.

For WT-versus-control interpretation, use [interpretation-guardrails.md](interpretation-guardrails.md). Failure of WT to separate from anchor mutants and matched scrambles means motif specificity is not established, even if every model has high confidence.

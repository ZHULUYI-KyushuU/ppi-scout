# Representation routing rules

Use these rules to convert a biological question into one auditable representation. Emit `route`, `confidence`, `reasons`, `warnings`, `selected_region`, and `selected_motif`. Use 1-based inclusive coordinates.

## Establish inputs first

Confirm:

- canonical protein identity, organism or strain, exact sequence, and sequence source;
- whether the question concerns a whole-protein interaction, a known domain, or a specific linear motif;
- known structures, domains, transmembrane segments, disorder, localization, cofactors, and mutations;
- whether either sequence is unpublished or otherwise sensitive.

Return `needs_review` rather than resolving an ambiguous name or isoform silently.

## Apply evidence in this order

1. Honor an explicit biological hypothesis, but warn when its representation is inappropriate.
2. Preserve a biologically complete molecule; do not equate short with peptide or long with truncation.
3. Prefer experimentally annotated interfaces, motifs, and domain boundaries over length heuristics.
4. Check whether the selected region is folded, disordered, transmembrane, terminal, or structurally unresolved.
5. Apply compute feasibility only after the biological representation is chosen. Use length as a feasibility warning, never as the sole route criterion.

## Select `full_length`

Select `full_length` when all of the following are true:

- both inputs represent complete biological protein chains;
- the question concerns their overall interaction or no credible localized interface is known;
- truncation could remove folding, oligomerization, localization, or regulatory context;
- the job is computationally feasible, or the user accepts the feasibility warning.

A complete protein of only tens of residues can still belong here. Add warnings for membrane dependence, obligatory cofactors, large disordered regions, or missing cellular context; lower confidence when these limitations are material.

## Select `domain`

Select `domain` when at least one strong localization signal exists:

- a known or well-supported interaction domain;
- an interface mapped by structure, mutagenesis, cross-linking, or curated annotation;
- a motif inside a folded region whose containing domain is the biologically meaningful unit;
- a multi-domain protein where unrelated regions make full-length modeling misleading or impractical.

Use curated or structure-supported boundaries. Preserve the folded core and record the source of every boundary. Do not cut through secondary structure or turn a folded-domain segment into a free peptide. If boundary evidence is weak, plan nearby boundary variants or return `needs_review`.

## Select `motif_peptide`

Select `motif_peptide` only when the question is genuinely local:

- the user names a motif, mutation, or short linear interaction hypothesis; or a supported motif scan identifies one;
- the partner has a compatible motif-binding pocket or established recognition mechanism;
- the candidate motif is plausibly accessible, such as in an intrinsically disordered region, exposed loop, or flexible terminus;
- flanking context and matched negative controls can be modeled.

For AIM/LIR, use the additional rules in [aim-lir-rules.md](aim-lir-rules.md). Do not select this route merely because one protein is long. If the motif lies in a transmembrane segment, return `needs_review`. If it lies in a folded domain, prefer that domain when the domain can be defined; otherwise return `needs_review`.

## Select `needs_review` or a comparison panel

Select `needs_review` when:

- identity, isoform, organism, or coordinates are unresolved;
- the only rationale is protein length;
- a candidate motif conflicts with topology or structural context;
- membrane, nucleic-acid, cofactor, or post-translational-modification dependence is essential but absent;
- competing representations encode different biological questions and the user has not chosen one.

When two routes remain plausible, plan them as separate hypotheses rather than merging their scores. For example, compare full-length versus a supported domain, or several peptide windows around one motif. Do not compare raw confidence values across representations as though they were calibrated on the same scale.

## Assign confidence

- `high`: identity and coordinates are exact, and the route is supported by direct interface/motif/domain evidence plus compatible structural context.
- `medium`: the route is biologically plausible but relies on annotation, predicted disorder, or an incomplete structure.
- `low`: the route is exploratory, evidence conflicts, or important context is missing. Prefer `needs_review` when the missing information can be obtained.

Always list positive reasons and material warnings. Never encode “predicted binding” as a routing reason.

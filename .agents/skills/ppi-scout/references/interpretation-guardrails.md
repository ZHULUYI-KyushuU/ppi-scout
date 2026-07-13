# Interpretation guardrails

Interpret PPI Scout output as structural-model evidence for a hypothesis. Do not convert it into an experimental binding claim.

## Preserve the evidence chain

Check, in order:

1. **Input integrity:** confirm identities, sequences, organism, coordinates, chain assignment, MSA mode, templates, and mutations.
2. **Representation validity:** confirm that full-length, domain, or peptide matches the biological question.
3. **Model confidence:** report raw confidence fields without redefining them.
4. **Interface plausibility:** inspect the expected pocket, peptide-local confidence, interface error, contacts, clashes, anchor placement, and pose convergence.
5. **Specificity controls:** compare WT, anchor mutants, flank controls, and matched scrambles under identical settings.
6. **Robustness:** compare multiple samples or seeds and, when informative, matched MSA conditions.
7. **Experimental validation:** propose an assay capable of testing the same interface or motif.

A failure at an earlier step limits every later conclusion.

## Treat confidence metrics correctly

- Treat ipTM, protein_ipTM, pair-chain ipTM, pTM, pLDDT, interface pLDDT, PAE/PDE, confidence score, and rank score as model diagnostics.
- Never describe ipTM or any composite score as a probability that the molecules interact.
- Never use a universal threshold such as “0.8 binds” or “0.9 is proven.”
- Never present rank order as an experimental affinity series.
- Compare scores directly only for matched inputs and settings. Representation, length, MSA, template, model version, sampling, and constraints can change score behavior.
- Inspect the structure. A high global score with the peptide at the wrong surface does not support the proposed mechanism.

## Exclude Boltz affinity from PPI analysis

Do not request the Boltz `properties.affinity` module for protein-protein or protein-peptide jobs. The local Boltz affinity module supports a small-molecule ligand against a protein target; it is not a PPI or peptide-affinity estimator.

If an imported PPI run contains `affinity_*.json`, ignore those values for PPI conclusions. Do not report them as Kd, IC50, binding probability, or evidence of interaction.

## Interpret matched controls

Use the following conservative labels:

- **Structural-model support:** WT repeatedly occupies the biologically expected pocket with plausible geometry and separates from matched anchor mutants and scrambles under the same settings.
- **Ambiguous:** WT forms a plausible pose but controls behave similarly, results depend strongly on MSA/sample/window, or the pose is inconsistent.
- **No structural-model support under tested conditions:** WT fails to form a plausible expected interface across the planned samples while inputs and route remain valid.

Do not turn the third label into “does not bind.” A negative model can reflect missing membrane context, cofactors, modifications, conformational state, or model limitations.

For AIM/LIR panels, failure of WT to outperform `double_anchor_A`, `core_AAAA`, or matched scrambles means motif specificity is not established. A decoy scoring above WT is a warning, not proof that the decoy binds better.

## Write the report conservatively

Report:

- the exact question and selected representation;
- raw metrics and structural observations separately;
- WT-control contrasts and robustness checks;
- missing biological context and computational limitations;
- a calibrated conclusion using the labels above;
- the next discriminating experiment, such as anchor mutation plus co-IP/pull-down, direct peptide-binding measurement, or rescue with a sequence-verified construct.

Use “supports a structural hypothesis,” “is consistent with,” or “remains ambiguous.” Avoid “binds,” “does not bind,” “validated,” and quantitative affinity language unless independent experiments establish them.

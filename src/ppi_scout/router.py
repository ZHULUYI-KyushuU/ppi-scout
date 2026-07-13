"""Choose a biological representation without using length as a proxy."""

from __future__ import annotations

from .models import InteractionQuery, RoutingDecision


_GOAL_ALIASES = {
    "full-length": "full_length",
    "full_length": "full_length",
    "domain": "domain",
    "motif-peptide": "motif_peptide",
    "motif_peptide": "motif_peptide",
    "auto": "auto",
}


def _manual_goal(query: InteractionQuery, goal: str) -> RoutingDecision:
    warnings: list[str] = []
    if goal == "motif_peptide" and not query.motif_sequence:
        warnings.append("Motif-peptide mode was requested without a resolved motif sequence.")
    if goal == "full_length" and (
        query.protein_a.membrane_dependent or query.protein_b.membrane_dependent
    ):
        warnings.append("A membrane-dependent interaction is being modeled without an explicit membrane environment.")
    return RoutingDecision(
        route=goal,
        confidence="user_selected",
        reasons=("The user explicitly selected this representation.",),
        warnings=tuple(warnings),
        selected_region=query.motif_region if goal == "motif_peptide" else None,
        selected_motif=query.motif_sequence if goal == "motif_peptide" else None,
    )


def route_interaction(query: InteractionQuery) -> RoutingDecision:
    """Return a conservative route plus the evidence used to select it."""

    goal = _GOAL_ALIASES.get(query.goal)
    if goal is None:
        raise ValueError(f"Unsupported interaction goal: {query.goal!r}")
    if goal != "auto":
        return _manual_goal(query, goal)

    proteins = (query.protein_a, query.protein_b)
    if any(protein.sequence is None for protein in proteins):
        return RoutingDecision(
            route="needs_review",
            confidence="low",
            reasons=("At least one protein identity has not been resolved to an exact sequence.",),
            warnings=("Resolve species, isoform, accession, and sequence before structural routing.",),
        )

    if query.motif_sequence and query.receptor_has_motif_pocket:
        if query.motif_in_disorder is True or query.motif_exposed is True:
            return RoutingDecision(
                route="motif_peptide",
                confidence="high",
                reasons=(
                    "A localized motif hypothesis is available.",
                    "The receptor has a corresponding motif-binding pocket.",
                    "The motif is predicted to be accessible or disordered.",
                ),
                selected_region=query.motif_region,
                selected_motif=query.motif_sequence,
            )
        if query.motif_in_disorder is False or query.motif_exposed is False:
            return RoutingDecision(
                route="domain",
                confidence="medium",
                reasons=(
                    "A motif-like sequence exists but appears structurally embedded.",
                    "Domain context is needed to test whether the site is naturally accessible.",
                ),
                warnings=("Run a peptide panel only as a sensitivity arm, not as the sole biological model.",),
                selected_region=query.motif_region,
                selected_motif=query.motif_sequence,
            )
        return RoutingDecision(
            route="needs_review",
            confidence="medium",
            reasons=(
                "A motif and receptor pocket are plausible, but full-length accessibility is unresolved.",
            ),
            warnings=("Assess disorder, surface exposure, domain context, and membrane topology before cropping.",),
            selected_region=query.motif_region,
            selected_motif=query.motif_sequence,
        )

    domain_candidates = [protein for protein in proteins if protein.known_domain or protein.domain_region]
    if domain_candidates:
        selected = next((protein.domain_region for protein in domain_candidates if protein.domain_region), None)
        return RoutingDecision(
            route="domain",
            confidence="high",
            reasons=("A biologically supported folded domain localizes the interaction question.",),
            selected_region=selected,
        )

    membrane_context = any(
        protein.has_transmembrane_region or protein.membrane_dependent for protein in proteins
    )
    if membrane_context:
        return RoutingDecision(
            route="full_length",
            confidence="medium",
            reasons=(
                "At least one input is a biologically complete membrane-associated protein.",
                "No independent linear-motif hypothesis justifies peptide cropping.",
            ),
            warnings=("The prediction backend does not reproduce the native membrane environment.",),
        )

    if any(protein.folded_interface_expected for protein in proteins):
        return RoutingDecision(
            route="full_length",
            confidence="medium",
            reasons=("The proposed interface is expected to involve a folded three-dimensional surface.",),
        )

    return RoutingDecision(
        route="full_length",
        confidence="low",
        reasons=(
            "No localized motif or domain evidence currently justifies cropping either protein.",
            "Full-length modeling preserves the stated whole-protein question.",
        ),
        warnings=(
            "Review domains, disorder, oligomerization, localization, and membrane dependence before live execution.",
        ),
    )

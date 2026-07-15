# Pinned Boltz 2 model payload

The portable v0.4.0 bundle uses the files downloaded by Boltz 2.2.1:

- `mols.tar`
- `boltz2_conf.ckpt`
- `boltz2_aff.ckpt`

Their exact SHA-256 values are recorded in `SHA256SUMS`. Boltz upstream states
that its code and weights are distributed under the MIT license. PPI Scout
structure-only protein/peptide panels do not request or interpret affinity;
the affinity checkpoint is included because the upstream Boltz 2.2.1 cache
bootstrap expects both checkpoints to be present before prediction.

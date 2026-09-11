from __future__ import annotations

GLOSSARY = [
    {"term": "stage", "definition": "One simulation run in its own directory, never overwritten."},
    {"term": "replica", "definition": "An independent copy of the same system with different initial velocities, from a deterministic per-replica seed."},
    {"term": "segment", "definition": "A 50 ns production stage; segments chain through checkpoints."},
    {"term": "lineage", "definition": "The ordered chain of stages a trajectory actually passed through, read from each stage's recorded parent rather than from stage numbering."},
    {"term": "branch", "definition": "A stage that is valid but not part of the lineage, because it was abandoned and another stage continued from the same point."},
    {"term": "gate", "definition": "A check that must pass before the next phase may begin, enforced in code."},
    {"term": "plateau", "definition": "The state in which the box size and shape no longer change systematically, judged by a slope compared with its own uncertainty."},
    {"term": "autocorrelation time", "definition": "How long a quantity takes to forget its previous value; it sets how many of the frames count as independent evidence."},
    {"term": "effective samples", "definition": "Window length divided by autocorrelation time; the honest sample count."},
    {"term": "area per lipid", "definition": "The membrane area minus the protein cross-section, divided by the lipids in that leaflet; the standard measure of whether a bilayer has relaxed."},
    {"term": "ionic lock", "definition": "The Arg173-Glu318 salt bridge between helices 3 and 6, associated with the inactive state; a distribution, not a switch."},
    {"term": "site sodium", "definition": "The sodium ion in the conserved allosteric pocket near Asp120, a hallmark of inactive class A GPCRs."},
    {"term": "barostat", "definition": "The algorithm holding pressure constant; this campaign uses stochastic cell rescaling, semiisotropic, so the membrane plane and normal are coupled separately."},
    {"term": "offload", "definition": "Which parts of the force calculation run on the GPU."},
    {"term": "reap", "definition": "Validate a stage whose simulation finished but whose driver died first."},
]
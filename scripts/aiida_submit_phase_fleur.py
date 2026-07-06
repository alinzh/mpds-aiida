#!/usr/bin/env python3

import sys
from aiida import load_profile
from aiida.plugins import DataFactory
from aiida.engine import submit
from aiida.orm import Dict
from mpds_aiida.workflows.fleur_mpds import MPDSFleurStructureWorkChain


load_profile()

try:
    phase = sys.argv[1].split("/")
except IndexError:
    phase = ("MgO", "225")
    print("Default phase for testing: " + "/".join(phase))

if len(phase) == 3:
    formula, sgs, pearson = phase
else:
    formula, sgs, pearson = phase[0], phase[1], None

sgs = int(sgs)

inputs = MPDSFleurStructureWorkChain.get_builder()

inputs.metadata = dict(label="/".join(phase))
inputs.mpds_query = DataFactory("dict")(dict={"formulae": formula, "sgs": sgs})
#inputs.workchain_options = DataFactory("dict")(dict={"codes":{"fleur": "fleur"}, "calculator":"scf", "optimizer":"CG"})
inputs.workchain_options = Dict(dict={
    "options": {
        "optimize_structure": True,
        "need_phonons": True,
        "optimizer": "CG",
        "calculator": "scf"
    }
})

wc = submit(MPDSFleurStructureWorkChain, **inputs)
print("Submitted FleurWorkChain %s" % wc.pk)

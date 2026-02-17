"""Parametric Generation — Item 08.

Accepts validated ParametricSpec from the NL parser (Item 06) and compliance
engine (Item 07), then produces complete element folders matching the
extraction pipeline (Item 01) output format.
"""

from aecos.generation.generator import ElementGenerator
from aecos.generation.assembly import AssemblyGenerator

__all__ = ["ElementGenerator", "AssemblyGenerator"]

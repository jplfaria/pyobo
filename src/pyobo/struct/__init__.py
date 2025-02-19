"""Data structures for OBO."""

from .reference import OBOLiteral, Reference, Referenced, default_reference
from .struct import (
    CHARLIE_TERM,
    HUMAN_TERM,
    PYOBO_INJECTED,
    Obo,
    Synonym,
    SynonymTypeDef,
    Term,
    TypeDef,
    int_identifier_sort_key,
    make_ad_hoc_ontology,
)
from .struct_utils import Stanza
from .typedef import (
    derives_from,
    enables,
    from_species,
    gene_product_member_of,
    has_category,
    has_citation,
    has_gene_product,
    has_member,
    has_part,
    has_participant,
    is_a,
    member_of,
    orthologous,
    part_of,
    participates_in,
    species_specific,
    superclass_of,
    transcribes_to,
    translates_to,
)

__all__ = [
    "CHARLIE_TERM",
    "HUMAN_TERM",
    "PYOBO_INJECTED",
    "OBOLiteral",
    "Obo",
    "Reference",
    "Referenced",
    "Stanza",
    "Synonym",
    "SynonymTypeDef",
    "Term",
    "TypeDef",
    "default_reference",
    "derives_from",
    "enables",
    "from_species",
    "gene_product_member_of",
    "has_category",
    "has_citation",
    "has_gene_product",
    "has_member",
    "has_part",
    "has_participant",
    "int_identifier_sort_key",
    "is_a",
    "make_ad_hoc_ontology",
    "member_of",
    "orthologous",
    "part_of",
    "participates_in",
    "species_specific",
    "superclass_of",
    "transcribes_to",
    "translates_to",
]

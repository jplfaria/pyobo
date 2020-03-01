# -*- coding: utf-8 -*-

"""This module has the parser for HGNC."""

from collections import defaultdict
from typing import Iterable

import pandas as pd
from tqdm import tqdm

from pyobo import Obo, Reference, Synonym, SynonymTypeDef, Term
from pyobo.constants import ensure_path

PREFIX = 'hgnc.genefamily'
FAMILIES_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/genenames/new/csv/genefamily_db_tables/family.csv'
HIERARCHY_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/genenames/new/csv/genefamily_db_tables/hierarchy.csv'

symbol_type = SynonymTypeDef(id='symbol', name='symbol')


def get_obo():
    terms = list(get_terms())
    hierarchy = get_hierarchy()

    id_to_term = {term.reference.identifier: term for term in terms}
    for child_id, parent_ids in hierarchy.items():
        child = id_to_term[child_id]
        for parent_id in parent_ids:
            parent: Term = id_to_term[parent_id]
            child.parents.append(Reference(
                prefix=PREFIX,
                identifier=parent_id,
                label=parent.name,
            ))

    return Obo(
        ontology=PREFIX,
        terms=terms,
        synonym_typedefs=[symbol_type],
        auto_generated_by='bio2obo:hgnc.genefamily',
    )


def get_hierarchy():
    path = ensure_path(PREFIX, HIERARCHY_URL)
    df = pd.read_csv(path, dtype={'parent_fam_id': str, 'child_fam_id': str})
    d = defaultdict(list)
    for parent_id, child_id in df.values:
        d[child_id].append(parent_id)
    return dict(d)


COLUMNS = ['id', 'abbreviation', 'name', 'pubmed_ids', 'desc_comment', 'desc_go']


def get_terms() -> Iterable[Term]:
    path = ensure_path(PREFIX, FAMILIES_URL)
    df = pd.read_csv(path, dtype={'id': str})

    it = tqdm(df[COLUMNS].values, desc=f'Mapping {PREFIX}')
    for hgncgenefamily_id, symbol, name, pubmed_ids, definition, desc_go in it:
        if pubmed_ids and pd.notna(pubmed_ids):
            provenance = [Reference(prefix='pubmed', identifier=s.strip()) for s in pubmed_ids.split(',')]
        else:
            provenance = []

        if not definition or pd.isna(definition):
            definition = ''

        xrefs = []
        if desc_go and pd.notna(desc_go):
            go_id = desc_go[len('http://purl.uniprot.org/go/'):]
            xrefs.append(Reference(prefix='go', identifier=go_id))

        synonyms = []
        if symbol and pd.notna(symbol):
            synonyms.append(Synonym(name=symbol, type=symbol_type))

        term = Term(
            name=name,
            reference=Reference(prefix=PREFIX, identifier=hgncgenefamily_id),
            definition=definition,
            provenance=provenance,
            xrefs=xrefs,
            synonyms=synonyms,
        )
        yield term


if __name__ == '__main__':
    get_obo().write_default()

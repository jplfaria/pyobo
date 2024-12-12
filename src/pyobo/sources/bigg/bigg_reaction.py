"""Converter for BiGG."""

from collections.abc import Iterable

import pandas as pd
from tqdm import tqdm

from pyobo.sources.bigg.bigg_metabolite import _parse_dblinks, _parse_model_links, _split
from pyobo.struct import Obo, Reference, Term
from pyobo.struct.typedef import enabled_by, participates_in
from pyobo.utils.path import ensure_df

__all__ = [
    "BiGGReactionGetter",
]

PREFIX = "bigg.reaction"
URL = "http://bigg.ucsd.edu/static/namespace/bigg_models_reactions.txt"
PROPERTY_MAP = {"eccode": enabled_by}


class BiGGReactionGetter(Obo):
    """An ontology representation of BiGG Reactions."""

    ontology = PREFIX
    bioversions_key = "bigg"
    typedefs = [participates_in, enabled_by]
    idspaces = {
        PREFIX: "http://bigg.ucsd.edu/models/universal/reactions/",
        "bigg.model": "http://bigg.ucsd.edu/models/",
    }

    def iter_terms(self, force: bool = False) -> Iterable[Term]:
        """Iterate over terms in the ontology."""
        return iterate_terms(force=force, version=self._version_or_raise)


def iterate_terms(force: bool = False, version: str | None = None) -> Iterable[Term]:
    """Iterate terms for BiGG Reaction."""
    bigg_reaction_df = ensure_df(
        prefix=PREFIX,
        url=URL,
        force=force,
        version=version,
    )

    for bigg_id, name, reaction_string, model_list, database_links, old_bigg_ids in tqdm(
        bigg_reaction_df.values, unit_scale=True, unit="reaction", desc=f"[{PREFIX}] processing"
    ):
        term = Term(
            reference=Reference(
                prefix=PREFIX, identifier=bigg_id, name=name if pd.notna(name) else None
            ),
            definition=reaction_string,
        )
        for old_bigg_id in _split(old_bigg_ids):
            if old_bigg_id == bigg_id:
                continue
            term.append_alt(Reference(prefix=PREFIX, identifier=old_bigg_id))
        _parse_model_links(term, model_list)

        # TODO make sure exact match goes to the bidirectional rhea reaction but not others
        _parse_dblinks(term, database_links)

        yield term


if __name__ == "__main__":
    BiGGReactionGetter().write_default(force=True, write_obo=True)
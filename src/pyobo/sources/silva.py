"""Convert SILVA small subunit (ssu) taxonomy to OBO format."""

import logging
from collections.abc import Iterable

import pandas as pd
from tqdm.auto import tqdm

from pyobo.struct import Obo, Reference, Term, TypeDef, default_reference
from pyobo.struct.typedef import has_taxonomy_rank
from pyobo.utils.path import ensure_path

__all__ = [
    "SILVAGetter",
]

PREFIX = "silva.taxon"

#: A mapping from SILVA rank names to TAXRANK references
SILVA_RANK_TO_TAXRANK = {
    "domain": Reference(prefix="TAXRANK", identifier="0000037", name="domain"),
    "major_clade": Reference(prefix="TAXRANK", identifier="0001004", name="major_clade"),
    "superkingdom": Reference(prefix="TAXRANK", identifier="0000022", name="superkingdom"),
    "kingdom": Reference(prefix="TAXRANK", identifier="0000017", name="kingdom"),
    "subkingdom": Reference(prefix="TAXRANK", identifier="0000029", name="subkingdom"),
    "superphylum": Reference(prefix="TAXRANK", identifier="0000027", name="superphylum"),
    "phylum": Reference(prefix="TAXRANK", identifier="0000001", name="phylum"),
    "subphylum": Reference(prefix="TAXRANK", identifier="0000008", name="subphylum"),
    "infraphylum": Reference(prefix="TAXRANK", identifier="0000040", name="infraphylum"),
    "superclass": Reference(prefix="TAXRANK", identifier="0000015", name="superclass"),
    "class": Reference(prefix="TAXRANK", identifier="0000002", name="class"),
    "subclass": Reference(prefix="TAXRANK", identifier="0000007", name="subclass"),
    "infraclass": Reference(prefix="TAXRANK", identifier="0000019", name="infraclass"),
    "superorder": Reference(prefix="TAXRANK", identifier="0000020", name="superorder"),
    "order": Reference(prefix="TAXRANK", identifier="0000003", name="order"),
    "suborder": Reference(prefix="TAXRANK", identifier="0000014", name="suborder"),
    "superfamily": Reference(prefix="TAXRANK", identifier="0000018", name="superfamily"),
    "family": Reference(prefix="TAXRANK", identifier="0000004", name="family"),
    "subfamily": Reference(prefix="TAXRANK", identifier="0000024", name="subfamily"),
    "genus": Reference(prefix="TAXRANK", identifier="0000005", name="genus"),
}

#: URLs for the SILVA files.
SILVA_TAXONOMY_URL = "https://www.arb-silva.de/fileadmin/silva_databases/current/Exports/taxonomy/tax_slv_ssu_138.2.txt.gz"
SILVA_TAXMAP_URL = "https://www.arb-silva.de/fileadmin/silva_databases/current/Exports/taxonomy/taxmap_slv_ssu_ref_nr_138.2.txt.gz"

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

HAS_TAXONOMIC_CLASSIFICATION = TypeDef(
    reference=default_reference(PREFIX, "has_taxonomic_classification", name="has taxonomic classification"),
    definition="Indicates that the genome sequence represented by an ENA accession is classified under this taxon by SILVA.",
    is_metadata_tag=True,
)


class SILVAGetter(Obo):
    """An ontology representation of the SILVA taxonomy."""

    ontology = bioversions_key = PREFIX
    typedefs = [has_taxonomy_rank, HAS_TAXONOMIC_CLASSIFICATION]
    idspaces = {
        PREFIX: "https://www.arb-silva.de/no_cache/download/archive/current/Exports/taxonomy/",
        "ena.embl": "https://www.ebi.ac.uk/ena/browser/view/",
    }
    root_terms = [
        Reference(prefix=PREFIX, identifier="2", name="Archaea"),
        Reference(prefix=PREFIX, identifier="3", name="Bacteria"),
        Reference(prefix=PREFIX, identifier="4", name="Eukaryota"),
    ]

    def iter_terms(self, force: bool = False) -> Iterable[Term]:
        """Iterate over terms in the SILVA ontology."""
        return iter_terms_silva(version=self._version_or_raise, force=force)


def iter_terms_silva(version: str, force: bool = False) -> Iterable[Term]:
    """Iterate over SILVA terms from the main taxonomy and taxmap files."""
    # --- Process the main taxonomy file ---
    taxonomy_path = ensure_path(PREFIX, url=SILVA_TAXONOMY_URL, version=version, force=force)
    tax_df = pd.read_csv(
        taxonomy_path,
        sep="\t",
        header=None,
        names=["taxonomy", "taxon_id", "rank", "ignore", "introduced"],
        dtype=str,
    )
    tax_df.fillna("", inplace=True)

    #: a dictionary that maps the joined taxonomy path (with trailing ";") to taxon_id
    tax_path_to_id: dict[str, str] = {}
    #: maps taxon_id to the Term object
    terms_by_id = {}

    for idx, row in tqdm(
        tax_df.iterrows(),
        total=len(tax_df),
        desc=f"[{PREFIX}] processing main taxonomy",
        unit="row",
    ):
        tax_str = row["taxonomy"].strip()
        taxon_id = row["taxon_id"].strip()
        rank_raw = row["rank"].strip()
        rank = rank_raw.lower()
        # Split taxonomy string by ";" and discard empty parts.
        parts = [p.strip() for p in tax_str.split(";") if p.strip()]
        if not parts:
            logger.warning(f"Row {idx}: empty taxonomy string: {tax_str}")
            continue

        # The term's name is the last element (e.g. for "Bacteria;Actinomycetota;", name is "Actinomycetota").
        name = parts[-1]
        term = Term(reference=Reference(prefix=PREFIX, identifier=taxon_id, name=name))
        if rank in SILVA_RANK_TO_TAXRANK:
            term.annotate_object(has_taxonomy_rank, SILVA_RANK_TO_TAXRANK[rank])
        else:
            logger.warning(
                f"Row {idx}: unknown rank '{rank_raw}' for taxonomy: {tax_str} (taxon id: {taxon_id})"
            )

        # Determine the parent by joining all but the last element.
        if len(parts) > 1:
            parent_key = ";".join(parts[:-1]) + ";"  # e.g. "Bacteria;"
            parent_id = tax_path_to_id.get(parent_key)
            if parent_id:
                term.append_parent(Reference(prefix=PREFIX, identifier=parent_id))
        full_key = ";".join(parts) + ";"
        tax_path_to_id[full_key] = taxon_id
        terms_by_id[taxon_id] = term

    # --- Process the taxmap file ---
    # This file has a header with columns: primaryAccession, start, stop, path, organism_name, taxid
    taxmap_path = ensure_path(PREFIX, url=SILVA_TAXMAP_URL, version=version, force=force)
    taxmap_df = pd.read_csv(taxmap_path, sep="\t", dtype=str)
    taxmap_df.rename(
        columns={
            "primaryAccession": "accession",
            "organism_name": "organism",
            "taxid": "species_taxon_id",
            "path": "taxonomy",
        },
        inplace=True,
    )
    taxmap_df.fillna("", inplace=True)

    for idx, row in tqdm(
        taxmap_df.iterrows(), total=len(taxmap_df), desc=f"[{PREFIX}] processing taxmap", unit="row"
    ):
        accession = row["accession"].strip()
        species_taxon_id = row["species_taxon_id"].strip()
        organism = row["organism"].strip()
        if not accession or not species_taxon_id:
            continue
        if species_taxon_id in terms_by_id:
            # Create a new term for the ENA accession.
            new_term = Term(
                reference=Reference(prefix="ena.embl", identifier=accession, name=organism)
            )
            # Do NOT annotate the new term with a rank (leave it unranked).
            new_term.annotate_object(
                HAS_TAXONOMIC_CLASSIFICATION, Reference(prefix=PREFIX, identifier=species_taxon_id)
            )
            yield new_term
        else:
            logger.warning(
                f"Row {idx} in taxmap: species_taxon_id {species_taxon_id} not found in main taxonomy"
            )

    # Yield all terms from the main taxonomy.
    for term in terms_by_id.values():
        yield term


if __name__ == "__main__":
    SILVAGetter().cli()

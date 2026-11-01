from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.11.0"
version = "0.1.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'aacps_policy_dm',
     'default_range': 'string',
     'description': 'The draft AACPS Board Policy DM, Responsible Use of '
                    'Artificial Intelligence (October 2026), the public documents '
                    'it cites or is bound by, and the public meeting records of '
                    'its adoption. Each document is held with its url, sha256 and '
                    'retrieval date, or recorded as metadata only with the reason.',
     'id': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema',
     'imports': ['linkml:types', '/Users/brock/GitHub/squiddy/squiddy/schema/core'],
     'license': 'MIT',
     'name': 'aacps_policy_dm',
     'prefixes': {'aacps_policy_dm': {'prefix_prefix': 'aacps_policy_dm',
                                      'prefix_reference': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/'},
                  'cito': {'prefix_prefix': 'cito',
                           'prefix_reference': 'http://purl.org/spar/cito/'},
                  'fabio': {'prefix_prefix': 'fabio',
                            'prefix_reference': 'http://purl.org/spar/fabio/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'prov': {'prefix_prefix': 'prov',
                           'prefix_reference': 'http://www.w3.org/ns/prov#'},
                  'squiddy': {'prefix_prefix': 'squiddy',
                              'prefix_reference': 'https://github.com/brockwebb/squiddy/schema/core/'}},
     'source_file': '/Users/brock/GitHub/aacps-ai-policy/graphs/aacps-policy-dm/schema/aacps_policy_dm.yaml',
     'title': 'the AACPS Policy DM corpus graph'} )

class AssertionStatus(str, Enum):
    """
    The authority model on an assertion, from fss-policy-kg's overlay discipline.
    """
    proposed = "proposed"
    accepted = "accepted"
    retracted = "retracted"


class ManifestStage(str, Enum):
    """
    Axis 1, pipeline position, profiling UNECE GSBPM v5.1 (icsp_notebook/corpus/manifest_schema.md). `admitting` is `in_graph` in the middle of becoming true (v7.11, DI-078).
    """
    cataloged = "cataloged"
    acquired = "acquired"
    admitting = "admitting"
    in_graph = "in_graph"
    assess_queue = "assess_queue"


class ManifestDisposition(str, Enum):
    """
    Axis 2, intent or role, profiling DDI-Lifecycle 3.3 with local reason codes. A graph's config restricts this to the values it uses; a value not in the config is a gate failure.
    """
    active = "active"
    reference = "reference"
    metadata_only = "metadata_only"
    excludedCOLONdeferred = "excluded:deferred"
    excludedCOLONrestricted = "excluded:restricted"
    excludedCOLONout_of_scope = "excluded:out_of_scope"


class EventKind(str, Enum):
    node = "node"
    edge = "edge"
    retract = "retract"
    manifest = "manifest"
    catalog = "catalog"


class CitoIntent(str, Enum):
    """
    CiTO citation intents, the subset a bibliographic evidence graph needs (Peroni and Shotton 2012, peroni2012fabio). The default is the weakest claim.
    """
    citesForInformation = "citesForInformation"
    citesAsAuthority = "citesAsAuthority"
    citesAsEvidence = "citesAsEvidence"
    usesMethodIn = "usesMethodIn"
    supports = "supports"
    disagreesWith = "disagreesWith"
    extends = "extends"
    """
    Fillable by extraction (S-007); no deterministic source sets it.
    """


class DocKind(str, Enum):
    """
    The sort of record an internal document is (S-008 Part A, fixed by the task). Decided by the path and the file name under the ordered rules in `engine.repodocs.doc_kind_rules`.
    """
    decision_record = "decision_record"
    handoff = "handoff"
    lab_note = "lab_note"
    delivery_report = "delivery_report"
    design_note = "design_note"
    cc_task = "cc_task"
    other = "other"



class GroundingSpan(ConfiguredBaseModel):
    """
    Character offsets into the parsed intermediate's `plain_text`, the sha256 of the located text (so anyone holding the intermediate can verify the slice), and the sha256 of the whole plain text (so a re-parse that moves the offsets is detectable rather than silent).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/schema/core'})

    start: int = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['GroundingSpan']} })
    end: int = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['GroundingSpan']} })
    sha256: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['GroundingSpan', 'ManifestEntry', 'Work']} })
    parsed_sha256: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['GroundingSpan']} })


class Node(ConfiguredBaseModel):
    """
    A property-graph node keyed by `id`.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://github.com/brockwebb/squiddy/schema/core'})

    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class Edge(ConfiguredBaseModel):
    """
    A property-graph edge from `subject` to `object`; the class is the predicate.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True,
         'from_schema': 'https://github.com/brockwebb/squiddy/schema/core'})

    subject: str = Field(default=..., description="""The id of the source node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    object: str = Field(default=..., description="""The id of the target node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class ManifestEntry(ConfiguredBaseModel):
    """
    One entry per document ever considered (DI-070). The two status axes are required.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/schema/core',
         'slot_usage': {'disposition': {'name': 'disposition', 'required': True},
                        'stage': {'name': 'stage', 'required': True}}})

    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    kind: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    stage: ManifestStage = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    disposition: ManifestDisposition = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    title: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    source_url: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    cited_in: Optional[str] = Field(default=None, description="""Where in the graph's own record this item is cited; the biblio assessment criterion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    provenance_flag: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    acquisition_status: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    local_path: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    sha256: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['GroundingSpan', 'ManifestEntry', 'Work']} })
    bytes: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    retrieved_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    verification_status: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    notes: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })
    admitting_since: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry']} })


class EventEnvelope(ConfiguredBaseModel):
    """
    One line of the ledger.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/schema/core',
         'slot_usage': {'event_kind': {'name': 'event_kind', 'required': True},
                        'run_id': {'name': 'run_id', 'required': True},
                        'ts': {'name': 'ts', 'required': True},
                        'type': {'name': 'type', 'required': True}}})

    event_id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    run_id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    event_stage: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    type: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    event_kind: EventKind = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    ts: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    schema_version: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    doc_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    provenance: Optional[Any] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })
    payload: Optional[Any] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['EventEnvelope']} })


class Work(Node):
    """
    A published or preprinted scholarly work; identity is DOI plus OpenAlex work id.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema',
         'slot_usage': {'cited_in': {'multivalued': True, 'name': 'cited_in'},
                        'title': {'name': 'title', 'required': True}}})

    title: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    source_url: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    cited_in: Optional[list[str]] = Field(default=None, description="""Where in the graph's own record this item is cited; the biblio assessment criterion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    local_path: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    sha256: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['GroundingSpan', 'ManifestEntry', 'Work']} })
    disposition: Optional[ManifestDisposition] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ManifestEntry', 'Work']} })
    doi: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work', 'ExternalReference']} })
    openalex_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    arxiv_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    year: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    publication_date: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    venue: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    work_type: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    oa_status: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    oa_url: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    licence: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    abstract: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    authors_raw: Optional[list[str]] = Field(default=None, description="""The author strings as the resolver returned them, kept for the pilot's gold.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    references_total: Optional[int] = Field(default=None, description="""References in the resolver's reference list (Crossref).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    references_keyed: Optional[int] = Field(default=None, description="""Of those, references that carry a DOI and so became a Cites edge. The difference is the logged abstention for references the graph cannot key (DI-046).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    doc_kind: Optional[DocKind] = Field(default=None, description="""What sort of record this is, for an internal document (S-008 Part A). Absent on a published work, and that absence is the signal that it came from a publisher.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    repo: Optional[str] = Field(default=None, description="""The repository the document lives in, as the catalog's source names it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    commit: Optional[str] = Field(default=None, description="""That repository's HEAD when the document was cataloged.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    file_type: Optional[str] = Field(default=None, description="""The file extension, without the dot.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    first_heading: Optional[str] = Field(default=None, description="""The document's first heading, which is also its title when it has one.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    doc_date: Optional[str] = Field(default=None, description="""The date in the file name or the YAML frontmatter, never the file's mtime: a date invented from the disk orders the record by when it was last touched.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    headings: Optional[list[str]] = Field(default=None, description="""Every heading, in reading order. This is what the mention layer scans for an internal document (Part E). The body prose is never stored: the graph holds the path, the hashes and the headings, and the file is the text.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Work']} })
    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class ExternalReference(Node):
    """
    A citation target outside the graph, keyed by DOI or URL (`id` is `doi:<doi>`), so a pointer outside is a node with a key and never a bare string (fss-policy-kg practice, DI-046). No slot may be named `key` or `label`: the projection reserves both (squiddy.project).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema'})

    ref_kind: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ExternalReference']} })
    doi: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Work', 'ExternalReference']} })
    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class Cites(Edge):
    """
    (Work)-[:CITES]->(Work | ExternalReference), from a public reference list; typed with a CiTO intent, default citesForInformation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema'})

    cito_intent: Optional[CitoIntent] = Field(default=CitoIntent.citesForInformation, json_schema_extra = { "linkml_meta": {'domain_of': ['Cites'], 'ifabsent': 'string(citesForInformation)'} })
    raw_reference: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Cites']} })
    subject: str = Field(default=..., description="""The id of the source node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    object: str = Field(default=..., description="""The id of the target node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class Supersedes(Edge):
    """
    (Work)-[:SUPERSEDES]->(Work), with the mechanism named (DI-051).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema'})

    mechanism: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Supersedes']} })
    subject: str = Field(default=..., description="""The id of the source node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    object: str = Field(default=..., description="""The id of the target node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class Obligation(Node):
    """
    One sentence a document states as an obligation, prohibition, permission or recommendation, with its deontic force and the party it binds (fss-policy-kg Obligation). Declared here because the kit's base schema does not carry it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema',
         'slot_usage': {'text': {'name': 'text', 'required': True}}})

    text: str = Field(default=..., description="""The located text, verbatim from the parsed intermediate.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition', 'Conflict']} })
    force: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation']} })
    binds: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation']} })
    section_path: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition']} })
    page: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition']} })
    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class Definition(Node):
    """
    A defined term and its definition as one document states it (fss-policy-kg Definition). Two Definitions of one term in two documents are the raw material of a definitional-consistency finding.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema',
         'slot_usage': {'text': {'name': 'text', 'required': True}}})

    text: str = Field(default=..., description="""The located text, verbatim from the parsed intermediate.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition', 'Conflict']} })
    term: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Definition']} })
    section_path: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition']} })
    page: Optional[int] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition']} })
    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class Conflict(Node):
    """
    An adjudicated conflict between two Obligations or Definitions, with the rationale and the criteria version (fss-policy-kg CONFLICTS_WITH overlay, reified as a node so the verdict can carry its reason).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema',
         'slot_usage': {'text': {'name': 'text', 'required': True}}})

    text: str = Field(default=..., description="""The located text, verbatim from the parsed intermediate.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Obligation', 'Definition', 'Conflict']} })
    criteria_version: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Conflict']} })
    verdict: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Conflict']} })
    id: str = Field(default=..., description="""The readable, source-scoped key the graph minted at admission. It never changes and is never reused; a name is a property (DI-060, DI-062, OD-4 §3.1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'ManifestEntry']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class ConflictsWith(Edge):
    """
    (Conflict)-[:CONFLICTS_WITH]->(Obligation | Definition): one of the two statements a Conflict adjudicates (fss-policy-kg CONFLICTS_WITH). Declared here because the kit's base schema has no conflict edge.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema'})

    side: Optional[str] = Field(default=None, description="""a or b: which of the two conflicting statements this edge points at.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ConflictsWith']} })
    subject: str = Field(default=..., description="""The id of the source node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    object: str = Field(default=..., description="""The id of the target node.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Edge']} })
    prov_wasGeneratedBy: Optional[str] = Field(default=None, description="""Run id of the activity that made the assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasGeneratedBy'} })
    prov_wasDerivedFrom: Optional[str] = Field(default=None, description="""The manifest entry or source the assertion was derived from.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge'], 'slot_uri': 'prov:wasDerivedFrom'} })
    method: Optional[str] = Field(default=None, description="""How the assertion was made (manifest, crossref, openalex, github, human_ruling, ...).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    ruling_id: Optional[str] = Field(default=None, description="""The event id of the human ruling that authorized this assertion, when one did.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    asserted_at: Optional[str] = Field(default=None, description="""When the assertion was made, ISO 8601 UTC.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    status: Optional[AssertionStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    superseded_by: Optional[str] = Field(default=None, description="""The event id of the assertion that replaced this one. Never a deletion (DI-053, DI-064).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor: Optional[str] = Field(default=None, description="""The instrument that made an extracted assertion, as `<provider>:<alias asked for>` (`claude_cli_max_oauth:sonnet`). Absent on a deterministic assertion, and that absence is itself the signal.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_extractor_version: Optional[str] = Field(default=None, description="""The model id the client ACTUALLY RESOLVED the alias to, read from the CLI envelope of the call that made the assertion; never the alias (DI-023: recording an alias as the model is citing a document that quotes a statute as if it were the statute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_prompt_sha256: Optional[str] = Field(default=None, description="""The sha256 of the prompt template the extraction ran under; a prompt change is a new extractor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    prov_run_id: Optional[str] = Field(default=None, description="""The run id of the extraction that proposed this assertion (also the envelope's run_id).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })
    grounding_span: Optional[GroundingSpan] = Field(default=None, description="""Where in the source the harness located the text behind this assertion. Located and cut by the harness from the parsed intermediate, never quoted by the model (ai-readiness-kg's anchor contract, S-001 finding 2). A span the harness cannot locate is a failed extraction, never a stored assertion.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Node', 'Edge']} })


class AacpsPolicyDmGraph(ConfiguredBaseModel):
    """
    The graph as two lists, the shape of the node-link export.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://github.com/brockwebb/squiddy/graphs/aacps_policy_dm/schema',
         'tree_root': True})

    nodes: Optional[list[Node]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Aacps_policy_dmGraph']} })
    edges: Optional[list[Edge]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Aacps_policy_dmGraph']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
GroundingSpan.model_rebuild()
Node.model_rebuild()
Edge.model_rebuild()
ManifestEntry.model_rebuild()
EventEnvelope.model_rebuild()
Work.model_rebuild()
ExternalReference.model_rebuild()
Cites.model_rebuild()
Supersedes.model_rebuild()
Obligation.model_rebuild()
Definition.model_rebuild()
Conflict.model_rebuild()
ConflictsWith.model_rebuild()
AacpsPolicyDmGraph.model_rebuild()

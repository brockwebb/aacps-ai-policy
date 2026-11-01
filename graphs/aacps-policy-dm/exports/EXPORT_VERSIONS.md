# Export versions

One row per versioned export, derived by `squiddy.registers` from the release diff and the
artifact. A version missing from this table does not exist as far as the graph is concerned.

| Version | File | Date | sha256 (first 16) | Nodes / edges | Contents |
|---|---|---|---|---|---|
| **ap02_pilot_dm** | `aacps_policy_dm_graph_ap02_pilot_dm_2026-11-01.json` | 2026-11-01 | `9357ea87ebf3b124` | 62 / 30 | extraction ap02_pilot_dm: 1 document(s) committed after preview. Work 0 -> 46 (+46); Obligation 0 -> 15 (+15); ExternalReference 0 -> 1 (+1); StatedIn 0 -> 15 (+15); Cites 0 -> 13 (+13); Supersedes 0 -> 2 (+2). Round-trip verified; 63,064 bytes. |
| **ap02_pilot_model** | `aacps_policy_dm_graph_ap02_pilot_model_2026-11-01.json` | 2026-11-01 | `9057130a87ca786d` | 104 / 85 | extraction ap02_pilot_model: 1 document(s) committed after preview. Obligation 15 -> 49 (+34); Definition 0 -> 7 (+7); ExternalReference 1 -> 2 (+1); StatedIn 15 -> 56 (+41); Cites 13 -> 27 (+14). Round-trip verified; 142,601 bytes. |
| **ap02_extract_all_01** | `aacps_policy_dm_graph_ap02_extract_all_01_2026-11-01.json` | 2026-11-01 | `b9a64c7a0f1a737c` | 226 / 251 | squiddy extract --all ap02_extract_all: 10 documents committed Obligation 49 -> 140 (+91); ExternalReference 2 -> 29 (+27); Definition 7 -> 11 (+4); StatedIn 56 -> 151 (+95); Cites 27 -> 98 (+71). Round-trip verified; 357,809 bytes. |
| **ap02_extract_all_02** | `aacps_policy_dm_graph_ap02_extract_all_02_2026-11-01.json` | 2026-11-01 | `96c2829f6e7f62fe` | 458 / 503 | squiddy extract --all ap02_extract_all: 10 documents committed Obligation 140 -> 290 (+150); ExternalReference 29 -> 85 (+56); Definition 11 -> 37 (+26); StatedIn 151 -> 327 (+176); Cites 98 -> 174 (+76). Round-trip verified; 721,741 bytes. |
| **ap02_extract_all_03** | `aacps_policy_dm_graph_ap02_extract_all_03_2026-11-01.json` | 2026-11-01 | `bc48e87ac3ea2687` | 1,507 / 1,604 | squiddy extract --all ap02_extract_all: 10 documents committed Obligation 290 -> 1,072 (+782); ExternalReference 85 -> 250 (+165); Definition 37 -> 139 (+102); StatedIn 327 -> 1,211 (+884); Cites 174 -> 391 (+217). Round-trip verified; 2,435,813 bytes. |
| **ap02_extract_all_04** | `aacps_policy_dm_graph_ap02_extract_all_04_2026-11-01.json` | 2026-11-01 | `79f5c2b683bec688` | 1,711 / 1,817 | squiddy extract --all ap02_extract_all: the end of the pass Obligation 1,072 -> 1,217 (+145); ExternalReference 250 -> 265 (+15); Definition 139 -> 183 (+44); StatedIn 1,211 -> 1,400 (+189); Cites 391 -> 415 (+24). Round-trip verified; 2,813,514 bytes. |

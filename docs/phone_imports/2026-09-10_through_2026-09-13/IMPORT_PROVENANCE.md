# Phone Markdown import: September 10–13, 2026

This directory accounts for every Markdown file whose phone-exposed modified
time falls from `2026-09-10T00:00:00-04:00` through
`2026-09-13T23:59:59.999999999-04:00` in the Samsung phone's `Download`
directory.

The phone was connected as Samsung `SM-S936U` through MTP. Its mounted MTP
surface did not expose filesystem birth/creation time, so selection uses the
witnessed `time::modified` value. Dated filenames corroborate several records
but are not the selection authority.

The imported files are recovered design inputs and historical evidence. They
do not establish current TrueSystems runtime behavior. Executable code, passing
tests, current receipts, and the repository authority order remain controlling.
No retained file was edited or renamed. At the user's direction, three `-1`
copies were removed from this repository only after SHA-256 and `cmp` both
proved each was byte-identical to its retained unsuffixed counterpart. The
phone source was not changed. No file was promoted into a current contract.

| Phone-relative path | Modified time (America/New_York) | Bytes | SHA-256 | Repository disposition |
|---|---:|---:|---|---|
| `Download/README.md` | `2026-09-10 20:32:13 -0400` | 733 | `e12f5ee34e96946767a4933a769caed060768eae067471f9b7f60f58292d83ef` | Retained |
| `Download/README-1.md` | `2026-09-10 20:32:42 -0400` | 733 | `e12f5ee34e96946767a4933a769caed060768eae067471f9b7f60f58292d83ef` | Proven identical by `cmp`; redundant repository copy removed |
| `Download/TrueSystems_Cubic_Cluster_Investigation_2026-09-10.md` | `2026-09-10 20:32:46 -0400` | 12,819 | `1674590674cddf8fdceb12f7f19f844466779716a9372548c92e0129d1225066` | Retained |
| `Download/TrueSystems_Cubic_Cluster_Investigation_2026-09-10-1.md` | `2026-09-10 20:32:59 -0400` | 12,819 | `1674590674cddf8fdceb12f7f19f844466779716a9372548c92e0129d1225066` | Proven identical by `cmp`; redundant repository copy removed |
| `Download/TrueSystems_Provenance_Backplane_2026-09-11.md` | `2026-09-11 10:54:45 -0400` | 29,130 | `e4cbb7b89fe606521d7b510647276d93e0d4c5628b5dc4b63ca614c535014c23` | Retained |
| `Download/START_HERE_TrueSystems_Local_Harness_2026-09-11.md` | `2026-09-11 11:00:19 -0400` | 9,457 | `47420d17f2ca82ec335cc5939c444c422f200d599e5a54b5e897aab09de6bb19` | Retained |
| `Download/START_HERE_TrueSystems_Local_Harness_2026-09-11-1.md` | `2026-09-11 11:03:06 -0400` | 9,457 | `47420d17f2ca82ec335cc5939c444c422f200d599e5a54b5e897aab09de6bb19` | Proven identical by `cmp`; redundant repository copy removed |
| `Download/the_basement_multilevel_graph_report.md` | `2026-09-12 07:06:44 -0400` | 4,626 | `3bd3ad5be235964d2cd2c4dcb6e4c1827a397dd0060d390ab7da7ab3d2ab1cd4` | Retained |
| `Download/04_context_cloud_adjustments_and_traversal.md` | `2026-09-12 07:13:48 -0400` | 6,736 | `008ce46cb06e9a73ab0269912c403e7d11e0b26b952049e0775517f8f3156c1c` | Retained |
| `Download/object_bound_symbol_projection.md` | `2026-09-13 07:22:03 -0400` | 5,350 | `b93d4e442f6078d49e3a76c294597d20f3f30b80970253c87c87c0a55fe8067c` | Retained |

The two `README` records, two cubic-cluster records, and two local-harness
records form three byte-identical duplicate pairs. The table preserves the full
ten-record phone inventory; the repository retains seven unique byte streams.

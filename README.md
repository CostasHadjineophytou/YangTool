# YangTool
 A python tool that interprets yang modules and makes a diff between them.

"""
main.py - a yang inspector tool.

Function:
1) load and validate a .yang file with pyang
2) extract a small summary (module, namespace, containers, leaves+types)
3) print that summary in a readable format in the CLI

Run:
  py main._draft.py -p .\yang .\yang\example-base.yang
"""

"""
yang_compare.py - a compare tool that makes a diff.

Function:
Given two .yang files (old and new), validate both and compare only:
- container paths
- leaf paths (and their types)

Run:
  py yang_compare_draft.py -p .\yang .\yang\example-base.yang .\yang\example-base-v2.yang
"""

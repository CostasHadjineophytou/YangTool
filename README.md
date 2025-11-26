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

Also point to a directory after -p for pyang to add dependent modules to its context i.e.
  py .\main.py -p .\yang\cisco_dependencies .\yang\Cisco-IOS-XR-um-config-validation-cfg.yang
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

"""
yang_dependency.py - a tool that produces a yang module dependency tree.

Function:
1) load and validate a .yang from the web with pyang
2) Produce a dependency tree showing which modules are imports and transitive imports.

Run:
  py .\yang_dependency.py https://github.com/YangModels/yang/blob/main/vendor/cisco/xr/2531/Cisco-IOS-XR-um-config-validation-cfg.yang
"""

"""
yang_online.py - a tool that validates and summarises directly from raw github yang modules and produces a yang module dependency tree.

Note this is a good way to find dependencies if wanting to use local files.

Function:
1) load and validate a .yang from the web with pyang
2) extract a small summary (module, namespace, containers, leaves+types)
3) print that summary in a readable format in the CLI
4) Produce a dependency tree showing which modules are imports and transitive imports.

Run:
  py .\yang_online.py https://raw.githubusercontent.com/YangModels/yang/main/vendor/cisco/xr/2531/Cisco-IOS-XR-um-config-validation-cfg.yang
"""
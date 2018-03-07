# pkg_list
PKG list generator for PS4 pkg files by n1ghty
<br><br>
This file is based on
- *UnPKG rev 0x00000008 (public edition), (c) flatz*
- *Python SFO Parser by: Chris Kreager a.k.a LanThief*
<br><br>
This tool parses all pkg files in the specified directory/directories recursively and then generates an excel sheet from the parsed infos.

### Usage
`python pkg_list.py <paths to pkg directories>`  
<br>
e.g.:  
`python pkg_list.py "D:\PS4_pkgs"`  
or  
`python pkg_list.py "D:\PS4_pkgs" "E:\second_pkg_directory" "C:\third_pkg_directory"`  
or for current directory:  
`python pkg_list.py .`  
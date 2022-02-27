"""
Prune most unused assets in a sourcemod.
This file is meant to be used for final builds, where everything is ready and there's nothing else left to do.
----------------------------------------------------------------------------------
USER INSTRUCTIONS:
Extract these files into the root directory of your sourcemod (e.g. for sourcemods/MyMod, you put them in MyMod).
You also need VMFs placed into the mod directory; anywhere is fine so long as you edit the MAP_FOLDER line to refer to your folder.
These VMFs must be one-to-one with your .bsp files; any small change might mean something gets removed that shouldn't.

Above traverse_and_evaluate is a bunch of stuff you can configure; if your file structure is different or you don't want something pruned, change it there.
If you want to specify the root folder, use "~/" in the appropriate section.
Don't edit the imports.

To run, you will need to have Python 3 installed. (I have no idea about version so 3.9 is your safest bet).
Then, open a command prompt window, navigate to your mod's root directory and type 'python3 prune_unused_assets.py' without quotes.
You can also use your own method; whichever is easier.

This is by no means the be-all-end-all solution; we take some liberties here but we should be able to remove a majority of the clutter; the rest is up to you, the user.
Quickly play through your build to make sure nothing's out of place once you're done.

For the love of all that is your mod, please create a backup! I take no responsibility if my code somehow fucks up and irrevocably removes something critical to your mod!

----------------------------------------------------------------------------------

Created by arbabf, 2022. Code is released under an AGPL-3.0 licence if you acquired this file without reading the licence.
"""

#TODO: this is very slow. this needs to be optimised... and look less like something that was clobbered together

import os
from typing import TypeVar
import re
T = TypeVar('T')

EXTRA_FILES_MODELS = (".dx80.vtx", ".dx90.vtx", ".sw.vtx", ".phy", ".vvd", ".ani")
SKY_SIDES = ("bk", "dn", "ft", "lf", "rt", "up")

##
## something missing ingame? add the folder of whatever was removed here
##
MATERIALS_TO_NOT_CHECK = ("models/weapons"
                        "vgui", "particle", "decals", "hud",
                        "sprites", "effects", "envmap", "console", "overlays")

MODELS_TO_NOT_CHECK = ("gibs", "~/", "humans", "weapons", "cremator")

##
## does your mod use more or fewer extra texture types for your vmts (e.g. roughness)? add/remove where applicable
##
VMT_PARAMS = ("$basetexture", "$bumpmap", "$detail", "$phongwarptexture", "$selfillummask",
                "$basetexture2", "$blendmodulatetexture", "$bumpmap2", "%tooltexture", "$envmap",
                "$fallbackmaterial", "$hdrcompressedtexture", "$normalmap", "$dudvmap",
                "$refracttinttexture", "$bottommaterial", "$reflecttexure", "$refracttexture",
                "$selfillummask")
##
## change this according to your mod's file structure
##
MAP_FOLDER = "maps"
MATERIAL_FOLDER = "materials"
MODEL_FOLDER = "models"
SCENE_FOLDER = "scenes"
FGD_FOLDER = "fgd"


def traverse_and_evaluate() -> None:
    """
    Traverses our mod directory.
    Input: None; we take whatever's in the same directory as this file.
    Output: None. We can print to files to debug but this, by itself, does not return anything.
    May take a long time! This search is exhaustive, and many assets and large maps will slow down computation.
    """
    model_list: list[str] = []
    material_list: list[str] = []
    scene_list: list[str] = []
    sky_list: list[str] = []
    materials_to_search: list[str] = []
    models_to_search: list[str] = []
    scenes_to_search: list[str] = []
    unused_assets: list[str] = []
    used_assets: list[str] = []
    mdl_allow_root = "~/" not in MODELS_TO_NOT_CHECK
    mat_allow_root = "~/" not in MATERIALS_TO_NOT_CHECK
    rest_str = lambda x: " ".join(x[1:]).lower().strip("\"")    # easy lambda function to avoid repeating code
                                                                # also allows catching kvs with spaces in the v
    path_maps = os.walk(MAP_FOLDER if MAP_FOLDER != "~/" else "")
    path_mat = os.walk(MATERIAL_FOLDER if MATERIAL_FOLDER != "~/" else "")
    path_mod = os.walk(MODEL_FOLDER if MODEL_FOLDER != "~/" else "")
    path_scenes = os.walk(SCENE_FOLDER if SCENE_FOLDER != "~/" else "")
    path_fgd = os.walk(FGD_FOLDER if FGD_FOLDER != "~/" else "")

    stock_assets: list[str] = []
    check_against_stock_assets = lambda asset: binary_search(stock_assets, asset) != -1
    with open("hl2-ep1-ep2-lc.txt", "r") as valve:
        for line in valve:
            stock_assets.append(line.strip().replace("\\", "/"))
    stock_assets.sort()

    print("Scraping FGDs...")
    for p, _, files in path_fgd:
        for file in files:
            if file.endswith(".fgd"):
                print("Scraping {0}...".format(file))
                line_count = 0
                with open(os.path.join(p, file), 'r') as f:
                    for line in f:
                        if len(line) > 5:
                            line_count += 1
                            res = re.search(r'"models/.+\.mdl"', line) # "models/x.mdl" where x can be anything except blank
                            if res:
                                res = res.group(0).strip("\"")
                                model_list.append(res)
                                if os.path.isfile(res): # so we don't search stock assets, which obviously won't exist in a mod's filestructure (unless we overwrite it)
                                    tup = get_stuff_from_mdls(res)
                                    model_list.extend(tup[0])
                                    material_list.extend(tup[1])
                print("Finished scraping {0}. ({1} lines checked)".format(file, line_count))

    print("Scraping maps...")
    for p, _, files in path_maps:
        for file in files:
            if file.endswith(".vmf"):
                print("Scraping {0}...".format(file))
                line_count = 0
                # painfully search every line in the vmf to see what models and materials are used
                f = open(os.path.join(p, file))
                for line in f:
                    if len(line) > 5: # so we don't attempt to parse anything that isn't worth looking at
                        line_count += 1
                        l = line.strip().split(" ")
                        if len(l) <= 1:
                            continue
                        l[0] = l[0].strip("\"")
                        l[1] = rest_str(l)  # yes, this includes the directory path -
                                            # this means that cases such as humans/group01/male_07 and humans/group02/male_07 are treated differently
                                            # due to how valve stores their vmfs in kv format we can safely use this since keys cannot have spaces
                        if l[0] == "model" and l[1] not in model_list and l[1].endswith(".mdl"): # env_sprites use "model" so we filter this out
                            model_list.append(l[1])
                            if os.path.isfile(l[1]):
                                tup = get_stuff_from_mdls(l[1])
                                model_list.extend([x for x in tup[0] if x.startswith("models/")]) # stops the model that we're searching from making it in... twice
                                material_list.extend(tup[1])
                        elif (l[0] == "material" or l[0] == "texture") and not l[1].isdigit() and "".join([MATERIAL_FOLDER + "/", l[1], ".vmt"]) not in material_list: # we need the isdigit() for func_breakables that spill in, and "texture" for infodecal entities
                            material_list.append("".join([MATERIAL_FOLDER + "/", l[1], ".vmt"])) # materials by default don't have the .vmt extension in vmfs so we gotta add them (this helps later)
                        elif l[0] == "SceneFile" and l[1] not in scene_list:
                            scene_list.append(l[1])
                        elif l[0] == "skyname" and l[1] not in sky_list:
                            sky_list.append(l[1])
                f.close()
                print("Finished scraping {0}. ({1} lines checked)".format(file, line_count))
    for sky in sky_list:
        for side in SKY_SIDES:
            material_list.append("".join([MATERIAL_FOLDER, "/skybox/", sky, side, ".vmt"]))
    print("Gathering assets...")

    for p, _, files in path_mat:
        for file in files:
            if file.endswith(".vmt") and not (any(x in p.lower() for x in MATERIALS_TO_NOT_CHECK) or (p == MATERIAL_FOLDER and not mat_allow_root)):
                materials_to_search.append(os.path.join(p.lower(), file.lower()).replace("\\", "/"))
            elif any(x in p.lower() for x in MATERIALS_TO_NOT_CHECK):
                # *normally* we wouldn't add this, but there's a really obscure bug that happens here:
                # given some folder which we don't check (e.g. decals/), anything in it is also not checked, and thus not marked as used/unused
                # if another file that we do check, that gets marked as unused, contains a .vtf that is in said file that we don't check, that file
                # gets marked as unused, even though we don't want to see it removed
                # e.g. for a file decals/decal_cool.vmt that points to materials/cool.vtf, neither file is marked as used/unused
                # if we check a file materials/cool.vmt and that gets marked as unused, cool.vtf will also get marked as unused
                # therefore decal_cool.vmt points to a texture that gets unused and thus has a missing texture
                # this one line fixes that problem
                tex = os.path.join(p.lower(), file.lower()).replace("\\", "/")
                used_assets.append(tex)
                if tex.endswith(".vmt"):
                    used_assets = get_textures_from_vmts(tex, used_assets)

    for p, _, files in path_mod:
        for file in files:
            if file.endswith(".mdl") and not (any(x in p.lower() for x in MODELS_TO_NOT_CHECK) or (p == MODEL_FOLDER and not mdl_allow_root)):
                models_to_search.append(os.path.join(p.lower(), file.lower()).replace("\\", "/"))
            elif any(x in p.lower() for x in MODELS_TO_NOT_CHECK):
                mdl = os.path.join(p.lower(), file.lower()).replace("\\", "/")
                used_assets.append(mdl)
                tup = get_stuff_from_mdls(mdl)
                used_assets.extend(tup[0])
                for tex in tup[1]:
                    if tex.endswith(".vmt"):
                        used_assets = get_textures_from_vmts(tex, used_assets)
                        used_assets.append(tex)
    
    for p, _, files in path_scenes:
        for file in files:
            if file.endswith(".vcd"):
                scenes_to_search.append(os.path.join(p, file.lower()).replace("\\", "/"))
    print("Finished gathering assets.")
    model_list.sort()
    material_list.sort()
    scene_list.sort()

    print("Cross-checking for unused content...")
    for mat in materials_to_search:
        if binary_search(material_list, mat) == -1:
            unused_assets.append(mat)

    # this block of code attempts to get back textures that were pruned from unused assets but also exist in used assets or stock assets
    materials_in_game = materials_to_search
    materials_in_game.sort()
    unused_assets.sort()
    fast_remove(unused_assets, materials_in_game)
    for tex in materials_in_game:
        if tex.endswith(".vmt"):
            used_assets = get_textures_from_vmts(tex, used_assets)
            used_assets.append(tex)

    for ua in unused_assets:
        if check_against_stock_assets(ua):
            used_assets.append(ua)  # if we find a match, we're doing some sort of texture replacement. add this to used_assets
            if ua.endswith(".vmt"):
                used_assets = get_textures_from_vmts(ua, used_assets)
    
    stop = len(unused_assets)
    count = 0
    while count < stop:
        unused_assets = get_textures_from_vmts(unused_assets[count], unused_assets) # we're modifying the list repeatedly and as long as stuff still exists here
        count += 1                                                                  # we will check it, so appending vtfs means we will check them.
                                                                                    # we need to tell this code to stop after all the vmts have been checked.    

    used_assets.sort()
    fast_remove(used_assets, unused_assets)

    for mod in models_to_search:
        if binary_search(model_list, mod) == -1:
            unused_assets.append(mod)
            for efm in EXTRA_FILES_MODELS:
                unused_assets.append(mod.replace(".mdl", efm))

    for scene in scenes_to_search:
        if binary_search(scene_list, scene) == -1:
            unused_assets.append(scene)
        else:
            used_assets.append(scene)

    # final check once and for all! may take forever but at least we clean it all up
    used_assets.sort()
    unused_assets.sort()
    fast_remove(used_assets, unused_assets)
    #print_to_file("debug_used.txt", used_assets)
    #print_to_file("debug_unused.txt", unused_assets)
    print("Collated unused content.")
    print("Writing unused assets and removing them...")
    f = open("unused_assets.txt", "w")
    for ua in unused_assets:
        if os.path.isfile(ua):
            f.write("".join([ua, "\n"]))
            os.remove(ua)
    f.close()

def print_to_file(filename, lst):
    """
    Debug method. Prints whatever list you want to whatever file you want.
    """
    f = open(filename, "w")
    for elem in lst:
        if elem != '':
            f.write("".join([elem + "\n"]))

def get_textures_from_vmts(file: str, lst: list[str]) -> list[str]:
    """
    Gets textures from a VMT and returns the resultant list of textures from that one VMT.
    Input: VMT file, list to place our textures into.
    Output: List of textures.
    """
    vmt = open(file)
    for line in vmt:
        li = line.strip().replace("\t", " ").split(" ")
        if any(x in li[0].lower() for x in VMT_PARAMS): # in case someone writes $baseTexture or $BASEtexture, etc.
            lst.append("".join([MATERIAL_FOLDER + "/", li[-1].strip("\""), ".vtf"]).replace("\\", "/").lower()) # $detailscale, etc. params get added but we don't check for them
                                                                                                                # in case the user is insane and names files as numbers (e.g. 35.vtf)
                                                                                                                # later checks take care of this anyway
    vmt.close()
    return lst

def fast_remove(list1: list[str], list2: list[str]) -> list[str]:
    """
    O(n) remove.
    Requires that both lists be sorted, so the time complexity is actually O(nlogn) if used in conjunction.
    Input: list1 - the list with stuff you want removed, and list2 - the list you want to remove stuff *from*.
    Output: list2 with all removed assets as blanks.
    """
    i = 0
    j = 0
    while i < len(list1) and j < len(list2):
        if list1[i] == list2[j]:
            list2[j] = ""   # yes, i realise that this is not actually 'removing' the item from the list but removal requires traversing the list again, which
                            # increases time complexity, and that is not super fast which is the point of this function in the first place
                            # this method, in practice, is faster
            j += 1
        elif list1[i] < list2[j]:
            i += 1
        else: # list1[i] > list2[j]
            j += 1
    return list2

def binary_search(lst: list[T], thing: T) -> int:
    """
    Binary search. Simple.
    Input: Our list we want to search, and the thing we're searching for.
    Output: Index of element, or -1 if it doesn't exist.
    """
    start = 0
    end = len(lst)-1
    while start<=end:
        mid = (start+end)//2
        if lst[mid] == thing:
            return mid
        elif lst[mid] < thing:
            start = mid+1
        else:
            end = mid-1
    return -1

def get_stuff_from_mdls(filename: str) -> tuple[list[str], list[str]]:
    """
    Get important content (other models, textures) from a .mdl file.
    Input: Our .mdl file.
    Output: A tuple containing .mdls and .vmts, in that order.

    NB: Yes, we can look through .qc files and get the textures that way.
    But I don't expect anyone to supply .qc files and place them in the correct areas.
    That would, 1: constitute a lot of work, and 2: take up more space, which is
    counterintuitive to what I want to do here.
    """
    mdls = []
    vmts = []
    paths = []
    li = ""
    # Get last line. This has the good stuff.
    with open(filename, 'rb') as mdl:
        li = mdl.readline()
        cur_pos = mdl.tell()
        mdl.seek(0, os.SEEK_END)
        if mdl.tell() != cur_pos: # if we are already at the end of the file just keep what we have
            # if not we look for the last line
            mdl.seek(-2, os.SEEK_END)
            while mdl.read(1) != b'\n':
                mdl.seek(-2, os.SEEK_CUR)
            li = mdl.readline()
    spl_li = li.strip(b'\x00').split(b'\x00')

    index = len(spl_li) - 1 # going backwards is faster than going forwards
    while spl_li[index].endswith((b'\\', b'/')) or (spl_li[index].startswith((b'models\\', b'models/')) and not spl_li[index].endswith(b'.mdl')):
        paths.append("".join([MATERIAL_FOLDER + "/", spl_li[index].decode()]).replace("\\", "/"))
        index -= 1
    while spl_li[index] and spl_li[index].endswith(b'.mdl') or try_decode(spl_li[index]):
        elem = spl_li[index].decode()
        if elem.endswith('.mdl'):
            mdls.append(elem)
        if not index:
            break # we've reached the end of the list
        index -= 1
    for path in paths:
        for item in spl_li:
            if try_decode(item):
                item = item.decode()
            else:
                continue # whatever we have is gibberish
            if os.path.isfile("".join([path, item, ".vmt"]).lower()): # this is an O(n^2) computation but ultimately my goal here is to make things compact, not be fast
                vmts.append("".join([path, item, ".vmt"]).lower())
        if not path.endswith(("\\", "/")):
            vmts.append("".join([path, ".vmt"])) # add the path itself if it happens to be a proper vmt (cs:go props do this)
    return (mdls, vmts)

def try_decode(li: str) -> bool:
    """
    Try to decode something in UTF-8.
    Input: Our line.
    Output: Whether it is possible to decode it in UTF-8.
    """
    try:
        li.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return True

if __name__ == "__main__":
    traverse_and_evaluate()
    print("Done!")

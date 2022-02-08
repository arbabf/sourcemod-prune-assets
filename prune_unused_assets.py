"""
Prune most unused assets in a sourcemod.
This file is meant to be used for final builds, where everything is ready and there's nothing else left to do.
----------------------------------------------------------------------------------
USER INSTRUCTIONS:
This file goes into the root directory of your sourcemod (e.g. for sourcemods/MyMod, you put it in MyMod).
You also need VMFs placed into the mod directory; anywhere is fine so long as you edit the MAP_FOLDER line to refer to your folder.
These VMFs must be one-to-one with your .bsp files; any small change might mean something gets removed that shouldn't.

Above traverse_and_evaluate is a bunch of stuff you can configure; if your file structure is different or you don't want something pruned, change it there.
Don't edit the imports, though.

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
T = TypeVar('T')

EXTRA_FILES_MODELS = (".dx80.vtx", ".dx90.vtx", ".sw.vtx", ".phy", ".vvd", ".ani")
SKY_SIDES = ("bk", "dn", "ft", "lf", "rt", "up")

##
## something missing ingame? add the folder of whatever was removed here
##
MATERIALS_TO_NOT_CHECK = ("models", "models/weapons", "vgui", "particle",
                            "sprites", "effects", "envmap", "console", "composite", "building_template")
MODELS_TO_NOT_CHECK = ("weapons", "items", "gibs")

##
## does your mod use more or fewer extra texture types for your vmts (e.g. roughness)? add/remove where applicable
##
VMT_PARAMS = ("$basetexture", "$bumpmap", "$detail", "$phongwarptexture", "$selfillummask",
                "$basetexture2", "$blendmodulatetexture", "$bumpmap2", "%tooltexture", "$envmap",
                "$fallbackmaterial", "$hdrcompressedtexture", "$normalmap", "$dudvmap",
                "$refracttinttexture", "$bottommaterial", "$reflecttexure", "$refracttexture")
##
## change this according to your mod's file structure
##
MAP_FOLDER = "maps"
MATERIAL_FOLDER = "materials"
MODEL_FOLDER = "models"
MATERIAL_MODEL_FOLDER = "materials/models"
SCENE_FOLDER = "scenes"


def traverse_and_evaluate() -> None:
    """
    Traverses our mod directory.
    Input: None; we take whatever's in the same directory as this file.
    Output: All unused assets in a list of strings.
    CAUTION: may take a long time! This search is exhaustive, and many assets and large maps will slow down computation.
    """
    model_list: list[str] = []
    material_list: list[str] = []
    scene_list: list[str] = []
    sky_list: list[str] = []
    materials_to_search: list[str] = []
    models_to_search: list[str] = []
    materials_models_to_search: list[str] = []
    scenes_to_search: list[str] = []
    unused_assets: list[str] = []
    rest_str = lambda x: " ".join(x[1:]).lower().strip("\"")    # easy lambda function to avoid repeating code
                                                                # also allows catching kvs with spaces in the v
    path_maps = os.walk(MAP_FOLDER)
    path_mat = os.walk(MATERIAL_FOLDER)
    path_mod = os.walk(MODEL_FOLDER)
    path_mat_mod = os.walk(MATERIAL_MODEL_FOLDER)
    path_scenes = os.walk(SCENE_FOLDER)

    print("Scraping maps...")
    for p, _, files in path_maps:
        for file in files:
            if file.endswith(".vmf"):
                print("Scraping {0}...".format(file))
                line_count = 0
                # painfully search every line in the vmf to see what models and materials are used
                f = open(os.path.join(p, file))
                for line in f:
                    if len(line) > 5: # so we don't attempt to parse curly brackets or really anything that shouldn't be worth looking at
                        line_count += 1
                        l = line.strip().split(" ")
                        if len(l) <= 1:
                            continue
                        l[0] = l[0].strip("\"")
                        l[1] = rest_str(l)  # yes, this includes the directory path -
                                            # this means that cases such as humans/group01/male_07 and humans/group02/male_07 are treated differently
                                            # due to how valve stores their vmfs in kv format we can safely use this since keys cannot have spaces (very cool)
                        if l[0] == "model" and l[1] not in model_list:
                            model_list.append(l[1])
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
            if file.endswith(".vmt") and not any(x in p.lower() for x in MATERIALS_TO_NOT_CHECK):
                materials_to_search.append(os.path.join(p.lower(), file.lower().replace("\\", "/")))

    for p, _, files in path_mod:
        for file in files:
            if file.endswith(".mdl") and not any(x in p.lower() for x in MODELS_TO_NOT_CHECK):
                models_to_search.append(os.path.join(p.lower(), file.lower()).replace("\\", "/"))

    for p, _, files in path_mat_mod:
        for file in files:
            materials_models_to_search.append(os.path.join(p.replace("".join([MATERIAL_MODEL_FOLDER, "/"]), ""), file.lower()).replace("\\", "/"))
    
    for p, _, files in path_scenes:
        for file in files:
            scenes_to_search.append(os.path.join(p, file.lower()).replace("\\", "/"))
    print("Finished gathering assets.")
    model_list.sort()
    material_list.sort()
    scene_list.sort()

    print("Cross-checking for unused content...")
    for mat in materials_to_search:
        mat = mat.replace("\\", "/")
        if binary_search(material_list, mat) == -1:
            unused_assets.append(mat)

    # this block of code attempts to get back textures that were pruned from unused assets but also exist in used assets (e.g. detail textures)
    materials_in_game = materials_to_search
    for i in range(len(materials_in_game)):
        materials_in_game[i] = materials_in_game[i].replace("\\", "/")
    for i in range(len(unused_assets)):
        unused_assets[i] = unused_assets[i].replace("\\", "/")
    
    used_assets = []

    for asset in unused_assets:
        materials_in_game = remove_occ(materials_in_game, asset)

    for tex in materials_in_game:
        if tex.endswith(".vmt"):
            used_assets = get_textures_from_vmts(tex, used_assets)
        used_assets.append(tex)

    for modmat in materials_models_to_search:
        if modmat.endswith(".vmt"):
            used_assets = get_textures_from_vmts(modmat, used_assets)
            used_assets.append(modmat) # so textures for proppered buildings are kept

    for asset in used_assets:
        unused_assets = remove_occ(unused_assets, asset)

    stop = len(unused_assets)
    for count, val in enumerate(unused_assets):
        if count < stop:
            unused_assets = get_textures_from_vmts(val, unused_assets)  # we're modifying the list repeatedly and as long as stuff still exists here
                                                                        # we will check it, so appending vtfs means we will check them.
                                                                        # we need to tell this code to stop after all the vmts have been checked.
        else:
            break
        
    for mod in models_to_search:
        if binary_search(model_list, mod) == -1 and len(mod.split("/")) > 2: #i.e. don't take from the root models/ directory
                                                                            #(hack for rtb:r; if this is not rtb:r, edit accordingly)
            unused_assets.append(mod)
            for efm in EXTRA_FILES_MODELS:
                unused_assets.append(mod.replace(".mdl", efm))
            x = mod.replace(".mdl", "").split("/")[1:-1] # e.g. models/humans/alyx.mdl -> humans/alyx
            for modmat in materials_models_to_search:
                if "".join(x) in modmat:
                    unused_assets.append("".join([MATERIAL_MODEL_FOLDER, modmat])) # prune the textures that also appear with these models

    for scene in scenes_to_search:
        if binary_search(scene_list, scene) == -1:
            unused_assets.append(scene)
        else:
            used_assets.append(scene)

    # final check once and for all! takes forever but at least we clean it all up
    for asset in used_assets:
        unused_assets = remove_occ(unused_assets, asset)
    
    print("Collated unused content.")
    print("Writing unused assets and removing them...")
    f = open("unused_assets.txt", "w")
    for ua in unused_assets:
        if os.path.isfile(ua):
            f.write("".join([ua, "\n"]))
            os.remove(ua)
    f.close()

def remove_occ(lst: list[T], thing: T) -> list[T]:
    """
    Remove all occurrences of some value in a given list, then return the list.
    """
    return [val for val in lst if val != thing]

def print_to_file(filename, lst):
    """
    Debug method. Prints whatever list you want to whatever file you want.
    """
    f = open(filename, "w")
    for elem in lst:
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
        if any(x in li[0].lower() for x in VMT_PARAMS): # in case someone writes $baseTexture or $BASEtexture or $BaSeTeXtUrE
            lst.append("".join([MATERIAL_FOLDER + "/", li[-1].strip("\""), ".vtf"]).replace("\\", "/")) # $detailscale, etc. params get added but we don't check for them
                                                                                                        # in case the user is insane and names files as numbers (e.g. 35.vtf)
    vmt.close()
    return lst

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

if __name__ == "__main__":
    traverse_and_evaluate()
    print("Done!")

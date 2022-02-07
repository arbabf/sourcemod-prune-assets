# sourcemod-prune-assets
Prune most unused assets in a sourcemod.<br>
This file is meant to be used for final builds, where everything is ready and there's nothing else left to do.

## User Instructions:
This file goes into the root directory of your sourcemod (e.g. for sourcemods/MyMod, you put it in MyMod).<br>
You also need VMFs placed into the mod directory; anywhere is fine so long as you edit the MAP_FOLDER line to refer to your folder.<br>
These VMFs must be one-to-one with your .bsp files; any small change might mean something gets removed that shouldn't.

Above traverse_and_evaluate is a bunch of stuff you can configure; if your file structure is different or you don't want something pruned, change it there.<br>
Don't edit the imports, though.

To run, you will need to have Python 3 installed. (I have no idea about version so 3.9 is your safest bet).<br>
Then, open a command prompt window, navigate to your mod's root directory and type 'python3 prune_unused_assets.py' without quotes.<br>
You can also use your own method; whichever is easier.

This is by no means the be-all-end-all solution; we take some liberties here but we should be able to remove a majority of the clutter; the rest is up to you, the user.<br>
Quickly play through your build to make sure nothing's out of place once you're done.

For the love of all that is your mod, please create a backup! I take no responsibility if my code somehow fucks up and irrevocably removes something critical to your mod!<br>

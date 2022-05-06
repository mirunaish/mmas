"""
a script to create character-list.txt, a file later used by weights_script

@author miruna
"""

import io
from itertools import chain

from fontTools.ttLib import TTFont
from fontTools.unicode import Unicode

# i fished this font file from some system folder on my laptop
ttf = TTFont("DejaVuSansMono-Bold.ttf", 0, allowVID=0, ignoreDecompileErrors=True)


# for map; return first element of a tuple
def fnc(t):
    return t[0]


# create a list of all characters in the font
# i most likely copied this from stackoverflow
chars = chain.from_iterable([y + (Unicode[y[0]],) for y in x.cmap.items()] for x in ttf["cmap"].tables)
chars = list(map(fnc, chars))  # characters are returned as tuples of data and i only need the first element

# some characters appear in the list twice. only keep one copy. all characters are allowed now
result = []
for i in chars:
    if i not in result:
        result.append(i)
chars = result

print(len(chars))
chars = map(str, chars)  # turn the numerical codes into strings, so + " " works

with io.open('character_list.txt', 'w', encoding='utf-8') as f:
    for i in list(chars):
        f.write(i+" ")
    f.write("32")  # the code breaks if the last character in the file is a space

ttf.close()

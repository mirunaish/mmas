"""
a script to create character-list.txt, a file later used by weights_script

@author miruna
"""

import io
import unicodedata
from itertools import chain
from fontTools.ttLib import TTFont
from fontTools.unicode import Unicode

# i fished this font file from some system folder on my laptop
ttf = TTFont("consola.ttf", 0, allowVID=0, ignoreDecompileErrors=True)

# these categories contains *mostly* characters that don't take up a monospace space and that break the image
# spent a long time studying https://www.unicode.org/reports/tr44/#General_Category_Values
forbidden_categories = ["Mn", "Zs", "Zl", "Zp", "Cc", "Cf"]
forbidden_bidirectional = ["NSM", "WS", "B", "BN"]

# had to manually sift through all the characters to find these exceptions...
whitelist = [8432, 786, 1161, 8413, 1160]
blacklist = [734, 96]

# this is the script used when manually looking for exceptions.
# if the two |--| are not aligned the character should not be included
# weights = unicode
# for i in range(len(weights)):
#     for j in range(len(weights[i])):
#         print("\n" + str(weights[i][j]) + " : " + unicodedata.bidirectional(chr(weights[i][j])) + " / " + unicodedata.category(chr(weights[i][j])) + "\n    |\na" + chr(weights[i][j]) + "a |\n")
# print("done.")


# for map; return first element of a tuple
def fnc(t):
    return t[0]


# based on the hardcoded blacklists and whitelists
def allowed(ch):
    if ch in map(chr, whitelist):  # this map function turns all the character ids in the whitelist into unicode codes
        return 1
    if ch in map(chr, blacklist):
        return 0

    b1 = unicodedata.bidirectional(ch) not in forbidden_bidirectional
    b2 = unicodedata.category(ch) not in forbidden_categories

    return b1 and b2


# create a list of all characters in the font
# i most likely copied this from stackoverflow
chars = chain.from_iterable([y + (Unicode[y[0]],) for y in x.cmap.items()] for x in ttf["cmap"].tables)
chars = list(map(fnc, chars))  # characters are returned as tuples of data and i only need the first element

# some characters appear in the list twice. only keep one copy of allowed ones
result = []
for i in chars:
    if i not in result and allowed(chr(i)):
        result.append(i)
chars = result

print(len(chars))
chars = map(str, chars)  # turn the numerical codes into strings, so + " " works

with io.open('character-list.txt', 'w', encoding='utf-8') as f:
    for i in list(chars):
        f.write(i+" ")
    f.write("32")  # the code breaks if the last character in the file is a space

ttf.close()

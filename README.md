# MMAS
MultiMedia Art Station

## Scripts

### Image to MP3

Creates jazzy audio based on an image.

Take the values of all pixels for each channel, map them into notes, and turns them into a sound file; the three R, G,
and B sound files are then overlayed.

Each 0-255 value is mapped to a note-length combo. There are a total of 88 notes (A0-C8 including #ed notes) and 3
lengths (2, 4, 6), which means 264 combos total, so 8 notes of length 6 won't be used.
A white R255 G255 B255 pixel will be 3 C8 notes of length 6; line breaks are rests of length 4.

Gray-ish images tend to sound pretty bad with this conversion algorithm.

Files:
* stores temporary files in [working_folder](files/working_folder)

See also: [ImageToMp3](https://github.com/mirunaish/image-to-mp3)

### Asciify
Turns an image into a String and saves it to a text document.

Scales the image so that one pixel in the image maps to one 10x22 character, gets the value (*weight*) of the pixel, and
picks a random character from the array of characters with that value, which is imported from
[weights.txt](files/asciify/weights.txt). Appends this character to a string, then prints the string to a file.

Despite the name, the characters are Unicode. The range of values in normal ASCII characters is pretty narrow, but
unicode has more range of values and therefore results in a prettier final image. But many characters in unicode are
[non-spacing](#asciify-listcharacters-whitelist-and-blacklist), so some preprocessing of the character list is required.

The text is meant to be viewed in the Consola font.

Files:
* consola.ttf - the font file used to determine the weights of characters
* list_characters_script.py - helper script that lists the codes of all the characters defined in a font
* character_list.txt - the list of characters defined by the font
* weights_script.py - helper script that determines the weights of the characters
* weights.txt - arrays of characters sorted by weight. See [weights section](#weights)

### Ascheatfy
Turns an image into an image of characters. Can also convert videos or GIFs. Very similar to Asciify, except instead of
appending the character to a string, prints it to an image. It can use characters that don't take up a monospace space
in text, as it writes the character on the character image and pastes this on the result image.

The font used is DejaVu Sans Mono.

Files:
* DejaVuSansMono-Bold.ttf - the font file used to determine the weights of characters
* list_characters_script.py - helper script that lists the codes of all the characters defined in a font
* character_list.txt - the list of characters defined by the font
* weights_script.py - helper script that determines the weights of the characters
* weights.txt - arrays of characters sorted by weight. See [weights section](#weights)

## Implementation notes

### DynamicGUI
The GUI is split into two classes, GUI and DynamicGUI, primarily to avoid circular imports when scripts modify the
interface.

### Weights
The format of weights.txt is:
```
weight1: character1 character2 ...
weight2: character1 characteer2 ...
...
```
Weights are between 0 and 255. They are white on black, so bigger numbers represent characters with a greater area.

### Clearing status
A new thread is created every time a script tries to clear the status. If a script prints an error message and starts a
thread that waits for some time before clearing the script, any other status message written afterwards will be removed
by this thread. To prevent the new status message from being deleted, the threads waiting to clear the status are
stopped when the status is updated.

### smallify()
The resized picture is very small to keep the generated audio files from getting too long. Maximum resized image size
is 625 RGB pixels, corresponding to 625 notes of varying lengths. Even with this small size the audio is usually over 5
minutes long.

Math explanation:
Old area is x*y, new area must be 625; 
Both x and y are divided by sqrt(x*y/625); 
New area will be x*y = (x/sqrt(x*y/625))*(y/sqrt(x*y/625)) = x*y/(x*y/625) = 625; 

### get_true_weight(): find_lighter() amd find_darker()
Because unicode characters are not evenly distributed across weights, some weights are empty. If a pixel in the resized
image is a weight that has no characters, the closest character in weight must be found and substituted. This is
achieved by finding the immediate lighter weight with characters and the immediate darker weight with characters and to
pick the one that is closest, or a random one if they are equally far away.

### Asciify list_characters whitelist and blacklist
Because the asciify script creates text that is meant to be displayed in a monospaced font, any characters that don't
take up one full monospace space must be blacklisted. To determine which characters should be blacklisted, the script
determines the category they belong to, and checks it against the blacklisted categories. Categories which contain
mostly non-monospace characters are blacklisted, but there are exceptions. For completeness, these exceptions
(characters in blacklisted categories that do take up one full monospace space) are whitelisted.

The individual character blacklist and whitelist were created manually by looking through all the characters.

### Libraries / dependencies
* tkinter `pip install tkinter`
* pillow `pip install tkinter`
* cv2 `pip install cv2`
* pydub `pip install pydub`
* [tomita pysynth](https://mdoege.github.io/PySynth/)
* must have [ffmpeg](https://ffmpeg.org/download.html) installed and on the path

## Sources
* Documentation
  * https://docs.python.org/3.9/library/tkinter.ttk.html
* Library documentation
* StackOverflow
  * https://gist.github.com/SebOh/5d2438c7987591757a3591495720a5e7
  * https://stackoverflow.com/questions/7503567/python-how-i-can-get-gif-frames
  * https://stackoverflow.com/questions/53364769/get-frames-per-second-of-a-gif-in-python#53365469
  * others
* https://www.unicode.org/reports/tr44/#General_Category_Values
* A [CodeProject article](https://www.codeproject.com/Articles/1179876/Unicode-Art) about ascii images
* [ImageToMp3](https://github.com/mirunaish/image-to-mp3), submitted last application cycle
* CS10 (multithreading, resource locking)
* Suggestions made by my IDE (Pycharm)
## scPacker
**scPacker** is a python script that allows you to convert
PNG files to _tex.sc files, **\_tex.sc** files are specific files used by **Supercell** in their own game engine.

### How to use it ?
The basic usage to pack one file is:  

> python Main.py <filename\> -p <pixeltype\>

Example:  

> python Main.py ui_tex.png -p 0

----------

However if you want to pack multiple files use:  

> python Main.py <filename1\> <filename2\> ... -p <pixeltype1\> <pixeltype2\> ...

Example:  

> python Main.py ui\_tex.png ui\_tex\_.png -p 0 4

in this case ui\_tex.png will be packed using pixelformat 0 and ui\_tex\_.png using pixelformat 4.

**Warning**: You should set as many pixelformats as filenames you've set.

### Options
**scPacker** can also takes few optionals arguments which are:  

* `-lzma`: if this argument is specified tex.sc file will be compressed using lzma
* `-lzham`: if this argument is specified tex.sc file will be compressed using lzham
* `-zstd`: if this argument is specified tex.sc file will be compressed using zstandard
* `-header`: add Supercell header at the beginning of the compressed tex.sc file
* `-o`: optionnal output filename for the tex.sc file, if this argument isn't specified tex.sc file will be saved as <first\_packed\_filename\> + _tex.sc 
* `-s`: enable 32x32 block texture splitting, 32x32 block splitting is used in most of the original Supercell _tex.sc files

Command Example:
> python Main.py loading\_tex.png loading\_tex\_.png loading\_tex\_\_.png -p 0 4 6 -lzma -header -s -o afilename\_tex.sc

### How do i know which pixeltype to use if i want to pack an original texture ?
Let's take an example from an original \_tex.sc files. For this example we'll use loading\_tex.sc from Clash Royale.  
First we'll extract the .png textures using [Dumpsc](https://github.com/Galaxy1036/Dumpsc).  
Here is the console logs after extracting textures:  

![Image](/dumpsc_example.PNG)

According to the logs it seems that loading\_tex.png use pixelformat 0, loading\_tex\_.png use pixelformat 4 and loading\_tex\_\_.png use pixelformat 6.

Basically to re-pack these .png we'll use the following command:
> python Main.py loading_tex.png loading\_tex\_.png loading\_tex\_\_.png -p 0 4 6 <optionalsargs\>

### Dependencies
To install **scPacker** dependencies run the following command 

> python -m pip install -r requirements.txt

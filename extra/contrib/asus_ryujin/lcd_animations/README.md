# Local Armoury Crate animation assets

The Ryujin III Extreme animation preset refers to GIFs in this directory.  The
GIFs are not included in this repository.

If Armoury Crate is installed locally, search its installation directory for
`iii_ex_st*.gif`.  A typical Windows installation starts at:

```
C:\Program Files (x86)\ASUS\ArmouryDevice
```

The files are normally below an
`lcd\common\35\hw_monitor\share_theme\bg_anim` directory.  The intermediate
version directory can change between releases.

Copy the files here while preserving their `horiz/` and `vert/` directories.
For example, the `ryujin_extreme_st4.json` preset expects:

```
extra/contrib/asus_ryujin/lcd_animations/horiz/iii_ex_st4.gif
```

The `.gitignore` file keeps copied assets out of Git.  Do not commit or
redistribute them without permission from the rights holder.

# Bedtime you little shit
Byls automatically shuts down your computer at a scheduled time each night, helping you stick to an earlier bedtime.
Licensed under GPLv3

# How to use
When you open the app and click "I need to sleep early tonight." you have to select the hour and the minute for the scheduled shutdown (default = 23:00). Once you press okay you'll be warned that the program will shutdown your computer and might cause file corruption if you have something running. You get notifications 10 minutes, 5 minutes and 1 minute before shutdown. If you know you need more time you can click the tray icon on your panel and cancel the shutdown entirely.

# Releases
For newer Fedora/Arch based distributions (glibc 2.43+) you can use the pre-compiled executable. For relatively older installations/Debian based  distributions you must compile from source using pyinstaller!

# Build from source
Install pyinstaller if you don't have it:
```pip install pyinstaller```
Then build:
```pyinstaller --name Byls --windowed --onefile main.py```

# Run from source
To start the program without a binary run ```pip install -r requirements.txt``` to install dependencies and then ```python main.py``` to start Byls.

# The "why"
This project was created because of a personal problem I had. After I participated in the GMTK Game Jam 2026 my already chaotic sleep schedule broke completely. I casually found myself awake at 4-5 AM. That made me feel really bad and because of that bad feeling I had even worse sleep quality. I knew this wasn't right so started this project. I wanted a program that forces me to shut down my computer because most of the time I stayed awake was because I didn't have the will power to shut it down myself. I just stared at my empty desktop for 30 minutes then I clicked something and repeated this loop until I couldn't stay up anymore. The core issue was that I naturally distrust programs that can turn my computer off randomly so I was basically forced to make my own. I needed a way to cancel/delay the shutdown so it doesn't corrupt my important project files for other things. And here we are 3 weeks later on GitHub, fully open source for everyone to use, fork and redistribute.

# AI
Current version(s) of Byls have parts of code written by generative AI. I'll fix that in the future.

# Operating System support:
- Linux: Fully supported
- Windows: Currently unsupported (Port W.I.P.)
- Mac: Unsupported

# Tested Linux distro list
- Fedora (KDE Plasma), pre-compiled binary
- Nobara (KDE Plasma), pre-compiled binary
- ZorinOS (Gnome), compiled on client

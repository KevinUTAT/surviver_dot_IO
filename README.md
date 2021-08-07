[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
# surviver_dot_IO
A "helper" to the surviv.io game \
![alt text](https://github.com/KevinUTAT/surviver_dot_IO/blob/master/Annotation%202020-09-20%20133655.png?raw=true)
This program auto fires at other players in game. \
So far the AI is simple, the program will pick a player at random, and fires at the center location of it. \
For now, the AI do not account for obstacles and the speed of witch plyers are moving. \
\
The objects tracking model is a YOLOv5 implementation made by Ultralytics LLC \
Small changes are made to the model to fit my project.\
You can find the original model here: \
https://github.com/ultralytics/yolov5

SORT is used for target tracking, and its original repo is here: \
https://github.com/abewley/sort
## Change log
### 2021-8-7:
**Tree** as a detection class is finally added. \
When deciding which target to shot, the program will now skip the target that don't have a clear shot due to tree in between. \
A visual tester is also added under */tester*. This program can replace a pre recorded game capture and visualize your mouse actions.
### 2021-5-23:
**Active Data set has since move to a separated repo [here](https://github.com/KevinUTAT/active_data_set)** \
This update are just some house cleaning, no feature updated. Some cleaning is needed for obstacles avoidance feature in the near future.
- Update for use of troch 1.7
- Update YOLOv5 implementation to v5.0
### 2020-11-22:
Introducing **Active Data Set**: \
This is a seperated GUI program that manage training data and process data generated by active learning. \
The program is still in early statge of development with very limited testing, please post in *issues* if you encounter any bugs. \
ADS also consolidates tools before so its all in one place. \
Here is a lsit of feartures:
 - Data visulization. With images and bonding boxes.
 - Data editing:
   - Modify target class
   - Delet targets
   - Delet images
   - Modify BBox positions
 - Auto rename
 - Training / validation split
 - Run active learning
### 2020-10-11:
Major cleaning up in tracking data structure *tracking_list*:
- *tracking_list* is updated every frame
- Only the vision thread (Main thread) modify it
- Synced with AI thread so AI thread only run when the list is updated with all the targets in a frame through a CV
- The list is cleaned every frame so it only contains active targets of the frame
### 2020-10-03:
Auto termination. When a game round end (when the Battle Results are shown), the program will terminate. \
Be sure to restart it if you are to play again.
### 2020-09-20:
Implementing defelcting shooting: Leading the target if it's moving relitive to you. \
In my limited testing, it dose seems to improve accuracy. Becasue this will taking account \
the time it takes for bullet to travel and more importantly, the response time of inferencing.
### 2020-09-12:
Apply SORT real time tracker. \
This allows targets to be identified across multiple frames. \
This is important because now we know wehther a Player in this frame is the same player from last frame, \
this allows us to calculate player's speed and heading later on and many other posibilities.
### 2020-08-02:
Main thread(target acquiring) and AI thread(firing) is now synced using a conditional variable. \
This slightly improve the reaction time and fix the bug of AI thread being overwhelmed by amount of targets.
### 2020-07-30:
- Upgrating to YOLOv5
- New screen capture mechanism (mss) \
\
With the two new upgrates, the program now is able to update aiming at about 5Hz (Tested on a RTX2070 Max-Q) \
and shown to be enough for game play (idealy, 10Hz would be nice) \
In my test, the program will still not get me to winning but it did scored several kil_ls ;)
### 2020-07-11:
First attempt of auto firing. Not very good due to 0.5s lag, still very interesting to play. \
Once you entered a game session, run:

### 2020-07-09: 
Add screen capture into the model detection source. \
The model originally accept still images, video files and \
video stream from IP or webcams. \
But the game data is none of those. \
So we will import the game data as screen capture witch is similar to a web stream. \
The LoadStreams class can be modified to accept this.
### 2020-07-08: 
Set up the tracking model. \
Import the model from the original author, \
making minor changers for data set of class of 1 and \
more agrassive learning rate because our target is going to be \
man made carton objects.

## Download pre-trained weights
Weights trained on 500+ images, Not the best yet, but surely usable: \
https://drive.google.com/file/d/1eh_syn9H7KijcB6zEY3bO020aTSdEgpX/view?usp=sharing \
Put it under weights/

## Instruction
1. Clone the repo
   ```
   git clone https://github.com/KevinUTAT/surviver_dot_IO.git
   ```
2. Download weight file and put it under *weights*
3. Install all the dependency by:
   ```
   pip install -r requirements.txt
   ```
   If get error due to lack of packge during run, please install them as my list might not cover it all. \
   Reconmend using Conda
4. Launch your game.
5. Run the program:
   ```
   python play_game.py
   ```
tips: If you are experencing long reaction time (latency), try lower your display resolution. 

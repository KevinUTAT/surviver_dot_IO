# surviver_dot_IO
A "helper" to the surviv.io game \
![alt text](https://github.com/KevinUTAT/surviver_dot_IO/blob/master/Untitled.png?raw=true)
The objects tracking model is a YOLOv3 implementation made by Ultralytics LLC \
Small changes are made to the model to fit my project.\
You can find the original model here: \
https://github.com/roboflow-ai/yolov3  
## Change log
### 2020-07-11:
First attempt of auto firing. Not very good due to 0.5s lag, still very interesting to play. \
Once you entered a game session, run:
```
cd vision
python .\play_game.py --source screen
```
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

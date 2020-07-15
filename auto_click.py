import pyautogui
import time

if __name__ == '__main__':
    center_screen = (pyautogui.size()[0]/2 , pyautogui.size()[1]/2)
    while True:
        pyautogui.mouseDown(x=int(center_screen[0] + 100), y=int(center_screen[1] + 100))
        time.sleep(0.5)
        pyautogui.mouseUp()
        time.sleep(1)
        pyautogui.mouseDown(x=int(center_screen[0] + 100), y=int(center_screen[1] - 100))
        time.sleep(0.5)
        pyautogui.mouseUp()
        time.sleep(1)
        pyautogui.mouseDown(x=int(center_screen[0] - 100), y=int(center_screen[1] - 100))
        time.sleep(0.5)
        pyautogui.mouseUp()
        time.sleep(1)
        pyautogui.mouseDown(x=int(center_screen[0] - 100), y=int(center_screen[1] + 100))
        time.sleep(0.5)
        pyautogui.mouseUp()
        time.sleep(1)
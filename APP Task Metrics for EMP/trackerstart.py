
import contextlib
import logging
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets,uic
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QDate, QTime, QDateTime, Qt,QTimer
from PyQt5.QtCore import QSize
import os
import config
from jsonhandler import Jsonopr
import schedule
import time
from PyQt5.QtGui import QPixmap,QImage,QColor
import threading
import datetime
from PIL import Image
import requests
import requests

import pyscreenshot
import cv2

from pynput.keyboard import Key, Listener
from pynput.mouse import Listener
from pynput import keyboard
from loguru import logger

json_handler = Jsonopr()

click_Mouse=0
click_key=0
is_paused = False

# ------------------------------------------
def on_click(x, y, button, pressed):
    """Track mouse clicks during tracking."""
    if pressed:
        global click_Mouse
        if config.key_mouse_event:
            click_Mouse += 1
            logger.debug(f"🖱️  Mouse Click #{click_Mouse} at ({x}, {y}) - Button: {button}")

def on_press(key):
    """Track keyboard key presses during tracking."""
    global click_key
    if config.key_mouse_event:
        click_key += 1
        try:
            logger.debug(f"⌨️  Key Press #{click_key} - Key: {key.char if hasattr(key, 'char') else key}")
        except:
            logger.debug(f"⌨️  Key Press #{click_key} - Special Key: {key}")

def start():
    key_listener = keyboard.Listener(on_press=on_press)
    key_listener.start()

    with Listener(on_click=on_click) as listener:
        listener.join()

t1 = threading.Thread(target=start)
t1.start()

def startT():
    global is_paused,hh,mm,ss 
    hh = 0
    mm = 0
    ss = 0
    while True:
        schedule.run_pending()
        time.sleep(1)
        ss = ss+1
        if(ss>=59):
            ss = 0
            mm = mm+1
        if (mm>=59):
            ss=0
            mm=0
            hh=hh+1
        if is_paused:
            break

# -create Class----------------------------------
class StartTracker(QtWidgets.QMainWindow):
    def __init__(self):
        super(StartTracker, self).__init__()
        uic.loadUi('./ui/tracker_page.ui', self)
        self.setWindowTitle("SkyTracker - Active Session")
        self.show()
        
        # Initialize tracking counters for this session
        self.session_mouse_clicks = 0
        self.session_key_presses = 0
        self.last_send_mouse = 0
        self.last_send_key = 0
        
        # Status tracking
        self.is_online = True  # Track online/offline status
        self.total_session_mouse = 0  # Accumulate total
        self.total_session_keys = 0   # Accumulate total
        
        # ------------------------toggle button----------------
        self.track = self.findChild(QCheckBox,"btntrack")
        self.logoutbtn = self.findChild(QPushButton,"btnlogout")
        
        # self.track.isChecked(True)
        self.track.clicked.connect(self.on_pause_resume)
        self.logoutbtn.clicked.connect(self.on_logout_with_data)
        
        # Status label
        self.status_label = self.findChild(QLabel, "status") or self.findChild(QLabel, "txtselectedtask")
        
        # ---------------------project_task Back btn--------------------
        b1 = self.findChild(QPushButton,"b1")   #for back
        b2 = self.findChild(QLabel,"txtselectedtask_2")

        self.datas = json_handler.redjson(config.USERDB)
        self.taskdata = json_handler.redjson(config.TASKDB)
        current_time = datetime.date.today()
        
        if len(self.taskdata)>=0:
            for i in range(len(self.taskdata)):
                if self.taskdata[i]["tid"] == self.datas["selected_project"]["task"]["id"] and self.taskdata[i]["current_time"] != str(current_time):
                    self.taskdata[i]["current_time"]=str(current_time)
                    self.taskdata[i]["todaysession"]="00:00:00"
                    json_handler.updatejson(config.TASKDB,self.taskdata)
                    break
        

        b1.setText("Project: "+self.datas["selected_project"]["project"]["pname"])
        b2.setText("Task: "+self.datas["selected_project"]["task"]["tname"])
        b1.clicked.connect(self.goback)

        self.hhc = self.findChild(QLabel,"hhc")
        self.mmc = self.findChild(QLabel,"mmc")
        self.hhc.setText(str(self.datas["selected_project"]["task"]["tduration"]*8))
        self.mmc.setText(str(00))

        # ---- show the last screen_short...........................
        screen_short = self.findChild(QLabel,"txtscreenshort")  ########## need to add condition....
        
        # Check if converted image exists, display placeholder if not
        if os.path.exists(config.CONVERTIMG):
            pixmap = QPixmap(config.CONVERTIMG)
        else:
            logger.warning(f"Screenshot file not found: {config.CONVERTIMG}, using placeholder")
            # Create a placeholder image (blank white image)
            pixmap = QPixmap(599, 250)
            pixmap.fill(QColor(200, 200, 200))  # Light gray placeholder
        
        screen_short.setPixmap(pixmap)
        self.show()
        
        # ------last screen short date and time---------
        path = config.CONVERTIMG
        if os.path.exists(path):
            try:
                ti_m = os.path.getmtime(path)  # elapsed since EPOCH in float
                m_ti = time.ctime(ti_m)     #Converting the time in seconds to a timestamp
            except Exception as e:
                logger.error(f"Failed to get file modification time: {e}")
                m_ti = time.ctime()  # Current time as fallback
        else:
            logger.warning(f"Screenshot file not found when getting time: {path}")
            m_ti = time.ctime()  # Use current time as fallback
            
        self.date = self.findChild(QLabel,"txtdate")
        self.time = self.findChild(QLabel,"txttime")
        self.date.setText(str(m_ti[:10]))
        self.time.setText(str(m_ti[10:16]))

        # Set initial status
        self.update_status_display("🟢 Online")
    
        global is_paused,click_key,click_Mouse
        click_Mouse=0
        click_key=0
        is_paused = False
        self.t1 = threading.Thread(target=startT)
        self.t1.start()

    def update_status_display(self, status_text):
        """Update tracking status display."""
        try:
            status_label = self.findChild(QLabel, "status")
            if status_label:
                status_label.setText(status_text)
                status_label.setStyleSheet("color: green; font-weight: bold;")
        except:
            pass
        logger.info(f"Status: {status_text}")

    def on_pause_resume(self):
        """Handle pause/resume (offline/online) toggle."""
        global is_paused, hh, mm, ss
        
        if self.track.isChecked():
            # PAUSE - Going Offline
            config.key_mouse_event = False
            config.update_login_status("IL")  # Idle/Offline
            self.is_online = False
            
            logger.info(f"❌ TRACKER PAUSED - Offline Mode")
            logger.info(f"📊 Session Data Saved: Mouse: {click_Mouse}, Keys: {click_key}")
            
            with contextlib.suppress(Exception):
                is_paused = True
                self.t1.join()
            
            self.update_status_display("⭕ Paused (Offline)")
            
            # Show notification
            QMessageBox.information(self, "Tracking Paused", 
                                  "Tracking paused. Click the button again to resume.\n"
                                  "Your session data is saved.")
        else:
            # RESUME - Going Online
            config.key_mouse_event = True
            config.update_login_status("ON")
            self.is_online = True
            
            logger.info(f"✅ TRACKER RESUMED - Online Mode")
            logger.info(f"📊 Continuing with accumulated data...")
            
            is_paused = False
            self.t1 = threading.Thread(target=startT)
            self.t1.start()
            
            self.update_status_display("🟢 Online")
            
            # Show notification
            QMessageBox.information(self, "Tracking Resumed", 
                                  "Tracking resumed.\n"
                                  "Session data continues from where it stopped.")
        
        hh = 0
        mm = 0
        ss = 0

    def on_logout_with_data(self):
        """Logout and send all accumulated activity data."""
        global click_Mouse, click_key
        
        # Confirm logout
        reply = QMessageBox.question(self, "Logout", 
                                    "Are you sure you want to logout?\n"
                                    "All your tracking data will be saved to your profile.",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            logger.info("User cancelled logout")
            return
        
        logger.info("🔴 LOGOUT INITIATED - Sending final data to server")
        
        # First, pause tracking
        if not self.track.isChecked():
            self.track.setChecked(True)
            self.on_pause_resume()
        
        try:
            # Send final accumulated data to server
            self.send_final_activity_data()
            logger.info("✅ Final activity data sent to server")
        except Exception as e:
            logger.error(f"Error sending final data: {e}")
        
        try:
            # Save final data locally
            datas = json_handler.redjson(config.USERDB)
            datas["selected_project"] = {}
            datas["final_mouse_clicks"] = click_Mouse
            datas["final_keyboard_presses"] = click_key
            json_handler.updatejson(config.USERDB, datas)
            logger.info("✅ Final data saved locally")
        except Exception as e:
            logger.error(f"Error saving local data: {e}")
        
        # Update login status
        config.update_login_status("OFF")
        
        logger.info(f"📊 Session Summary:")
        logger.info(f"   🖱️  Total Mouse Clicks: {click_Mouse}")
        logger.info(f"   ⌨️  Total Keyboard Presses: {click_key}")
        logger.info("🔴 User Logged Out")
        
        # Return to login
        self.hide()
        import mainapp
        self.win = mainapp.login()

    def send_final_activity_data(self):
        """Send accumulated activity data before logout."""
        global click_Mouse, click_key
        
        try:
            taskdata = json_handler.redjson(config.TASKDB)
            t_data = next((d for d in taskdata if d['tid'] == self.datas["selected_project"]["task"]["id"]), {})
            
            # Send total accumulated clicks/presses
            final_payload = {
                "loginid": self.datas["user"]["id"],
                "projectid": t_data.get("pid"),
                "taskid": t_data.get("tid"),
                "img": "img",
                "cs": t_data.get("currentsession", "00:00:00"),
                "tds": t_data.get("todaysession", "00:00:00"),
                "tos": t_data.get("totalsession", "00:00:00"),
                "mouseclick": click_Mouse,       # Total accumulated
                "keyboardclick": click_key,       # Total accumulated
                "is_final": True                 # Mark as final send
            }
            
            logger.info(f"📤 Sending final data: Mouse: {click_Mouse}, Keys: {click_key}")
            
            url = config.HOSTURL + config.SCREENSHOTURL
            files = []
            
            # Send without screenshot on final
            if os.path.exists(config.CONVERTIMG):
                files = [('img', ('screenshot.png', open(config.CONVERTIMG, 'rb'), 'image/png'))]
            
            headers = {}
            response = requests.request("POST", url, headers=headers, data=final_payload, files=files)
            
            if response.status_code == 200:
                logger.info(f"✅ Final data accepted by server: {response.text}")
            else:
                logger.warning(f"⚠️  Server response: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error in send_final_activity_data: {e}", exc_info=True)

    def ActionLogout(self):
        """Deprecated - use on_logout_with_data instead."""
        logger.warning("ActionLogout called - redirecting to on_logout_with_data")
        self.on_logout_with_data() 


#   --sceenshort...........
    def capture(self):
        """Capture screenshot and webcam image."""
        with contextlib.suppress(Exception):
            logger.debug("Starting screenshot capture")
            
            # Ensure screenshot directory exists
            os.makedirs(os.path.dirname(config.SCREENSHOT), exist_ok=True)
            os.makedirs(os.path.dirname(config.FACESHOT), exist_ok=True)
            os.makedirs(os.path.dirname(config.CONVERTIMG), exist_ok=True)
            
            # --Take a screenshot--
            time.sleep(0.5)
            # To capture the screen
            image = pyscreenshot.grab()
            # To save the screenshot
            image.save(config.SCREENSHOT)
            logger.info("Screenshot saved successfully")
    #   --get face..........   
            camera_port = 0
            camera = cv2.VideoCapture(camera_port)
            time.sleep(0.5)  # If you don't wait, the image will be dark
            return_value, image = camera.read()
            cv2.imwrite(config.FACESHOT, image)
            logger.info("Webcam image saved successfully")
    # ------------------------------------------------------------------
            img = cv2.imread(config.FACESHOT, cv2.IMREAD_UNCHANGED)
            width = 200
            height = 200
            dim = (width, height)
            # resize image
            resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
            cv2.imwrite(config.FACESHOT, resized)
            cv2.destroyAllWindows()
            logger.info("Image resized successfully")

   # --show the sceent shortframe------------------------------------------

    def shortframe(self):
        screen_short = self.findChild(QLabel,"txtscreenshort")
        
        # Check if converted image exists
        if os.path.exists(config.CONVERTIMG):
            pixmap = QPixmap(config.CONVERTIMG)
        else:
            logger.debug(f"Screenshot not found: {config.CONVERTIMG}, using placeholder")
            # Create a placeholder image (blank gray image)
            pixmap = QPixmap(599, 250)
            pixmap.fill(QColor(200, 200, 200))  # Light gray placeholder
            
        screen_short.setPixmap(pixmap)
        self.show()
# ---- Show the img Time and Date......     
    def img_td(self):
        path = config.CONVERTIMG     # Path to the file/directory
        
        # Handle missing file gracefully
        if not os.path.exists(path):
            logger.warning(f"Screenshot file not found: {path}")
            self.m_ti1 = time.ctime()
        else:
            try:
                ti_m = os.path.getmtime(path)  # elapsed since EPOCH in float
                self.m_ti1 = time.ctime(ti_m)  # Converting the time in seconds to a timestamp
            except Exception as e:
                logger.error(f"Failed to get file modification time: {e}")
                self.m_ti1 = time.ctime()
        
        self.date = self.findChild(QLabel,"txtdate")
        self.time = self.findChild(QLabel,"txttime")
        self.date.setText(str(self.m_ti1[:10]))
        self.time.setText(str(self.m_ti1[10:16]))
        return self.m_ti1

    #   --ramdom time_captu.....        
    def time_captu(self):
        """Capture screenshot and send activity data to server (only if online)."""
        global click_Mouse, click_key
        
        # Skip if tracker is paused
        if not config.key_mouse_event:
            logger.debug("⭕ Tracker paused - skipping data send")
            return
        
        try:
            self.capture()
            
            # Check if files exist before opening them
            if not os.path.exists(config.SCREENSHOT):
                logger.warning(f"Screenshot not found: {config.SCREENSHOT}")
                return
            if not os.path.exists(config.FACESHOT):
                logger.warning(f"Faceshot not found: {config.FACESHOT}")
                return
            
            img1 = Image.open(config.SCREENSHOT)
            img2 = Image.open(config.FACESHOT).convert("RGBA")
            img1.paste(img2, (0,0), mask = img2)
            img1 = img1.resize((599,250))
            img1.save(config.CONVERTIMG, format="png")
            self.shortframe()
            datetime_d = self.img_td()
            logger.info("📸 Screenshot captured successfully")
        except Exception as e:
            logger.error(f"Error in screenshot capture: {e}", exc_info=True)
            return

        try:
            # Get tracking data
            taskdata = json_handler.redjson(config.TASKDB)
            t_data = next((d for d in taskdata if d['tid'] == self.datas["selected_project"]["task"]["id"]), {})

            # Calculate delta (new clicks/presses since last send)
            delta_mouse = click_Mouse - self.last_send_mouse
            delta_key = click_key - self.last_send_key
            
            logger.info(f"📊 Activity Stats - Total Mouse: {click_Mouse}, Total Keys: {click_key}")
            logger.info(f"📈 Delta Since Last Send - Mouse: {delta_mouse} (+), Keys: {delta_key} (+)")
            
            # Prepare tracking payload with mouse and keyboard activity
            payload = {
                "loginid": self.datas["user"]["id"],
                "projectid": t_data.get("pid"),
                "taskid": t_data.get("tid"),
                "img": "img",
                "cs": t_data.get("currentsession", "00:00:00"),
                "tds": t_data.get("todaysession", "00:00:00"),
                "tos": t_data.get("totalsession", "00:00:00"),
                "mouseclick": delta_mouse,  # Send only the delta
                "keyboardclick": delta_key  # Send only the delta
            }
            
            logger.debug(f"Sending tracking data: {payload}")
            
            url = config.HOSTURL + config.SCREENSHOTURL
            files = [
                ('img', ('screenshot.png', open(config.CONVERTIMG, 'rb'), 'image/png'))
            ]
            headers = {}
            response = requests.request("POST", url, headers=headers, data=payload, files=files)
            
            logger.info(f"✓ Server Response: {response.status_code}")
            logger.debug(f"Server Message: {response.text}")
            
            # Update last sent counters
            if response.status_code == 200:
                self.last_send_mouse = click_Mouse
                self.last_send_key = click_key
                logger.info("✅ Activity data sent successfully and counters updated")
                
        except Exception as e:
            logger.error(f"Error sending tracking data to server: {e}", exc_info=True)



    #   --show the minitunes and hours..........................    
    def schedule_d1(self):
        
        # self.on_click()
        # self.on_press()
        global is_paused,hh,mm,ss 
        self.h = self.findChild(QLabel,"hh")
        self.m = self.findChild(QLabel,"mm")
        # self.s = self.findChild(QLabel,"ss")
        self.h.setText(str(hh))
        self.m.setText(str(mm))

    def update_in_min(self):
        global is_paused,hh,mm,ss 
        self.ht = self.findChild(QLabel,"hht")
        self.mt = self.findChild(QLabel,"mmt")
        self.gettinghours = self.findChild(QLabel,"txtgettinghours")
        taskdata = json_handler.redjson(config.TASKDB)
        for d in range(len(taskdata)):
            if taskdata[d]["tid"] == self.datas["selected_project"]["task"]["id"]:
                
                #for todays
                ts = str(taskdata[d]["todaysession"]).split(":")
                t = datetime.timedelta(hours=0, minutes=0, seconds=1)
                todays_combine_result = t + datetime.timedelta(hours=int(ts[0]), minutes=int(ts[1]), seconds=int(ts[2]))
                #for totals
                new_ts = str(todays_combine_result).split(":")
                self.ht.setText(str(new_ts[0]))
                self.mt.setText(str(new_ts[1]))

                tos = str(taskdata[d]["totalsession"]).split(":")
                result1 = t + datetime.timedelta(hours=int(tos[0]), minutes=int(tos[1]), seconds=int(tos[2]))

                taskdata[d]["currentsession"] = str(datetime.timedelta(hours=hh, minutes=mm, seconds=ss))
                taskdata[d]["todaysession"] = str(todays_combine_result)
                taskdata[d]["totalsession"]= str(result1)
                self.gettinghours.setText(str(result1)[:-3])

        # json_handler.updatejson(config.TASKDB,taskdata)
        json_handler_th = threading.Thread(target=json_handler.updatejson,args=(config.TASKDB,taskdata))
        json_handler_th.start()
        
  

    # ---------------------on_of_Tracker_Function--------------------------
    def tracker(self):
        """Deprecated - use on_pause_resume instead."""
        logger.warning("tracker() called - redirecting to on_pause_resume")
        self.on_pause_resume()

        

    def goback(self):
        # config.Update_log_status("IL")
        self.track.setChecked(True)
        
        self.tracker()
        self.hide()
        import task
        self.win = task.Task()
        self.win.show() 
    
    def closeEvent(self,MainWindow):
        logger.info("Tracking window closing")
        with contextlib.suppress(Exception):
            config.logout()
            os._exit(0)

    
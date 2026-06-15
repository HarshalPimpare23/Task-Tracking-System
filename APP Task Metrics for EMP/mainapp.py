import contextlib
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QSize
import sys
import json
import requests
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from loguru import logger
import os

import task
import config
from jsonhandler import Jsonopr

json_handler = Jsonopr()


def CallApi(method="",url="", payload=None, files=None, headers=None):
    if payload is None:
        payload = {}
    if files is None:
        files = []
    if headers is None:
        headers = {}
    return  requests.request(method, url, headers=headers, data=payload, files=files)



class login(QtWidgets.QMainWindow):
    def __init__(self):
        super(login, self).__init__()
        uic.loadUi('./ui/login.ui', self)
        self.setWindowTitle("SkyTracker - Employee Login")
        self.show()
        self.findChild(QLineEdit, "txtemail").setFocus()
# -------------login Button --------------------------
        login_button = self.findChild(QPushButton,"btnlogin1")
        login_button.clicked.connect(self.Userlogin)
        login_button.clicked.connect(self.clearBox)
# -----------------Rember me object-----------------
        self.checkbox = self.findChild(QCheckBox,"chkrem")
        self.email = self.findChild(QLineEdit,"txtemail")
        self.password = self.findChild(QLineEdit,"txtpass")

        user_data = json_handler.redjson(config.USERDB)
        
        if user_data["user_check"] == True:
            self.email.setText(user_data["autouserfill"]["email"])
            self.password.setText(user_data["autouserfill"]["password"])
            self.checkbox.setChecked(True)
        else:
            self.checkbox.setChecked(False)
      
    def Userlogin(self):
        email = self.email.text()
        password = self.password.text()

        try:
            user_data = json_handler.redjson(config.USERDB)
            payload = {"email":email,"password":password}
            response = CallApi(url=config.HOSTURL+config.LOGINAPI, payload=payload, files=None, headers=None,method="POST")

            if response.status_code == 200:
                res_data = json.loads(response.text)
                if res_data["status_code"] == 200:
                    # Verify user identity before proceeding
                    user_name = res_data["data"].get("fname", "User")
                    if not self.verify_user_identity(user_name):
                        logger.warning(f"User verification failed for {user_name}")
                        return
                    
                    self.complete_login_process(res_data, user_data)
                else:
                    logger.warning("Login failed: invalid credentials")
                    config.update_login_status("OFF")
                    QMessageBox.information(self,"Login Failed",res_data["messages"])
            else:
                logger.error("Login failed: connection error")
                config.update_login_status("OFF")
                QMessageBox.information(self,"Connection Error","Connection failed. Please check your internet connection and try again.")

        except Exception as e:
            logger.error(f"Login error: {e}")
            config.update_login_status("OFF")
            QMessageBox.information(self,"Error",f"Login failed: {str(e)}")
    
    def verify_user_identity(self, user_name):
        """Ask user to verify their identity before proceeding."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("✓ Verify Your Identity")
        msg_box.setText(
            f"Hello {user_name}!\n\n"
            "Please confirm that you are logging in as yourself and not someone else.\n\n"
            "Only employees can use the tracking system. Admins should use the web portal."
        )
        msg_box.setIcon(QMessageBox.Question)
        btn_yes = msg_box.addButton("Yes, This is Me", QMessageBox.AcceptRole)
        btn_no = msg_box.addButton("No, Wrong User", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_yes)
        
        logger.info(f"User identity verification started for {user_name}")
        result = msg_box.exec_()
        
        if result == 1:  # No, Wrong User button
            logger.warning(f"User {user_name} clicked 'Wrong User' - returning to login")
            QMessageBox.information(self, "Login Cancelled", 
                                  "Please login with the correct credentials.")
            self.email.clear()
            self.password.clear()
            self.email.setFocus()
            return False
        
        return True

    def complete_login_process(self, res_data, user_data):
        """Complete the login process after successful authentication."""
        config.update_login_status("IL")
        current_time = datetime.datetime.now()
        user_data["user"]=res_data["data"]
        user_data["last_login"] = user_data["login_time"]
        user_data["login_time"] = str(current_time)
        
        # Check if user is an admin
        user_designation = user_data["user"].get("designation", "").upper()
        user_name = user_data["user"].get("fname", "User")
        
        if user_designation in ["CEO", "ADMIN", "ADMINISTRATOR", "MANAGER"]:
            logger.warning(f"Admin user {user_name} tried to access tracker")
            QMessageBox.critical(self, "❌ Admin Access Denied", 
                                f"Dear Admin ({user_name}),\n\n"
                                f"Admins cannot use the employee tracking system.\n\n"
                                "Please use the Web Admin Portal to:\n"
                                "• Assign projects to employees\n"
                                "• View employee tracking reports\n"
                                "• Manage tasks and projects\n\n"
                                "Employees must login individually to track their work.")
            self.email.clear()
            self.password.clear()
            self.email.setFocus()
            config.update_login_status("OFF")
            return

        try:
            user_id = user_data['user']['id']
            url = f"{config.HOSTURL}{config.TASKAPI}{user_id}/"
            logger.info(f"Fetching projects from URL: {url}")
            
            response = CallApi(url=url, payload=None, files=None, headers=None, method="get")
            logger.info(f"Project API response status: {response.status_code}")
            logger.debug(f"Project API response: {response.text}")

            if response.status_code == 200:
                task_data = json.loads(response.text)
                if task_data["status_code"] == 200:
                    projects = task_data.get("data", [])
                    user_data["project"] = projects
                    logger.info(f"Successfully loaded {len(projects)} projects for user {user_name}")
                else:
                    logger.warning(f"Failed to fetch project data: {task_data.get('messages', 'Unknown error')}")
                    user_data["project"] = []
                    QMessageBox.warning(self,"Data Error",f"Warning: {task_data.get('messages', 'Failed to load projects')}")
            else:
                logger.error(f"Failed to fetch project data: HTTP {response.status_code}")
                user_data["project"] = []
                QMessageBox.warning(self,"Connection Error","Warning: Could not load projects. Connected to old session data.")
        except Exception as e:
            logger.error(f"Project data fetch error: {e}", exc_info=True)
            user_data["project"] = []
            QMessageBox.warning(self,"Error",f"Warning: Could not load projects:\n{str(e)}")

        json_handler.updatejson(config.USERDB,user_data)
        logger.info(f"Login successful for employee {user_name}")
        
        # Check if user has projects assigned
        if not user_data.get("project") or len(user_data.get("project", [])) == 0:
            logger.warning(f"User {user_name} has no projects assigned")
            QMessageBox.information(self, "Login Successful", 
                                  f"Welcome {user_name}!\n\n"
                                  "Your login was successful, but you don't have any projects assigned yet.\n"
                                  "Please contact your administrator to assign projects to your account.")
        
        self.hide()
        self.window = task.Task()
        self.window.show()


    
    def clearBox(self):
        self.email.setFocus()
        self.email.clear()
        self.password.clear()
        
# ------------close event------------------------------------------------
    # ------------close event------------------------------------------------
    def setupUi(self, MainWindow):
        app = QtWidgets.QApplication(sys.argv)
        MainWindow.setObjectName("MainWindow")
        ##
        #......some more codes
        ##
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        app.aboutToQuit.connect(self.closeEvent)

    def retranslateUi(self):
        ## codes
        pass
        
    def closeEvent(self, MainWindow):
        logger.info("Application closing")
        with contextlib.suppress(Exception):
            config.logout()
            os._exit(0)



# app = QtWidgets.QApplication(sys.argv)
# window = login()
# app.exec_()
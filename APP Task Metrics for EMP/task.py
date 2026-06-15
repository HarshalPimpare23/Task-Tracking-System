
import contextlib
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QSize
import sys
import json
from PyQt5.uic.uiparser import QtCore
import requests
import schedule
from loguru import logger
import os
import datetime

import config
from jsonhandler import Jsonopr

from trackerstart import StartTracker




json_handler = Jsonopr()

def CallApi(method="",url="", payload=None, files=None, headers=None):
    if payload is None:
        payload = {}
    if files is None:
        files = []
    if headers is None:
        headers = {}
    return  requests.request(method, url, headers=headers, data=payload, files=files)



class Task(QtWidgets.QMainWindow):
    def __init__(self):
        logger.info("Task selection window opened.")
        super(Task, self).__init__()
        uic.loadUi('./ui/task_project.ui', self)
        self.setWindowTitle("SkyTracker - Select Project & Task")
        self.show()
        self.findChild(QComboBox, "cmbproject").setFocus()
# --------Start Button---------------------------
        start_button = self.findChild(QPushButton,"btnstart")
        start_button.clicked.connect(self.start_task_tracking)
        start_button.clicked.connect(self.clearBox)
# ----------cancel Button----------------------
        cancel_button = self.findChild(QPushButton,"btncancel")
        cancel_button.clicked.connect(self.cancelbtn)
# ----------------------------------------------------------
        # project and task
        self.project = self.findChild(QComboBox,"cmbproject")
        self.task = self.findChild(QComboBox,"cmbtask")

        user_data = json_handler.redjson(config.USERDB)
        
        # Load projects with error handling
        try:
            projects_list = user_data.get("project", [])
            logger.info(f"Found {len(projects_list)} projects")
            
            if not projects_list:
                logger.warning("No projects assigned to user")
                self.show_no_projects_notification(user_data)
                return
            
            for p in projects_list:
                try:
                    # Handle both nested format (p["project"]) and flat format (p)
                    if isinstance(p, dict) and "project" in p:
                        project_info = p["project"]
                    else:
                        project_info = p
                    
                    project_name = project_info.get("pname", "Unknown")
                    project_id = project_info.get("id", None)
                    
                    if project_id:
                        self.project.addItem(str(project_name), userData=project_id)
                        logger.info(f"Added project: {project_name} (ID: {project_id})")
                    else:
                        logger.warning(f"Project missing ID: {project_name}")
                except Exception as e:
                    logger.error(f"Error processing project: {e}", exc_info=True)
                    continue
                    
            self.project.activated.connect(self.selecttasklist)
            
        except Exception as e:
            logger.error(f"Error loading projects: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load projects: {str(e)}")
    
    def show_no_projects_notification(self, user_data):
        """Show a prominent notification when no projects are assigned."""
        user_name = user_data.get("user", {}).get("fname", "User")
        
        # Create a custom message box with more options
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("⚠️  Project Not Assigned")
        msg_box.setText(
            f"Hello {user_name},\n\n"
            "No projects have been assigned to you yet.\n\n"
            "Please contact your administrator to assign projects to your account."
        )
        msg_box.setIcon(QMessageBox.Warning)
        
        # Add buttons
        msg_box.addButton("Contact Admin", QMessageBox.AcceptRole)
        msg_box.addButton("Go Back to Login", QMessageBox.RejectRole)
        msg_box.setDefaultButton(msg_box.button(QMessageBox.AcceptRole))
        
        logger.warning(f"Project Not Assigned notification shown for user: {user_name}")
        result = msg_box.exec_()
        
        # Handle button clicks
        if result == 0:  # Contact Admin button
            logger.info(f"User {user_name} selected Contact Admin option")
        
        # Go back to login
        config.logout()
        self.hide()
        from mainapp import login
        self.window = login()
        self.window.show()


        
# --------------select activated function ---------------------------------    
    def selecttasklist(self):
        try:
            pname = self.project.currentText()
            user_data = json_handler.redjson(config.USERDB)
            
            # Clear previous tasks
            self.task.clear()
            
            projects_list = user_data.get("project", [])
            logger.info(f"Selecting tasks for project: {pname}")
            
            for p in projects_list:
                try:
                    # Handle both nested format and flat format
                    if isinstance(p, dict) and "project" in p:
                        project_info = p["project"]
                        tasks = p.get("task", []) if isinstance(p.get("task"), list) else [p.get("task", {})]
                    else:
                        project_info = p
                        # If the API returns tasks at the same level, access them
                        tasks = p.get("tasks", []) if isinstance(p.get("tasks"), list) else []
                    
                    if project_info.get("pname") == pname:
                        logger.info(f"Found project {pname}, loading tasks")
                        
                        if not tasks:
                            logger.warning(f"No tasks found for project {pname}")
                            QMessageBox.warning(self, "⚠️  No Tasks Assigned", 
                                              f"No tasks have been assigned for the project '{pname}'.\n\n"
                                              "Please contact your administrator to assign tasks to this project.")
                            return
                        
                        for t in tasks:
                            try:
                                task_name = t.get("tname", "Unknown")
                                task_id = t.get("id", None)
                                
                                if task_id:
                                    self.task.addItem(str(task_name), userData=task_id)
                                    logger.info(f"Added task: {task_name} (ID: {task_id})")
                                else:
                                    logger.warning(f"Task missing ID: {task_name}")
                            except Exception as e:
                                logger.error(f"Error processing task: {e}", exc_info=True)
                                continue
                        break
                except Exception as e:
                    logger.error(f"Error in selecttasklist for project {pname}: {e}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Error selecting tasks: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load tasks: {str(e)}")

                    
# --------------------------------------------------------------------------------------                
    def start_task_tracking(self):
        """Start tracking the selected project and task."""
        
        # Validation: Check if project is selected
        if not self.project.currentData():
            QMessageBox.warning(self, "Selection Required", 
                              "Please select a project before starting tracking.")
            logger.warning("Start tracking attempted without project selection")
            return
        
        # Validation: Check if task is selected
        if not self.task.currentData():
            QMessageBox.warning(self, "Selection Required", 
                              "Please select a task before starting tracking.")
            logger.warning("Start tracking attempted without task selection")
            return
        
        current_time = datetime.datetime.now()
        des = self.findChild(QTextEdit,"txtdes")
        user_data = json_handler.redjson(config.USERDB)
        task_records = json_handler.redjson(config.TASKDB)

        obj = {"project":{},"task":{},"des":des.toPlainText(),"starttime":str(current_time)}
        for i in user_data["project"]:
            if i["project"]["id"] == self.project.currentData():
                obj["project"] = i["project"]
                break
        for i in user_data["project"]:
            for j in i["task"]:
                if j["id"] == self.task.currentData():
                    obj["task"] = j
                    break
        user_data["selected_project"]=obj

        # Update task records
        current_date = datetime.date.today()
        if task_records:
            if all(d['tid'] != self.task.currentData() for d in task_records):
                task_records.append({"pid":self.project.currentData(),"tid":self.task.currentData(),"currentsession":"00:00:00","todaysession":"00:00:00","totalsession":"00:00:00","current_time":str(current_date)})
            else:
                for i in range(len(task_records)):
                    if task_records[i]["tid"] == self.task.currentData() and task_records[i]["current_time"] != str(current_date):
                        task_records[i]["current_time"]=str(current_date)
                        task_records[i]["todaysession"]="00:00:00"

        json_handler.updatejson(config.USERDB,user_data)
        json_handler.updatejson(config.TASKDB,task_records)
        config.update_login_status("ON")
        config.key_mouse_event=True
        self.project.clear()
        self.task.clear()
        self.hide()
        self.window = StartTracker()
        
        schedule.clear()
        schedule.every(1).seconds.do(self.window.schedule_d1)
        schedule.every(1).seconds.do(self.window.update_in_min)
        schedule.every(1).to(2).minutes.do(self.window.time_captu)
        self.window.show()     
# ---------------------------------------------------------------------------------------    
    def clearBox(self):
        sltproject = self.findChild(QComboBox,"cmbproject")
        slttask = self.findChild(QComboBox,"cmbtask")
        des = self.findChild(QTextEdit,"txtdes")
        sltproject.clear()
        sltproject.setFocus()
        slttask.clear() 
        des.clear()
# --------cancel-Button----------------
    def cancelbtn(self):
        """Cancel button - confirms logout and return to login."""
        reply = QMessageBox.question(self, "Confirm Logout", 
                                    "Are you sure you want to logout and return to login page?",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            logger.info("User clicked cancel - logging out and returning to login")
            user_data = json_handler.redjson(config.USERDB)
            user_data["selected_project"] = {}
            json_handler.updatejson(config.USERDB, user_data)
            config.logout()
            self.hide()
            from mainapp import login
            self.window = login()
            self.window.show()
        else:
            logger.info("User cancelled logout")

    def resume_previous_session(self):
        self.hide()
        
        self.window = StartTracker()
        schedule.clear()
        schedule.every(1).seconds.do(self.window.schedule_d1)
        schedule.every(1).seconds.do(self.window.update_in_min)
        schedule.every(1).to(2).minutes.do(self.window.time_captu)
        self.window.show()    
    
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
        logger.info("Task selection window closing")
        with contextlib.suppress(Exception):
            config.logout()
            os._exit(0)

          

    
# window = Task()
# app.exec_()
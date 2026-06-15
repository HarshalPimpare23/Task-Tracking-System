import mainapp
from PyQt5.QtWidgets import *
import sys

from PyQt5 import  QtWidgets
app = QtWidgets.QApplication(sys.argv)
window = mainapp.login()
app.exec_()
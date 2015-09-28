from qa_client import *
from PySide import QtCore
from PySide import QtGui
import json
import sys


qt_app = QtGui.QApplication(sys.argv)

class QuestionAnswerSystem(QtGui.QWidget):
    def __init__(self):
        logic = QAClientLogic()
        self.config = self.read_config(logic.confpath)
        QWidget.__init__(self)
        self.setWindowTitle("Makerspace QA System")
        self.setMinimumWidth(600)
        # Create the top level layouts and widgets of the program
        self.layout = QtGui.QVBoxLayout()
        self.room_info = QtGui.QHBoxLayout()
        self.chat_core = QtGui.QHBoxLayout()
        self.control_panel = QtGui.QHBoxLayout()
        self.chat_bar = QtGui.QLineEdit(self)
        # Create the room info widgets
        self.discussion_topic = QtGui.QLabel("Placeholder", self)
        self.room_address = QtGui.QLabel(self.config["client"]["default_host"], self)
        self.room_info.addWidget(self.discussion_topic)
        self.room_info.addWidget(self.room_address)
        # Create the chat core widgets
        self.discussion_view_frame = QtGui.QFrame(self)
        self.discussion_view = QtGui.QTextDocument(self)
        self.user_list = QtGui.QTextDocument(self)
        # Create the control panel widgets
        self.

    def read_config(self, confpath):
        """Read the configuration file and return a JSON dictionary representing
        the client configuration."""
        config_file = open(confpath)
        return json.load(config_file)
        

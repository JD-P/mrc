from qa_client import *
from PySide.QtCore import *
from PySide.QtGui import *
import json
import sys


qt_app = QApplication(sys.argv)

class QuestionAnswerSystemClient(QWidget):
    def __init__(self):
        logic = QAClientLogic()
        self.config = self.read_config(logic.confpath)
        QWidget.__init__(self)
        self.setWindowTitle("Makerspace QA System")
        self.setMinimumWidth(600)
        # Create the top level layouts and widgets of the program
        self.layout = QVBoxLayout()
        self.room_info = QHBoxLayout()
        self.chat_core = QHBoxLayout()
        self.control_panel = QHBoxLayout()
        self.chat_bar = QLineEdit(self)
        # Create the room info widgets
        self.discussion_topic = QLabel("Placeholder", self)
        self.room_address = QLabel(self.config["client"]["default_host"], self)
        self.room_info.addWidget(self.discussion_topic)
        self.room_info.addWidget(self.room_address)
        # Create the chat core widgets
        self.discussion_view_frame = QFrame(self)
        self.discussion_view = QTextDocument(self)
        self.user_list = QTextDocument(self)
        # Create the control panel widgets
        if os.name == 'posix':
            iconpath = "icons/"
        elif platform.system() == 'Windows':
            iconpath = "icons\\"
        self.screenshot_icon = QIcon(iconpath + "application_add.png")
        self.mute_indicator_icon = QIcon(iconpath + "comment.png")

    def read_config(self, confpath):
        """Read the configuration file and return a JSON dictionary representing
        the client configuration."""
        config_file = open(confpath)
        return json.load(config_file)
        

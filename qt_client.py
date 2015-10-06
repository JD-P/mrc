from qa_client import *
from PySide.QtCore import *
from PySide.QtGui import *
import json
import queue
import sys


class QuestionAnswerSystemClient(QWidget):
    def __init__(self):
        self.logic = QAClientLogic()
        self.logic.connect(hostname="localhost")
        self.logic.logon()
        self.config = self.read_config(self.logic.confpath)
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
        self.discussion_view = QTextEdit(self)
        self.discussion_view_text = QTextDocument(self)
        self.discussion_view.setReadOnly(True)
        self.discussion_view.setDocument(self.discussion_view_text)
        self.user_list = QTextEdit(self)
        self.user_list_text = QTextDocument(self)
        self.user_list.setReadOnly(True)
        self.user_list.setDocument(self.user_list_text)
        self.chat_core.addWidget(self.discussion_view)
        self.chat_core.addWidget(self.user_list)
        # Create the control panel widgets
        if os.name == 'posix':
            iconpath = "icons/"
        elif platform.system() == 'Windows':
            iconpath = "icons\\"
        self.screenshot_icon = QIcon(iconpath + "application_add.png")
        self.screenshot_button = QToolButton
        self.mute_indicator_icon = QIcon(iconpath + "comment.png")
        # Add layouts to top level layout and run program
        self.layout.addLayout(self.chat_core)
        # Connect signals and slots for events
        self.pacemaker = QTimer(self)
        self.connect(self.pacemaker, SIGNAL("timeout()"), self.circulate)
        self.pacemaker.start(50)

    def circulate(self):
        """Callback triggered by the main event loop to update 

        Attempt to grab a pubmsg from the client logics queue. If found update
        the QTextDocument representing the chat window with a new block 
        which is the text of the recieved message, along with the username of the
        sender and the time the message was sent.
        """
        try:
            raw_pubmsg = self.logic.get_pubmsg()
        except queue.Empty:
            return False
        pubmsg_wrapped = json.loads(raw_pubmsg)
        pubmsg = pubmsg_wrapped[1]
        pubmsg_text = (str(pubmsg["timestamp"]) + 
                       " <" + str(pubmsg["username"]) + "> " 
                       + str(pubmsg["msg"]))
        self.append_text(pubmsg_text, self.discussion_view_text)

    def append_text(self, text, text_document):
        """Append a piece of text to the end of a QTextDocument as a new block."""
        appender = QTextCursor(text_document)
        appender.movePosition(QTextCursor.End)
        appender.insertBlock()
        text_insert = QTextDocumentFragment.fromPlainText(text)
        appender.insertFragment(text_insert)
        print("Text appended!")
        return True
                
    def read_config(self, confpath):
        """Read the configuration file and return a JSON dictionary representing
        the client configuration."""
        config_file = open(confpath)
        return json.load(config_file)
        

    def show_and_raise(self):
        self.show()
        self.raise_()
        return True

if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    qa_client = QuestionAnswerSystemClient()
    qa_client.show_and_raise()
    sys.exit(qt_app.exec_())

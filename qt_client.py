from qa_client import *
from PySide.QtCore import *
from PySide.QtGui import *
import json
import queue
import time
import datetime
import sys
import argparse


class QuestionAnswerSystemClient(QWidget):
    def __init__(self, hostname="localhost"):
        self.logic = QAClientLogic()
        self.logic.connect(hostname=hostname)
        self.logic.logon()
        self.config = self.read_config(self.logic.confpath)
        QWidget.__init__(self)
        self.setWindowTitle("Makerspace QA System")
        self.setMinimumWidth(600)
        # Create the top level layouts and widgets of the program
        self.top_layout = QVBoxLayout()
        self.room_info = QHBoxLayout()
        self.chat_core = QHBoxLayout()
        self.control_panel = QHBoxLayout()
        self.chat_bar = QLineEdit(self)
        self.chat_bar.returnPressed.connect(self.send_msg_to_room)
        # Create the room info widgets
        self.discussion_topic = QLabel("Placeholder Topic", self)
        self.discussion_topic.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.room_address = QLabel("Host: " + self.logic.host, self)
        self.room_address.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.room_info.addWidget(self.discussion_topic)
        self.room_info.addWidget(self.room_address)
        # Create the chat core widgets
        self.discussion_view = QTextEdit(self)
        self.discussion_view_text = QTextDocument(self.discussion_view)
        self.discussion_view_cursor = QTextCursor(self.discussion_view_text)
        self.discussion_view.setReadOnly(True)
        self.discussion_view.setDocument(self.discussion_view_text)
        self.discussion_view.setTextCursor(self.discussion_view_cursor)
        self.user_list = QVBoxLayout()
        self.user_list_label = QLabel("Users", self)
        self.user_list_label.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.user_list_dict = dict()
        self.user_list.addWidget(self.user_list_label, alignment=Qt.AlignTop)
        self.chat_core.addWidget(self.discussion_view)
        self.chat_core.addLayout(self.user_list)
        # Create the control panel widgets
        if os.name == 'posix':
            iconpath = "icons/"
        elif platform.system() == 'Windows':
            iconpath = "icons\\"
        self.screenshot_icon = QIcon(iconpath + "application_add.png")
        self.screenshot_button = QToolButton
        self.mute_indicator_icon = QIcon(iconpath + "comment.png")
        # Add layouts to top level layout and run program
        self.setLayout(self.top_layout)
        self.top_layout.addLayout(self.room_info)
        self.top_layout.addLayout(self.chat_core)
        self.top_layout.addWidget(self.chat_bar)
        # Connect signals and slots for events
        self.pacemaker = QTimer(self)
        self.pacemaker.timeout.connect(self.circulate)
        self.pacemaker.start(50)

    def circulate(self):
        """Callback triggered by the main event loop to update 

        Attempt to grab a pubmsg from the client logics queue. If found update
        the QTextDocument representing the chat window with a new block 
        which is the text of the recieved message, along with the username of the
        sender and the time the message was sent.
        """
        try:
            raw_msg = self.logic.get_msg()
        except queue.Empty:
            return False
        wrapped_msg = json.loads(raw_msg)
        update = wrapped_msg[1]["type"]
        update_method = getattr(self, "update_on_" + update)
        update_method(wrapped_msg)
        return True

    def update_on_pubmsg(self, wrapped_msg):
        pubmsg = wrapped_msg[1]
        hh_mm = self.convert_and_extract_hh_mm(pubmsg["timestamp"])
        pubmsg_text = (hh_mm + 
                       " <" + str(pubmsg["username"]) + "> " 
                       + str(pubmsg["msg"]))
        self.append_text(pubmsg_text, self.discussion_view_cursor)
        scroll = self.discussion_view.verticalScrollBar()
        scroll.triggerAction(scroll.SliderToMaximum)
        return True

    def update_on_room(self, wrapped_msg):
        """Update the display when the user enters the room. Room messages are of
        the following form:

        {"type":"room",
         "users":<LIST OF STRINGS REPRESENTING USERNAMES>,
         "topic":<STRING REPRESENTING THE CURRENT ROOM TOPIC>}
         """
        message = wrapped_msg[1]
        for user in message["users"]:
            self.user_list_dict[user] = QLabel(user, self)
            self.user_list.addWidget(self.user_list_dict[user], alignment=Qt.AlignTop)
        self.discussion_topic = QLabel(message["topic"], self)
        return True

    def update_on_entrance(self, wrapped_msg):
        """Update the display when a user enters the room. Entrance messages are
        of the following form:

        {"type":"entrance",
         "username":<STRING REPRESENTING USERNAME>,
         "timestamp":<UNIX TIMESTAMP>}
        """
        entrance = wrapped_msg[1]
        

    def update_on_exit(self, wrapped_msg):
        pass

    @Slot(str, result=bool) 
    def send_msg_to_room(self):
        """Send a pubmsg to the room which the client is logged into."""
        line = self.chat_bar.text()
        self.chat_bar.clear()
        self.logic.pubmsg(line)
        return True

    def append_text(self, text, appender_cursor):
        """Append a piece of text to the end of a QTextDocument as a new block."""
        appender_cursor.movePosition(QTextCursor.End)
        appender_cursor.insertBlock()
        text_insert = QTextDocumentFragment.fromPlainText(text)
        appender_cursor.insertFragment(text_insert)
        appender_cursor.movePosition(QTextCursor.End)
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

    def convert_and_extract_hh_mm(self, unix_timestamp):
        """Convert a POSIX timestamp to a python datetime object in local time
        and then return a string representing the HH:MM of the stamp."""
        datetime_timestamp = datetime.datetime.fromtimestamp(unix_timestamp)
        return datetime_timestamp.strftime("%H:%M")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost", 
                        help="The host to connect to.")
    arguments = parser.parse_args()
    qt_app = QApplication(sys.argv)
    qa_client = QuestionAnswerSystemClient(arguments.host)
    qa_client.show_and_raise()
    sys.exit(qt_app.exec_())

import os
import platform
import socket
import random
import json
# import pyscreenshot
from PySide import QtCore
from PySide import QtGui

class QAClientLogic():
    """Question Answer client that provides both administrator and user interfaces.

    The question answer client is a qt application which registers with the server
    either an administrative client or user client based on the information in its
    configuration file. There is *no authentication*, the question answer system is
    meant to be used in a computer lab where all users are physically present and
    shenanigains can be dealt with through the intervention of an on-site instructor.
    You have been warned.

    """
    def __init__(self):
        if os.name == 'posix':
            self.confpath = os.path.join(os.path.expanduser("~"), ".mrc/qa_system/",
                                         "client/settings.conf")
        elif platform.system == 'Windows':
            self.confpath = os.path.join(os.environ['APPDATA'] + "mrc\\qa_system\\",
                                         "client\\settings.conf")

    def make_connection(self, hostname=None):
        """Make a connection to a given host. If host not given make a connection
        to the address specified in the config file."""
        

    def build_initial_connect_msg(self):
        """Create and return the string that is sent as the initial connect message
        to the server."""
        connect_msg = {
            "user":{},
            "server":{}
            }
        config = open(self.confpath)
        config_json = json.load(config)
        connect_msg["type"] = "logon"
        # Create user connect info
        connect_msg["user"]["username"] = "Guest" + str(random.randrange(10000))
        connect_msg["user"]["type"] = config["user_access"]
        if connect_msg["user"]["type"] not in ["user", "admin"]:
            raise Exception("User access was not 'user' or 'admin'.")
        # Create server connect info
        connect_msg["server"]["protocol"] = "QAServ1.0"
        connect_msg["server"]["client"] = "QA_QT1.0"
        connect_msg["length"] = self._calculate_recursive_length(connect_msg)
        return json.dumps(connect_msg)
        
    def _calculate_recursive_length(self, json_dict):
        """Calculate the length of a dictionary represented as JSON once a length
        field has been added as a key."""
        initial_length = len(json.dumps(json_dict))
        json_dict["length"] = initial_length
        recursive_length = len(json.dumps(json_dict))
        json_dict["length"] = recursive_length
        while len(json.dumps(json_dict)) != json_dict["length"]:
            json_dict["length"] = len(json.dumps(json_dict))
        return json_dict["length"]


class QAClientGUI(QtGui.QApplication):
    """Graphical interface code for the Questions Answers client."""
    def on_click(self):
        self.beep()

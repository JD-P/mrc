import os
import platform
import threading
import socket
import random
import json
# import pyscreenshot
import cmd
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

    def make_connection(self, hostname=None, port=9665):
        """Make a connection to a given host. If host not given make a connection
        to the address specified in the config file."""
        # Try connecting to given host
        try:
            connection = socket.create_connection((hostname, port))
        except socket.error:
            # If failure, open config file and get host from there
            try:
                config_file = open(self.confpath)
            except IOError:
                # If fail to open config file create default with address 'localhost'
                self._mkconfig(self.confpath)
                config_file = open(self.confpath)
            config = json.load(config_file)
            # Try connecting with new host
            try:
                connection = socket.create_connection(
                    (config["client"]["default_host"], port))
            except socket.error:
                # If failure, unrecoverable error and return to parent
                return False
        # If connection succeeds, create input and output threads
        print(config_file)
        connection.send(b"Testing 1 2")
        return True

    def _mkconfig(self, confpath):
        """Create a configuration file in the specified platform directory."""
        try:
            config_file = open(confpath, "w")
        except IOError:
            confdirs = os.path.split(confpath)[0]
            os.makedirs(confdirs, exist_ok=True)
            config_file = open(confpath, "w")
        user_info = {"username":"Guest" + str(random.randrange(10000)),
                     "type":"user"}
        server_info = {"protocol":"QAServ1.0", "client":"QA_QT1.0"}
        client_info = {"default_host":"localhost"}
        config = {"user":user_info, "server":server_info, "client":client_info}
        config_json = json.dumps(config)
        config_file.write(config_json)
        config_file.close()
        return True

    def build_initial_connect_msg(self):
        """Create and return the string that is sent as the initial connect message
        to the server."""
        connect_msg = {
            "user":{},
            "server":{}
            }
        config_file = open(self.confpath)
        config = json.load(config_file)
        connect_msg["type"] = "logon"
        # Create user connect info
        connect_msg["user"]["username"] = "Guest" + str(random.randrange(10000))
        connect_msg["user"]["type"] = config["user_access"]
        if connect_msg["user"]["type"] not in ["user", "admin"]:
            raise Exception("User access was not 'user' or 'admin'.")
        # Create server connect info
        connect_msg["server"]["protocol"] = "QAServ1.0"
        connect_msg["server"]["client"] = "QA_QT1.0"
        recursive_length = self._calculate_recursive_length(connect_msg)
        return json.dumps([recursive_length, connect_msg])
        
    def _calculate_recursive_length(self, json_dict):
        """Calculate the length of a dictionary represented as JSON once a length
        field has been added as a key."""
        initial_length = len(
            json.dumps(
                json_dict))
        initial_list = [initial_length, json_dict]
        recursive_length = len(
            json.dumps(
                initial_list))
        recursive_list = [recursive_length, json_dict]
        while len(json.dumps(recursive_list)) != recursive_list[0]:
            recursive_length = len(
                json.dumps(
                    recursive_list))
            recursive_list = [recursive_length, json_dict]
        return recursive_list[0]


class QAClientGUI(QtGui.QApplication):
    """Graphical interface code for the Questions Answers client."""
    def on_click(self):
        self.beep()

class DebugMenu(cmd.Cmd):
    def do_test_connection(self, arg):
        logic = QAClientLogic()
        logic.make_connection()

class ConfigurationError(Exception):
    """Error raised when the client is configured improperly and it is not 
    recoverable."""
    pass

debug = DebugMenu()
debug.cmdloop()

import os
import platform
import threading
import queue
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
        self.registry = {}

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
        logon_msg = self.build_initial_connect_msg()
        send_loop = threading.Thread(target=SendLoop, args=(self, connection))
        send_loop.start()
        while True:
            try:
                self.registry["Sender"].put_msg(logon_msg)
            except KeyError:
                pass
            break

    def register(self, component, provider):
        """Register a <provider> as the object which acts as <component> for this
        instance of the client logic."""
        self.registry[component] = provider
        

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
        connect_msg["user"]["type"] = config["user"]["type"]
        if connect_msg["user"]["type"] not in ["user", "admin"]:
            raise Exception("User access was not 'user' or 'admin'.")
        # Create server connect info
        connect_msg["server"]["protocol"] = "QAServ1.0"
        connect_msg["server"]["client"] = "QA_QT1.0"
        recursive_length = self._calculate_recursive_length(connect_msg)
        return [recursive_length, connect_msg]
        
    def _calculate_recursive_length(self, json_dict):
        """Calculate the length of a dictionary represented as JSON once a length
        field has been added as a key."""
        delimiter = "\r\n\r\n"
        initial_length = len(
            json.dumps(json_dict) + delimiter)
        initial_list = [initial_length, json_dict]
        recursive_length = len(
            json.dumps(initial_list) + delimiter)
        recursive_list = [recursive_length, json_dict]
        while len(json.dumps(recursive_list) + delimiter) != recursive_list[0]:
            recursive_length = len(
                json.dumps(recursive_list) + delimiter)
            recursive_list = [recursive_length, json_dict]
        return recursive_list[0]


class SendLoop():
    """
    Manages messages sent from the client to the server.

    The SendLoop class implements a queue based blocking loop to recieve messages
    generated by the rest of the program such as user input and send them to the 
    server. This loop runs in its own thread of execution, taking the socket object
    representing the clients server connection in its constructor and doing send() 
    requests on it.
    """
    def __init__(self, logic_instance, connection):
        self.send_queue = queue.Queue()
        logic_instance.register("Sender", self)
        self.loop_forever(connection)

    def loop_forever(self, connection):
        """
        The mainloop for the thread.

        A method is provided for other threads to add items to a queue maintained 
        by this object. This method continually grabs items from that queue and
        uses the send() method of the connection object given as argument to send
        messages to the server. Messages are first dumped as a string and then
        encoded as utf-8 before transfer.
        """
        while True:
            message = self.send_queue.get()
            json_message = json.dumps(message) + '\r\n\r\n'
            utf8_message = json_message.encode("utf-8")
            self.send_msg(connection, utf8_message)
            

    def send_msg(self, connection, utf8_message):
        """Send a message that the connection mainloop has in its send queue."""
        while utf8_message:
            try:
                sent = connection.send(utf8_message)
            except connection.timeout:
                self.handle_quit("Timeout occurred.")
            utf8_message = utf8_message[sent:]
        return True

    def put_msg(self, message):
        """Put a message into the clients send queue."""
        self.send_queue.put(message)

class RecieveLoop():
    pass
    

class QAClientGUI(QtGui.QApplication):
    """Graphical interface code for the Questions Answers client."""
    def on_click(self):
        self.beep()

class DebugMenu(cmd.Cmd):
    def do_test_connection(self, hostname):
        logic = QAClientLogic()
        fail = logic.make_connection(hostname=hostname)
        print(fail)

    def do_logon(self, hostname):
        logic = QAClientLogic()
        self.connection = logic.make_connection(hostname=hostname)
        self.connection.logon()

class ConfigurationError(Exception):
    """Error raised when the client is configured improperly and it is not 
    recoverable."""
    pass

debug = DebugMenu()
debug.cmdloop()

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
        self.pubmsg_queue = queue.Queue()

    def make_connection(self, hostname=None, port=9665):
        """Make a connection to a given host. If host not given make a connection
        to the address specified in the config file."""
        # Try connecting to given host
        try:
            self.connection = socket.create_connection((hostname, port))
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
                self.connection = socket.create_connection(
                    (config["client"]["default_host"], port))
            except socket.error:
                # If failure, unrecoverable error and return to parent
                return False
        # If connection succeeds, create input and output threads
        self.instantiate_components(self.connection)
        return True

    def instantiate_components(self, connection):
        """
        Instantiate the components used by the logic instance and then wait for
        them to register with the instance.
        """
        self.Sender_reg = threading.Event()
        send_loop = threading.Thread(target=SendLoop, args=(self, connection))
        send_loop.start()
        self.Sender_reg.wait()
        self.Receiver_reg = threading.Event()
        receive_loop = threading.Thread(target=ReceiveLoop, args=(self, connection))
        receive_loop.start()
        self.Receiver_reg.wait()
        return True

    def register(self, component, provider):
        """Register a <provider> as the object which acts as <component> for this
        instance of the client logic."""
        self.registry[component] = provider
        signal = getattr(self, component + "_reg")
        signal.set()
        return True

    def logon(self):
        """
        Logon to the server.
        """
        logon_msg = self.build_initial_connect_msg()
        self.registry["Sender"].put_msg(logon_msg)
        return True

    def pubmsg(self, message_text):
        """
        Send a pubmsg to the server over this connection.
        """
        json_dict = {"type":"pubmsg", "msg":message_text}
        message = [self._calculate_recursive_length(json_dict), json_dict]
        self.registry["Sender"].put_msg(message)
        return True

    def get_pubmsg(self):
        """Get and return a pubmsg from the logic instances pubmsg queue."""
        return self.pubmsg_queue.get()

    def put_pubmsg(self, message):
        """Put a pubmsg from a ReceieveLoop into the logic instances pubmsg queue.
        
        Pubmsg's are pulled from their underlying logic instance by the client 
        interface and displayed to the user.
        """
        self.pubmsg_queue.put(message)
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
        The mainloop for the SendLoop thread.

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
            except socket.timeout:
                self.handle_quit("Timeout occurred.")
            utf8_message = utf8_message[sent:]
        return True

    def put_msg(self, message):
        """Put a message into the clients send queue."""
        self.send_queue.put(message)

class ReceiveLoop():
    """
    Manages messages sent from the server to the client.
    """
    def __init__(self, logic_instance, connection):        
        logic_instance.register("Receiver", self)
        self.loop_forever(logic_instance, connection)

    def loop_forever(self, logic_instance, connection):
        """The mainloop for the ReceiveLoop thread.

        """
        msg_buffer = bytes() # The message input buffer
        while 1:
            if msg_buffer:
                msg_length = self.determine_length_of_json_msg(msg_buffer)
                if len(msg_buffer) >= msg_length:
                    message = self.extract_msg(msg_buffer, msg_length)
                    logic_instance.put_pubmsg(message)
                    print("Message put into queue!") #DEBUG
                    msg_buffer = msg_buffer[msg_length + 1:]
                else:
                    try:
                        msg_buffer += connection.recv(1024)
                    except socket.timeout:
                        pass
            else:
                try:
                    msg_buffer += connection.recv(1024)
                except socket.timeout:
                    pass

    def determine_length_of_json_msg(self, message_bytes):
        """Incrementally parse a JSON message to extract the length header.

        message_bytes: The bytes that represent the portion of the message 
        recieved.
        """
        # All messages must be written in utf-8
        message = message_bytes.decode('utf-8')
        # Check that the message we have been given looks like a valid length header
        length_portion = message.split(",")[0]
        left_bracket = length_portion[0] == "["
        number_before_comma = length_portion[-1] in "1234567890"
        if left_bracket and number_before_comma:
            for character in enumerate(length_portion):
                if character[1] not in "[ \n\t\r1234567890,":
                    raise InvalidLengthHeader(length_portion)
                elif character[1] in "1234567890":
                    length_start = character[0]
                    return int(length_portion[length_start:])
        elif left_bracket:
            raise InvalidLengthHeader(length_portion)
        else:
            raise MissingLengthHeader(length_portion)
        return False

    def extract_msg(self, msg_buffer, length):
        message = msg_buffer[:length].decode()
        try:
            right_curly_bracket = message[-6] == "}" or message[-2] == "}"
        except IndexError:
            print(message, msg_buffer, length)
        valid_delimiter = message[-6:] == "}]\r\n\r\n"
        if right_curly_bracket and valid_delimiter:
            return message
        elif right_curly_bracket:
            raise InvalidMessageDelimiter(message)
        else:
            raise MissingMessageDelimiter(message)
    

class QAClientGUI(QtGui.QApplication):
    """Graphical interface code for the Questions Answers client."""
    def on_click(self):
        self.beep()

class DebugMenu(cmd.Cmd):
    def do_test_connection(self, hostname):
        logic = QAClientLogic()
        fail = logic.make_connection(hostname=hostname)
        print(fail)

    def do_connect(self, hostname):
        self.logic = QAClientLogic()
        fail = self.logic.make_connection(hostname=hostname)
        if fail is False:
            print(fail)
        else:
            print("Connection Made")

    def do_logon(self, hostname):
        self.logic.logon()

    def do_pubmsg(self, message_text):
        self.logic.pubmsg(message_text)

    def do_pull_pubmsg(self, arg):
        """Pull a pubmsg off the stack."""
        print(self.logic.get_pubmsg())

class ConfigurationError(Exception):
    """Error raised when the client is configured improperly and it is not 
    recoverable."""
    pass

class StreamError(Exception):
    """Errors related to handling MRC streams."""
    pass

class LengthHeaderError(StreamError):
    """Abstract length header error class."""
    def __init__(self, length_portion="Portion not given"):
        self.length_portion = length_portion
    def __str__(self):
        return repr(self.length_portion)

class MissingLengthHeader(LengthHeaderError):
    """Error raised when a length header appears to be missing."""
    pass

class InvalidLengthHeader(LengthHeaderError):
    """Error raised when a length header appears to be present but
    garbled."""
    pass

class MessageDelimiterError(LengthHeaderError):
    """Abstract message delimiter error class."""
    pass

class MissingMessageDelimiter(MessageDelimiterError):
    """Error raised when a message delimiter appears to be missing."""
    pass

class InvalidMessageDelimiter(MessageDelimiterError):
    """Error raised when a message delimiter appears to be present but
    garbled."""
    pass

class JSONDecodeError(Exception):
    """Error raised when a json encoded message fails to decode to a valid JSON
    document."""
    def __init__(self, invalid_json="JSON not given."):
        self.invalid_json = invalid_json
    def __str__(self):
        return repr(self.invalid_json)

debug = DebugMenu()
debug.cmdloop()

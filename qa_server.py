import socketserver
import socket
import select
import threading
import queue
import json
import argparse

class PublishSubscribe():
    """Publish Subscribe mechanism for the QA system.

    Each thread spawned by the QAServer registers itself with an instance of this
    class by calling its subscribe() method with itself as an argument and 
    associated logon info. When a thread wants to send a message to the room it 
    is put into a central queue using the send_pubmsg() method of this class which 
    puts it into a FIFO queue. PublishSubscribe runs in its own thread and pulls
    each of these messages from the queue and timestamps them in utc before sending
    them to each relevant subscriber in the subscription list.
    """
    def __init__(self):
        global PubSub
        PubSub = self
        self.Subscriptions = {}
        self.Messages = queue.Queue()
        self.swear_words_list = None #TODO: Make this point to a real file in the config.
        self.pub_sub_loop()

    def subscribe(self, connection, logon_info):
        """Add a QAServer <connection> to the subscriber list with the logon info
        given in the dictionary <logon_info>."""
        self.Subscriptions[connection] = logon_info
        return True

    def put_msg_into_publish_queue(self, message):
        """Put a <message> into this objects publish queue."""
        self.Messages.put(message)
        return True

    def pub_sub_loop(self):
        """
        Main Publish Subscribe loop for MRC.

        This loop runs in a seperate thread of execution. It takes items from a
        push queue which is filled through a method of this object put_msg_into_publish_queue().
        
        Messages are sent with their associated connection in a tuple of the form
        (message, connection). This connection has its privileges checked before 
        publish time. If the connection has a privilege setting effecting its 
        ability to publish such as being muted that is handled here.

        How it is handled is that a function corresponding to the type of message
        is grabbed as an attribute from PublishSubscribe. Passed to this function
        is all the information necessary to determine whether or not it should be
        sent and if so to whom. A seperate communication channel is opened in the
        returned values for error messages such as those informing a user they are
        muted to be sent to the client.

        The message is grabbed, then the privilege checks are applied, finally
        if applicable the message is sent to the entire subscriber list.
        """
        # TODO: Write a system that lets you have functions to generate lists of
        # subscribers to send a message to based on its type and contents.
        while True:
            message_tuple = self.Messages.get()
            print("Pubsub got a message!") #DEBUG
            message = message_tuple[0]
            connection = message_tuple[1]
            message["timestamp"] = None # Need to add later.
            if not message["username"]: # Reject messages from clients which have not logged in
                print("Not logged in.") #DEBUG
                continue
            msg_type = message["type"]
            msg_filter = getattr(self, "filter_" + msg_type)
            filtered = msg_filter(self.Subscriptions.copy(), connection, message)
            filtered_recipients = filtered[0]
            error_notifications = filtered[1]
            message = filtered[2]
            print(filtered_recipients, error_notifications, message) #DEBUG
            for recipient in filtered_recipients:
                recipient.put_msg(message)
            for error in error_notifications:
                self.put_msg_into_publish_queue(error)

    def filter_pubmsg(self, subscriptions, connection, pubmsg):
        """Filter a public message sent to the entire room.

        Public messages are filtered on swear words and privileges such as whether
        a given user is currently muted.
        """
        if "muted" in subscriptions[connection]["user_info"]["privileges"]:
            print("Muted.") #DEBUG
            muted = subscriptions[connection]["user_info"]["privileges"]["muted"]
            if muted:
                return (list(), list(), None) 
                #TODO: Make this send a message back to the client that
                # their message was not sent.
        # pubmsg["msg"] = censor_swear_words(pubmsg["msg"]) TODO: Implement this.
        else:
            return (subscriptions, list(), pubmsg)

    def filter_screenshot(self, subscriptions, connection, screenshot):
        recipients = []
        for subscriber in subscriptions:
            if subscriptions[subscriber]["user_info"]["privileges"]["type"] == "admin":
                recipients.append(subscriber)
        return (recipients, list(), screenshot)
        

    def censor_swear_words(self, message_text):
        """Replace swear words in the text of a message with astericks."""
        pass

class QAServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Questions and answer server for demonstrations in a computer lab.

    Includes filtering for messages sent to channel, in particular curse
    worse filter. Uses a mutex lock on speaking who is allowed to speak at
    any particular time. While a user is typing packets are sent to the 
    server that reset the lock which has a three second timer. The user
    gets to 'hold focus' for those three seconds while they begin typing
    up to two more lines.

    Once those three lines have been typed or the lock has expired that user
    cannot type again for thirty seconds. This is all configurable in 
    qa_config.json. The swear filter is applied before messages are sent
    to channel, filters are applied over all messages before being sent
    including the admins. 

    Users can press a button on the client to send a screenshot to the admin.
    The admin recieves these in a simple image viewer in a sub window of 
    their chat client. There is a configurable rate limit of one image sent
    per ten seconds.

    All messages are sent as JSON with a 'header' key 'type' that tells the
    server what sort of message can be expected within the rest of the JSON
    document.
    """
    pass
    

class MRCStreamHandler(socketserver.BaseRequestHandler):
        """Handles incoming requests for MRC connections for the question
        answer system. 

        Connections to the server should be essentially kept alive as long 
        as ping's are responded to with pong's by the client. A timeout 
        should be handled by waiting several minutes for the client to recover
        before cutting the cord.
        """

        def handle(self):
            """Handle a QA connection.

            Messages are taken in by an input buffer 1024 bytes at a time until
            they are fully recieved. All messages are JSON documents. Once a 
            message has been recieved by the server it is sent to select_and_handle_msg()
            to be parsed as JSON and then passed on to a message handler. The
            selector knows which handler to invoke by the messages 'type' value.
            The name of a handler is always 'handle_' with the type of the message
            appended. 

            The first handler invoked on each connection is the handle_logon()
            method. The handle_logon() method initializes a connection, setting
            its privileges and registering client information.

            The QA system only supports one chatroom on-server. Each public
            message sent to the server is handled by the handle_pubmsg() method
            which puts messages into the PublishSubscribe system. The Publish
            Subscribe system keeps a queue of all messages to be sent to clients
            and a subscriber list. Each message in the queue is put in every 
            clients send queue.

            The mainloop for each client connection handles both input and output.
            Input is prioritized over output so that if the room is flooded by a
            malicious client an administrator can send the messages to the server
            necessary to silence them.

            The QA system also supports sending images to the room. When an image
            is sent to the room it is only sent to administrators. This is because
            the actual intended use of this feature is to send screenshots to the
            instructor of the computer lab. For example if you are demonstrating
            a piece of software and the demonstration is based on the state of the
            software at a given time, a screenshot can be sent to the instructor
            so he can see the state without having to get up and look. Images
            are encoded as base64 so that they can be sent as JSON documents.
            """
            self.send_queue = queue.Queue() # The message output queue
            self.user_info = {"username":None, "privileges":dict()}
            self.server_info = {"protocol":None, "client":None}
            msg_buffer = bytes() # The message input buffer
            while 1:
                if not self.send_queue.empty():
                    print("Queue message detected!") #DEBUG
                    message = self.send_queue.get()
                    self.send_msg(message)
                elif msg_buffer:
                    try:
                        msg_length = self.determine_length_of_json_msg(msg_buffer)
                    except InvalidLengthHeader:
                        msg_length = float("inf")
                    if len(msg_buffer) >= msg_length:
                        message = self.extract_msg(msg_buffer, msg_length)
                        self.select_and_handle_msg(message)
                        msg_buffer = msg_buffer[msg_length + 1:]
                    else:
                        if select.select([self.request], [], [], 0.1)[0]:
                            msg_buffer += self.request.recv(1024)
                        else:
                            continue
                else:
                    if select.select([self.request], [], [], 0.1)[0]:
                        msg_buffer += self.request.recv(1024)
                    else:
                        continue
                        

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

        def determine_length_of_json_msg(self, message_bytes):
            """Incrementally parse a JSON message to extract the length header.

            message_bytes: The bytes that represent the portion of the message 
            recieved.
            """
            # All messages must be written in utf-8
            message = message_bytes.decode('utf-8')
            # Check that the message we have been given looks like a valid length header
            if "," not in message:
                raise InvalidLengthHeader(message)
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
            

        def put_msg(self, utf8_message):
            """Put a message into the connections send queue."""
            self.send_queue.put(utf8_message)
            print("Message put in send queue!") #DEBUG

        def send_msg(self, message):
            """Send a message that the connection mainloop has in its send queue."""
            message_tuple = [self._calculate_recursive_length(message), message]
            json_message = json.dumps(message_tuple) + '\r\n\r\n'
            print("Sending message!" + repr(json_message), len(json_message.encode('utf-8'))) #DEBUG
            utf8_message = json_message.encode('utf-8')
            while utf8_message:
                try:
                    sent = self.request.send(utf8_message)
                except socket.timeout:
                    self.handle_quit("Timeout occurred.")
                utf8_message = utf8_message[sent:]
            print("Message sent!") #DEBUG
            return True

        def select_and_handle_msg(self, message):
            """
            Generic message handler.

            This function takes a text message extracted by the program mainloop
            and further extracts the message dictionary from the list which
            contains it and the length header. After this has been accomplished
            the message dictionary's 'type' key is read to find out which handler
            should be passed this mesasge. The handler to be passed is defined
            as a method of this class with the prefix "handle_" and then the type
            of message appened. For example to handle a 'pubmsg' you would call
            handle_pubmsg().
            """
            try:
                json_message = json.loads(message)[1] 
            except ValueError:
                raise JSONDecodeError(message)
            msg_type = json_message["type"]
            handler = getattr(self, "handle_" + msg_type)
            handler(json_message)
            return True

        def handle_logon(self, message):
            """Handles an initial client connection to the server.

            user_info: Information about the user such as username, realname and
            submitted passwords.

            server_info: Information *for* the server not *about* it.
            The reason why it's named like this is that future extensions and
            variants of this protocol will store information besides client
            info here such as preferences for a chat matchmaking system.
            """
            self.user_info.update(message["user"])
            self.server_info.update(message["server"])
            print("LOGON REACHED!") #DEBUG
            print(message) #DEBUG
            print(self.user_info, self.server_info) #DEBUG
            PubSub.subscribe(self, {"user_info":self.user_info, 
                                    "server_info":self.server_info})
            return True

        def handle_pubmsg(self, message):
            """Handle a public message sent to the single QA room."""
            message["username"] = self.user_info["username"]
            PubSub.put_msg_into_publish_queue((message, self))
            return True

        def handle_screenshot(self, screenshot):
            """Handle a screenshot sent to the administrators of the QA room."""
            screenshot["username"] = self.user_info["username"]
            PubSub.put_msg_into_publish_queue((screenshot, self))
            return True

        def handle_quit(self, timout_msg):
            """Handle a connection quitting or timing out."""
            self.request.close()
            

        
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost", 
                        help="The hostname to serve on.")
    parser.add_argument("-p", "--port", default=9665, type=int, 
                        help="The port number on which to allow access.")
    #TODO: Add 'debug' argument that profiles code and let's you know which 
    # portions were called during a program run.
    # One way to do this as a general process might be to find a way to do it and
    # then find a way to do that thing from python. Eg if you can use the python
    # debugger to get a stack trace, then using the python debugger from within
    # python should let you get a stack trace.
    arguments = parser.parse_args()

    PubSubThread = threading.Thread(target=PublishSubscribe)

    PubSubThread.start()

    HOST, PORT = arguments.host, arguments.port
    
    server = QAServer((HOST, PORT), MRCStreamHandler)

    server.serve_forever()

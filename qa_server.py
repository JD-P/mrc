import socketserver
import threading
import queue
import json

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
        self.pub_sub_loop()

    def subscribe(self, connection, logon_info):
        """Add a QAServer <connection> to the subscriber list with the logon info
        given in the dictionary <logon_info>."""
        self.Subscriptions[connection] = logon_info
        return True

    def send_pubmsg(self, message):
        """Put a <message> into the publish queue."""
        self.Messages.put(message)
        return True

    def pub_sub_loop(self):
        """
        Main Publish Subscribe loop for MRC.

        This loop runs in a seperate thread of execution. It takes items from a
        push queue which is filled through a method of this object send_pubmsg().
        
        Messages are sent with their associated connection in a tuple of the form
        (message, connection). This connection has its privileges checked before 
        publish time. If the connection has a privilege setting effecting its 
        ability to publish such as being muted that is handled here.

        The message is grabbed, then the privilege checks are applied, finally
        if applicable the message is sent to the entire subscriber list.
        """
        while True:
            message_tuple = self.Messages.get()
            message = message_tuple[0]
            connection = message_tuple[1]
            message["timestamp"] = None # Need to add later.
            if not message["name"]:
                continue
            json_message = json.dumps(message)
            utf8_message = json_message.encode("utf-8")
            if "muted" in self.Subscriptions[connection]["user_info"]["privileges"]:
                muted = self.Subscriptions[connection]["user_info"]["privileges"]["muted"]
                if muted:
                        continue #TODO: Make this send a message back to the client that
                              # their message was not sent.
                else:
                    for subscriber in self.Subscriptions:
                        subscriber.put_msg(utf8_message)
        

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
        send_queue = queue.Queue() # The message output queue
        user_info = {"name":None, "privileges":None}
        server_info = {"protocol":None, "client":None}

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
            msg_buffer = bytes() # The message input buffer
            while 1:
                if not self.send_queue.empty():
                    utf8_message = self.send_queue.get()
                    self.send_msg(utf8_message)
                elif msg_buffer:
                    msg_length = self.determine_length_of_json_msg(msg_buffer)
                    if len(msg_buffer) >= msg_length:
                        message = self.extract_msg(msg_buffer, msg_length)
                        self.select_and_handle_msg(message)
                        msg_buffer = msg_buffer[msg_length + 1:]
                    else:
                        msg_buffer += self.request.recv(1024)
                else:
                    msg_buffer += self.request.recv(1024)
                        

        def extract_msg(self, msg_buffer, length):
            message = msg_buffer[:length].decode()
            try:
                right_curly_bracket = message[-6] == "}" or message[-2] == "}"
            except IndexError:
                print(message, msg_buffer)
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
            # All messages must be sent in utf-8
            msg_utf8 = str(message_bytes, 'utf-8')
            # Check that the message we have been given looks like a valid length header
            length_portion = msg_utf8.split(",")[0]
            left_bracket = length_portion[0] == "["
            number_before_comma = length_portion[-1] in "1234567890"
            if left_bracket and number_before_comma:
                for character in enumerate(length_portion):
                    if character[1] not in "[ \n\t\r1234567890,":
                        raise InvalidLengthHeader(length_portion)
                    elif character[1] in "1234567890":
                        length_start = character[0]
            elif left_bracket:
                raise InvalidLengthHeader(length_portion)
            else:
                raise MissingLengthHeader(length_portion)
            return int(length_portion[length_start:])

        def put_msg(self, utf8_message):
            """Put a message into the connections send queue."""
            self.send_queue.put(utf8_message)

        def send_msg(self, utf8_message):
            """Send a message that the connection mainloop has in its send queue."""
            while utf8_message:
                try:
                    sent = self.request.send(utf8_message)
                except timeout:
                    self.handle_quit("Timeout occurred.")
                utf8_message = utf8_message[sent:]
            return True

        def select_and_handle_msg(self, message):
            try:
                json_message = json.loads(message)
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
            PubSub.subscribe(self, {"user_info":self.user_info, 
                                    "server_info":self.server_info})
            return True

        def handle_pubmsg(self, message):
            """Handle a public message sent to the single QA room."""
            message["name"] = self.user_info["name"]
            PubSub.send_pubmsg((message, self))
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
    PubSubThread = threading.Thread(target=PublishSubscribe)

    PubSubThread.start()

    HOST, PORT = "localhost", 9665
    
    server = QAServer((HOST, PORT), MRCStreamHandler)

    server.serve_forever()

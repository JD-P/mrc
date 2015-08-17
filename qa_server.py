import socketserver
import threading
import queue
import json

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
            """Handle a QA connection."""
            # Initialize the connection and get necessary client info
            name = None
            msg_buffer = bytes()
            while 1:
                if msg_buffer:
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
            message = msg_buffer[:length + 1]
            utf8_message = str(message, 'utf-8')
            right_curly_bracket = utf8_message[-5] == "}"
            valid_delimiter = utf8_message[-5:] == "}\r\n\r\n"
            if right_curly_bracket and valid_delimiter:
                return utf8_message
            elif right_curly_bracket:
                raise InvalidMessageDelimiter(utf8_message)
            else:
                raise MissingMessageDelimiter(utf8_message)

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
            number_before_comma = length_portion[-2] in "1234567890"
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
            return int(length_portion[length_start:-2])

        def select_and_handle_msg(self, message):
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


if __name__ == '__main__':
    HOST, PORT = "localhost", 9665
    
    server = QAServer((HOST, PORT), MRCStreamHandler)

    server.serve_forever()

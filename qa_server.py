import socketserver
import threading
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

    class MRCStreamHandler(socketserver.StreamRequestHandler):
        """Handles incoming requests for MRC connections for the question
        answer system. 

        Connections to the server should be essentially kept alive as long 
        as ping's are responded to with pong's by the client. A timeout 
        should be handled by waiting several minutes for the client to recover
        before cutting the cord.
        """
        def handle_qa_main(self):
            """Handle a QA connection."""

    

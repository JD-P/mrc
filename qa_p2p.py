from Crypto.PublicKey import DSA
from Crypto.Hash import SHA256
from Crypto.Random import random
import socket
import socketserver
import threading
import queue
import base64
import json

def base64_pub_encode(self, key):
    """Return a base64 representation of the public key. The representation is
    just the variables y g p q concatenated together with colon seperators
    and then encoded."""
    (y, g, p, q) = (str(key.y), str(key.g), str(key.p), str(key.q))
    return base64.b64encode((y + "," + g + "," + p + "," + q).encode('utf-8')).decode('utf-8')

def base64_pub_decode(self, base64_pub):
    """Return a tuple with the variables y g p q given a base64 representation
    of a DSA public key."""
    base64_pub_bytes = base64_pub.encode('utf-8')
    pubkey_text = base64.b64decode(base64_pub_bytes)
    pubkey_vars = pubkey_text.split(":")
    y = int(pubkey_vars[0])
    g = int(pubkey_vars[1])
    p = int(pubkey_vars[2])
    q = int(pubkey_vars[3])
    return DSA.construct((y,g,p,q))

def fingerprint(self, key):
    """Return a SHA256 fingerprint of a base64 encoded public key."""
    base64_pub = self.base64_pub_encode(key)
    return SHA256.new(base64_pub.encode('utf-8')).digest()
        

class ClientList():
    """A list of clients who are on the network. This is used to call them back
    if an IP is reassigned or to swap information on what IP the server is hosting
    at."""
    def __init__(self):
        self._neighbors = set()

    def add(self, address):
        if type(address) != type(str()):
            raise self.IPAddError("Expected IP address to be of type string.")
        self._neighbors.add(address)

    def list(self):
        return self._neighbors

    class IPAddError(Exception):
        """Error raised when an improper IP address is added to the ClientList."""
        def __init__(self, error_message="No error message given."):
            self.error_message = error_message
        def __str__(self):
            return repr(self.error_message)

class ServerAddressBook():
    """An address book containing the key for a server and all the addresses the 
    server is known to have used."""
    def __init__(self):
        self.book = dict()
        
    def add_server(self, key):
        base64_pub = base64_pub_encode(key)
        if base64_pub not in self.book:
            self.book[base64_pub] = set()
        else:
            return False

    def add_address(self, key, ip_address, timestamp, signature, port=9665):
        """Add an address to the list that a server has hosted at. Each address
        includes a timestamp of when the server signed it so that it's easy to
        sort and determine what the most recent address is. The dialer goes
        through each entry in this list in the case of a disconnection or failure
        to connect."""
        base64_pub = base64_pub_encode(key)
        digest = SHA256.new(ip_address + "," + str(port) + "," + str(timestamp)).digest()
        if not key.verify(digest, signature):
            return False
        if (ip_address, timestamp, signature) not in self.book[base64_pub]:
            self.book[base64_pub].add((ip_address, timestamp, signature))
        else:
            return False

    def remove_server(self, key):
        base64_pub = base64_pub_encode(key)
        if base64_pub in self.book:
            self.book.pop(base64_pub)
            return True
        else:
            return False

    def list_by_key(self, key):
        base64_pub = base64_pub_encode(key)
        if base64_pub in self.book:
            return self.book[base64_pub]
        else:
            return False

class P2PNode(socketserver.ThreadingMixIn, socketserver.TCPServer):
:
    """Implements the callback function of the QA p2p system. (For a description
    of this function see the callback() method.) This class handles client dialing 
    by default, but the subclass ServerNode handles the callback function from 
    the server side.
    """
    def __init__(self, client_logic, address_book, client_list, key):
        self._client_logic = client_logic
        self._address_book = address_book
        self._client_list = client_list
        self._key = key
        self._send_queue = queue.Queue()
        self._shutdown = threading.Event()

    def loop_forever(self):
        while True:
            self._client_logic.connection_error.wait()
            self.callback()
        
    def callback(self):
        """
        When a connection is lost to the server, the callback() method goes through the 
        ServerAddressBook associated with this object to try every IP address the 
        server is known to have hosted from. If this fails it then goes through and 
        tries connecting to each client address in the ClientList. If successful it
        will ask the client for its most recent address entry for the server in the 
        ServerAddressBook. The client will then validate this entry using its copy of
        the server key.
        
        If an entry is valid and not already in the book it will be added and tried.
        Finally if this process fails to yield the server address the client will need
        to be reconfigured manually. Otherwise dial() returns the servers new address.
        server_addresses = address_book.list_by_key(key)
        """
        for address in server_addresses:
            if self._client_logic.connection_error.is_set():
                try:
                    connection = socket.create_connection((address, 9665))
                    self.sident_verify(connection, v_event)
                except socket.error:
                    continue
            else:
                return True
            

    def sident_verify(self, connection):
        """Request the server send a signed verification of its identity with 
        IP address, port and timestamp.

        sident stands for 'Server Identity'

        An sident_verify message is of the following form:

        {'type':'sident_verify'}

        The server should reply with an sident_response message which is of
        the following form:

        {'type':'sident_response',
         'ip_addr':<IP ADDRESS AS A STRING>,
         'port':<PORT NUMBER AS AN INTEGER>,
         'timestamp':<UNIX TIMESTAMP>,
         'signature':<SIGNED DIGEST OF THE THREE PREVIOUS VALUES AS A UTF-8 STRING 
                      CONCATENATED TOGETHER WITH COMMA SEPERATORS>}
        """
        sident_verify_msg = {'type':'sident_verify'}
        self._send_queue.put((sident_verify_msg, connection))
        return True

    def send_loop(self):
        """Send loop that is meant to be started from a seperate thread of 
        execution. The send loop pulls 'raw' python object messages from this 
        objects send_queue attribute and converts them to json strings before 
        encoding them as utf-8 to send across the wire. Sent along with the 
        message is the connection to send it on.

        Responses are handled and received by the receive_loop method of this class
        which is ran in a seperate thread of execution."""
        while not self._shutdown.is_set():
            message_tuple = self._send_queue.get()
            message = message_tuple[0]
            message_length = self._calculate_recursive_length(message)
            wrapped_message = [message_length, message]
            wire_message = (json.dumps(wrapped_message) + "\r\n\r\n").encode('utf-8')
            message_tuple[1].sendall(wire_message)
        return True

    def receive_loop(self):
        """Receive loop that is meant to be started from a seperate thread of
        execution. The receive loop takes in 'raw' utf-8 json messages from the
        wire and decodes them, then interprets them to produce native python 
        objects. The resulting objects are then handled by a method of this class
        of the form handle_<message_type>. For example if a message with the 
        'type' key 'test' came in like so:

        {'type':'test'}

        The method self.handle_test(message) would be called with the message
        dictionary object passed along.
        """
        msg_buffer = bytes() # The message input buffer
        while not self._shutdown.is_set():
            if msg_buffer:
                try:
                    msg_length = self.determine_length_of_json_msg(msg_buffer)
                except InvalidLengthHeader:
                    msg_length = float("inf")
                if len(msg_buffer) >= msg_length:
                    message = self.extract_msg(msg_buffer, msg_length)
                    try:
                        handler = getattr(self, "handle_" + message['type'])
                    except AttributeError:
                        print("Can't handle message of type: " +
                              str(message['type']))
                        continue
                    handler(message)
                    msg_buffer = msg_buffer[msg_length:]
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

    def _calculate_recursive_length(self, msg_dict):
        """Calculate the length of a dictionary represented as JSON once a length
        field has been added as a key."""
        delimiter = "\r\n\r\n"
        initial_length = len(
            json.dumps(msg_dict) + delimiter)
        initial_list = [initial_length, msg_dict]
        recursive_length = len(
            json.dumps(initial_list) + delimiter)
        recursive_list = [recursive_length, msg_dict]
        while len(json.dumps(recursive_list) + delimiter) != recursive_list[0]:
            recursive_length = len(
                json.dumps(recursive_list) + delimiter)
            recursive_list = [recursive_length, msg_dict]
        return recursive_list[0]

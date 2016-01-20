from Crypto.PublicKey import DSA
from Crypto.Hash import SHA256
from Crypto.Random import random
import base64

class QAKey(DSA):
    """Question answer system keypair system. This is a basic DSA signing key
    generation class, this class adds methods to dump public key params to base64 
    and a fingerprint of the key based on such."""
    def base64_pub_encode(self, key):
        """Return a base64 representation of the public key. The representation is
        just the variables y g p q concatenated together with colon seperators
        and then encoded."""
        (y, g, p, q) = (str(key.y), str(key.g), str(key.p), str(key.q))
        return base64.b64encode((y + ":" + g + ":" + p + ":" + q).encode('utf-8')).decode('utf-8')

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
        return self.construct((y,g,p,q))

    def fingerprint(self, base64_pub):
        """Return a SHA256 fingerprint of a base64 encoded public key."""
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
        
    def add_server(self, base64_pub):
        if base64_pub not in self.book:
            self.book[base64_pub] = set()
        else:
            return False

    def add_address(self, base64_pub, ip_address, timestamp, signature):
        """Add an address to the list that a server has hosted at. Each address
        includes a timestamp of when the server signed it so that it's easy to
        sort and determine what the most recent address is. The dialer goes
        through each entry in this list in the case of a disconnection or failure
        to connect."""
        key = QAKey.base64_pub_decode(base64_pub)
        digest = SHA256.new(ip_address + str(timestamp)).digest()
        if not key.verify(digest, signature):
            return False
        if (ip_address, timestamp, signature) not in self.book[base64_pub]:
            self.book[base64_pub].add((ip_address, timestamp, signature))
        else:
            return False

    def remove_server(self, base64_pub):
        if base64_pub in self.book:
            self.book.pop(base64_pub)
            return True
        else:
            return False

    def list_by_key(self, base64_pub):
        

class Dialer():
    """Implements the callback function of the QA p2p system. This class handles 
    client dialing by default, but the subclass ServerDialer handles the callback
    function from the server side.

    When a connection is lost to the server, the dial() method goes through the 
    ServerAddressBook associated with this object to try every IP address the 
    server is known to have hosted from. If this fails it then goes through and 
    tries connecting to each client address in the ClientList. If successful it
    will ask the client for its most recent address entry for the server in the 
    ServerAddressBook. The client will then validate this entry using its copy of
    the server key.

    If an entry is valid and not already in the book it will be added and tried.
    Finally if this process fails to yield the server address the client will need
    to be reconfigured manually. Otherwise dial() returns the servers new address.
    """
    def __init__(self, address_book, client_list, key):
        self._address_book = address_book
        self._client_list = client_list
        self._key = key

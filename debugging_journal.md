Mon Sep  7 23:19:21 UTC 2015:

Seperated out extract_msg() from the rest of qa_server for analysis. 
When pasting, the line spacing for function got messed up, discovered
this through manual analysis with python debugger and promptly smacked
forehead.

Also discovered that part of the problem with the right curly brace check 
is that the '\r\n\r\n' delimiter is not included in the length count, which
needs to be fixed. Another problem is that the indexing is offset improperly
because the delimiter is not taken into account.

----

Tue Sep  8 01:05:49 UTC 2015:

Fixed length header in the msg_buffer variable, this was the wrong place to fix it
because length was hardcoded as a seperate variable inside my ExtractMessage test.
Fixing this variable to be 138 characters rather than 134 seems to have fixed the
problem.

This means that the code is now working and I can focus on other parts of the program
in searching for the reason why the length header is being returned improperly in 
production.

----

Tue Sep  8 20:44:21 PDT 2015:

Fixed error where a for loop in determine_length_of_json_msg() went through each
number in the length string and assigned it to the variable meant to store the 
start of the length string. That is by the time the loop would complete only the
last digit of the length would be stored and converted to the servers internal
representation of what the length for the message is. Fixed this by having the
return statement at the bottom of the function after the loop moved to the if
conditional inside the loop for when the first digit is detected so that it
properly stores the starting position of the length string.

----

Thu Sep 10 15:11:00 PDT 2015:

Client no longer sending data. Appears to be an issue related to the try catch
blocks in make_connection(), currently investigating and will update with more
information.

----

Thu Sep 10 15:36:56 PDT 2015:

Figured out problem, code works fine. (As it should since it hadn't been changed
since the last time it worked.) Instead the problem was with the way I was invoking netcat. I was using netcat -l localhost 9665 instead of netcat -l -p 9665.

----

Thu Sep 10 19:31:53 PDT 2015:

(Cmd) Exception in thread Thread-1:
Traceback (most recent call last):
  File "/usr/lib/python3.2/threading.py", line 740, in _bootstrap_inner
    self.run()
  File "/usr/lib/python3.2/threading.py", line 693, in run
    self._target(*self._args, **self._kwargs)
  File "/home/user/projects/mrc/qa_client.py", line 141, in __init__
    self.loop_forever(connection)
  File "/home/user/projects/mrc/qa_client.py", line 155, in loop_forever
    json_message = json.dumps(message)
  File "/usr/lib/python3.2/json/__init__.py", line 226, in dumps
    return _default_encoder.encode(obj)
  File "/usr/lib/python3.2/json/encoder.py", line 187, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/lib/python3.2/json/encoder.py", line 245, in iterencode
    return _iterencode(o, 0)
  File "/usr/lib/python3.2/json/encoder.py", line 169, in default
    raise TypeError(repr(o) + " is not JSON serializable")
TypeError: b'[138, {"type": "logon", "user": {"username": "Guest3189", "type": "user"}, "server": {"client": "QA_QT1.0", "protocol": "QAServ1.0"}}]\r\n\r\n' is not JSON serializable

Design conflict. My client is currently dumping and encoding json at different
points of the program. Encoding/decoding into UTF-8 and dumping/encoding should
only happen at the start and end of the messaging process. I need to figure out
if I want messages to be passed to the send loop as strings or as JSON. Right 
now the test case set up appends a message delimiter '\r\n\r\n' to the string of
the message. However if we followed this precedent into the rest of the program
 then each message generator would append a delimiter, increasing the 
probability of getting it wrong many times. So the message delimiter should be 
added at the point of send.

----

Sun Sep 20 20:16:19 PDT 2015:

Figured out two problems in server code. First was that 'name' was used to store
username on server and username sent under 'username' key by client code. The
dictionary that stores client information associated with a connection is updated
with a call to update() once the JSON logon message is decoded. This means that
when the update happens 'username' is added to the updated dictionary but the 
'name' key by which the username is actually referred is left empty, thus always
giving the connection the appearance that it has not logged on.

Another problem is that there are no timeouts on the sockets used in the mainloop
of the server. This means that if you have a message in the send queue that is put
there by a seperate thread. (As every message is.) Then you can have a race condition
where the mainloop takes a blocking action before it can detect and send the message,
thus congesting things until another message is sent.

----

Sun Sep 20 22:09:59 PDT 2015:

Think I figured out bug that's been annoying me for a bit now. When the server
sends a message back to the client it uses the code from the client to calculate
the length of the message and send it back. This message is missing the '\r\n\r\n'
message delimiter that is required for all mrc messages. I'll add an exception in
the client side code to handle this. (Update after looking two seconds later: 
There *is* a special exception in the code to handle this which is what raised
an error in the first place I just didn't pay attention to the exception name.)
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
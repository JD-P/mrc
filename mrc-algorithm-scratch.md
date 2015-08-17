Algorithm for recieving messages and passing them to an output queue:

Rationale: When we don't have messages we want to listen for more, when we *do* have
messages we want to process those because listening for messages blocks.

Rough sketch of algorithm:

recieve_msg

extract_msg

select_and_handle_msg

set_buffer

Main loop:
  Do we have data in buffer?
    Yes:
      Check if data includes a complete message.
        Determine length of message
	Check if there's at least that much data in buffer
	If yes:
	  Split buffer at the amount of length specified and check that it has proper
	  end marker.
	  If no:
	    Raise invalid message delimiter error
      If yes:
        send that message to select_and_handle_msg
	set_buffer such that message is removed from buffer
      If no:
        recieve more data and start loop over again
    No:
      recieve more data and start loop over again





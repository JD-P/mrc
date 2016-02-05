from qa_server import *
from PySide.QtCore import *
from PySide.QtGui import *
import sys
import os
import platform
import threading

class DesktopQAServerController():
    """Create a system tray icon to control the qa_server with."""
    def __init__(self):
        self.application = QApplication(sys.argv)
        self.menu = QMenu()
        shutdown = self.menu.addAction("Shutdown")
        shutdown.triggered.connect(self.shutdown_action)
        if os.name == 'posix':
            iconpath = "icons/"
        elif platform.system() == 'Windows':
            iconpath = "icons\\"
        self.icon = QIcon(os.path.join(iconpath, "makerspace_chat.png"))
        self.sys_tray_widget = QSystemTrayIcon()
        self.sys_tray_widget.setIcon(self.icon)
        self.sys_tray_widget.setContextMenu(self.menu)

    def run(self):
        """Post-initialization, show the system tray icon and run the 
        application."""
        self.sys_tray_widget.show()
        self.application.exec_()

    def shutdown_action(self):
        """Shutdown the server when directed from the system tray icon."""
        server.shutdown()
        server.server_close()
        quit()

class ServerThread(threading.Thread):
    def run(self):
        server.serve_forever()

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
    PubSubThread.daemon = True
    PubSubThread.start()
    
    HOST, PORT = arguments.host, arguments.port
    
    server = QAServer((HOST, PORT), MRCStreamHandler)
    
    sthread = ServerThread()
    sthread.start()
    controller = DesktopQAServerController()
    controller.run()

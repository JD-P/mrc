import sys
from PySide.QtCore import *
from PySide.QtGui import *

def test_slot():
    print("Slot activated!")
    sys.exit()

application = QApplication(sys.argv)

icon = QIcon("/home/user/projects/mrc/icons/makerspace_chat.png")

sys_tray_icon = QSystemTrayIcon()

menu = QMenu()
test_action = menu.addAction("Test")
test_action.triggered.connect(test_slot)

sys_tray_icon.setIcon(icon)
sys_tray_icon.setContextMenu(menu)
sys_tray_icon.show()
application.exec_()


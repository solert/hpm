import sys
import os
from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QIcon
from src.dedge_bot import DedgeBot
from src.hpm import Hpm
from constants import ROOT_PATH, SETTINGS_DICT, Version


def run_program():
    # Create app with icon
    app = QApplication(sys.argv)
    # app.setStyle("Fusion")
    software_icon_path = os.path.join(ROOT_PATH, SETTINGS_DICT["software_icon_path"])
    app.setWindowIcon(QIcon(software_icon_path))

    # Create D-Edge bot
    desktop_size = app.screens()[0].availableGeometry()
    bot = DedgeBot(desktop_size)

    # Create ui and run app
    ui = Hpm(bot, desktop_size, version=Version.PREMIUM)
    app.exec_()  # sys.exit(app.exec_())

    # Close the browser when closing the software
    if bot.driver_has_already_been_created:
        bot.destroy()


if __name__ == "__main__":
    run_program()

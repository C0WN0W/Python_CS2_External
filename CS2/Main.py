import threading

from ESP import Esp
import gui

esp = Esp()

gui_thread = threading.Thread(target=gui.render)
esp_thread = threading.Thread(target=esp.run)

gui_thread.start()
esp_thread.start()

gui_thread.join()
esp_thread.join()
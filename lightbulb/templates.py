import shutil
import platform
import os


class templates():
  def load(self, template):
    self.os = platform.system
    if self.os == "windows":
      path = f"C:\\Python312\\Lib\\site-packages\\lightbulb\\templates\\{template}"
    else:
      print("Currently only support windows for automatically coping templates. Please goto you python file and then 'Lib\\site-packages\\lightbulb\\templates\\{template}' to manually copy it")
      return
    dest = os.path.dirname(os.path.realpath(__file__))
    destination = shutil.copytree(path, dest)

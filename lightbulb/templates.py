import shutil
import platform
import os

class template_():
    def __init__(self, template, path, destination=None) -> None:
        self.template = template
        self.path = path
        self.dest = destination
    
    def save(self, rootPath, os, savePath:str="C:\\Python312\\Lib\\site-packages\\lightbulb\\templates"):
        return

class templates():
    def load(self, template, copy:bool=False, dest:str=None) -> None|template_:
        os_ = platform.system()
        if os_ == "windows":
            path = f"C:\\Python312\\Lib\\site-packages\\lightbulb\\templates\\{template}"
        else:
            print("Currently only support windows for automatically coping templates. Please goto you python file and then 'Lib\\site-packages\\lightbulb\\templates\\{template}' to manually copy it")
            return
        #dest = os.path.dirname(os.path.realpath(__file__))
        __template__=template_(template, path, dest)
        if copy == False:
            return __template__
        else:
            self.copy(__template__)


      
    def copy(self, template:template_, dest:str=None) -> None:
        dest = dest or template.dest or os.path.dirname(os.path.realpath(__file__))
        template_ = template.template
        path=template.path
        destination = shutil.copytree(path, dest, copy_function = shutil.copy)
        print(f"Copied {template_} to {destination}")


    def get(self, rootPath, name, copy:bool=False, copyPath:str|None=None, save:bool=False):
        return template_.save(rootPath, platform.system())
    


    def save(self, template:template_.save):
        if template.os == "windows":
            if str(input("Would you like us to save this to the templates folder? Y/n: ").lower() == "y"):
                destination = shutil.copytree(template.rootPath,  copy_function = shutil.copy)
                print(f"Saved to {destination}")

        savePath = input("Please enter the exact absolute path of where to save: ")
        destination = shutil.copytree(template.rootPath, savePath, copy_function = shutil.copy)

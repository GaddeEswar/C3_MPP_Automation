import json
import requests
from datetime import datetime
import os
import time
import psutil
import subprocess
import xml.etree.ElementTree as ET

class JsonOperations:
    def __init__(self,path):
        self.path =path
    def read_file(self):
        try:
            with open(self.path, "r", encoding="utf-8") as rf:
                values = json.load(rf)
            return values
        except Exception as e:
            print(e)
    def update_file(self,values):
        with open(self.path, "w") as outfile:
            json.dump(values, outfile)
    # def CreateResultJson(self,Mode,project):
    #     #create json file for report
    #     now = datetime.now()
    #     timestamp = now.strftime("%d%m%Y_%H%M%S")
    #     reponame = f'{Mode}_{project}_{timestamp}_Offline'
    #     file ='./Results'
    #     path2 = file+'\\'+reponame+'.json'
    #     if os.path.exists(path2):
    #         file_object = open(path2, "w")
    #         file_object.truncate(0)
    #     else:
    #         file_object = open(path2, "w")
    #     #Adding a empty list in result json
    #     li = []
    #     with open(file+'\\'+reponame+'.json', "w") as outfile:
    #         json.dump(li, outfile, default=self.defaultconverter)
    #     #update path in TCP
    #     TCP["test_config_data"]["Report_path"] = str(os.path.abspath(file)).replace("\\", "\\\\")+'\\'+reponame+'.json'
    #     with open('Test_config_properties.json', "w") as outfile:
    #         json.dump(TCP, outfile, default=self.defaultconverter)

    def defaultconverter(o):
        if isinstance(o, datetime.datetime):
            return o.__str__()
        
class APIOperations:
    def __init__(self,url,pathparam=None,retype = None,files =None,param1=None,param2=None,json=None):
        self.url = url
        # self.port = port
        self.pathparam=pathparam
        self.retype = retype
        self.files = files
        self.param1 = param1
        self.param2 =param2
        self.json = json
    def GetRequest(self):
        try:
            url1=self.url
            if self.pathparam is not None: url1= str(url1)+f'/{self.pathparam}'
            if self.param1 is not None: url1=url1.replace('#param1#',str(self.param1))
            if self.param2 is not None: url1=url1.replace('#param2#',str(self.param2))
            print(url1)
            resp = requests.get(url1)
            if resp:
                if self.retype == 'json':
                    return resp.json()
                elif self.retype == 'text':
                    return resp.text
                else: return resp.status_code
            return None
        except Exception as e:
            pass
            # if 'GetAppState','GetMessageBox' not in self.url:
            #     print(e)
    def PutRequest(self):
        try:
            # url=self.url.replace("#port#",str(self.port))
            if self.files is not None:
                resp = requests.put(self.url,files=self.files)
            elif self.json is not None:
                resp = requests.put(self.url,json=self.json)
            else:
                resp = requests.put(self.url)
            # print(self.url,resp)
            return int(resp.status_code)
        except Exception as e:
            print(e)
    def PostRequest(self):
        try:
            if self.json is not None:
                resp = requests.post(self.url,json=self.json)
            # print(self.url,resp)
            return resp.status_code
        except Exception as e:
            print(e)

class GeneralMethods:
    def GetFloatFromStr(strg):
        try:
            appl = ['0','1','2','3','4','5','6','7','8','9','.','-']
            val = []
            id = 0
            # print(strg)
            while id < len(strg):
                # print(id)
                if strg[id] in appl:
                    # print('id',id)
                    tid = id
                    v =[]
                    while tid < len(strg):
                        # print('tid',tid)
                        if strg[tid] in appl:
                            v.append(strg[tid])
                        else:
                            break
                        tid+=1
                    # print(v)
                    if len(v)>0:
                        if len(v) == 1:
                            if all(res not in v for res in ['.','-'] ): 
                                val.append(float(''.join(v)))
                        else:val.append(float(''.join(v)))
                    id=tid
                id+=1
                # print(val)
            return val
        except Exception as e:
            print(e)

class XMLRead:
    def __init__(self,path="C:\\Users\\Dinesh\\Downloads\\OptimumCoilValue.xml"):
        tree = ET.parse(path)
        self.root = tree.getroot()
    
    def ReturnValuesAsJSON(self):
        Rtag = self.root.tag
        for book in self.root.findall(Rtag):
            pass
class Server:
    def __init__(self, Mode,Product):
        self.Mode = Mode
        self.Product = Product

        self.app_folder = os.path.join("C:\\", "Program Files", "GRL", "GRL-C3-MP-TPR", "AppFiles") if self.Mode=="TPR" else  os.path.join("C:\\", "Program Files", "GRL", "GRL-C3-MP-TPT", "AppFiles")
        if self.Product=="C3" and self.Mode=="TPR":self.app_folder=os.path.join("C:\\", "Program Files", "GRL", "GRL-WP-TPR-C3", "AppFiles")

    def is_process_running(self, process_name):
        for process in psutil.process_iter():
            if process.name().lower() == process_name.lower():
                return True
        return False
    def open_C3_server_application(self):
        """
        Open C3 server application if it's not already running
        """
        process_name = {
            ("C3", "TPR"): "C3BrowserApp.exe",
            ("MPP", "TPT"): "C3BrowserApp_C3_TPT.exe",
            ("MPP", "TPR"): "C3BrowserApp_MPP_TPR.exe"
        }[(self.Product, self.Mode)]

        if not self.is_process_running(process_name):
            try:
                subprocess.run(["start", "cmd", "/c", process_name], cwd= self.app_folder, shell=True, check=True)
                time.sleep(10)
            except subprocess.CalledProcessError:
                print(f"{process_name} not found. Make sure the application is installed.")
            except Exception as e:
                print(f"An error occurred while opening the application: {e}")

    def close_C3_server_application(self):
        """
        Close C3 server application if it's running
        """
        process_name = {
            ("C3", "TPR"): "C3BrowserApp.exe",
            ("MPP", "TPT"): "C3BrowserApp_C3_TPT.exe",
            ("MPP", "TPR"): "C3BrowserApp_MPP_TPR.exe"
        }[(self.Product, self.Mode)]
        if self.is_process_running(process_name):
            try:
                subprocess.run(["taskkill", "/f", "/im", process_name], check=True)
                time.sleep(5)
            except subprocess.CalledProcessError:
                print(f"An error occurred while closing {process_name}.")
            except Exception as e:
                print(f"An error occurred while closing the application: {e}")
class ModifyAppPropertyData:
    def __init__(self):
        self.JTester = JsonOperations('json/Tester.json')
        self.JJTesterData =self.JTester.read_file()
        self.JAllMOIRun = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIRunData =self.JAllMOIRun.read_file()
        self.Product = self.JAllMOIRunData['Product']
        self.Mode = self.JAllMOIRunData['Mode']
        self.server = Server(self.Mode, self.Product)
        # Define filename mapping based on Product and Mode
        filenames = {
            #("C3", "TPR"): r"C:\GRL\GRL-WP-TPR-C3\AppData\AppProperty.json",
            ("MPP", "TPT"): r"C:\GRL\GRL-C3-MP-TPT\AppData\AppProperty.json",
            ("MPP", "TPR"): r"C:\GRL\GRL-C3-MP-TPR\AppData\AppProperty.json"
        }

        # Get the appropriate filename based on Product and Mode
        self.filename = filenames.get((self.Product, self.Mode))
        #self.JJTesterData[self.Product][self.Mode]['filepath'] = self.JTester.update_file(self.JJTesterData[self.Product][self.Mode])
        if self.filename:
            self.JJTesterData[self.Product][self.Mode]['filepath'] = self.filename
            self.JTester.update_file(self.JJTesterData)
        else:
            print(f"Error: No valid file path found for Product: {self.Product}, Mode: {self.Mode}")
        if self.Product == "MPP" and self.Mode == "TPT":
            self.server.is_process_running("C3BrowserApp_C3_TPT.exe")
            self.server.close_C3_server_application()
        else:
            self.server.is_process_running("C3BrowserApp_MPP_TPR.exe")
            self.server.close_C3_server_application()

        if self.filename:
            result = self.modify_app_property_filedata(self.filename)
            print(result)
        else:
            print(f"No matching AppProperty.json file found for Product: {self.Product}, Mode: {self.Mode}")

    def modify_app_property_filedata(self, filename):
        """
        Modify the 'Enable_Calibration_Assertions' and 'DisplayMPPTPT_TTVAssertions' values in the given AppProperty.json file to True if they are currently False.
        
        Args:
            filename (str): The path of the AppProperty.json file to modify.
        """
        json_operations = JsonOperations(filename)
        app_property_data = json_operations.read_file()
        
        if not app_property_data:
            return f"Failed to read the JSON file: {filename}"
        
        # Keys to be updated
        keys_to_modify = ["Enable_Calibration_Assertions", "DisplayMPPTPT_TTVAssertions"]
        changes_made = False
        
        for key in keys_to_modify:
            if key in app_property_data:
                key_data = app_property_data[key]
                
                if not (key_data.get("DefaultValue") is True and key_data.get("PropertyValue") is True):
                    key_data["DefaultValue"] = True
                    key_data["PropertyValue"] = True
                    changes_made = True
                    #print(f"Updated '{key}' to have 'DefaultValue' and 'PropertyValue' set to True.")

        if changes_made:
            json_operations.update_file(app_property_data)
            return f"Successfully updated the JSON file: {filename}"
        
    def reloadserver(self):
        self.server.open_C3_server_application()

# Change_Json = ModifyAppPropertyData()



# import json
import orjson
import requests
from datetime import datetime
import time
import psutil
import subprocess
import xml.etree.ElementTree as ET

# class JsonOperations:
#     def __init__(self,path):
#         self.path =path
#     def read_file(self):
#         try:
#             with open(self.path, "r", encoding="utf-8") as rf:
#                 values = json.load(rf)
#             return values
#         except Exception as e:
#             print("Read File Error :",e)
#     def update_file(self,values):
#         with open(self.path, "w") as outfile:
#             json.dump(values, outfile)
 
#     def defaultconverter(o):
#         if isinstance(o, datetime.datetime):
#             return o.__str__()
        
class JsonOperations:
    def __init__(self, path):
        self.path = path

    def read_file(self):
        try:
            with open(self.path, "rb") as rf:   # must be binary mode
                values = orjson.loads(rf.read())
            return values
        except Exception as e:
            print("Read File Error :", e)

    def update_file(self, values):
        try:
            with open(self.path, "wb") as outfile:  # binary mode
                outfile.write(orjson.dumps(values,default=self.defaultconverter,option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS))
        except Exception as e:
            print("Write File Error :", e)

    @staticmethod
    def defaultconverter(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()   # better than __str__()
        raise TypeError(f"Type not serializable: {type(o)}")

class APIOperations:
    _session = requests.Session()  # shared session for all instances

    def __init__(self, url, pathparam=None, retype=None, files=None, param1=None, param2=None, json=None):
        self.url = url
        self.pathparam = pathparam
        self.retype = retype
        self.files = files
        self.param1 = param1
        self.param2 = param2



        self.json = json

    def GetRequest(self):
        try:
            url1 = self.url
            if self.pathparam is not None:
                url1 = f"{url1}/{self.pathparam}"
            if self.param1 is not None:
                url1 = url1.replace('#param1#', str(self.param1))
            if self.param2 is not None:
                url1 = url1.replace('#param2#', str(self.param2))
           

            with self._session.get(url1) as resp:
                if resp:
                    if self.retype == 'json':
                        return resp.json()
                    elif self.retype == 'text':
                        return resp.text
                    else:
                        return resp.status_code
                return None
        except Exception as e:
            print("Get Request Error", e)

    def PutRequest(self):
        try:
            if self.files is not None:
                with self._session.put(self.url, files=self.files) as resp:
                    return resp.status_code
            elif self.json is not None:
                with self._session.put(self.url, json=self.json) as resp:
                    return resp.status_code
            else:
                with self._session.put(self.url) as resp:
                    return resp.status_code
        except Exception as e:
            print("Put Request Error", e)

    def PostRequest(self):
        try:
            if self.json is not None:
                with self._session.post(self.url, json=self.json) as resp:
                    print("Post Request Print", self.url, resp, resp.text)
                    return resp.status_code
        except Exception as e:
            print("Post Request Error", e)

# class APIOperations:
#     def __init__(self,url,pathparam=None,retype = None,files =None,param1=None,param2=None,json=None):
#         self.url = url
#         # self.port = port
#         self.pathparam=pathparam
#         self.retype = retype
#         self.files = files
#         self.param1 = param1
#         self.param2 =param2
#         self.json = json
#     def GetRequest(self):
#         try:
#             url1=self.url
#             if self.pathparam is not None: url1= str(url1)+f'/{self.pathparam}'
#             if self.param1 is not None: url1=url1.replace('#param1#',str(self.param1))
#             if self.param2 is not None: url1=url1.replace('#param2#',str(self.param2))
#             # print(url1)
#             resp = requests.get(url1)
#             if resp:
#                 if self.retype == 'json':
#                     return resp.json()
#                 elif self.retype == 'text':
#                     return resp.text
#                 else: return resp.status_code
#             return None
#         except Exception as e:
#             pass
#             # if 'GetAppState','GetMessageBox' not in self.url:
#             #     print(e)
#     def PutRequest(self):
#         try:
#             # url=self.url.replace("#port#",str(self.port))
#             if self.files is not None:
#                 resp = requests.put(self.url,files=self.files)
#             elif self.json is not None:
#                 resp = requests.put(self.url,json=self.json)
#             else:
#                 resp = requests.put(self.url)
#             # print(self.url,resp)
#             return int(resp.status_code)
#         except Exception as e:
#             print("Put Request Error",e)
#     def PostRequest(self):
#         try:
#             if self.json is not None:
#                 resp = requests.post(self.url,json=self.json)
#             print("Post Request Print",self.url,resp,resp.text)
#             return resp.status_code
#         except Exception as e:
#             traceback.print_exc()

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
            print("GetFloatFromStr Error",e)

class Server:
    def __init__(self):
        #JSON data
        self.Jtester = JsonOperations('json/Tester.json')
        self.JtesterData =self.Jtester.read_file()

        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.Mode = self.JAllMOIData['Mode']
        self.Product = self.JAllMOIData['Product']

        self.StatusLogs = UpdateStatusLogs()
    def AutoCheck(self):
        #1. Check for the SW is running 
        AppStatus = self.CheckSelectedAppRunningStatus()
        if AppStatus == True:
            self.StatusLogs.update_logs("UI",f"{self.Product}-{self.Mode} Software is running")
            #SW is running, check for the tags to be enabled if that is already set ignore
            if self.Product=='MPP' and self.Mode=='TPR':
                if self.AppPropertyCheck() == False:
                    self.StatusLogs.update_logs("UI",f"AppProperty file required tags are not set to true")
                    #Close the running app and update the properies to true and re-open the SW
                    self.StatusLogs.update_logs("UI",f"Closing the software for update the property tags")
                    self.CloseApp()
                    self.UpdateAppProperty()
                    self.StatusLogs.update_logs("UI",f"Launching the software...")
                    self.OpenApp()
        else:
            self.StatusLogs.update_logs("UI",f"{self.Product}-{self.Mode} software is currently not running,Please wait for the tool to launch the software and establish the connection")
            #SW is not running
            if self.Product=='MPP' and self.Mode=='TPR':
                self.StatusLogs.update_logs("UI",f"AppProperty file tags are setting to true")
                self.UpdateAppProperty()
            self.StatusLogs.update_logs("UI",f"Launching the software...")
            self.OpenApp()
    def CheckSelectedAppRunningStatus(self):
        GetSWversion = APIOperations(url=self.JapiData[self.Product][self.Mode]['GetSoftwareVersion'])
        res = GetSWversion.GetRequest()
        if res is None:
            return False
        else:return True
    def AppPropertyCheck(self):
        res = []
        #check for the mentioned tags are set to true
        AppPro = JsonOperations(self.JtesterData[self.Product][self.Mode]['PropertyPath'])
        AppProData = AppPro.read_file()
        for tags in self.JtesterData[self.Product][self.Mode]['PropertyTags']:
            if tags in AppProData:
                if AppProData[tags]['DefaultValue'] == True and AppProData[tags]['PropertyValue']==True:
                    res.append("Pass")
                else:res.append("Fail")
            else:print(f"{tags} not available in the AppProperty file")
        return False if 'Fail' in res else True 
    def UpdateAppProperty(self):
        AppPro = JsonOperations(self.JtesterData[self.Product][self.Mode]['PropertyPath'])
        AppProData = AppPro.read_file()
        for tags in self.JtesterData[self.Product][self.Mode]['PropertyTags']:
            if tags in AppProData:
                AppProData[tags]['DefaultValue'] = True 
                AppProData[tags]['PropertyValue'] = True
            else:print(f"{tags} not available in the AppProperty file")
            # print(AppProData[tags])
        AppPro.update_file(AppProData) 
    def CloseApp(self):
        process_name = self.JtesterData[self.Product][self.Mode]['ProcessName']
        if self.is_process_running(process_name):
            try:
                subprocess.run(["taskkill", "/f", "/im", process_name], check=True)
                time.sleep(3)
                return True
            except subprocess.CalledProcessError:
                print(f"An error occurred while closing {process_name}.")
            except Exception as e:
                print(f"An error occurred while closing the application: {e}")
        else:
            print(f"{process_name} is not running.")
        return False
    def OpenApp(self):
        process_name = self.JtesterData[self.Product][self.Mode]['ProcessName']
        app_folder = self.JtesterData[self.Product][self.Mode]['ExecutableLocation']
        if not self.is_process_running(process_name):
            try:
                subprocess.run(["start", "cmd", "/c", process_name], cwd= app_folder, shell=True, check=True)
                time.sleep(10)
            except subprocess.CalledProcessError:
                print(f"{process_name} not found. Make sure the application is installed.")
            except Exception as e:
                print(f"An error occurred while opening the application: {e}")
        else:
            print(f"{process_name} is already running.")
    def is_process_running(self, process_name):
        for process in psutil.process_iter():
            if process.name() == process_name:
                return True
        return False
    

class UpdateStatusLogs:
    def __init__(self):
        self.JLogs = JsonOperations("json/DebugLogs.json")
        self.JLogsData = self.JLogs.read_file()
    def update_logs(self,logtype,log):
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.JLogsData = self.JLogs.read_file()
        self.JLogsData.append([str(dt_object),logtype,log])
        self.JLogs.update_file(self.JLogsData)
        # if logtype == 'UI':self.LogsUI()

class XMLRead:
    def __init__(self,path="C:\\Users\\Dinesh\\Downloads\\OptimumCoilValue.xml"):
        tree = ET.parse(path)
        self.root = tree.getroot()
    
    def ReturnValuesAsJSON(self):
        Rtag = self.root.tag
        for book in self.root.findall(Rtag):
            pass
        #     for 

# obj = Server()
# status = obj.AutoCheck()
# obj.OpenApp()
# print(status)
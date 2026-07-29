import traceback
import datetime,time
from datetime import datetime,date
import threading
import time
# from Scripts.MainModule import JsonOperations,APIOperations,GeneralMethods
# from Scripts.postool import PosTool

from MainModule import JsonOperations,APIOperations,GeneralMethods
from postool import PosTool

class GetOptimumPosition():
    def __init__(self,coil):
        
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData =self.JAllMOI.read_file()

        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.product = self.JAllMOIData['Product']
        self.mode = self.JAllMOIData['Mode']
        self.AllRun = self.JsettingsData['Runall']
        self.postool = PosTool()
        self.JLogs = JsonOperations("json/DebugLogs.json")
        self.JLogsData = self.JLogs.read_file()
        #Set Current position as Home i.e. 0,0
        # self.postool.SendCommands(self.ArduinoCon,f"MOVE_X SetHome")
        # self.postool.SendCommands(self.ArduinoCon,f"MOVE_Y SetHome")
        # self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z SetHome")
        self.XaxisSteps = 0
        self.YaxisSteps = 0
        #API's Required
        # print({"dutName":self.JsettingsData['OptimumData']['DUTname'],"coilType":self.JsettingsData['OptimumData']['DUTname'],"position":"(0,0)"})
        self.API_Start_Optimum = APIOperations(url=self.JapiData[self.product][self.mode]['PutOptimum'],json={"dutName":"XXXXX","coilType":str(coil),"position":"(0,0)"}) #TPR : {"dutName":"XXXXX","coilType":"MPP_TPR1","position":"(0,0)"}
        self.APIstate_Tester = APIOperations(url=self.JapiData[self.product][self.mode]['GetAppState'],retype='json')
        self.APIpopup =  APIOperations(url=self.JapiData[self.product][self.mode]['GetMessageBox'],retype='json')
        self.APIHandlePopup = APIOperations(url=self.JapiData[self.product][self.mode]['PutMessageBoxResponse'])
        self.APIForceStop = APIOperations(url=self.JapiData[self.product][self.mode]['StopTestExecution'])
       
        self.RunOptimumPos()
       
    def RunOptimumPos(self):
        try:
            self.update_logs("UI","Optimum position check Excecution started.")
            self.postool.Disconnection()
            self.ArduinoCon = self.postool.Connection(port=self.JsettingsData['PositionTool']['Port'])

            # print(self.ArduinoCon)
            if self.ArduinoCon is not None and 'Not Connected' not in self.ArduinoCon:
                self.update_logs("UI","Position tool connected.")
                print("Position tool connected.")
                #Set Current position as Home i.e. 0,0
                # self.postool.SendCommands(self.ArduinoCon,f"MOVE_X SetHome")
                # self.postool.SendCommands(self.ArduinoCon,f"MOVE_Y SetHome")
                # self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z SetHome")
                #1. Run Optimum position
                # self.API_Start_Optimum.json={"dutName":self.JsettingsData['OptimumData']['DUTname'],"coilType":self.JsettingsData['OptimumData']['DUTname']}
                threading.Thread(target=self.API_Start_Optimum.PutRequest).start()
                time.sleep(1)
                while True:
                    # print("Running")
                    self.HandlePopUps()
                    if self.GetTesterBusyStatus() == False: break
                    if self.CheckThreadStop() == True:
                        self.APIForceStop.GetRequest()
                        break
            else:
                print('Not connected')
                self.update_logs("UI",f"Position not tool connected.!, Try to connect the tool and proceed.")
            self.update_logs("UI","Optimum position check Excecution completed.")
            print("Optimum position check Excecution completed.")
            self.postool.Disconnection()
        except Exception as e:
            traceback.print_exc()
        
    def GetTesterBusyStatus(self):
        Testrundata = self.APIstate_Tester.GetRequest()
        if Testrundata is not None:
            if Testrundata['appState'] == 'READY':
                return False
        return True
    def HandlePopUps(self):
        try:
            self.APIpopup.url=self.JapiData[self.product][self.mode]['GetMessageBox']
            data = self.APIpopup.GetRequest()
            if data is not None:
                if data['isValid']==True and data['message'] not in ['']:
                    #SS/Vrect
                    if 'Default SS Values were consider to plot Quadratic expression' in data['message']:
                        #handle popup
                        popupdata = {"userTextBoxInput":":","responseButton":"Yes","shouldTextBoxBeAdded":False,"isValid":True,"popID":data['index'],"displayPopUp":False,"isDisplayPopUpOpen":False,"title":"GRL-C3-MP-TPR Test Solution","message":data['message'],"button":"YesNo","image":None,"icon":"Asterisk","isFrontEndPopUp":False,"callBackMethod":None,"comboBoxEntries":None,"comboBoxEntriesFE":[],"selectedComboBoxValueFE":"","onlyDropdownAdded":False,"enableTimerOKButton":False,"enableCustomUserInputs":False,"customInputValues":{},"backgroundColor":""}
                        self.APIHandlePopup.url=self.JapiData[self.product][self.mode]['PutMessageBoxResponse']
                        self.APIHandlePopup.json=popupdata
                        res = self.APIHandlePopup.PutRequest()
                        print(res)
                    elif 'Position the Power ' in  data['message']:
                        print(data['message'])
                        pos = GeneralMethods.GetFloatFromStr(data['message'])
                        print("pos:",pos)
                        self.update_logs("UI",f"Moving in position tool X={pos[0]}mm , Y={pos[1]}mm")
                        print(f"Moving in position tool X={pos[0]}mm , Y={pos[1]}mm")
                        self.XaxisSteps = self.XaxisSteps + int(pos[0]/0.05)
                        self.YaxisSteps = self.YaxisSteps + int(pos[1]/0.05)
                        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {float(self.JsettingsData['PositionTool']['MOVE_Z'])*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm'])}")
                        time.sleep(1)
                        #Move X axis 
                        if pos[0] != 0.0:
                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                            time.sleep(1)
                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_X {int(pos[0]*self.JsettingsData['PositionTool']['Motors']['StepsTomm'])}")
                        else: self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                        time.sleep(1)
                        #Move Y axis 
                        if pos[1] != 0.0:
                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_Y Home")
                            time.sleep(1)
                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_Y {int(pos[1]*self.JsettingsData['PositionTool']['Motors']['StepsTomm'])}")
                        else: self.postool.SendCommands(self.ArduinoCon,f"MOVE_Y Home")
                        time.sleep(1)
                        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                        #read pop-up and adjust position tool
                        time.sleep(2)
                        #Handle Pop-up
                        popupdata = {"userTextBoxInput":"","responseButton":"Ok","shouldTextBoxBeAdded":False,"isValid":True,"popID":data['index'],"displayPopUp":False,"isDisplayPopUpOpen":False,"title":"GRL-C3-MP-TPR Test Solution","message":data['message'],"button":"OK","image":None,"icon":"Asterisk","isFrontEndPopUp":False,"callBackMethod":None,"comboBoxEntries":None,"comboBoxEntriesFE":[],"selectedComboBoxValueFE":"","onlyDropdownAdded":False,"enableTimerOKButton":False,"enableCustomUserInputs":False,"customInputValues":{}}
                        self.APIHandlePopup.url=self.JapiData[self.product][self.mode]['PutMessageBoxResponse']
                        self.APIHandlePopup.json=popupdata
                        self.APIHandlePopup.PutRequest()
                    else:
                        #click Ok by defualt for other pop-ups
                        popupdata = {"userTextBoxInput":"","responseButton":"Ok","shouldTextBoxBeAdded":False,"isValid":True,"popID":data['index'],"displayPopUp":False,"isDisplayPopUpOpen":False,"title":"GRL-C3-MP-TPR Test Solution","message":data['message'],"button":"OK","image":None,"icon":"Asterisk","isFrontEndPopUp":False,"callBackMethod":None,"comboBoxEntries":None,"comboBoxEntriesFE":[],"selectedComboBoxValueFE":"","onlyDropdownAdded":False,"enableTimerOKButton":False,"enableCustomUserInputs":False,"customInputValues":{}}
                        self.APIHandlePopup.url=self.JapiData[self.product][self.mode]['PutMessageBoxResponse']
                        self.APIHandlePopup.json=popupdata
                        self.APIHandlePopup.PutRequest()
                    # print('got popup',data['index'],data['message'])
        except Exception as e:
            traceback.print_exc()
    def update_logs(self,logtype,log):
        try:
            dt_object = datetime.fromtimestamp(datetime.now().timestamp())
            self.JLogsData.append([str(dt_object),logtype,log])
            self.JLogs.update_file(self.JLogsData)
        except Exception as e: 
            traceback.print_exc()
    def CheckThreadStop(self):
        self.JsettingsData =self.Jsettings.read_file()
        if self.JsettingsData['_stop_flag'] == True:
            return True
        return False
# obj = GetOptimumPosition()
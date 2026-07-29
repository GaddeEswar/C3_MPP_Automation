import threading
import sys
sys.path.append('Scripts')
from MainModule import JsonOperations,APIOperations
# from offlineValidation import OfflineValidation
from postool import PosTool
from datetime import datetime,date
# from Scripts.SmartPlug import WiproPlug

# from MPPGUIform_New import MPPGUI
import traceback
import time
import json,os,glob
from SQLite import SQLiteConnection 


class RunTests():
    def __init__(self,fltr):
        #Get inputs from JSON
        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        self.Jtester = JsonOperations('json/Tester.json')
        self.JtesterData =self.Jtester.read_file()
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JQI = JsonOperations('json/QIconfig.json')
        self.JQIData = self.JQI.read_file()
        self.JMOI = JsonOperations('json/MOIJson.json')
        self.JMOIData = self.JMOI.read_file()
        self.JTestConf = JsonOperations('json/TestConfig.json')
        self.JTestConfData = self.JTestConf.read_file()
        self.JTCP = JsonOperations('json/Test_config_properties.json')
        self.JTCPData = self.JTCP.read_file()
        self.JLogs = JsonOperations("json/DebugLogs.json")
        self.JLogsData = self.JLogs.read_file()
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.JEsdf = JsonOperations('json/ESDF.json')
        self.JEsdfData = self.JEsdf.read_file()
        self.TesterConfig = JsonOperations('json/TesterConfig.json')
        self.TesterConfigData = self.TesterConfig.read_file()
        self.mode = self.JAllMOIData['Mode']
        self.Product = self.JAllMOIData['Product']
        self.SQLConn = SQLiteConnection()
        # if self.JAllMOIData['SPConnection']:
        #     from Scripts.SmartPlug2 import WiproPlug
        #     self.smartplug_obj = WiproPlug()
            
        self.TestStop = False
        # print("mode:",self.mode)
        self.postool = PosTool()
        # self.ArduinoCon = self.postool.Connection(port=self.JsettingsData['PositionTool']['Port'])
        self.filters = fltr
        if self.mode =='TPT':
            self.DUTport = self.JtesterData[self.Product]['TPR']['port'] 
            self.Testerport = self.JtesterData[self.Product]['TPT']['port'] 
            self.DUT = 'TPR'
        else :
            self.DUTport = self.JtesterData[self.Product]['TPT']['port']
            self.Testerport = self.JtesterData[self.Product]['TPR']['port'] 
            self.DUT = 'TPT'
        #define API's
        self.APIcreateProj_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['PutProjectFolder'],json={"projectName":self.JsettingsData['Online_validation'][self.DUT]['ProjectName'],"moiName":"MPP"})
        self.APIcreateProj_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['PutProjectFolder'],json={"projectName":self.JsettingsData['Online_validation'][self.mode]['ProjectName'],"moiName":"MPP"})
        
        self.APISendQI_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['PutQIConfiguration'],json=self.JQIData[self.Product][self.DUT])
        self.APISendQI_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['PutQIConfiguration'],json=self.JQIData[self.Product][self.mode])
        
        self.APIStartTest_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['PostTestListToExecute'])
        self.APIStartTest_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['PostTestListToExecute'])
        
        self.APIstate_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['GetAppState'],retype='json')
        self.APIstate_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['GetAppState'],retype='json')
        
        self.APIForceStop_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['StopTestExecution'])
        self.APIForceStop_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['StopTestExecution'])
        
        self.APIStartExcer_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['EXCR_PutStartExerciser'])
        self.APIStartExcer_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['EXCR_PutStartExerciser'])
        
        self.APIStopExcer_Tester = APIOperations(url=self.JapiData[self.Product][self.mode]['EXCR_GetStopExerciser'])
        self.APIStopExcer_DUT = APIOperations(url=self.JapiData[self.Product][self.DUT]['EXCR_GetStopExerciser'])
        
        self.APIpopup =  APIOperations(url=self.JapiData[self.Product][self.DUT]['GetMessageBox'],retype='json')
        self.APIHandlePopup = APIOperations(url=self.JapiData[self.Product][self.DUT]['PutMessageBoxResponse'])

        self.APICurrentTC = APIOperations(url=self.JapiData[self.Product][self.mode]['GetTestStatus'],retype='json')

        self.Setcertificate =  APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutCertificationFilter']}/{self.JAllMOIData['Certificate']}")
        self.APIReportsIP = APIOperations(url=self.JapiData[self.Product][self.mode]['PostUpdateReportInputs'],json={"manufacturer":"","modelNumber":"","serialNumber":"","testLab":"","testEngineer":"","remarksComments":"","testlabmanager":"","testlablocation":"","email":"","phonenumber":"","qiID":"","productName":""})
        self.APIAppActiveTrue = APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutApplicationActiveStatus']}/true")
        self.APIAppActiveFalse = APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutApplicationActiveStatus']}/false")
        self.APITempFalse = APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutTemperatureSelectionMode']}/false")
        self.APIExButnStus = APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutExecutionButtonStatus']}",json={"fodStartTestCaseInProgress":False,"fodStartCaptureInProgress":False,"optimumCoilInProgress":False,"loadRampInProgress":False,"testStatusInProgress":True,"readCapsInProgress":False,"readCertificateInProgress":False})
        self.APICapData = APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutGetCapabilitiesData']}",json={"bsutName":"Sample","majorVersion":1,"minorVersion":2,"manufacturerCode":"0x0000","guaranteedPower":5,"potentialPower":15,"wpid":False,"ai":False,"ob":False,"dupSupport":False,"bufferSize":0,"nrs":False,"negotiablePower":5,"concurrentDataStreams":0,"g_coil_Rx":0,"estimatedK":0})
        self.APIClearCaptures = APIOperations(url=f"{self.JapiData[self.Product][self.mode]['PutClearCapture']}")
        #new
        self.APIPutESDFData=APIOperations(url=self.JapiData[self.Product][self.mode]['PutESDFData'],json=self.JEsdfData[self.Product][self.mode])
        if self.Product == "MPP":self.APIPutTesterReportConfig=APIOperations(url=self.JapiData[self.Product][self.mode]['PutTesterReportConfig'],json=self.TesterConfigData[self.Product][self.mode])
        if self.filters['TAD']==True:
            #Run auto. mode
            if self.filters['TADmode'] =='Automation Tests':
                self.RunTesterAsDUTAuto()
            else: 
                self.RunTesterAsDUTExcer()
        else:
            #Run Normal Mode of with DUT
            self.RunTestOnDUT()   
            #self.OfflineValidationAFRun()

    def RunTestOnDUT(self):
        try:
            self.JAllMOIData = self.JAllMOI.read_file()
            self.JTestConfData = self.JTestConf.read_file()
            self.JsettingsData =self.Jsettings.read_file()

            if self.Product == "MPP":
                if self.filters['PositionTool']:
                    self.postool.Disconnection()
                    self.ArduinoCon = self.postool.Connection(port=self.JsettingsData['PositionTool']['Port'])

                if self.JTestConfData['SPConnection'] and self.JAllMOIData['Run']['EnableSmartSwitch']:
                    from SmartPlug2 import WiproPlug
                    self.smartplug_obj = WiproPlug()
                    self.smartplug_obj.TogglePlug("ON") #initially plug should be in ON state
                    self.JAllMOIData['Run']['SmartSwitch_Mode']=True
                    self.JAllMOI.update_file(self.JAllMOIData)

            # CurrentTC = ""
            # 1. Ensure Tester Connected
            if self.JtesterData[self.Product][self.mode]['status'] == 'Connected':
                # #Set certification
                # self.Setcertificate.PutRequest()
                # 2. Send QI config
                # self.APIClearCaptures.PutRequest()
                # self.APISendQI_Tester.PutRequest()
                # self.APIReportsIP.PostRequest()
                # self.APIAppActiveTrue.PutRequest()
                # self.APITempFalse.PutRequest()
                # self.APIExButnStus.PutRequest()
                # self.APICapData.PutRequest()

                # 3.  Get the list of tests to be run
                # print("self.filters['Rerun']:",self.filters['Rerun'])
                if self.Product == "MPP":
                    # if self.filters['Rerun']:
                    #     TestObj = self.SQLConn.FetchDataFromQRY(f"SELECT Testcase from AllTestcases WHERE Status=1 and TestResult IN ('Fail', 'Inconclusive')")
                    if len(self.filters['Pos'])==1:
                        TestObj = self.SQLConn.FetchDataFromQRY(f"SELECT Testcase from AllTestcases WHERE Status=1 and Position = '{self.filters['Pos'][0]}'")
                    else:TestObj = self.SQLConn.FetchDataFromQRY(f"SELECT Testcase from AllTestcases WHERE Status=1 and Position in {tuple(self.filters['Pos'])}")
                else:TestObj = self.SQLConn.FetchDataFromQRY(f"SELECT Testcase from AllTestcases WHERE Status=1")
                # print("TestObj:", TestObj)
                TestList = list(TestObj['Testcase']) if TestObj is not None else []
                print("TestList:",TestList)

                if len(TestList)>0:
                    self.APIClearCaptures.PutRequest()
                    # self.APIPutESDFData.PutRequest()
                    if self.Product == "MPP":self.APIPutTesterReportConfig.PutRequest()
                    # if not self.filters['Rerun']:
                    self.APIReportsIP.PostRequest()
                    self.APICapData.PutRequest()
                    if self.Product =="MPP" and self.mode =="TPR":self.APITempFalse.PutRequest()
                    self.APIExButnStus.PutRequest()

                    #Adjust The Position tool, make sure to coil placed on home
                    
                    if self.Product =="MPP" and self.filters['PositionTool'] == True:
                        self.update_logs("UI",f"Moving position tool Z to home")
                        print("Moving position tool Z to home")
                        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                    repcount = self.JAllMOIData['Run']['RepeatCount']
                    repid = 0
                    print("repcount:",repcount)

                    # Start Automatic pop-up handling in thread
                    threading.Thread(target=self.handlePopup,daemon=True).start()

                    while repid <= repcount:
                        CurrentTC = ""
                        self.update_logs("UI", f"Run {repid}/{repcount}")
                        # 4.clear coil filters - new feature updated in the 2.210.1.8 MPP TPR
                        # self.APIGetAllCoils = APIOperations(url=self.JapiData[self.Product][self.mode]['GetCoilFilter'],retype='json')
                        # Coils = self.APIGetAllCoils.GetRequest()
                        # self.APISetCoils= APIOperations(url=self.JapiData[self.Product][self.mode]['PutCoilFilter'],json=Coils)
                        # self.APISetCoils.PutRequest()
                        
                        # 5. Start the testcase on Tester
                        self.APIStartTest_Tester.json = TestList
                        self.APIStartTest_Tester.PostRequest()

                        if self.JAllMOIData['SPConnection'] and self.JAllMOIData['Run']['EnableSmartSwitch'] and self.JAllMOIData['Run']['PowerOFF&ON']: threading.Thread(target=self.ONOFF,daemon=True).start()

                        # time.sleep(2)
                        TCcount = 1
                        # self.PosToolPopUp()
                        while True:
                            try:
                                # Get Current Test to show in logs
                                CurTC = self.APICurrentTC.GetRequest()
                                # print("CurTC:",CurTC)
                                if CurTC is not None:
                                    if 'Test Status' in CurTC:
                                        if 'Test' in CurTC['Test Status']:
                                            if CurTC['Test Status'].split(':')[1].replace(' ','') != CurrentTC:
                                                # if self.JAllMOIData['SPConnection'] and self.JAllMOIData['Run']['PowerOFF&ON']:
                                                #     print("common toggling")
                                                #     self.smartplug_obj.TogglePlug("OFF&ON") #power off and power on dut
                                                CurrentTC = CurTC['Test Status'].split(':')[1].replace(' ','')
                                                self.update_logs("UI", f"Test case: {CurrentTC} In progress {TCcount}/{len(TestList)}|Run:{repid}/{repcount}")
                                                TCcount+=1

                                                Testcasepos = self.SQLConn.FetchDataFromQRY(f"SELECT Position FROM AllTestcases WHERE Testcase like '%{CurrentTC}'")
                                                print("TCobj",Testcasepos)
                                                TCpos = list(Testcasepos['Position'])[0] if Testcasepos is not None else ""
                                                print("TCpos",TCpos)



                                                if (self.Product =="MPP" and self.mode == "TPR" and self.filters['PositionTool'] == True and not (any(resp in CurrentTC for resp in ['BEFOREPOWER', 'PREPOWER', 'PARAMETER', 'MPP_PTX_NEG_POW_KEST_SLIDING']) and TCpos in ["0.0,0.0"])):
                                                    #Since the has varity of msgs to remove and place coils,by default Remove the Coil once test execution completes and place after 7sec . the place pop-up will come and handled by the time.
                                                    #Remove Coil
                                                    self.update_logs("UI",f"Moving position tool Z={self.JsettingsData['PositionTool']['MOVE_Z']} mm")
                                                    self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {int(float(self.JsettingsData['PositionTool']['MOVE_Z'])*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                                                    #Move Axis - 
                                                    #fetch testcase details form DB
                                                    print("CurrentTC:",CurrentTC)
                                                    # Testcasepos = self.SQLConn.FetchDataFromQRY(f"SELECT Position FROM AllTestcases WHERE Testcase like '%{CurrentTC}'")
                                                    # print("TCobj",Testcasepos)
                                                    # TCpos = list(Testcasepos['Position'])[0] if Testcasepos is not None else ""
                                                    # print("TCpos",TCpos)
                                                    xvalue = '0.0'
                                                    zvalue = '0.0'
                                                    if TCpos !="":
                                                        xvalue = str(TCpos).split(",")[0]
                                                        zvalue = str(TCpos).split(",")[1]
                                                        self.update_logs("UI",f"Moving coil X-axis ={xvalue}")
                                                        if xvalue =="0.0":
                                                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                                                        else:
                                                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                                                            time.sleep(1)
                                                            self.postool.SendCommands(self.ArduinoCon,f"MOVE_X {int(float(xvalue)*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                                                    #Place Coil
                                                    time.sleep(2)
                                                    self.update_logs("UI",f"Moving position tool Z Home")
                                                    self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                                                    # self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {int((float(self.JsettingsData['PositionTool']['MOVE_Z'])-float(zvalue))*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm']))*-1}")
                                                    time.sleep(2)
                                # Force stop user I/p
                                if self.GetProcessStatus():
                                    self.APIForceStop_Tester.GetRequest()
                                    self.APIForceStop_Tester.GetRequest()
                                    time.sleep(2)
                                    while True:
                                        Testrundata = self.APIstate_Tester.GetRequest()
                                        print("appState:",Testrundata['appState'])
                                        if Testrundata is not None:
                                            if Testrundata['appState'] == 'READY':
                                                #self.update_logs("UI", 'Test Execution stopped')
                                                break
                                    self.update_logs("UI", 'Force stopping execution.......')
                                    self.TestStop = True
                                    break
                                Testrundata = self.APIstate_Tester.GetRequest()
                                if Testrundata is not None:
                                    if Testrundata['appState'] == 'READY':
                                        # self.update_logs("UI", 'Test Execution stopped')
                                        self.TestStop = True
                                        break
                            except Exception as e:
                                traceback.print_exc()
                        if self.GetProcessStatus():
                            self.APIForceStop_Tester.GetRequest()
                            self.APIForceStop_Tester.GetRequest()
                            break
                        repid += 1
                        self.TestStop = False
                        time.sleep(0.5)
                    #set all axis to home by default
                    if self.filters['PositionTool']: 
                        #self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {int(float(self.JsettingsData['PositionTool']['MOVE_Z'])*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                        time.sleep(1)
                        self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                        time.sleep(1)
                        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                else:
                    self.update_logs("UI", f'No testcases listed')
            self.APIAppActiveFalse.PutRequest()
            self.JsettingsData['_stop_flag'] = True
            self.JsettingsData['_Logs_flag'] = True
            self.Jsettings.update_file(self.JsettingsData)
            
            self.postool.Disconnection()
        except Exception as e:
            traceback.print_exc()

    def ONOFF(self):
        CurrentTC = ""
        while True:
            try:
                print('ONOFF loop - teststop:',self.TestStop)
                CurTC = self.APICurrentTC.GetRequest()
                if CurTC is not None:
                    if CurTC['Test Status']:
                        if CurTC['Test Status'].split(':')[1].replace(' ','') != CurrentTC:
                            # print("CurTC:",CurTC['Test Status'].split(':')[1].replace(' ',''))
                            self.smartplug_obj.TogglePlug("OFF&ON") #power off and power on dut
                            CurrentTC = CurTC['Test Status'].split(':')[1].replace(' ','')
                if self.TestStop: break       
            except Exception as e:
                traceback.print_exc()
    def PosToolPopUp(self):
        print("Pop-Up Tool")
        #remove
        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {float(self.JsettingsData['PositionTool']['MOVE_Z'])*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm'])}")
        #Place
        # time.sleep(1)
        self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")

    def GetProcessStatus(self):
        self.JsettingsData =  self.Jsettings.read_file()
        if self.JsettingsData is not None:
            # print("GetProcessStatus:",self.JsettingsData['_stop_flag'])
            return self.JsettingsData['_stop_flag']
            # return False
        return None
    
    def update_logs(self,logtype,log):
        # print("log:",log)
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.JLogsData.append([str(dt_object),logtype,log])
        self.JLogs.update_file(self.JLogsData)
    def Pos_PopUp(self):
        pass
    def RunTesterAsDUTAuto(self):
        #1.Ensure both testers are connected
        if self.JtesterData[self.Product]['TPR']['status'] =='Connected':
            if self.JtesterData[self.Product]['TPT']['status'] =='Connected':
                #2.create project folder for both tester and DUT
                self.APIcreateProj_Tester.PutRequest()
                self.APIcreateProj_DUT.PutRequest()
                #3.send qi config for bother tester and DUT
                self.APISendQI_Tester.PutRequest()
                self.APISendQI_DUT.PutRequest()
                repcount = self.JQIData[self.Product][self.mode]['repCount']
                repid = 0
                while repid <= repcount:
                    #3.Loop through onebyone tests from tester.
                    for pos in self.filters['Pos']:
                        if len(self.JTestConfData[self.mode][pos])>0:
                            for Tests in self.JTestConfData[self.mode][pos]:
                                print("Tests:",Tests)
                                if 'DUTTestID' in self.JMOIData[Tests]:
                                    try:
                                        if self.JMOIData[Tests]['DUTTestID'] not in ['NA','Excerciser']:
                                            #run DUT side tests in automation
                                            #1. start the testcase on DUT side
                                            self.APIStartTest_DUT.json=[self.JMOIData[self.JMOIData[Tests]['DUTTestID']]['Testcase_Name']]
                                            self.APIStartTest_DUT.PostRequest()
                                            # self.handlePopup(self.DUT)
                                            #wait for 2sec delay
                                            time.sleep(3)
                                            self.handlePopup(self.DUT)
                                            #start from Tester side
                                            self.APIStartTest_Tester.json=[self.JMOIData[Tests]['Testcase_Name']]
                                            self.APIStartTest_Tester.PostRequest()
                                            #wait until tests to complete
                                            while True:
                                                try:
                                                    #handle popup
                                                    self.handlePopup(self.DUT)
                                                    self.handlePopup(self.mode)
                                                    Testrundata = self.APIstate_Tester.GetRequest()
                                                    Dutrundata= self.APIstate_DUT.GetRequest()
                                                    #if DUT stopped and Tester still running force stop the Tester
                                                    if Dutrundata['appState']=='READY':
                                                        print('Test force stopping from Tester side')
                                                        self.APIForceStop_Tester.GetRequest()
                                                    if Testrundata['appState']=='READY':
                                                        print('Test Ended from Tester side')
                                                        while True:
                                                                self.handlePopup(self.DUT)
                                                                Dutrundata= self.APIstate_DUT.GetRequest()
                                                                if Dutrundata['appState']!='READY':
                                                                    #force stop the Tester DUT
                                                                    print('Test force stopping from DUT side')
                                                                    self.APIForceStop_DUT.GetRequest()
                                                                    break
                                                                    #wait for Test to stop
                                                                else: 
                                                                    print('Execution Stopped at DUT side')
                                                                    break
                                                        break
                                                except Exception as e:
                                                    traceback.print_exc()
                                            time.sleep(2)
                                        else:
                                            #Run excerciser mode, d
                                            pass
                                    except Exception as e: 
                                        traceback.print_exc()
                    repid+=1
            else:print('TPT not connnected')
        else:print('TPR not connnected')
    def RunTesterAsDUTExcer(self):
        print(f'Running as {self.DUT} as DUT, from {self.mode}')
        TestList = []
        #1.Ensure both testers are connected
        if self.JtesterData[self.Product]['TPR']['status'] =='Connected':
            if self.JtesterData[self.Product]['TPT']['status'] =='Connected':
                #2.create project folder for both tester and DUT
                self.APIcreateProj_Tester.PutRequest()
                self.APIcreateProj_DUT.PutRequest()
                #3.send qi config for bother tester and DUT
                self.APISendQI_Tester.PutRequest()
                self.APISendQI_DUT.PutRequest()
                #get the list of tests to be run ,
                for pos in self.filters['Pos']:
                    if len(self.JTestConfData[self.mode][pos])>0:
                        for Tests in self.JTestConfData[self.mode][pos]:
                            #select only tests has no confg. DUTTestid
                            if 'DUTTestID' not in self.JMOIData[Tests]:
                                TestList.append(self.JMOIData[Tests]['Testcase_Name'])
                if len(TestList)>0:
                    #Start DUT tester Excerciser mode
                    #1.Reset Excerciser
                    self.ResterExcerciser(self.DUT)
                    self.handlePopup(self.DUT)
                    #2.Start Excerciser
                    self.APIStartExcer_DUT.PutRequest()
                    #consider repcont ,since SW api not found use repeat mode using tester
                    repcount = self.JQIData[self.Product][self.mode]['repCount']
                    repid = 0
                    while repid <= repcount:
                        #1. start the testcase on Tester
                        self.APIStartTest_Tester.json=TestList
                        self.APIStartTest_Tester.PostRequest()
                        #Run untile tester stops
                        while True:
                            try:
                                self.handlePopup(self.mode)
                                self.handlePopup(self.DUT)
                                Testrundata = self.APIstate_Tester.GetRequest()
                                if Testrundata['appState']=='READY':
                                    print('Test Ended')
                                    break
                            except Exception as e:
                                traceback.print_exc()
                        repid+=1
                    #Stop Excerciser
                    self.APIStopExcer_DUT.GetRequest()
                    #Call the offline Validation
                    if self.mode == 'TPR': self.OfflineValidationAFRun()
            else:print('TPT not connnected')
        else:print('TPR not connnected')
    def handlePopup(self):
        try:
            while True:
                self.JAllMOIData = self.JAllMOI.read_file()
                self.APIpopup.url=self.JapiData[self.Product][self.mode]['GetMessageBox']
                data = self.APIpopup.GetRequest()
                if data is not None:
                    if data['isValid']==True and data['message'] not in ['']:
                        if self.filters['EnableSmartSwitch']:
                            if any(res in str(data['message']).lower() for res in ["power off","powered off","power on the ptxdut with its surface clear","power on the ptx and click ok","power off and then power on the ptx-dut","click ok, then remove power","click ok, then power on"]):
                                self.update_logs("POPUP : SmartSwitch",f"{data['message']}:{time.time()}")
                                if "powered off" in str(data['message']).lower():
                                    print("condition1")
                                    #ensure that the Switch mode is true 
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==True:
                                        print("smartswitch:",data['message'])
                                        self.smartplug_obj.TogglePlug("OFF")
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONOROFF")
                                        time.sleep(0.5)
                                        self.respondpopup(data)
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=False
                                        self.JAllMOI.update_file(self.JAllMOIData)
                                 
                                elif "power off" in str(data['message']).lower():
                                    print("condition2")
                                    #ensure that the Switch mode is true 
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==True:
                                        print("smartswitch:",data['message'])
                                        self.smartplug_obj.TogglePlug("OFF")
                                        time.sleep(0.5)
                                        self.respondpopup(data)
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONOROFF")
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=False
                                        self.JAllMOI.update_file(self.JAllMOIData)
                                    
                                elif "click ok, then power on" in str(data['message']).lower():
                                    print("condition3")
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==False:
                                        print("smartswitch:",data['message'])
                                        self.respondpopup(data)
                                        time.sleep(0.5)
                                        self.smartplug_obj.TogglePlug("ON")
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONOROFF")
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=True
                                        self.JAllMOI.update_file(self.JAllMOIData)
                               
                                elif "power on the ptxdut with its surface clear" in str(data['message']).lower():
                                    print("condition4")
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==False:
                                        print("smartswitch:",data['message'])
                                        self.respondpopup(data)
                                        time.sleep(0.5)
                                        self.smartplug_obj.TogglePlug("ON")
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONOROFF")
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=True
                                        self.JAllMOI.update_file(self.JAllMOIData)
                                elif "power on the ptx and click ok" in str(data['message']).lower():
                                    print("condition5")
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==False:
                                        print("smartswitch:",data['message'])
                                        self.smartplug_obj.TogglePlug("ON")
                                        time.sleep(0.5)
                                        self.respondpopup(data)
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONOROFF")
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=True
                                        self.JAllMOI.update_file(self.JAllMOIData)
                                elif "power off and then power on the ptx-dut" in str(data['message']).lower():
                                    print("condition6")
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==True:
                                        print("smartswitch:",data['message'])
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONANDOFF")
                                        self.smartplug_obj.TogglePlug("OFF&ON")
                                        time.sleep(0.5)
                                        self.respondpopup(data)
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=True
                                        self.JAllMOI.update_file(self.JAllMOIData)
                                elif "click ok, then remove power" in str(data['message']).lower():
                                    print("condition7")
                                    if self.JAllMOIData['Run']['SmartSwitch_Mode']==True:
                                        print("smartswitch:",data['message'])
                                        self.respondpopup(data)
                                        time.sleep(0.5)
                                        self.smartplug_obj.TogglePlug("OFF")
                                        #self.postool.SendCommands(self.ArduinoCon,"SmartPlug ONOROFF") #power off
                                        self.JAllMOIData['Run']['SmartSwitch_Mode']=False
                                        self.JAllMOI.update_file(self.JAllMOIData)
                                      
                                #self.respondpopup(data)
                        if self.filters['PositionTool']:
                            # print("handlepopup5")
                            print("PositionTool:",str(data['message']).lower())
                            self.update_logs("POPUP : PositionTool",f"{data['message']}:{time.time()}")
                            if any(res in str(data['message']).lower() for res in ["please remove the"]):
                                self.update_logs("UI",f"Moving position tool Z={self.JsettingsData['PositionTool']['MOVE_Z']} mm")
                                self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {int(float(self.JsettingsData['PositionTool']['MOVE_Z'])*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                                self.respondpopup(data)
                            elif all(res in str(data['message']).lower() for res in ["place"]):
                                if self.Product == "MPP" and self.mode == "TPR":
                                    self.respondpopup(data)
                                    time.sleep(1)
                                    self.update_logs("UI",f"Moving position tool Z to home")
                                    self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                                elif self.Product == "MPP" and self.mode == "TPT":
                                    self.update_logs("UI",f"Moving position tool Z to home")
                                    self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                                    time.sleep(2)
                                    self.respondpopup(data)

                            # elif 'increase the radial position (r) of the tpr' in data['message']:
                            #     Xaxis = float(str(data['message']).split()[-5])
                            #     self.update_logs("UI",f"Moving in position tool X={Xaxis}mm")
                            #     self.postool.SendCommands(self.ArduinoCon,f"MOVE_X {int(Xaxis*self.JsettingsData['PositionTool']['Motors']['StepsTomm'])}")   

                            # elif 'Adjust the position of the coil to' in data['message']:
                            #     Xaxis = int(str(data['message']).split('(')[1].split(',')[0])
                            #     self.update_logs("UI",f"Moving in position tool X={Xaxis}mm")
                            #     if Xaxis == 0: 
                            #         self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                            #     else:
                            #         self.postool.SendCommands(self.ArduinoCon,f"MOVE_X Home")
                            #         self.postool.SendCommands(self.ArduinoCon,f"MOVE_X {int(Xaxis*self.JsettingsData['PositionTool']['Motors']['StepsTomm'])}") 

                            elif 'Place the BSUT at Z' in data['message']:
                                Zaxis = int(str(data['message']).split('Z=')[1].split('mm')[0].replace(' ',''))
                                self.update_logs("UI",f"Moving position tool Z={Zaxis} mm")
                                self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z {int(float(self.JsettingsData['PositionTool']['MOVE_Z'])*float(self.JsettingsData['PositionTool']['Motors']['StepsTomm']))}")
                                #Wait for sometime to user to place the slider
                                time.sleep(3)
                                self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                            # else:
                            #     self.postool.SendCommands(self.ArduinoCon,f"MOVE_Z Home")
                            print("Other POPUPs:",str(data['message']).lower())
                            self.update_logs("POPUP",f"{data['message']}:{time.time()}")
                            # print(data)
                            self.respondpopup(data)

                        print("Other POPUPs:",str(data['message']).lower())
                        self.update_logs("POPUP",f"{data['message']}:{time.time()}")
                        print(data)
                        self.respondpopup(data)
                        
                # Force stop user I/p
                if self.GetProcessStatus(): break
        except Exception as e:
            traceback.print_exc()
    def respondpopup(self,data):
        #handle popup
        if self. Product == "MPP":
            popupdata = {"userTextBoxInput":"","responseButton":"Ok","shouldTextBoxBeAdded":False,"isValid":True,"popID":data['index'],"displayPopUp":False,"isDisplayPopUpOpen":False,"title":data['title'],"message":data['message'],"button":"OK","image":None,"icon":"Asterisk","isFrontEndPopUp":False,"callBackMethod":None,"comboBoxEntries":None,"selectedComboBoxValue":"","comboBoxEntriesFE":[],"selectedComboBoxValueFE":"","onlyDropdownAdded":False,"enableTimerOKButton":False,"enableCustomUserInputs":False,"customInputValues":{},"backgroundColor":""}
        else:
            popupdata = {"userTextBoxInput":"","responseButton":"Ok","shouldTextBoxBeAdded":False,"isValid":True,"popID":data['index'],"displayPopUp":False,"isDisplayPopUpOpen":False,"title":data['title'],"message":data['message'],"button":"OK","image":None,"icon":"Asterisk","isFrontEndPopUp":False,"callBackMethod":None,"comboBoxEntries":None,"selectedComboBoxValue":"PASS","comboBoxEntriesFE":[],"selectedComboBoxValueFE":"","onlyDropdownAdded":False,"enableTimerOKButton":False,"enableCustomUserInputs":False,"customInputValues":{}}
        self.APIHandlePopup.url=self.JapiData[self.Product][self.mode]['PutMessageBoxResponse']
        self.APIHandlePopup.json=popupdata
        resp = self.APIHandlePopup.PutRequest()
        print("APIHandlePopup:",resp)
        # self.APIHandlePopup.PutRequest()
    def OfflineValidationAFRun(self):
        print('Offline Validation')
        path = self.JtesterData[self.Product][self.mode]['ReportPath']
        repo = list(filter(os.path.isdir, glob.glob(path+ "/*"))) 
        repo.sort(key=os.path.getctime) 
        id = len(repo)-1
        while id >= 0:
            # print(repo[id])
            if all(res not in repo[id] for res in  ['TempReport','CurrentReport','OfflineReport']):
                CurrentRunPath = repo[id]
                break
            id-=1
        # print(CurrentRunPath)
        #clear existing projects
        self.JsettingsData['Offline_validation']['json_path'][self.Product][self.mode].clear()
        self.JsettingsData['Offline_validation']['json_path'][self.Product][self.mode].append(CurrentRunPath)
        self.Jsettings.update_file(self.JsettingsData)
        self.JTestConfData[self.Product][self.mode]['Offline'].clear()
        self.JTestConf.update_file(self.JTestConfData)
        #Add current project
        jsonlist=[]
        # if '_MPP_' in CurrentRunPath:
        # for root, dirs, files in os.walk(CurrentRunPath):
        #     for d in dirs:
        #         if d.startswith("Run"):
        #             if os.path.join(root, d) not in self.JsettingsData['Offline_validation']['json_path'][self.Product][self.mode]:
        #                 # print(os.path.join(root, d))
        #                 jsonlist.append(os.path.join(root, d))
        # self.JsettingsData['Offline_validation']['json_path'][self.Product][self.mode].extend(jsonlist)
        # self.Jsettings.update_file(self.JsettingsData)
        #Prepare for Validation list
        TClist={}
        projects = self.JsettingsData['Offline_validation']['json_path'][self.Product][self.mode]
        if len(projects)>0:
            for pro in projects:
                filepath = None
                jsonpath = None
                for root, dirs, files in os.walk(pro):
                    for file in files:
                        if file.endswith(".gproj") and file.__contains__("Run"):
                            filepath = os.path.join(root, file)
                        if file.endswith(".json") and file.__contains__("Run"):
                            jsonpath = os.path.join(root, file) 
                if filepath is not None and jsonpath is not None:
                    # print(os.path.join(pro,filepath))
                    test = JsonOperations(os.path.join(pro,filepath))
                    testdata =test.read_file()
                    proname = str(filepath.split('\\')[len(filepath.split('\\'))-4])+'-'+str(filepath.split('\\')[len(filepath.split('\\'))-3])
                    if proname not in TClist:TClist[proname] ={}
                    for tcl in testdata['testBkpTestResultsandPath']:
                        if 'testinformation' in tcl:
                            if tcl['testinformation'] is not None:
                                if tcl['testcaseDetails']['m_DisplayName'] is not None and tcl['testinformation']['TestResult'] not in [' ',None,'NotRun']:
                                    # if any(self.master.JMOIData[self.master.Mode][i].get('Testcase_Name') == tcl['testcaseDetails']['m_DisplayName'] for i in self.master.JMOIData[self.master.Mode] if str(self.master.Mode)+"_TD_" in i):
                                        testpath = tcl['actualTracePath'].split('\\')
                                        TClist[proname][tcl['testcaseDetails']['m_DisplayName']]=[tcl['testcaseDetails']['m_TestId'],pro+'\\'+testpath[len(testpath)-2]+'\\'+testpath[len(testpath)-1],jsonpath]
            self.JTestConfData[self.Product][self.mode]['Offline'].clear()
            self.JTestConfData[self.Product][self.mode]['Offline']=TClist
            self.JTestConf.update_file(self.JTestConfData)
        # #Start tests
        # TraceUPL = APIOperations(url=self.JapiData[self.Product][self.mode]['PutWaveformFile'])
        # TCstatus = APIOperations(url=self.JapiData[self.Product][self.mode]['TCstatus'],retype='json')
        # if len(self.JTestConfData[self.mode]['Offline'])>0:
        #     for ProjRun in self.JTestConfData[self.mode]['Offline']:
        #         #Create Json for Results TBD--
        #         self.CreateResultJson(ProjRun)
        #         if len(self.JTestConfData[self.mode]['Offline'][ProjRun])>0:
        #            for tests in self.JTestConfData[self.mode]['Offline'][ProjRun]:
        #                 TraceUPL.files = {"WaveformFile":open(self.JTestConfData[self.mode]['Offline'][ProjRun][tests][1].replace('/','\\'),"rb")}
        #                 status = int(TraceUPL.PutRequest())
        #                 if status == 200:
        #                     t_end = time.time() + 60
        #                     while time.time() < t_end:
        #                         data = TCstatus.GetRequest()
        #                         if len(data['2']['displayDataChunk'])>0:
        #                             #call Validation
        #                             #----class call
        #                             # print(tests) 
        #                             if self.JMOIData[tests]['Status'] == True:
        #                                 pass
        #                                 # Offval = OfflineValidation(TestID=tests,ProjectJson=self.JTestConfData[self.mode]['Offline'][ProjRun][tests][2],TracePath=self.JTestConfData[self.mode]['Offline'][ProjRun][tests][1])
        #                             else: print(f'No Validation config for Test {tests}')
        #                             # Offval.UpdateHeaderInfo()
        #                             #call old scripts
        #                             # os.system(f"py Scripts\TCvalidation.py {tests} {str(self.JTestConfData[self.mode]['Offline'][ProjRun][tests][1]).replace(' ','#')} {str(self.JTestConfData[self.mode]['Offline'][ProjRun][tests][2]).replace(' ','#')}")
        #                             break
    def CreateResultJson(self,project):
        #create json file for report
        now = datetime.now()
        timestamp = now.strftime("%d%m%Y_%H%M%S")
        reponame = f'{self.mode}_{project}_{timestamp}_Offline'
        path ="Results\\JsonReports\\"+reponame+'.json'
        li = []        
        resjson = JsonOperations(path)
        resjson.update_file(li)
        #update path in TCP
        print(str(os.path.abspath(path)))
        self.JTCPData["test_config_data"]["Report_path"] = str(os.path.abspath(path))
        self.JTCP.update_file(self.JTCPData)
    def ResterExcerciser(self,mode):
        for apis in self.JapiData[mode]:
            print("apis:",apis)
            if 'EXCR_RS' in apis:
                rsobj = APIOperations(url=self.JapiData[mode][apis])
                if 'Get' in apis: rsobj.GetRequest()
                if 'Put' in apis:rsobj.PutRequest()
            #setpackets
            if 'EXCR_SPK_' in apis:
                if '_PutModulatorValues360' in apis:
                    inobj = APIOperations(url=self.JapiData['TPR']['EXCR_GetModulatorValues'],retype='json')
                    inres = indata = inobj.GetRequest()
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis],json=indata)
                    outres = rsobj.PutRequest()
                elif '_PutRxCoil' in apis:
                    inobj = APIOperations(url=self.JapiData['TPR']['EXCR_GetRxCoilValues'],retype='json')
                    inres =indata = inobj.GetRequest()
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis],json=indata)
                    outres =rsobj.PutRequest()
                elif '_PutTxCoil' in apis:
                    inobj = APIOperations(url=self.JapiData['TPR']['EXCR_GetTxCoil'],retype='json')
                    inres =indata = inobj.GetRequest()
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis],json=indata)
                    outres =rsobj.PutRequest()
                elif '_PutPhaseSetting' in apis:
                    inobj = APIOperations(url=self.JapiData['TPR']['EXCR_GetDefaultPhaseSettings'],retype='json')
                    inres =indata = inobj.GetRequest()
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis],json=indata)
                    outres =rsobj.PutRequest()
                elif '_PutQiPacketInformation' in apis:
                    Packetdata = JsonOperations('json/TPTSetPackets.json')
                    Packetdataval =Packetdata.read_file()
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis],json=Packetdataval)
                    outres = rsobj.PutRequest()
                    inres=0
                elif '_PutSelectedQiSpecMode' in apis:
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis])
                    outres =rsobj.PutRequest()
                    inres=0
                elif '_GetRxCoilRectifiedReadings' in apis:
                    rsobj = APIOperations(url=self.JapiData['TPR'][apis])
                    outres =rsobj.GetRequest()
                    inres=0
        #Enable clock if DUT is TPT
        if mode=='TPT':
            enclkobj = APIOperations(url=self.JapiData[mode]['EXCR_EnableClk'],json={"enableCloak":True})
            enclkobj.PutRequest()
# fltr = {'Pos': ['0,0'], 'TAD': False, 'TADmode': '', 'PowerProfile': 'MPP', 'PositionTool': False}
# obj = RunTests(fltr)
# obj.OfflineValidationAFRun()
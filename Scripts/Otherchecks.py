import json

import requests
from MainModule import JsonOperations,APIOperations


class otherchecks():
    def __init__(self):
        #define jsons
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

        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
    
    def MatchMOItestwithApp(self,mode):
        MOItests = []
        SWtests = []
        #Get tests list from MOIjson
        for header in self.JMOIData:
            if mode+'_TD_' in header:
                MOItests.append(self.JMOIData[header]['Testcase_Name'])
        #Get Tests from SW
        apptests = requests.get(f'http://localhost:{self.JtesterData[mode]["port"]}/api/TestConfiguration/GetTestCaseList/APP')
        testdata = apptests.json()
        for phase in testdata[0]['children']:
            for test in phase['children']:
                SWtests.append(test['key'])
        if len(MOItests)>0 and len(SWtests)>0:
            print('Test Not macthing/avaialable with SW')
            for mts in MOItests:
                if mts not in SWtests:
                    print(mts)
            print('Tests not matching/avaialable with MOI')
            for sts in SWtests:
                if sts not in MOItests:
                    print(sts)

    def GetAllMOITCcount(self):
        cnt = 0
        for Coil in self.JAllMOIData['All_Testcases']:
            for Phase in self.JAllMOIData['All_Testcases'][Coil]:
                for TC in self.JAllMOIData['All_Testcases'][Coil][Phase]:
                    cnt+=1
        print(cnt)
    #Get Testcases and i'ts CTS checks from the CTS version file
    def GetTestcaseCTSChks(self):
        Results = {}
        JCTS = JsonOperations("json/CTSvalidation/CTSChecks_MPP25W_WD5V_3.0.json")
        JCTSData = JCTS.read_file()
        for Checks in JCTSData['MPP']['TPR']:
            for TC in JCTSData['MPP']['TPR'][Checks]:
                if TC not in Results:Results[TC]=[]
                Results[TC].append(Checks)
        # print(Results)
        for tc in Results:
            
            print(tc)
    #Update CTS 

#JOSN operations
class JOSNOPE():
    def __init__(self):
        Jtemp = JsonOperations('json/t2.json')
        JtempData =Jtemp.read_file()
        for Phase in JtempData['testResults'][0]['children']:
            for Testcase in Phase['children']:
                if Testcase['result'] == 'RUNNING':
                    print(Phase['displayString'],Testcase['displayString'])
#Backtest the APIS
class APICheck():
    def __init__(self):
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.JQI = JsonOperations('json/QIconfig.json')
        self.JQIData = self.JQI.read_file()
        self.mode = "TPR"
        # #Active status
        # self.APIACtiveStus = APIOperations(url="http://localhost:2002/api/App/PutApplicationActiveStatus/true")
        # res = self.APIACtiveStus.PutRequest()
        # print(res)
        # #certificate
        # self.Setcertificate =  APIOperations(url=f"{self.JapiData[self.mode]['PutCertificationFilter']}/{self.JAllMOIData['Certificate']}")
        # res = self.Setcertificate.PutRequest()
        # print(res)
        # #Qi
        # self.APISendQI_Tester = APIOperations(url=self.JapiData[self.mode]['PutQIConfiguration'],json=self.JQIData[self.mode])
        # res = self.APISendQI_Tester.PutRequest()
        # print(res)
        # #Repoerts in
        # self.APIReportsIP = APIOperations(url=self.JapiData[self.mode]['PostUpdateReportInputs'],json={"manufacturer":"samsung","modelNumber":"24","serialNumber":"124","testLab":"","testEngineer":"Gokul","remarksComments":"","testlabmanager":"","testlablocation":"","email":"","phonenumber":"","qiID":"24","productName":""})
        # res = self.APIReportsIP.PostRequest()
        # print(res)
        # #Temp
        # #Active status
        # self.APItemp = APIOperations(url="http://localhost:2002/api/CustomAPIConfiguration_MPPTPR/PutTemperatureSelectionMode/false")
        # res = self.APItemp.PutRequest()
        # print(res)
        #clear coil filters
        self.APIGetAllCoils = APIOperations(url=self.JapiData[self.mode]['GetCoilFilter'],retype='json')
        Coils = self.APIGetAllCoils.GetRequest()
        self.APISetCoils= APIOperations(url=self.JapiData[self.mode]['PutCoilFilter'],json=Coils)
        res = self.APISetCoils.PutRequest()
        print(Coils,res)
        #Testcase run
        self.APIStartTest_Tester = APIOperations(url=self.JapiData[self.mode]['PostTestListToExecute'])
        self.APIStartTest_Tester.json = ["6.1 MPP.PTX.POW.Digital_Ping_128kHz_P1", "6.2 MPP.PTX.POW.Digital_Ping_360kHz_P1"]
        res = self.APIStartTest_Tester.PostRequest()

        print(res)

# obj =  APICheck()

oc = otherchecks()
oc.GetTestcaseCTSChks()
# oc.GetAllMOITCcount()

# obj =  JOSNOPE()
        

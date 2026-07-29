import sys
sys.path.append('Scripts')
from MainModule import APIOperations,JsonOperations,UpdateStatusLogs
from SQLite import SQLiteConnection
import traceback
# from MainModule import APIOperations,JsonOperations

class ALLMOIModule():
    def __init__(self):
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JAllMOI = JsonOperations('json/AllMOIRun.json')
        self.JAllMOIData = self.JAllMOI.read_file()
        self.JTestConfig = JsonOperations('json/TestConfig.json')
        self.JTestConfigData = self.JTestConfig.read_file()
        self.SQLConn = SQLiteConnection()
        # self.JAllMOIData['Mode'] = self.JAllMOIData['Mode']
        # self.PP =self.JAllMOIData['PowerProfile']
        # self.JAllMOIData['Product'] = self.JAllMOIData['Product']
        
    def PrepareTestCases(self):
        #Get filters from DB
        PhasesObj = self.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE FilterType='Phase' and Status=1")
        CatObj = self.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE FilterType='Cat' and Status=1")
        CoilObj = self.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE FilterType='Coil' and Status=1")
        OffsetObj = self.SQLConn.FetchDataFromQRY(f"SELECT Name FROM TestFilters WHERE FilterType='offset' and Status=1")

        PhaseList = list(PhasesObj['Name']) if PhasesObj is not None else []
        CatList = list(CatObj['Name']) if CatObj is not None else []
        CoilList = list(CoilObj['Name'])  if CoilObj is not None else []
        OffsetList = list(OffsetObj['Name']) if OffsetObj is not None else []
        Phases =  f"('{PhaseList[0]}')" if len (PhaseList) == 1 else tuple(PhaseList)
        Categories = f"('{CatList[0]}')" if len (CatList) == 1 else tuple(CatList)
        Offsets =  f"('{OffsetList[0]}')" if len (OffsetList) == 1 else tuple(OffsetList)
        Coils =  f"('{CoilList[0]}')" if len (CoilList) == 1 else tuple(CoilList)
        #set all TC as 0 first
        self.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases set Status=0")
        #Update status as 1 for the filtered TCs
        # self.SQLConn.ExecutebyQuery(f"UPDATE AllTestcases set Status=1 WHERE Coil in {Coils} and Position in {Offsets} and Phase in {Phases}")
        query = f"UPDATE AllTestcases SET Status=1 WHERE Coil IN {Coils}"
        # Add Position condition only if Offsets is not empty
        if Offsets:
            query += f" AND Position IN {Offsets}"
        # Add Phase condition
        query += f" AND Phase IN {Phases}"
        # Execute the query
        self.SQLConn.ExecutebyQuery(query)
    def GetAllTestcases(self):
        try:
            AllTestData = []
            TestFilters = []
            phase=[]
            offset = []
            Coil = []
            Cat = []
            #To get all the applicable testcase for the selected product and mode and sync with DB
            self.JAllMOIData = self.JAllMOI.read_file()
            self.GetTestList = APIOperations(url=f"{self.JapiData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['GetTestCaseList']}",retype='json')
            TCdata = self.GetTestList.GetRequest()
            # print("TCdata:",TCdata)
            if TCdata is not None:
                if len(TCdata)>0:
                    for PhaseData in TCdata[0]['children']:
                        if PhaseData['key'] not in phase:phase.append(PhaseData['key'])
                        for TC in PhaseData['children']:
                            #if TC['coilPosition']=="":print("check:",TC)
                            AllTestData.append({
                                "Product":self.JAllMOIData['Product'],
                                "Mode":self.JAllMOIData['Mode'],
                                "Certificate":self.JAllMOIData['Certificate'],
                                "PowerProfile":self.JAllMOIData['PowerProfile'],
                                "Coil":TC['coilType'],
                                "Position":TC['coilPosition'].replace('(','').replace(')','') if TC['coilPosition'] else 'NA',
                                "Phase":PhaseData['key'],
                                "Testcase":TC['key'],
                                "FF1":"NA" if TC['testNotification'] == "" else TC['testNotification'].upper(),
                                "FF2":"NA",
                                "FF3":"NA",
                                "FF4":"NA",
                                "TestResult":"Not Tested",
                                "Status":1
                            })
                            if TC['coilType'] not in Coil : Coil.append(TC['coilType'])
                            #if TC['coilPosition'] != "" and TC['coilPosition'].replace('(','').replace(')','') not in offset: offset.append(TC['coilPosition'].replace('(','').replace(')',''))
                            #offset.append(TC['coilPosition'].replace('(','').replace(')','')) if TC['coilPosition'] not in offset and TC['coilPosition'] != "" and TC['coilPosition'] is not None and TC['coilPosition'].replace('(','').replace(')','') not in offset else offset.append()
                            if TC['coilPosition'] and TC['coilPosition'].replace('(','').replace(')','') not in offset: 
                                offset.append(TC['coilPosition'].replace('(','').replace(')',''))
                            elif 'NA' not in  offset and TC['coilPosition'] == "" and TC['coilPosition'] is not None:
                                offset.append("NA")
                            
                            if TC['testNotification'] and TC['testNotification'].upper() not in Cat: 
                                Cat.append(TC['testNotification'].upper())
                            elif TC['testNotification'] == "" and "NA" not in Cat:
                                Cat.append("NA")
                else: 
                    self.SQLConn.ExecutebyQuery("DELETE FROM AllTestcases")
                    self.SQLConn.ExecutebyQuery("DELETE FROM TestFilters")
                    # self.SQLConn.DeleteTableData("AllTestcases")
                    # self.SQLConn.DeleteTableData("TestFilters")
            else:print("Issue in Testcase API")
            Cat.sort()
            if len(AllTestData)>0:
                self.SQLConn.DeleteTableData("AllTestcases")
                self.SQLConn.InsertDataFromDict("AllTestcases",AllTestData)
                #sync Testfilters
                for val in Coil:TestFilters.append({"FilterType":"Coil","Name":val,"Status":1,"Product":self.JAllMOIData['Product'],"Mode":self.JAllMOIData['Mode']})
                for val in phase:TestFilters.append({"FilterType":"Phase","Name":val,"Status":1,"Product":self.JAllMOIData['Product'],"Mode":self.JAllMOIData['Mode']})
                for val in offset:TestFilters.append({"FilterType":"offset","Name":val,"Status":1,"Product":self.JAllMOIData['Product'],"Mode":self.JAllMOIData['Mode']})
                for val in Cat: TestFilters.append({"FilterType":"Cat","Name":val,"Status":1,"Product":self.JAllMOIData['Product'],"Mode":self.JAllMOIData['Mode']})
                self.SQLConn.DeleteTableData("TestFilters")
                self.SQLConn.InsertDataFromDict("TestFilters",TestFilters)
        except Exception as e:
            traceback.print_exc()
    

    # def create_offlinetestcases_table(self):
    #     """Create the OfflineTestcases table if it doesn't exist"""
    #     query = """
    #     CREATE TABLE IF NOT EXISTS OfflineTestcases (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         Product TEXT NOT NULL,
    #         Mode TEXT NOT NULL,
    #         TestCase VARCHAR(255) NOT NULL,
    #         TestID VARCHAR(255) NOT NULL,
    #         TracePath VARCHAR(255) NOT NULL,
    #         JsonPath VARCHAR(255) NOT NULL,
    #         BackupPath VARCHAR(255),
    #         Status INTEGER NOT NULL
    #     )
    #     """        
    #     self.SQLConn.ExecutebyQuery(query)  # Ensure this method executes SQL commands

    # def Offlinetestcase(self):
    #     try:
    #         self.create_offlinetestcases_table()  # Ensure table is created before inserting

    #         AllTestData = []
    #         TestFilters = []
    #         # Retrieve test cases from JSON and format them
    #         for project_name, test_cases in self.JTestConfigData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['Offline'].items():
    #             for test_case_name, test_case_details in test_cases.items():
    #                 AllTestData.append({
    #                     "Product": self.JAllMOIData['Product'],
    #                     "Mode": self.JAllMOIData['Mode'],
    #                     "TestCase": test_case_name,
    #                     "TestID": test_case_details[0],
    #                     "TracePath": test_case_details[1],
    #                     "JsonPath": test_case_details[2],
    #                     "BackupPath": test_case_details[3] if len(test_case_details) > 3 else None,
    #                     "Status": 1                  
    #                 })
            
    #         # Insert into DB
    #         if len(AllTestData)>0:
    #             self.SQLConn.DeleteTableData("OfflineTestcases")  # Optional: Clears old data
    #             self.SQLConn.InsertDataFromDict("OfflineTestcases", AllTestData)
    #             for val in test_case_name:TestFilters.append({"FilterType":"Tescasename","Name":val,"Status":1})
    #             # print(TestFilters)
    #             self.SQLConn.DeleteTableData("TestFilters")
    #             self.SQLConn.InsertDataFromDict("TestFilters",TestFilters)
        
    #     except Exception as e:
    #         traceback.print_exc()


    def GetApplicablePosPhase(self):
        try:
            self.JAllMOIData = self.JAllMOI.read_file()
            #API's
            self.GetAllPos = APIOperations(url=self.JapiData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['GetCoilFilter'],retype='json')
            self.PutPosFilter = APIOperations(url=self.JapiData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['PutCoilFilter'])
            if self.JAllMOIData['Product'] in ["C3","MPP"] and self.JAllMOIData['Mode']=="TPT":
                self.GetTestList = APIOperations(url=f"{self.JapiData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['GetTestCaseList']}",retype='json')
            else:
                self.GetTestList = APIOperations(url=f"{self.JapiData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['GetTestCaseList']}",retype='json')
            # print(self.JAllMOIData['Mode'],self.PP)
            #get All Applicable Positions
            # print(self.GetAllPos.url)
            self.JAllMOIData = self.JAllMOI.read_file()
            Pos = self.GetAllPos.GetRequest()
            print(Pos)
            if Pos is not None:
                self.JAllMOIData['Offset']={}
                self.JAllMOIData['All_Testcases']={}
                self.JAllMOIData['Chapters']={}
                for p in Pos:
                    # print(p)
                    self.JAllMOIData['Offset'][p.replace('(','').replace(')','')]=True
                    # self.JAllMOIData['Offset'].append(p.replace('(','').replace(')',''))
                    #Load All applicable Testcases by loading each positions.
                    self.PutPosFilter.json = [p]
                    self.PutPosFilter.PutRequest()
                    #Fetch Testcase
                    TCdata = self.GetTestList.GetRequest()
                    # print(self.GetTestList.url)
                    # print(TCdata)
                    if TCdata is not None:
                        if len(TCdata)>0:
                            self.JAllMOIData['All_Testcases'][p.replace('(','').replace(')','')]={}
                            for PhaseData in TCdata[0]['children']:
                                self.JAllMOIData['All_Testcases'][p.replace('(','').replace(')','')][PhaseData['key']]=[]
                                if PhaseData['key'] not in self.JAllMOIData['Chapters']: self.JAllMOIData['Chapters'][PhaseData['key']]=True
                                for TestData in PhaseData['children']:
                                    self.JAllMOIData['All_Testcases'][p.replace('(','').replace(')','')][PhaseData['key']].append(TestData['key'])
                self.JAllMOI.update_file(self.JAllMOIData)
                self.PrepareTestCases()
        except Exception as e:
            traceback.print_exc()
    #deg Skip current running Testcases
    def SkipTestcase(self):
        self.SkipTC = APIOperations(url=f"{self.JapiData[self.JAllMOIData['Product']][self.JAllMOIData['Mode']]['PutSkipTestCase']}")
        res = self.SkipTC.PutRequest()
        print("skip response:",res)
# obj = ALLMOIModule()
# obj.PrepareTestCases()
# obj.GetAllTestcases()
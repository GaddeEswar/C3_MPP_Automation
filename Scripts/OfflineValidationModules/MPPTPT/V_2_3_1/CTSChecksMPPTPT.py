import traceback
import re
import io
import zipfile
import pandas as pd
import csv
import json
import math
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Scripts.Enums import Enums
from Scripts.TestConfigs import *
from OfflineValidationModules.MPPTPT.CommonHelper import CommonCTSChecks


class CTSChecks_MPPTPT():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson):

        #Define Global variables
        CTS = JsonOperations('json/CTSvalidation/MPPTPT.json')
        self.JCTSData =CTS.read_file()
        # self.JCTSData = JCTSData
        self.JapiData = JapiData
        self.Header = Header
        self.Product = GeneralConfig.Product
        self.Mode = GeneralConfig.Mode
        self.file_list = file_list
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
        self.TestResultsjson = JsonOperations("json/TestResults.json")
        self.TestData = self.TestResultsjson.read_file()
        # with open('BckupJson.json', 'w') as json_file:
        #     json.dump(self.BKjsonData, json_file, indent=4)
        self.AuthPktAPI = APIOperations(url=self.JapiData[GeneralConfig.Product][GeneralConfig.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        #Define modules
        self.PktMethod = PacketMethods(file_list=self.file_list,Header=self.Header)
        self.PlotMethod = PlotMethods(Header=self.Header)
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        self.CTSMethod=CommonCTSChecks(file_list=self.file_list,Header=self.Header,JapiData=JapiData,BackupJson=BackupJson,Product=GeneralConfig.Product,Mode=GeneralConfig.Mode)

   
    def CTSChecks(self,flwID,flows,CTSJson):
        
        AllMeasures={}
        for CTSCheck in CTSJson:
            AllMeasures[CTSCheck] = None
            AllMeasures[f'{CTSCheck}_Details']=[]
            AllMeasures[f'{CTSCheck}_exp']="NA"
            for Check in CTSJson[CTSCheck]:
                if Check['flow'] == flwID:
                    self.Flow_limit = flows[flwID]['Limit']
                 #Validation checks starts_______________________
                    try:
                        methodcall=getattr(self, CTSCheck)
                        AllMeasures[f"{CTSCheck}_Details"]=methodcall(CTSCheck,Check,flows,flwID)
                    except Exception as e:
                        methodcall=getattr(self.CTSMethod,CTSCheck)
                        AllMeasures[f"{CTSCheck}_Details"]=methodcall(CTSCheck,Check,flows,flwID)

                    #by default all the checks has sub-checks ensure the sub-checks results for main check pass / fail 
                    AllMeasures[f"{CTSCheck}_SEQ"] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
                    AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                    AllMeasures[f'{CTSCheck}_remarks']='NA'
                    if len(AllMeasures[f"{CTSCheck}_Details"]) >0:
                        tempRes = AllMeasures[f"{CTSCheck}_Details"]
                        # print('Tempres',tempRes)
                        if Enums.TestResult.FAIL in [item[1] for item in tempRes]:
                            if AllMeasures[CTSCheck] is None: AllMeasures[CTSCheck]=f"Issue in {CTSCheck}"
                            AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                        else:
                            if Enums.TestResult.INCONCLUSIVE in [item[1] for item in tempRes]:
                                if AllMeasures[CTSCheck] is None: AllMeasures[CTSCheck]=f"Issue in {CTSCheck}"
                                AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.INCONCLUSIVE
                            else:
                                if AllMeasures[CTSCheck] is None: AllMeasures[CTSCheck]=f"No Issue  in {CTSCheck}"
                                AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.PASS
                        AllMeasures[f'{CTSCheck}_remarks']=';'.join([item[0] for item in tempRes if item[1]==Enums.TestResult.FAIL])
                        AllMeasures[f'{CTSCheck}_Details']=tempRes
                        # Update Validation for Eye Diagram
                        if 'ASK_MOD' in TestCaseConfig.TestcaseID:
                            if Enums.TestResult.PASS in tempRes[-1]: AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.PASS
                               
                                
                    #Update Final Result
                    
                    if Check['Result_check'] == True:
                        # print(Header)
                        if TestCaseConfig.AutomationResult == Enums.TestResult.NOT_RUN:
                            TestCaseConfig.AutomationResult = AllMeasures[str(CTSCheck)+'_res']
                        elif (TestCaseConfig.AutomationResult == Enums.TestResult.INCONCLUSIVE and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.FAIL) or (TestCaseConfig.AutomationResult == Enums.TestResult.FAIL and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.INCONCLUSIVE) :
                            TestCaseConfig.AutomationResult=Enums.TestResult.FAIL
                        elif (TestCaseConfig.AutomationResult == Enums.TestResult.INCONCLUSIVE and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.PASS) or (TestCaseConfig.AutomationResult == Enums.TestResult.PASS and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.INCONCLUSIVE) :
                            TestCaseConfig.AutomationResult=Enums.TestResult.INCONCLUSIVE
                        elif (TestCaseConfig.AutomationResult == Enums.TestResult.PASS and AllMeasures[str(CTSCheck)+'_res']==Enums.TestResult.FAIL) or (TestCaseConfig.AutomationResult == Enums.TestResult.FAIL and AllMeasures[str(CTSCheck)+'_res']==Enums.TestResult.PASS):
                            TestCaseConfig.AutomationResult=Enums.TestResult.FAIL #Add remarks for the test fail
                    
                    # Update TestResult to Not-Run if SW result is NotRun
                    if TestCaseConfig.SoftwareResult==Enums.TestResult.NOT_RUN:TestCaseConfig.AutomationResult=Enums.TestResult.NOT_RUN
        
        return AllMeasures
    
    

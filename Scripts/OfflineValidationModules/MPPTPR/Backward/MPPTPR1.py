# import os
import sys
sys.path.append('Scripts')
import traceback
# import zipfile
from MainModule import JsonOperations,APIOperations,GeneralMethods

from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
from datetime import datetime,date
from OfflineValidationModules.MPPTPR.MPPTPR1_CommonHelper import CommonCTSChecks
# from collections import deque
import traceback
import logging

# logging setup
Jsettings = JsonOperations('json/setting.json')
JsettingsData = Jsettings.read_file()
logging.basicConfig(
    filename=JsettingsData["Validation_logs_path"],
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s\n%(message)s"
)

DIVIDER = "=" * 100
THIN    = "-" * 100

class CTSChecks_MPP_TPR1():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson):
        #Define Global variables
        CTS = JsonOperations('json/CTSvalidation/MPPTPR.json')
        self.JCTSData =CTS.read_file()

        # self.JCTSData = JCTSData
        self.JapiData = JapiData
        self.Header = Header
        self.Product = self.Header['Product']
        self.Mode = self.Header['Mode']
        self.TestCaseName = self.Header['TestcaseName']
        self.ProjectJson = ProjectJson
        self.file_list = file_list
        self.BackupJson = BackupJson
        self.BKjson = JsonOperations(self.BackupJson)
        self.BKjsonData = self.BKjson.read_file()
        # self.TestResultsjson = JsonOperations("json/CTSvalidation/TestResults.json")
        # self.TestData = self.TestResultsjson.read_file()
        # with open('BckupJson.json', 'w') as json_file:
        #     json.dump(self.BKjsonData, json_file, indent=4)
        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        #Define modules
        self.PktMethod = PacketMethods(file_list=self.file_list,Header=self.Header)
        self.PlotMethod = PlotMethods(Header=self.Header)
        # self.Certification=self.BKjsonData['testBkpAppModeString']
        

    def CTSChecks(self,flwID,flows,CTSJson):
       
        # self.GetInitailVoltage(2)
        self.CTSMethod=CommonCTSChecks(self.Header,self.file_list,self.JapiData,self.BackupJson,self.ProjectJson,flows)
        AllMeasures={}
        for CTSCheck in CTSJson:
            AllMeasures[CTSCheck] = None
            AllMeasures[f'{CTSCheck}_Details']=[]
            AllMeasures[f'{CTSCheck}_exp']="NA"
            for Check in CTSJson[CTSCheck]:
                if Check['flow'] == flwID:
                    Flow_limit = flows[flwID]['Limit']
                    # try:
                    #     methodcall=getattr(self, CTSCheck)
                    #     AllMeasures[f"{CTSCheck}_Details"]=methodcall(Flow_limit,Check)
                    # except Exception as e:
                    #     methodcall=getattr(self.CTSMethod, CTSCheck)
                    #     AllMeasures[f"{CTSCheck}_Details"]=methodcall(Flow_limit,Check)
                    # Dispatch: self takes priority, fallback to CTSMethod
                    if hasattr(self, CTSCheck):
                        methodcall = getattr(self, CTSCheck)
                        source = "self"
                    elif hasattr(self.CTSMethod, CTSCheck):
                        methodcall = getattr(self.CTSMethod, CTSCheck)
                        source = "CTSMethod"
                    else:
                        logging.error(
                            f"\n{'='*120}"
                            f"\nMISSING METHOD: '{CTSCheck}' not found on self or CTSMethod"
                            f"\nTESTCASE    : {self.Header}"
                            f"\nFlow ID     : {flwID}"
                            f"\nFlow Limit  : {Flow_limit}"
                            f"\nCheck       : {Check}"
                            f"\n{'='*120}"
                        )
                        continue  # or raise, depending on your desired behaviour
                    # Single call site — one place to log actual runtime errors
                    try:
                        AllMeasures[f"{CTSCheck}_Details"] = methodcall(Flow_limit, Check)
                    except Exception:
                        exc = traceback.format_exc()
                        logging.error(
                            f"{DIVIDER}\n"
                            f"  ERROR — {source}.{CTSCheck}()\n"
                            f"{THIN}\n"
                            f"{self._fmt_header()}\n"
                            f"{THIN}\n"
                            f"  CTSCheck  : {CTSCheck}\n"
                            f"  Flow ID   : {flwID}  |  Limit: {Flow_limit}\n"
                            f"  Check     : {Check}\n"
                            f"{THIN}\n"
                            f"{exc}"
                            f"{DIVIDER}\n\n\n"
                        )
                        raise

                    
                    
                    
                    # Apply Validation....
                    if CTSCheck not in ['BitsCheck_New','PacketCheck_New']:
                    # if CTSCheck not in ['PacketCheck']:
                        exp = Check['expected']
                        AllMeasures[f"{CTSCheck}_SEQ"] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
                        if type(exp) != str:
                            if type(AllMeasures[CTSCheck]) !=list:
                                if AllMeasures[CTSCheck] is not None:
                                    # print("hi1")
                                    reslt = self.check_measure(exp, AllMeasures[CTSCheck],Check['comp'])
                                    AllMeasures[str(CTSCheck)+'_exp']=reslt[2]+str(reslt[0][0]) if reslt[2] != 0 else str(reslt[0][0])+'-'+str(reslt[0][1])
                                    AllMeasures[str(CTSCheck)+'_res'] = reslt[1]
                                    if reslt[1]==Enums.TestResult.PASS:
                                        AllMeasures[f'{CTSCheck}_Details'].append([f"The Measured {CTSCheck} is {AllMeasures[CTSCheck]}, which is in limit: [{reslt[2]}]",Enums.TestResult.PASS])
                                    else:AllMeasures[f'{CTSCheck}_Details'].append([f"The Measured {CTSCheck} is {AllMeasures[CTSCheck]}, which is not in limit: [{reslt[2]}]",Enums.TestResult.FAIL])
                                else:
                                    # print("hi2")
                                    # AllMeasures[str(CTSCheck)+'_exp'] = str(exp[0])+'-'+str(exp[1]) if len(exp)>1 else exp[0]
                                    AllMeasures[str(CTSCheck)+'_res']=Enums.TestResult.PASS
                                if len(AllMeasures[f"{CTSCheck}_Details"]) >0:
                                    # print("hi3")
                                    tempRes = AllMeasures[f"{CTSCheck}_Details"]
                                    # print('Tempres:',tempRes)
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
                                  
                        #For Str based exp results calucaltion
                        else:
                            # print("Str based exp results calucaltion")
                            if CTSCheck in [CTSCheck]:
                                AllMeasures[f'{CTSCheck}_exp'] =exp
                                AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                                AllMeasures[f'{CTSCheck}_remarks']='NA'
                                if AllMeasures[CTSCheck] is not None or len(AllMeasures[f"{CTSCheck}_Details"]) >0:
                                   
                                    if exp=='VrectF0>VrectF1>VrectF2':
                                        if None not in [AllMeasures['Vrectfinal0'],AllMeasures['Vrectfinal1'],AllMeasures['Vrectfinal2']]:
                                            if AllMeasures['Vrectfinal0'] > AllMeasures['Vrectfinal1'] and AllMeasures['Vrectfinal1'] > AllMeasures['Vrectfinal2']:
                                                AllMeasures['VrecrfinalComp_res'] = Enums.TestResult.PASS
                                   
                                   
                                    
                                    elif exp=="PTphaseCheck" and CTSCheck in ["PTPhase"]:
                                        AllMeasures[f'{CTSCheck}_exp'] =exp
                                        AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.PASS
                                        # AllMeasures[f'{CTSCheck}_remarks']=f"PT phase started on {AllMeasures[CTSCheck]}sec."
                                   
                                    # elif exp in ["RenegoCheck","LoadForNegoPower","PLAOffsetCheck","DPlossCalibrationCheck","RenegoPRECTInterval","ChargeStatus","Linearization","KestCheck"]:
                                    
                                    elif exp=="PLAOffsetCheck":
                                        tempRes = AllMeasures[f"{CTSCheck}_Details"]
                                        # print('Tempres:',tempRes)
                                        throttle_failcnt = 0
                                 
                                        for item in tempRes:
                                            if item[1]==Enums.TestResult.FAIL and "not throttled" in item[0]:
                                                throttle_failcnt+=1
                                                if throttle_failcnt>=3:
                                                    AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                                                    break
                                                else: AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.PASS

                                            else:
                                                if Enums.TestResult.INCONCLUSIVE in [item[1] for item in tempRes]:
                                                    if AllMeasures[CTSCheck] is None: AllMeasures[CTSCheck]=f"Issue in {CTSCheck}"
                                                    AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.INCONCLUSIVE
                                                else:
                                                    if AllMeasures[CTSCheck] is None: AllMeasures[CTSCheck]=f"No Issue  in {CTSCheck}"
                                                    AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.PASS
                                        
                                        for item in tempRes:
                                            if item[1]==Enums.TestResult.FAIL and "not throttled" not in item[0]:
                                                AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                                                break


                                       
                                        AllMeasures[f'{CTSCheck}_remarks']=';'.join([item[0] for item in tempRes if item[1]==Enums.TestResult.FAIL])
                                        AllMeasures[f'{CTSCheck}_Details']=tempRes
                                    
                                    
                                    
                                    else:
                                        tempRes = AllMeasures[f"{CTSCheck}_Details"]
                                        # print('Tempres:',tempRes)
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
                                        # print("AllMeasures:",AllMeasures)
                    else:
                        if CTSCheck in [CTSCheck]:
                            AllMeasures[f'{CTSCheck}_exp'] =CTSCheck
                            AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                            AllMeasures[f'{CTSCheck}_remarks']='NA'
                            AllMeasures[f'{CTSCheck}_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
                            if AllMeasures[CTSCheck] is not None or len(AllMeasures[f"{CTSCheck}_Details"]) >0:          
                                tempRes = AllMeasures[f"{CTSCheck}_Details"]
                                # print('Tempres:',tempRes)
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


                    #Update Final Result
                    # # print(Header)
                    if self.Header['TCresult'] == 'NA':
                        self.Header['TCresult'] = AllMeasures[str(CTSCheck)+'_res']
                    elif (self.Header['TCresult'] == Enums.TestResult.INCONCLUSIVE and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.FAIL) or (self.Header['TCresult'] == Enums.TestResult.FAIL and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.INCONCLUSIVE) :
                        self.Header['TCresult']=Enums.TestResult.FAIL
                    elif (self.Header['TCresult'] == Enums.TestResult.INCONCLUSIVE and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.PASS) or (self.Header['TCresult'] == Enums.TestResult.PASS and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.INCONCLUSIVE) :
                        self.Header['TCresult']=Enums.TestResult.INCONCLUSIVE
                    elif (self.Header['TCresult'] == Enums.TestResult.PASS and AllMeasures[str(CTSCheck)+'_res']==Enums.TestResult.FAIL) or (self.Header['TCresult'] == Enums.TestResult.FAIL and AllMeasures[str(CTSCheck)+'_res']==Enums.TestResult.PASS):
                        self.Header['TCresult']=Enums.TestResult.FAIL #Add remarks for the test fail
                    
                    # Update TestResult to Not-Run if SW result is NotRun
                    if self.Header['SWresult']=="Not Run":self.Header['TCresult']='NA'
        return AllMeasures


    # Logging
    def _fmt_header(self):
        h = self.Header
        return (
            f"  Testcase  : {h.get('TestcaseName')} ({h.get('TestcaseID')})\n"
            f"  DUT       : {h.get('DUTName')} ({h.get('DUTID')}) | Board: {h.get('BoardNo')} | Coil: {h.get('Coil')}\n"
            f"  Run       : {h.get('Run')} | Cert: {h.get('Certification')} | SW: {h.get('SWVersion')} | FW: {h.get('FWVersion')}\n"
            f"  Result    : TC={h.get('TCresult')}  SW={h.get('SWresult')} | Engineer: {h.get('Engineer')}"
        )
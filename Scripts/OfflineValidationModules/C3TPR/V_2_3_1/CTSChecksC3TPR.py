
import traceback
import sys
sys.path.append('Scripts')
from Models.Enums import Enums
from Models.TestConfigs import *
from OfflineValidationModules.C3TPR.CommonHelper import CommonCTSChecks


class CTSChecks_C3TPR():

    def CTSChecks(self,flwID,flows,CTSJson):

        CTSMethod= CommonCTSChecks()
        CTSMethod.Flow_limit = flows[flwID]['Limit']
        CTSMethod.flows = flows
        AllMeasures={}
        for CTSCheck in CTSJson:
            AllMeasures[CTSCheck] = None
            AllMeasures[f'{CTSCheck}_Details']=[]
            AllMeasures[f'{CTSCheck}_exp']="NA"
            for Check in CTSJson[CTSCheck]:
                if Check['flow'] == flwID:
                    try:
                        methodcall=getattr(self, CTSCheck)
                        AllMeasures[f"{CTSCheck}_Details"]=methodcall(CTSCheck,Check,flows,flwID)
                    except Exception as e:
                        methodcall=getattr(CTSMethod,CTSCheck)
                        AllMeasures[f"{CTSCheck}_Details"]=methodcall(CTSCheck,Check,flows,flwID)

                 #Validation checks starts_______________________
                   
                    # # Apply Validation....
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
            #Update Final Result
            
            if Check['Result_check'] == True:
                # print(Header)
                if TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.NOT_RUN:
                    TestObjects.TestCaseConfig.AutomationResult = AllMeasures[str(CTSCheck)+'_res']
                elif (TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.INCONCLUSIVE and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.FAIL) or (TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.FAIL and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.INCONCLUSIVE) :
                    TestObjects.TestCaseConfig.AutomationResult=Enums.TestResult.FAIL
                elif (TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.INCONCLUSIVE and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.PASS) or (TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.PASS and AllMeasures[str(CTSCheck)+'_res'] ==Enums.TestResult.INCONCLUSIVE) :
                    TestObjects.TestCaseConfig.AutomationResult=Enums.TestResult.INCONCLUSIVE
                elif (TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.PASS and AllMeasures[str(CTSCheck)+'_res']==Enums.TestResult.FAIL) or (TestObjects.TestCaseConfig.AutomationResult == Enums.TestResult.FAIL and AllMeasures[str(CTSCheck)+'_res']==Enums.TestResult.PASS):
                    TestObjects.TestCaseConfig.AutomationResult=Enums.TestResult.FAIL #Add remarks for the test fail
            
            # Update TestResult to Not-Run if SW result is NotRun
            if TestObjects.TestCaseConfig.SoftwareResult==Enums.TestResult.NOT_RUN:TestObjects.TestCaseConfig.AutomationResult=Enums.TestResult.NOT_RUN
        
        # Reserved Bit Check
        res=self.ReservedResponseCheck()
        if len(res)>0:
            AllMeasures['Reserved_Check'] = None
            AllMeasures[f'Reserved_Check_Details']=res
            AllMeasures[f"Reserved_Check_SEQ"]=1
            AllMeasures[f'Reserved_Check_res']=Enums.TestResult.FAIL
            TestObjects.TestCaseConfig.AutomationResult=Enums.TestResult.FAIL
                        
        return AllMeasures

    @staticmethod
    def ReservedResponseCheck():
        res=[]
        id= TestObjects.TestCaseConfig.Flow_limit[0]
        while id < TestObjects.TestCaseConfig.Flow_limit[1]:
            if TestObjects.PktMethod.GetPacketType(id) == 'Response':
                if 'Reserved' in TestObjects.TestCaseConfig.file_list[id]['pktType'] or 'Reserved' in TestObjects.TestCaseConfig.file_list[id]['value'] or 'NONE' in TestObjects.TestCaseConfig.file_list[id]['pktType']:
                    res.append([f'Transmitter sent Reserved Response at {{{id}}}',Enums.TestResult.FAIL])
            id+=1
        return res
        
    
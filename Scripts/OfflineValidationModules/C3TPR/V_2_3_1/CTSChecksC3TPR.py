import traceback
import io
import zipfile
import pandas as pd
import sys
sys.path.append('Scripts')
import csv
import json
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
from OfflineValidationModules.C3TPR.CommonHelper import CommonCTSChecks


class CTSChecks_C3TPR():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson):

        #Define Global variables
        CTS = JsonOperations('json/CTSvalidation/C3TPR.json')
        self.JCTSData =CTS.read_file()
        # self.JCTSData = JCTSData
        self.JapiData = JapiData
        self.Header = Header
        self.Product = self.Header['Product']
        self.Mode = self.Header['Mode']
        self.file_list = file_list
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
        # with open('BckupJson.json', 'w') as json_file:
        #     json.dump(self.BKjsonData, json_file, indent=4)
        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        #Define modules
        self.PktMethod = PacketMethods(file_list=self.file_list,Header=self.Header)
        self.PlotMethod = PlotMethods(Header=self.Header)
        self.CTSMethod=CommonCTSChecks(file_list=self.file_list,Header=self.Header,JapiData=JapiData,BackupJson=BackupJson,Product=self.Product,Mode=self.Mode)
       
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']

    def CTSChecks(self,flwID,flows,CTSJson):
        
        AllMeasures={}
        for CTSCheck in CTSJson:
            AllMeasures[CTSCheck] = None
            AllMeasures[f'{CTSCheck}_Details']=[]
            AllMeasures[f'{CTSCheck}_exp']="NA"
            for Check in CTSJson[CTSCheck]:
                if Check['flow'] == flwID:
                    self.Flow_limit = flows[flwID]['Limit']
                
                    try:
                        
                        methodcall=getattr(self, CTSCheck)
                        AllMeasures[f"{CTSCheck}_Details"]=methodcall(CTSCheck,Check,flows,flwID)
                    except Exception as e:
                        methodcall=getattr(self.CTSMethod,CTSCheck)
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
        
        # Reserved Bit Check
        res=self.ReservedResponseCheck()
        if len(res)>0:
            AllMeasures['Reserved_Check'] = None
            AllMeasures[f'Reserved_Check_Details']=res
            AllMeasures[f"Reserved_Check_SEQ"]=1
            AllMeasures[f'Reserved_Check_res']=Enums.TestResult.FAIL
            self.Header['TCresult']=Enums.TestResult.FAIL
                        
        return AllMeasures

    def ReservedResponseCheck(self):
        res=[]
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            if self.PktMethod.GetPacketType(id) == 'Response':
                if 'Reserved' in self.file_list[id]['pktType'] or 'Reserved' in self.file_list[id]['value'] or 'NONE' in self.file_list[id]['pktType']:
                    res.append([f'Transmitter sent Reserved Response at {{{id}}}',Enums.TestResult.FAIL])
            id+=1
        return res
        
    
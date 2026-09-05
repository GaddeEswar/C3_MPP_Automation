import traceback
import io
import zipfile
import pandas as pd
import csv
import time
import json
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
from OfflineValidationModules.C3TPT.CommonHelper import CommonCTSChecks

class CTSChecks_C3TPT():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson):

        #Define Global variables
        CTS = JsonOperations('json/CTSvalidation/C3TPT.json')
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
                     # Get the method reference
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
            else: 
                AllMeasures[f'{CTSCheck}_Details']=[['Did not found any Measures',Enums.TestResult.INCONCLUSIVE]]
                AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.INCONCLUSIVE
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

        return AllMeasures
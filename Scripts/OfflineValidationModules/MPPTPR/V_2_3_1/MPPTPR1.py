# import os
import sys
sys.path.append('Scripts')
import traceback
# import zipfile
from MainModule import JsonOperations,APIOperations,GeneralMethods

from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
# from datetime import datetime,date
from OfflineValidationModules.MPPTPR.MPPTPR1_CommonHelper import CommonCTSChecks
# from collections import deque
import traceback
import logging

# from concurrent.futures import ThreadPoolExecutor, as_completed

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
        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        # self.Certification=self.BKjsonData['testBkpAppModeString']
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        if self.Certification in ["2.0.1","2.1.0","2.2.1","2.3.0"]:
            self.ECAP_pkt = "Extended_Power_Transmitter_Extended_Capabilities"
            self.XID_pkt = "MPP_Extended_Identification"
        else:
            self.ECAP_pkt = "Power Transmitter Extended Capabilities"
            self.XID_pkt = "Extended Identification"
        

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






   





    def Auth_Flows_New(self,Flow_limit,Check):
        res=[]


    def Cloak_Compatibility(self,Flow_limit,Check):
        # print("Cloak_Compatibility")
        start = Flow_limit[0]
        end = len(self.file_list)-1
        res=[]
        SDSR_ACK_flag = True
        # 1st GET_CERTIFICATE
        sadc_open1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[start, Flow_limit[1]],Type="Packet")
        if len(sadc_open1)>2:
            res.append([f"SADC Open Stream packet found at {round(sadc_open1[0],3)} sec", Enums.TestResult.PASS])
            sadc1_resp = self.PktMethod.GetPacketResponse2(sadc_open1[2], [sadc_open1[2]+1, Flow_limit[1]])
            if sadc1_resp is not None and self.file_list[sadc1_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadc1_resp]['value']:
                res.append([f"SDSR/ACK response found at {round(self.file_list[sadc1_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.PASS])
            else:
                SDSR_ACK_flag = False
                res.append([f"{self.file_list[sadc1_resp]['pktType']}_{self.file_list[sadc1_resp]['value']} found at {round(self.file_list[sadc1_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.FAIL])

            sadt1 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open1[2], end],Type="Packet")
            if len(sadt1)>2:
                
                cert_type1 = self.PktMethod.GetPayloadDetails(sadt1[2],'Get_Certificate')[0]['sDescription'].strip()
                print("cert_type1:",cert_type1)   
                normal_chk1 = {"ChecksList": [{"packet": ["SADT",None],"Checks": {"OffsetA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"LengthA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Offset70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Length70": {"expected": 16,"flag": "sRawData","comp": "EQL","units": " "},"Slot_Number": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},},"PacketType": "Packet","refPrevious": False}],"flow": 2,"Result_check": False,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 3}
                bits_resp = self.CTSMethod.BitsCheck_New([sadc_open1[2],Flow_limit[1]],normal_chk1)
                print("bits_resp:", bits_resp)
                res.append(bits_resp[0])

                if cert_type1 == "Get_Certificate":
                    res.append([f"{cert_type1} found in SADT found at {round(sadt1[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.PASS])
                else:
                    res.append([f"Invalid {cert_type1} found in SADT found at {round(sadt1[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.FAIL])
                for chks in bits_resp[1:]:
                    res.append(chks)

                sadc_close1 = self.PktMethod.GetPacketDetails(packet="SADC",value="Close Stream:",limit=[sadt1[2], Flow_limit[1]],Type="Packet")
                if len(sadc_close1)>2:
                    res.append([f"SADC Close Stream packet found at {round(sadc_close1[0],3)} sec", Enums.TestResult.PASS])

                    atn1 = self.PktMethod.GetPacketDetails(packet='ATN',limit=[sadc_close1[2], Flow_limit[1]],Type="Response")
                    if len(atn1)>2:
                        res.append([f"PTx sent ATN after Get_Certificate at {round(atn1[0],3)} sec", Enums.TestResult.PASS])

                        dsr1 = self.PktMethod.GetPacketDetails(packet="DSR",value="POLL",limit=[atn1[2], Flow_limit[1]],Type="Packet")
                        if len(dsr1)>2:
                            res.append([f"TPR sent DSR(POLL) at {round(dsr1[0],3)} sec", Enums.TestResult.PASS])

                            # Certificate 1
                            sadc_open2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[dsr1[2], Flow_limit[1]],Type="Response")
                            print("sadc_open2", sadc_open2)
                            if len(sadc_open2)>2:
                                res.append([f"SADC Open Stream(Response) found at {round(sadc_open2[0],3)} sec", Enums.TestResult.PASS])
                                idx = sadc_open2[2]
                                sadtx_cnt = 0
                                while idx < Flow_limit[1]:
                                    sadtx = self.PktMethod.GetPacketDetails(packet="SADT",limit=[idx, Flow_limit[1]],Type="Response")
                                    if len(sadtx)>2:
                                        sadtx_cnt += 1
                                        
                                        if sadtx_cnt == 1:
                                            cert_type2 = self.PktMethod.GetPayloadDetails(sadtx[2],'Certificate')[0]['sDescription'].strip()
                                            if cert_type2 == "Certificate":
                                                res.append([f"{self.file_list[sadtx[2]]['pktType']} response with {cert_type2} found at {round(sadtx[0],3)} sec, Expected: Certificate", Enums.TestResult.PASS])
                                            else:
                                                res.append([f"{self.file_list[sadtx[2]]['pktType']} response with {cert_type2} found at {round(sadtx[0],3)} sec, Expected: Certificate", Enums.TestResult.FAIL])
                                        else:
                                            res.append([f"{self.file_list[sadtx[2]]['pktType']} response found at {round(sadtx[0],3)} sec", Enums.TestResult.PASS])
                                        idx = sadtx[2]
                                    idx += 1

                                cert_data1 = self.CTSMethod.GetAuthPacketDetails(packet="CERTIFICATE",limit=[0, len(self.Auth_file_list)],Type="Response")
                                print("authlimit:", [0, len(self.Auth_file_list)])
                                print("cert_data1:", cert_data1)
                                if len(cert_data1) > 2:
                                    s1 = self.Auth_file_list[cert_data1[2]]['header_Payload']['sFieldType'].split(":")[-1].strip()
                                    # s1 = self.CTSMethod.GetAuthPayloadDetails(cert_data1[2], "Certificate_Chain_Segment", "B1_B5", "[7:0")[0]['sRawData']
                                    res.append([f"s1 is {s1}",Enums.TestResult.PASS])
                                    # print("s1:", s1)
                                else: res.append([f"CERTIFICATE is not found", Enums.TestResult.FAIL])


                                # Cloak
                                clk1 = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[sadc_open2[2], end],Type="Packet")
                                if len(clk1)>2:
                                    clk_rsn1 = self.PktMethod.GetPayloadDetails(clk1[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                                    res.append([f"Cloak initiated with {clk_rsn1} reason at {round(clk1[0],3)} sec", Enums.TestResult.PASS])

                                    clk_exit = self.PktMethod.GetPacketDetails(packet='MPP_Cloak_Exit',limit=[sadc_open2[2], end],Type="TesterMsg")
                                    if len(clk_exit)>2:

                                        # If ATN is observed
                                        atn1 = self.PktMethod.GetPacketDetails(packet='ATN',limit=[clk1[2], clk_exit[2]],Type="Response")
                                        if len(atn1)>2:
                                            res.append([f"PTx sent ATN in cloak phase at {round(atn1[0],3)} sec", Enums.TestResult.PASS])
                                            clk_force = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[atn1[2], clk_exit[2]],Type="Packet")
                                            if len(clk_force)>2:
                                                clk_rsn2 = self.PktMethod.GetPayloadDetails(clk_force[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                                            else: res.append([f"Cloak Packet not found after ATN", Enums.TestResult.FAIL])

                                        # 2 cloak cycles
                                        id = clk1[2]
                                        clk_cnt = 0
                                    
                                        while id < clk_exit[2]:
                                            clkx = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[id+1, clk_exit[2]],Type="Packet")
                                            if len(clkx)>2:
                                                clk_rsnx = self.PktMethod.GetPayloadDetails(clkx[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                                                id = clkx[2]
                                                clk_cnt += 1
                                                res.append([f"Cloak_{clk_cnt} found with {clk_rsnx} reason at {round(clkx[0],3)} sec", Enums.TestResult.PASS])

                                                if clk_cnt == 2:
                                                    # Report 
                                                    report_pkt = self.PktMethod.GetPacketDetails(packet='Report',limit=[id, clk_exit[2]],Type="Packet")
                                                    if len(report_pkt)>2:
                                                        report_rsn = self.PktMethod.GetPayloadDetails(report_pkt[2],'Report_ID')[0]['sDescription']
                                                        if report_rsn == "PRx Identification":
                                                            res.append([f"Report Packet found with PRx Identification at {round(report_pkt[0],3)} sec", Enums.TestResult.PASS])
                                                        else: res.append([f"Report Packet found with {report_rsn} at {round(report_pkt[0],3)} sec", Enums.TestResult.FAIL])

                                                        PTX_ID_pkt = self.PktMethod.GetPacketDetails(packet='Get Request',value="PTx Extended Identification",limit=[report_pkt[2], clk_exit[2]],Type="Packet") 
                                                        if len(PTX_ID_pkt)>2:
                                                            res.append([f"Get Request (PTx Extended Identification) packet found at {round(PTX_ID_pkt[0],3)} sec", Enums.TestResult.PASS])
                                                            respid2 = self.PktMethod.GetPacketResponse2(PTX_ID_pkt[2], [PTX_ID_pkt[2]+1, clk_exit[2]])
                                                            if respid2 is not None and self.file_list[respid2]['pktType'] == "Extended Power Transmitter Identification":
                                                                res.append([f"Extended Power Transmitter Identification response found at {round(self.file_list[respid2]['startTime'],3)} sec", Enums.TestResult.PASS])
                                                            else:
                                                                res.append([f"Extended Power Transmitter Identification response not found", Enums.TestResult.FAIL])
                                                        else:
                                                            res.append([f"Get Request (PTx Extended Identification) packet not found", Enums.TestResult.FAIL])
                                                

                                                    else: res.append([f"Report Packet not found", Enums.TestResult.FAIL])
                                                    break
                                            else: res.append([f"Cloak Packet_{clk_cnt+1} not found", Enums.TestResult.FAIL])
                                                    
                                            id += 1
                                        res.append([f"Cloak exit found at {round(clk_exit[0],3)} sec", Enums.TestResult.PASS])

                                        atn2 = self.PktMethod.GetPacketDetails(packet='ATN',limit=[clk_exit[2], end],Type="Response")
                                        if len(atn2)>2:
                                            res.append([f"PTx sent ATN after Cloak exit at {round(atn2[0],3)} sec", Enums.TestResult.PASS])

                                            dsr2 = self.PktMethod.GetPacketDetails(packet="DSR",value="POLL",limit=[atn2[2], end],Type="Packet")
                                            if len(dsr2)>2:
                                                res.append([f"TPR sent DSR(POLL) at {round(dsr2[0],3)} sec", Enums.TestResult.PASS])

                                                # Certificate 2
                                                sadc_open3 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[dsr2[2], end],Type="Response")
                                                if len(sadc_open3)>2:
                                                    res.append([f"SADC Open Stream Response found at {round(sadc_open3[0],3)} sec", Enums.TestResult.PASS])
                                                    
                                                    idx2 = sadc_open3[2]
                                                    sadtx2_cnt = 0
                                                    s2_bytes_length = 0
                                                    while idx2 < end:
                                                        sadtx2 = self.PktMethod.GetPacketDetails(packet="SADT",limit=[idx2, end],Type="Response")
                                                        if len(sadtx2)>2:
                                                            sadtx2_cnt += 1
                                                            if sadtx2_cnt == 1:
                                                                cert_type2 = self.PktMethod.GetPayloadDetails(sadtx2[2],'Certificate')[0]['sDescription'].strip()
                                                            
                                                                if cert_type2 == "Certificate":
                                                                    res.append([f"{self.file_list[sadtx2[2]]['pktType']} response with {cert_type2} found at {round(sadtx2[0],3)} sec, Expected: Certificate", Enums.TestResult.PASS])
                                                                else:
                                                                    res.append([f"{self.file_list[sadtx2[2]]['pktType']} response with {cert_type2} found at {round(sadtx2[0],3)} sec, Expected: Certificate", Enums.TestResult.FAIL])
                                                            else:
                                                                res.append([f"{self.file_list[sadtx2[2]]['pktType']} response found at {round(sadtx2[0],3)} sec", Enums.TestResult.PASS])
                                                            rece_data = self.file_list[sadtx2[2]]['pktType'].split("/")
                                                            s2_bytes_length = s2_bytes_length + int(rece_data[1][0])
                                                            idx2 = sadtx2[2]
                                                        idx2 += 1
                                                
                                                    sadc_close3 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[sadc_open3[2], end],Type="Response")
                                                    if len(sadc_close3)>2:
                                                        res.append([f"SADC Close Stream Response found at {round(sadc_close3[0],3)} sec", Enums.TestResult.PASS])
                                                    else:
                                                        res.append([f"SADC Close Stream Response not found", Enums.TestResult.FAIL])
                                                    cert_data2 = self.CTSMethod.GetAuthPacketDetails(packet="CERTIFICATE",limit=[len(self.Auth_file_list)-1,0],Type="Response")
                                                    print("cert_data2:", cert_data2)
                                                    if len(cert_data2) > 2:
                                                        if s2_bytes_length == 17:
                                                            res.append([f"s2 consists of {s2_bytes_length} bytes, Expected: 17 bytes",Enums.TestResult.PASS])
                                                        else:
                                                            res.append([f"s2 consists of {s2_bytes_length} bytes, Expected: 17 bytes",Enums.TestResult.FAIL])

                                                        s2 = self.Auth_file_list[cert_data2[2]]['header_Payload']['sFieldType'].split(":")[-1].strip()
                                                        res.append([f"s2 is {s2}",Enums.TestResult.PASS])
                                                        s2_data = s2.split()
                                                        if s2_data[0] == "0x12":
                                                            res.append([f"The first byte of s2 is 0x12, Expected: 0x12", Enums.TestResult.PASS])
                                                        else:
                                                            res.append([f"The first byte of s2 is {s2_data[0]}, Expected: 0x12", Enums.TestResult.FAIL])
                                                        # print("s2:", s2)
                                                        if s1 in s2:
                                                            res.append([f"The bytes in s1: {s1} are equal to the corresponding bytes in s2: {s2}",Enums.TestResult.PASS])
                                                        else:
                                                            res.append([f"The bytes in s1: {s1} are not equal to the corresponding bytes in s2: {s2}",Enums.TestResult.FAIL])
                                                    else: res.append([f"CERTIFICATE is not reinitiated", Enums.TestResult.FAIL])
                                                else: res.append([f"SADC Open Stream Response not found", Enums.TestResult.FAIL])
                                            else: res.append([f"DSR(POLL) not found", Enums.TestResult.FAIL])
                                        else: res.append([f"ATN not found", Enums.TestResult.FAIL])
                                    else: res.append([f"MPP_Cloak_Exit not found", Enums.TestResult.FAIL])
                                else: res.append([f"Cloak ping is not initiated.", Enums.TestResult.FAIL])
                            else: res.append([f"SADC Open Stream Response not found", Enums.TestResult.FAIL])   
                        else: res.append([f"PTx didn't sent DSR(POLL) after Get_Certificate at {round(atn1[0],3)} sec", Enums.TestResult.PASS])
                    else: res.append([f"ATN not found", Enums.TestResult.FAIL])
                else: res.append([f"SADC Close Stream Packet not found", Enums.TestResult.FAIL])
            else: res.append([f"SADT Packet not found", Enums.TestResult.FAIL])
        else: res.append([f"SADC Open Stream Packet not found", Enums.TestResult.FAIL])   

        return res

    def Cloak_Compatibility2(self,Flow_limit,Check):
        start = Flow_limit[0]
        end = len(self.file_list)-1
        res=[]
        
        # 1st GET_CERTIFICATE
        sadc_open1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[start, Flow_limit[1]],Type="Packet")
        if len(sadc_open1)>2:
            res.append([f"SADC Open Stream packet found at {round(sadc_open1[0],3)} sec", Enums.TestResult.PASS])
            sadc1_resp = self.PktMethod.GetPacketResponse2(sadc_open1[2], [sadc_open1[2]+1, Flow_limit[1]])
            if sadc1_resp is not None and self.file_list[sadc1_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadc1_resp]['value']:
                res.append([f"SDSR/ACK response found at {round(self.file_list[sadc1_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.PASS])
            else:
                res.append([f"{self.file_list[sadc1_resp]['pktType']}_{self.file_list[sadc1_resp]['value']} found at {round(self.file_list[sadc1_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.FAIL])

            sadt1 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open1[2], end],Type="Packet")
            if len(sadt1)>2:
                
                cert_type1 = self.PktMethod.GetPayloadDetails(sadt1[2],'Get_Certificate')[0]['sDescription'].strip()
                print("cert_type1:",cert_type1)   
                normal_chk1 = {"ChecksList": [{"packet": ["SADT",None],"Checks": {"OffsetA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"LengthA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Offset70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Length70": {"expected": 16,"flag": "sRawData","comp": "EQL","units": " "},"Slot_Number": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},},"PacketType": "Packet","refPrevious": False}],"flow": 2,"Result_check": False,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 3}
                bits_resp = self.CTSMethod.BitsCheck_New([sadc_open1[2],Flow_limit[1]],normal_chk1)
                # print("bits_resp:", bits_resp)
                res.append(bits_resp[0])

                if cert_type1 == "Get_Certificate":
                    res.append([f"{cert_type1} found in SADT found at {round(sadt1[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.PASS])
                else:
                    res.append([f"Invalid {cert_type1} found in SADT found at {round(sadt1[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.FAIL])

                for chks in bits_resp[1:]:
                    res.append(chks)

                sadt_respid = self.PktMethod.GetPacketResponse2(sadt1[2], [sadt1[2]+1, Flow_limit[1]])
                if sadt_respid is not None:
                    if self.file_list[sadt_respid]['pktType'] == "ACK":
                        res.append([f"ACK response received for SADT packet at {round(self.file_list[sadt_respid]['startTime'],3)} sec, Expected: ACK", Enums.TestResult.PASS])

                        # Cloak
                        clk1 = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[sadt_respid, end],Type="Packet")
                        if len(clk1)>2:
                            clk_rsn1 = self.PktMethod.GetPayloadDetails(clk1[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                            res.append([f"Cloak initiated with {clk_rsn1} reason at {round(clk1[0],3)} sec", Enums.TestResult.PASS])

                            clk_exit = self.PktMethod.GetPacketDetails(packet='MPP_Cloak_Exit',limit=[sadt_respid, end],Type="TesterMsg")
                            if len(clk_exit)>2:

                                # If ATN is observed
                                atn1 = self.PktMethod.GetPacketDetails(packet='ATN',limit=[clk1[2], clk_exit[2]],Type="Response")
                                if len(atn1)>2:
                                    res.append([f"PTx sent ATN in cloak phase at {round(atn1[0],3)} sec", Enums.TestResult.PASS])
                                    clk_force = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[atn1[2], clk_exit[2]],Type="Packet")
                                    if len(clk_force)>2:
                                        clk_rsn2 = self.PktMethod.GetPayloadDetails(clk_force[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                                    else: res.append([f"Cloak Packet not found after ATN", Enums.TestResult.FAIL])

                                # 2 cloak cycles
                                id = clk1[2]
                                clk_cnt = 0
                            
                                while id < clk_exit[2]:
                                    clkx = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[id+1, clk_exit[2]],Type="Packet")
                                    if len(clkx)>2:
                                        clk_rsnx = self.PktMethod.GetPayloadDetails(clkx[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                                        id = clkx[2]
                                        clk_cnt += 1
                                        res.append([f"Cloak_{clk_cnt} found with {clk_rsnx} reason at {round(clkx[0],3)} sec", Enums.TestResult.PASS])

                                        if clk_cnt == 2:
                                            # Report 
                                            report_pkt = self.PktMethod.GetPacketDetails(packet='Report',limit=[id, clk_exit[2]],Type="Packet")
                                            if len(report_pkt)>2:
                                                report_rsn = self.PktMethod.GetPayloadDetails(report_pkt[2],'Report_ID')[0]['sDescription']
                                                if report_rsn == "PRx Identification":
                                                    res.append([f"Report Packet found with PRx Identification at {round(report_pkt[0],3)} sec", Enums.TestResult.PASS])
                                                else: res.append([f"Report Packet found with {report_rsn} at {round(report_pkt[0],3)} sec", Enums.TestResult.FAIL])

                                                PTX_ID_pkt = self.PktMethod.GetPacketDetails(packet='Get Request',value="PTx Extended Identification",limit=[report_pkt[2], clk_exit[2]],Type="Packet") 
                                                if len(PTX_ID_pkt)>2:
                                                    res.append([f"Get Request (PTx Extended Identification) packet found at {round(PTX_ID_pkt[0],3)} sec", Enums.TestResult.PASS])
                                                    respid2 = self.PktMethod.GetPacketResponse2(PTX_ID_pkt[2], [PTX_ID_pkt[2]+1, clk_exit[2]])
                                                    if respid2 is not None and self.file_list[respid2]['pktType'] == "Extended Power Transmitter Identification":
                                                        res.append([f"Extended Power Transmitter Identification response found at {round(self.file_list[respid2]['startTime'],3)} sec", Enums.TestResult.PASS])
                                                    else:
                                                        res.append([f"Extended Power Transmitter Identification response not found", Enums.TestResult.FAIL])
                                                else:
                                                    res.append([f"Get Request (PTx Extended Identification) packet not found", Enums.TestResult.FAIL])
                                        

                                            else: res.append([f"Report Packet not found", Enums.TestResult.FAIL])
                                            break
                                    else: res.append([f"Cloak Packet_{clk_cnt+1} not found", Enums.TestResult.FAIL])
                                            
                                    id += 1
                                res.append([f"Cloak exit found at {round(clk_exit[0],3)} sec", Enums.TestResult.PASS])


                                # 2nd GET_CERTIFICATE
                                sadc_open2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[clk_exit[2], end],Type="Packet")
                                if len(sadc_open2)>2:
                                    res.append([f"SADC Open Stream packet found at {round(sadc_open2[0],3)} sec", Enums.TestResult.PASS])
                                    sadc2_resp = self.PktMethod.GetPacketResponse2(sadc_open2[2], [sadc_open2[2]+1, end])
                                    if sadc2_resp is not None:
                                        if self.file_list[sadc2_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadc2_resp]['value']:
                                            res.append([f"stream_response_1 is SDSR/ACK found at {round(self.file_list[sadc2_resp]['startTime'],3)} sec, Expected: stream_response_1: SDSR/ACK", Enums.TestResult.PASS])
                                        else:
                                        
                                            res.append([f"{self.file_list[sadc2_resp]['pktType']}_{self.file_list[sadc2_resp]['value']} found at {round(self.file_list[sadc2_resp]['startTime'],3)} sec, Expected: stream_response_1: SDSR/ACK", Enums.TestResult.FAIL])
                                    else:
                                        res.append([f"Response not found for SADC/open", Enums.TestResult.FAIL])

                                    sadt2 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open2[2], end],Type="Packet")
                                    if len(sadt2)>2:  
                                        cert_type2 = self.PktMethod.GetPayloadDetails(sadt2[2],'Get_Certificate')[0]['sDescription'].strip()
                                        print("cert_type2:",cert_type2)   
                                        normal_chk2 = {"ChecksList": [{"packet": ["SADT",None],"Checks": {"OffsetA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"LengthA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Offset70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Length70": {"expected": 16,"flag": "sRawData","comp": "EQL","units": " "},"Slot_Number": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},},"PacketType": "Packet","refPrevious": False}],"flow": 2,"Result_check": False,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 3}
                                        bits_resp2 = self.CTSMethod.BitsCheck_New([sadc_open2[2],end],normal_chk2)
                                        res.append(bits_resp2[0])

                                        if cert_type2 == "Get_Certificate":
                                            res.append([f"{cert_type2} found in SADT found at {round(sadt2[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.PASS])
                                        else:
                                            res.append([f"Invalid {cert_type2} found in SADT found at {round(sadt2[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.FAIL])

                                        for chks in bits_resp2[1:]:
                                            res.append(chks)

                                        sadt2_respid = self.PktMethod.GetPacketResponse2(sadt2[2], [sadt2[2]+1, end])
                                        if sadt2_respid is not None:
                                            if self.file_list[sadt2_respid]['pktType'] == "ACK":
                                                res.append([f"stream_response_2: ACK response received for SADT packet at {round(self.file_list[sadt2_respid]['startTime'],3)} sec, Expected: stream_response_2: ACK", Enums.TestResult.PASS])
                                            else:
                                                res.append([f"stream_response_2:{self.file_list[sadt2_respid]['pktType']} response received for SADT packet at {round(self.file_list[sadt2_respid]['startTime'],3)} sec, Expected: stream_response_2: ACK", Enums.TestResult.FAIL])
                                        else:
                                            res.append([f"Response not found for SADT", Enums.TestResult.FAIL])
                                    else: res.append([f"SADT not found", Enums.TestResult.FAIL])
                                    
                                    sadc_close2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[sadc_open2[2], end],Type="Packet")
                                    if len(sadc_close2)>2:
                                        res.append([f"SADC Close Stream Packet found at {round(sadc_close2[0],3)} sec", Enums.TestResult.PASS])
                                        sadc_close2_resp = self.PktMethod.GetPacketResponse2(sadc_close2[2], [sadc_close2[2]+1, end])
                                        if sadc_close2_resp is not None:
                                            if self.file_list[sadc_close2_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadc_close2_resp]['value']:
                                                res.append([f"stream_response_3 is SDSR/ACK found at {round(self.file_list[sadc_close2_resp]['startTime'],3)} sec, Expected: stream_response_3: SDSR/ACK", Enums.TestResult.PASS])
                                            else:
                                                res.append([f"stream_response_3 is {self.file_list[sadc_close2_resp]['pktType']}_{self.file_list[sadc_close2_resp]['value']} found at {round(self.file_list[sadc_close2_resp]['startTime'],3)} sec, Expected: stream_response_3: SDSR/ACK", Enums.TestResult.FAIL])
                                        else:
                                            res.append([f"Response not found for SADC/close", Enums.TestResult.FAIL])

                                        atn2 = self.PktMethod.GetPacketDetails(packet='ATN',limit=[sadc_close2[2], end],Type="Response")
                                        if len(atn2)>2:
                                            res.append([f"PTx sent ATN after Cloak exit at {round(atn2[0],3)} sec", Enums.TestResult.PASS])

                                            dsr2 = self.PktMethod.GetPacketDetails(packet="DSR",value="POLL",limit=[atn2[2], end],Type="Packet")
                                            if len(dsr2)>2:
                                                res.append([f"TPR sent DSR(POLL) at {round(dsr2[0],3)} sec", Enums.TestResult.PASS])

                                                # Certificate
                                                sadc_open3 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[dsr2[2], end],Type="Response")
                                                if len(sadc_open3)>2:
                                                    res.append([f"SADC Open Stream Response found at {round(sadc_open3[0],3)} sec", Enums.TestResult.PASS])
                                                    
                                                    idx2 = sadc_open3[2]
                                                    sadtx2_cnt = 0
                                                    s1_bytes_length = 0
                                                    while idx2 < end:
                                                        sadtx2 = self.PktMethod.GetPacketDetails(packet="SADT",limit=[idx2, end],Type="Response")
                                                        if len(sadtx2)>2:
                                                            sadtx2_cnt += 1
                                                            if sadtx2_cnt == 1:
                                                                cert_type2 = self.PktMethod.GetPayloadDetails(sadtx2[2],'Certificate')[0]['sDescription'].strip()
                                                            
                                                                if cert_type2 == "Certificate":
                                                                    res.append([f"{self.file_list[sadtx2[2]]['pktType']} response with {cert_type2} found at {round(sadtx2[0],3)} sec, Expected: Certificate", Enums.TestResult.PASS])
                                                                else:
                                                                    res.append([f"{self.file_list[sadtx2[2]]['pktType']} response with {cert_type2} found at {round(sadtx2[0],3)} sec, Expected: Certificate", Enums.TestResult.FAIL])
                                                            else:
                                                                res.append([f"{self.file_list[sadtx2[2]]['pktType']} response found at {round(sadtx2[0],3)} sec", Enums.TestResult.PASS])
                                                            rece_data = self.file_list[sadtx2[2]]['pktType'].split("/")
                                                            s1_bytes_length = s1_bytes_length + int(rece_data[1][0])
                                                            idx2 = sadtx2[2]
                                                        idx2 += 1


                                                    cert_data2 = self.CTSMethod.GetAuthPacketDetails(packet="CERTIFICATE",limit=[len(self.Auth_file_list)-1,0],Type="Response")
                                                    print("cert_data2:", cert_data2)
                                                    if len(cert_data2) > 2:
                                                        if s1_bytes_length == 17:
                                                            res.append([f"s1 consists of {s1_bytes_length} bytes, Expected: 17 bytes",Enums.TestResult.PASS])
                                                        else:
                                                            res.append([f"s1 consists of {s1_bytes_length} bytes, Expected: 17 bytes",Enums.TestResult.FAIL])

                                                        s1 = self.Auth_file_list[cert_data2[2]]['header_Payload']['sFieldType'].split(":")[-1].strip()
                                                        res.append([f"s1 is {s1}",Enums.TestResult.PASS])
                                                        s1_data = s1.split()
                                                        if s1_data[0] == "0x12":
                                                            res.append([f"The first byte of s1 is 0x12, Expected: 0x12", Enums.TestResult.PASS])
                                                        else:
                                                            res.append([f"The first byte of s1 is {s1_data[0]}, Expected: 0x12", Enums.TestResult.FAIL])
                                                        
                                                    else: res.append([f"CERTIFICATE is not initiated", Enums.TestResult.FAIL])
                                                
                                                    sadc_close3 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[sadc_open3[2], end],Type="Response")
                                                    if len(sadc_close3)>2:
                                                        res.append([f"SADC Close Stream Response found at {round(sadc_close3[0],3)} sec", Enums.TestResult.PASS])
                                                    else:
                                                        res.append([f"SADC Close Stream Response not found", Enums.TestResult.FAIL])
                                                else: res.append([f"SADC Open Stream Response not found", Enums.TestResult.FAIL])
                                            else: res.append([f"DSR(POLL) not found", Enums.TestResult.FAIL])
                                        else: res.append([f"ATN not found", Enums.TestResult.FAIL])
                                    else: res.append([f"SADC Close Stream Packet not found", Enums.TestResult.FAIL])
                                else: res.append([f"SADC Open Stream Packet not found for Get_Certificate", Enums.TestResult.FAIL])
                            else: res.append([f"Cloak Exit packet not found", Enums.TestResult.FAIL])
                        else: res.append([f"Cloak is not initiated", Enums.TestResult.FAIL])
                    else:res.append([f"{self.file_list[sadt_respid]['pktType']} response received for SADT packet at {round(self.file_list[sadt_respid]['startTime'],3)} sec, Expected: ACK", Enums.TestResult.FAIL])
                else:res.append([f"No response received for SADT packet, Expected: ACK", Enums.TestResult.FAIL])
            else: res.append([f"SADT Packet not found", Enums.TestResult.FAIL])
        else: res.append([f"SADC Open Stream Packet not found", Enums.TestResult.FAIL])


        return res

        
        
    def Digest_returned(self,Flow_limit,Check):
        res=[]
        cnt = 0
        digests_details = []
        auth_limit = [0, len(self.Auth_file_list) - 1]
        id = 0
        while id < auth_limit[1]:
            get_dig1 = self.CTSMethod.GetAuthPacketDetails(packet="GET_DIGESTS", limit=[id,auth_limit[1]], Type="Packet")
            if len(get_dig1) > 2:
                cnt += 1
                res.append([f"GET_DIGESTS_{cnt} packet found at {self.PktMethod.Timeconvert(get_dig1[0])}", Enums.TestResult.PASS])
                dig1 = self.CTSMethod.GetAuthPacketDetails(packet="DIGESTS", limit=[get_dig1[2],auth_limit[1]], Type="Response")
                if len(dig1) > 2:
                    res.append([f"DIGESTS_{cnt} response found at {self.PktMethod.Timeconvert(dig1[0])} with following details", Enums.TestResult.PASS])
                    # Authentication_Protocol_Version = self.CTSMethod.GetAuthPayloadDetails(dig1[2], "Authentication_Protocol_Version", "B0", "[7:4")[0]['sDescription'].split(":")[-1].strip()
                    # Slots_Populated_Mask = self.CTSMethod.GetAuthPayloadDetails(dig1[2], "Slots_Populated_Mask", "B1", "[7:4")[0]['sDescription'].split(":")[-1].strip()
                    # Slots_Returned_Mask = self.CTSMethod.GetAuthPayloadDetails(dig1[2], "Slots_Returned_Mask", "B1", "[3:0")[0]['sDescription'].split(":")[-1].strip()
                    # Digests_Returned = self.CTSMethod.GetAuthPayloadDetails(dig1[2], "Digests_Returned", "B2_B32", "[7:0")[0]['sRawData']
                    Authentication_Protocol_Version = self.CTSMethod.PayloadDetails_Auth(dig1[2], "Authentication_Protocol_Version")[0]['sDescription'].split(":")[-1].strip()
                    Slots_Populated_Mask = self.CTSMethod.PayloadDetails_Auth(dig1[2], "Slots_Populated_Mask")[0]['sDescription'].split(":")[-1].strip()
                    Slots_Returned_Mask = self.CTSMethod.PayloadDetails_Auth(dig1[2], "Slots_Returned_Mask")[0]['sDescription'].split(":")[-1].strip()
                    Digests_Returned = self.CTSMethod.PayloadDetails_Auth(dig1[2], "Digests_Returned")[0]['sRawData']
                    res.append([f"Authentication_Protocol_Version: {Authentication_Protocol_Version}", Enums.TestResult.PASS])
                    res.append([f"Slots_Populated_Mask: {Slots_Populated_Mask}", Enums.TestResult.PASS])
                    res.append([f"Slots_Returned_Mask: {Slots_Returned_Mask}", Enums.TestResult.PASS])
                    res.append([f"Digests_Returned: {Digests_Returned}", Enums.TestResult.PASS])
                    # print("Authentication_Protocol_Version:",Authentication_Protocol_Version)
                    # print("Slots_Populated_Mask:",Slots_Populated_Mask)
                    # print("Slots_Returned_Mask:",Slots_Returned_Mask)
                    # print("Digests_Returned:",Digests_Returned)
                    digests_details.append([Authentication_Protocol_Version,Slots_Populated_Mask,Slots_Returned_Mask,Digests_Returned])
                    id = dig1[2]
                else: res.append([f"DIGESTS_{cnt} response not found.", Enums.TestResult.FAIL])
            # else: res.append([f"GET_DIGESTS_{cnt} Packet not found.", Enums.TestResult.FAIL])
            id += 1

        if len(digests_details) == 5:
            for i,val in enumerate(digests_details[1:]):
                if digests_details[0][0] == val[0] and digests_details[0][1] == val[1] and digests_details[0][2] == val[2] and digests_details[0][3] == val[3]:
                    res.append([f"Digest_1 = Digest_{i+2}", Enums.TestResult.PASS])
                else: res.append([f"Digest_1 != Digest_{i+2}", Enums.TestResult.FAIL])
        else: res.append([f"Only {len(digests_details)} Digests are received instead of 5.", Enums.TestResult.FAIL])

        # print("values:",digests_details[0][3].split("-"))
        data = digests_details[0][3].split("-")
        dig_len = len(data)

        if dig_len == 32:
            res.append([f"Digest_1 = the 32-byte SHA-256 digest of Certificate_1, Expected: 32 bytes", Enums.TestResult.PASS])
        else: res.append([f"Digest_1 = the {dig_len}-byte SHA-256 digest of Certificate_1, Expected: 32 bytes", Enums.TestResult.FAIL])
        return res

    def Neg_Error_Status(self,Flow_limit,Check):
        # print("Neg_Error_Status")
        res=[]
        config = self.PktMethod.GetPacketDetails(packet="Configuration",limit=Flow_limit,Type="Packet")
        if len(config) > 2:
            res.append([f"Configuration packet found at {round(config[0],3)} sec", Enums.TestResult.PASS])
            respid = self.PktMethod.GetPacketResponse2(config[2], [config[2]+1, Flow_limit[1]])
            if respid is not None:
                R1 = self.file_list[respid]['pktType']
                if "MPP" in R1:
                    res.append([f"R1:{R1} response received for configuration packet", Enums.TestResult.PASS])
                elif "NAK" in R1:
                    res.append([f"R1:{R1} response received for configuration packet", Enums.TestResult.PASS])
                    get_error = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx error status",limit=[respid,Flow_limit[1]],Type="Packet")
                    if len(get_error) > 2:
                        res.append([f"Get Request(PTx error status) packet found at {round(get_error[0],3)} sec", Enums.TestResult.PASS])
                        respid2 = self.PktMethod.GetPacketResponse2(get_error[2], [get_error[2]+1, Flow_limit[1]])
                        if respid2 is not None:
                            if self.file_list[respid2]['pktType'] == "PTx Error status":
                                res.append([f"PTx Error status response received at {round(self.file_list[respid2]['startTime'],3)} sec with following details", Enums.TestResult.PASS])
                                error_code = int(self.PktMethod.GetPayloadDetails(respid2, "Error")[0]['sRawData'],16)
                                error_data = self.PktMethod.GetPayloadDetails(respid2, "Error")[0]['sDescription'].split(":")[-1].strip()
                                if error_code == 1 and all(ele in error_data.lower() for ele in ["unable to compute","k","est"]):
                                    res.append([f"E1: {error_data}(Value:{error_code}) found in PTx error status response, Expected: Unable to compute KEST (Value:1)", Enums.TestResult.PASS])
                                else: res.append([f"E1: {error_data}(Value:{error_code}) found in PTx error status response, Expected: Unable to compute KEST (Value:1)", Enums.TestResult.FAIL])

                                end_pkt = self.PktMethod.GetPacketDetails(packet=Check["packet1"][0],value=Check["packet1"][1],limit=[respid2,Flow_limit[1]],Type=Check["packet1"][2])
                                if len(end_pkt) > 2:
                                    res.append([f"{Check["packet1"][0]}({Check["packet1"][1]}) {Check["packet1"][2]} found at {round(end_pkt[0],3)} sec", Enums.TestResult.PASS])

                                    if "SRQ" in Check["packet1"][0]:
                                        respid3 = self.PktMethod.GetPacketResponse2(end_pkt[2], [end_pkt[2]+1, Flow_limit[1]])
                                        if respid3 is not None:
                                            R2 = self.file_list[respid3]['pktType']
                                            if "NAK" in R2:
                                                res.append([f"R2: {R2} response received for {Check["packet1"][0]}({Check["packet1"][1]}) {Check["packet1"][2]}, Expected: NAK", Enums.TestResult.PASS])
                                                cvpkp = self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk",limit=[respid3,Flow_limit[1]],Type="TesterMsg")
                                                if len(cvpkp) > 2:
                                                    res.append([f"Uro drops below 200mV at {round(cvpkp[0],3)} sec", Enums.TestResult.PASS])
                                                    t1 = round((cvpkp[0]-self.file_list[respid3]['stopTime'])*1000,3)
                                                    ChkRes = CommonMethods.check_measure([28], t1, "LTEQL")
                                                    res.append([f"Tterminate t1 is {ChkRes[3]} ms from the end of NAK to the start of Uro droppping below 200mV, Expected: {ChkRes[2]} ms", ChkRes[1]])
                                                else: res.append([f"Uro drops below 200mV packet not found", Enums.TestResult.FAIL])
                                            else: res.append([f"R2: {R2} response received for {Check["packet1"][0]}({Check["packet1"][1]}) {Check["packet1"][2]}, Expected: NAK", Enums.TestResult.FAIL])
                                        else: res.append([f"Response not found for {Check["packet1"][0]}({Check["packet1"][1]}) {Check["packet1"][2]}", Enums.TestResult.FAIL])
                                    
                                    elif "End Power Transfer" in Check["packet1"][0]:
                                        cvpkp = self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk",limit=[end_pkt[2],Flow_limit[1]],Type="TesterMsg")
                                        if len(cvpkp) > 2:
                                            res.append([f"Uro drops below 200mV at {round(cvpkp[0],3)} sec", Enums.TestResult.PASS])
                                            t1 = round((cvpkp[0]-end_pkt[1])*1000,3)
                                            ChkRes = CommonMethods.check_measure([28], t1, "LTEQL")
                                            res.append([f"Tterminate t1 is {ChkRes[3]} ms from the end of {Check["packet1"][0]}({Check["packet1"][1]}) {Check["packet1"][2]} to the start of Uro droppping below 200mV, Expected: {ChkRes[2]} ms", ChkRes[1]])
                                        else: res.append([f"Uro drops below 200mV packet not found", Enums.TestResult.FAIL])

                                else: res.append([f"{Check["packet1"][0]}({Check["packet1"][1]}) {Check["packet1"][2]} not found", Enums.TestResult.FAIL])
                            else: res.append([f"{self.file_list[respid2]['pktType']} response found for Get Request(PTx error status) packet, Expected: PTx Error status", Enums.TestResult.FAIL])
                        else: res.append([f"Response not found for Get Request(PTx error status) packet", Enums.TestResult.FAIL])
                    else: res.append([f"Get Request(PTx error status) packet not found", Enums.TestResult.FAIL])
                else: res.append([f"R1: {R1} response found for Configuration packet, Expected: MPP or ACK or NAK", Enums.TestResult.FAIL])
            else: res.append([f"Response not found for Configuration packet", Enums.TestResult.FAIL])
        else: res.append([f"Configuration packet not found", Enums.TestResult.FAIL])

                                        

                                        



                                        
                             





            
                        
                        




                




        return res

        
    # Logging
    def _fmt_header(self):
        h = self.Header
        return (
            f"  Testcase  : {h.get('TestcaseName')} ({h.get('TestcaseID')})\n"
            f"  DUT       : {h.get('DUTName')} ({h.get('DUTID')}) | Board: {h.get('BoardNo')} | Coil: {h.get('Coil')}\n"
            f"  Run       : {h.get('Run')} | Cert: {h.get('Certification')} | SW: {h.get('SWVersion')} | FW: {h.get('FWVersion')}\n"
            f"  Result    : TC={h.get('TCresult')}  SW={h.get('SWresult')} | Engineer: {h.get('Engineer')}"
        )

import traceback
# import io
# import zipfile, re
# import os
# import csv
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
from OfflineValidationModules.MPPTPR.MPPTPR4_CommonHelper import CommonCTSChecks

# from pathlib import Path
# import pandas as pd1
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


class CTSChecks_MPP_TPR4():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson):
        #Define Global variables
        # self.JCTSData = JCTSData
        CTS = JsonOperations('json/CTSvalidation/MPPTPR.json')
        self.JCTSData =CTS.read_file()
        self.JapiData = JapiData
        self.Header = Header
        self.Product = self.Header['Product']
        self.Mode = self.Header['Mode']
        self.ProjectJson = ProjectJson
        self.file_list = file_list
        self.BackupJson = BackupJson
        self.BKjson = JsonOperations(self.BackupJson)
        self.BKjsonData = self.BKjson.read_file()

        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        #Define modules
        self.PktMethod = PacketMethods(file_list=self.file_list,Header=self.Header)
        self.PlotMethod = PlotMethods(Header=self.Header)
        # self.Certification=self.BKjsonData['testBkpAppModeString']
       

    def CTSChecks(self,flwID,flows,CTSJson):
        # print("CTSChecks starts")
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
                    #     methodcall=getattr(self.CTSMethod,CTSCheck)
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


                    
                    AllMeasures[f"{CTSCheck}_SEQ"] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
                    AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL

                    AllMeasures[f'{CTSCheck}_remarks']='NA'
                    if Check.get('expected') and Check['expected'] in ["OffsetReneg2"]:
                        tempRes = AllMeasures[f"{CTSCheck}_Details"]
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
                        AllMeasures[f'{CTSCheck}_remarks']=';'.join([item[0] for item in tempRes if item[1]==Enums.TestResult.FAIL])
                        AllMeasures[f'{CTSCheck}_Details']=tempRes
                    
                    else:
                        #by default all the checks has sub-checks ensure the sub-checks results for main check pass / fail 
                        AllMeasures[f"{CTSCheck}_SEQ"] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
                        AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                        AllMeasures[f'{CTSCheck}_remarks']='NA'
                        if len(AllMeasures[f"{CTSCheck}_Details"]) >0:
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
                    if Check['Result_check'] == True:
                        # print("Header:",self.Header)
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
        # # print("AllMeasures:",AllMeasures)
        return AllMeasures

    def Poffset(self,Flow_limit,Check):
        print("Poffset checking")
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)

        end = Flow_limit[1]
        pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=Flow_limit)
        if len(pkt_exit)>2:
            ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[pkt_exit[2],0],Type="Response")
            if len(ECAP)>2:
                renegpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                res.append([f"Negotiable_Load_Power in ECAP is {renegpwr}W", Enums.TestResult.PASS])

                reqload = renegpwr*(Check['TargetLoadPercent'])/100
                res.append([f"{Check['TargetLoadPercent']}% of Negotiable_Load_Power is {reqload}W", Enums.TestResult.PASS])

                renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(reqload*1000)}mW",limit=[ECAP[2],end],Type='TesterMsg')
                # print("renegload:",renegload)
                if len(renegload)>2:
                    res.append([f"Set_Load {int(reqload*1000)}mW found at {round(renegload[0],3)}sec",Enums.TestResult.PASS])
                    self.GetInitailVoltage(Check['flow'],[renegload[2],end])
                    
                    irect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                    vrect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData)
                    power = round(vrect[0]*irect[0],3)
                    # print("vrect:",vrect,"irect:",irect,"power:",power)
                    res.append([f"Prect after control stabilization is {power} W at {round(self.file_list[self.stability]['startTime'],3)} sec, Expected: >= {reqload}W", Enums.TestResult.PASS if power>=reqload else Enums.TestResult.FAIL])
                # else: res.append([f"Set_Load {int(reqload*1000)}mW not found", Enums.TestResult.FAIL])

                    #2.Find PLA packts has power offset
                    duration_flag = False
                    removepwr = False
                    id = self.stability#renegload[2]
                    while id < end:
                        TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,end])
                        # # print("TempPkt2:",TempPkt2)
                        if len(TempPkt2)>2:
                            Pktresp = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,end])
                            if Pktresp is not None:
                                if 'exp_resp' in Check:
                                    if 'Response' in self.PktMethod.GetPacketType(Pktresp):
                                        if self.file_list[Pktresp]['pktType'] in Check["exp_resp"]:
                                            res.append([f"{self.file_list[Pktresp]['pktType']} response received for PLA packet at index@{Pktresp}, Expected: {Check["exp_resp"]}", Enums.TestResult.PASS])
                                        else: res.append([f"{self.file_list[Pktresp]['pktType']} response received for PLA packet at index@{Pktresp}, Expected: {Check["exp_resp"]}", Enums.TestResult.FAIL])
                                else: res.append([f"{self.file_list[Pktresp]['pktType']} response received to PLA_2 packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                                

                            TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                            TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                            if len(TempPkt3)>2 and len(TempPkt4)>2:
                                RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[1]
                                Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[0]

                                RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                                Prect_Offset =  GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                                
                                Prect_Rcv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"PRECT")[0]['sDescription'])[0]
                                RP_Rcvd = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'])[0]
                                # print("Prect_Actual:",Prect_Actual,"Prect_Offset:",Prect_Offset,"Prect_Rcv:",Prect_Rcv)
                                # print("RP_Actual:",RP_Actual,"RP_Offset:",RP_Offset,"RP_Rcvd:",RP_Rcvd)
                                #check for offset value are applied as like mentioned in the CTS
                                if 'FixedOffsetValues' in Check:
                                    # # print(RP_Offset,Prect_Offset)
                                    if RP_Offset!=Check['FixedOffsetValues']['RP'] or Prect_Offset!=Check['FixedOffsetValues']['Prect']:
                                        res.append([f"PLA offset issue at {round(TempPkt2[0],3)}: RP Offset:{RP_Offset}W Expected :{Check['FixedOffsetValues']['RP']}, Prect Offset:{Prect_Offset}W Expected :{Check['FixedOffsetValues']['Prect']}W",Enums.TestResult.FAIL])
                                #Ensure that the offset calculations are correct
                                PLARes = Enums.TestResult.PASS if Prect_Rcv == round((Prect_Actual-(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual-(RP_Offset)),3) else Enums.TestResult.FAIL
                                if PLARes==Enums.TestResult.FAIL:res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect_Rcv}W and RP={RP_Rcvd}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
                                else: res.append([f"Prect_Actual:{Prect_Actual}W is matching with Prect_Rcv:{Prect_Rcv}W after applying Prect_Offset:{Prect_Offset}W and RP_Actual:{RP_Actual}W is matching with RP_Rcvd:{RP_Rcvd}W after applying RP_Offset:{RP_Offset}W",Enums.TestResult.PASS])
                                
                                
                                # PLA response
                                x = TempPkt2[2]+1
                                if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                                    x += 1
                                
                                # if 'Response' in self.PktMethod.GetPacketType(x):
                                #     res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet", Enums.TestResult.PASS])
                                    

                                # Throttle check  
                                if 'NAK' in self.file_list[x]['pktType']:
                                    nak_chk = True
                                    vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                    irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                    Prect1 = vrect1*irect1

                                    vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                    irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                    Prect2 = vrect2*irect2

                                    pwr_diff = round((Prect2-Prect1)*1000,3)
                                    
                                    
                                    if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                                    
                                elif 'ACK' in self.file_list[x]['pktType']:
                                    res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                                
                                
                                #check PLA until
                                if 'CheckDuration' in Check:
                                    # # print('diff',TempPkt2[0] - TempPkt1[0])
                                    duration = (TempPkt2[0] - self.file_list[self.stability]['startTime'])
                                    if duration >= Check['CheckDuration']:
                                        duration_flag = True
                                        break
                                if Pktresp is not None:
                                    if self.file_list[Pktresp]['pktType'] in ['ATN']:
                                        id = Pktresp
                                        break
                            id = TempPkt2[2]
                        id += 1
                    
                    # Power remove
                    if 'Remove_Power' in Check:
                        sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[id,end],Type="TesterMsg")
                        if Check['Remove_Power']:
                            if len(sd)> 2:
                                removepwr = True
                                res.append([f"PTx removed power at {round(sd[0],3)} sec", Enums.TestResult.PASS])
                            else: res.append([f"PTx does not removed power", Enums.TestResult.FAIL])
                        else:
                            if len(sd)> 2:
                                removepwr = True
                                res.append([f"PTx removed power at {round(sd[0],3)} sec", Enums.TestResult.FAIL])
                            else: res.append([f"PTx does not removed power", Enums.TestResult.PASS])

                    if 'CheckDuration' in Check:
                        if not removepwr:
                            if duration_flag:
                                res.append([f"TPR monitored PLA packets for at least 1 minute after stabilizing.", Enums.TestResult.PASS])
                            else: res.append([f"TPR monitored PLA packets for only {round(duration,3)} sec after stabilizing.", Enums.TestResult.FAIL])

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

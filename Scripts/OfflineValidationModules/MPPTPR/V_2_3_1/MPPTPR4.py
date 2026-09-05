# from OfflineValidationModules import CTSChecksC3TPT
import traceback
# import io
# import zipfile
import re
# import os
# import csv
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
from OfflineValidationModules.MPPTPR.MPPTPR4_CommonHelper import CommonCTSChecks



# from concurrent.futures import ThreadPoolExecutor, as_completed
# import traceback
# import logging


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
    # logged_testcases = set()
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
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        if self.Certification in ["2.0.1","2.1.0","2.2.1","2.3.0"]:
            self.ECAP_pkt = "Extended_Power_Transmitter_Extended_Capabilities"
            self.XID_pkt = "MPP_Extended_Identification"
        else:
            self.ECAP_pkt = "Power Transmitter Extended Capabilities"
            self.XID_pkt = "Extended Identification"
   

    def CTSChecks(self, flwID, flows, CTSJson):
        print("flwID:", flwID, flows[flwID]['Limit'])
        self.CTSMethod = CommonCTSChecks(self.Header, self.file_list, self.JapiData,self.BackupJson, self.ProjectJson, flows)
        AllMeasures = {}

        for CTSCheck in CTSJson:
            AllMeasures[CTSCheck] = None
            AllMeasures[f'{CTSCheck}_Details'] = []
            AllMeasures[f'{CTSCheck}_exp'] = "NA"

            for Check in CTSJson[CTSCheck]:
                if Check['flow'] == flwID:
                    Flow_limit = flows[flwID]['Limit']

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

                    # Results validation
                    AllMeasures[f"{CTSCheck}_SEQ"] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
                    AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                    AllMeasures[f'{CTSCheck}_remarks']='NA'
                    if Check.get('expected') and Check['expected'] in ["Poffset","OffsetReneg2","OffsetReneg","PLAOffsetCheck"]:
                        if len(AllMeasures[f"{CTSCheck}_Details"]) >0:
                            tempRes = AllMeasures[f"{CTSCheck}_Details"]
                            throttle_failcnt = 0
                           
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

                            for item in tempRes:
                                if item[1]==Enums.TestResult.FAIL and "not throttled" in item[0]:
                                    throttle_failcnt+=1
                                    if throttle_failcnt>=3:
                                        AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.FAIL
                                        break
                                    else: AllMeasures[f'{CTSCheck}_res']=Enums.TestResult.PASS

                            AllMeasures[f'{CTSCheck}_remarks']=';'.join([item[0] for item in tempRes if item[1]==Enums.TestResult.FAIL])
                            AllMeasures[f'{CTSCheck}_Details']=tempRes
                            print("throttle_failcnt:",throttle_failcnt)
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
                                PLARes = Enums.TestResult.PASS if Prect_Rcv == round((Prect_Actual+(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual+(RP_Offset)),3) else Enums.TestResult.FAIL
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


    def PNG_ILL(self,Flow_limit,Check):
        print("I am in PNG_ILL")
        res = []
        id = Flow_limit[0]
        end = Flow_limit[1]
        XID = self.PktMethod.GetPacketDetails(packet=self.XID_pkt,limit=[id,end],Type="Packet") 
        if len(XID)>2:
            res.append([f"{self.XID_pkt} Packet found at {round(XID[0],3)} sec", Enums.TestResult.PASS])
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[XID[2],end+1],Type="TesterMsg") 
            if len(sd)>2:
                x = XID[2]+1
                t1 = 0
                self.illegal_flag = False

                while x < sd[2]:
                    if self.PktMethod.GetPacketType(x) == "Packet" and self.file_list[x]['pktType'] in ["Signal strength","Identification",self.XID_pkt,"Configuration"]:
                        res.append([f"{self.file_list[x]['pktType']} illegal Packet found at {round(self.file_list[x]['startTime'],3)} sec", Enums.TestResult.PASS])
                        self.illegal_flag = True
                        if self.file_list[x]['pktType'] == "Signal strength":
                            t1 = self.file_list[x]['stopTime']
                            if sd[0]-t1 <= 0.028:
                                # res.append([f"Uro drops below 200 mV within {round((sd[0]-t1)*1000,3)} ms from the end of the illegal SIG data packet, Expected: <= 28 ms", Enums.TestResult.PASS])
                                res.append([f"PTxDUT removes the power signal in Tterminate {round((sd[0]-t1)*1000,3)} ms after illegal SIG packet is received, Expected: <= 28 ms", Enums.TestResult.PASS])
                            elif sd[0]-t1 <= 0:
                                res.append([f"Tterminate is 0 ms as Uro drops below 200 mV before the end of the illegal SIG data packet, Expected: <= 0 ms", Enums.TestResult.PASS])
                            else: res.append([f"Uro drops below 200 mV within {round((sd[0]-t1)*1000,3)} ms from the end of the illegal SIG data packet, Expected: <= 28 ms", Enums.TestResult.FAIL])
                    x += 1
                
                res.append([f"Shutdown TesterMsg found at {round(sd[0],3)} sec", Enums.TestResult.PASS])
                cvpkp = self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk",limit=[XID[2]+1,len(self.file_list)-1],Type="TesterMsg") 
                if len(cvpkp)>2:
                    res.append([f"CoilVoltpkpk TesterMsg found at {round(cvpkp[0],3)} sec", Enums.TestResult.PASS])
                    # reping 
                    pd = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[sd[2]+1,len(self.file_list)-1],Type="TesterMsg") 
                    if len(pd)>2:
                        res.append([f"Ping Detected at {round(pd[0],3)} sec", Enums.TestResult.PASS])
                        ChkRes = CommonMethods.check_measure([500],(pd[0]-cvpkp[1])*1000,"LTEQL")
                        res.append([f"Measured Tstart_after_illegal is {round(ChkRes[3],3)} ms from CoilVoltpkpk to Ping Detected., Expected: {ChkRes[2]} ms", ChkRes[1]])

                        fop_pkt = self.PktMethod.GetPacketDetails(packet="",value="FOP:",limit=[pd[2]+1,len(self.file_list)-1],Type="TesterMsg") 
                        if len(fop_pkt)>2:
                            fop = float(self.file_list[fop_pkt[2]]['value'].split(":")[1].split(" ")[0].strip())
                            ChkRes2 = CommonMethods.check_measure([127.5,128.5],fop,0)
                            res.append([f"PTx repinged in {ChkRes2[3]} kHz, Expected: {ChkRes2[2]} kHz", ChkRes2[1]])

                            ss = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[fop_pkt[2]+1,len(self.file_list)-1],Type="Packet") 
                            if len(ss)>2:
                                res.append([f"Signal strength Packet found at {round(ss[0],3)} sec", Enums.TestResult.PASS])
                                AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
                                vrect_max = self.PktMethod.CalculateVoltTwindow(ss[2],AllChannelData,winsize=[9,(ss[0]-pd[0])*1000],max=True)[0]
                                ChkRes3 = CommonMethods.check_measure([19],vrect_max,"LTEQL")
                                res.append([f"Vrect_max of {ChkRes3[3]} V at Signal strength packet, Expected: {ChkRes3[2]} V", ChkRes3[1]])
                            else: res.append([f"Signal strength Packet not found", Enums.TestResult.FAIL])

                    else: res.append([f"Ping not detected after shutdown", Enums.TestResult.FAIL])
                else: res.append([f"CoilVoltpkpk TesterMsg not found after illegal packet", Enums.TestResult.FAIL])
                
                if not self.illegal_flag: res.append([f"Illegal Packet not found after {self.XID_pkt} packet", Enums.TestResult.FAIL])
            else: res.append([f"Shutdown TesterMsg not found", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"{self.XID_pkt} Packet not found", Enums.TestResult.FAIL])
        return res


    def Cloak_EDS(self,Flow_limit,Check):
        start = Flow_limit[0]
        end = len(self.file_list)-1
        res=[]
        SDSR_ACK_flag = True
        # 1st GET_CERTIFICATE
        sadc_open1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[start, end],Type="Packet")
        if len(sadc_open1)>2:
            res.append([f"SADC Open Stream packet found at {round(sadc_open1[0],3)} sec", Enums.TestResult.PASS])
            sadc1_resp = self.PktMethod.GetPacketResponse2(sadc_open1[2], [sadc_open1[2]+1, end])
            if sadc1_resp is not None and self.file_list[sadc1_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadc1_resp]['value']:
                res.append([f"SDSR/ACK response found at {round(self.file_list[sadc1_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.PASS])
            else:
                SDSR_ACK_flag = False
                res.append([f"{self.file_list[sadc1_resp]['pktType']}_{self.file_list[sadc1_resp]['value']} found at {round(self.file_list[sadc1_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.FAIL])

            sadt1 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open1[2], end],Type="Packet")
            if len(sadt1)>2:
                
                cert_type1 = self.PktMethod.GetPayloadDetails(sadt1[2],'Get_Certificate')[0]['sDescription'].strip()
                print("cert_type1:",cert_type1)   
                normal_chk1 = {"ChecksList": [{"packet": ["SADT",None],"Checks": {"OffsetA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"LengthA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Offset70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Length70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Slot_Number": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},},"PacketType": "Packet","refPrevious": False}],"flow": 2,"Result_check": False,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 3}
                bits_resp = self.CTSMethod.BitsCheck_New([sadc_open1[2],end],normal_chk1)
                print("bits_resp:", bits_resp)
                res.append(bits_resp[0])

                if cert_type1 == "Get_Certificate":
                    res.append([f"{cert_type1} found in SADT found at {round(sadt1[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.PASS])
                else:
                    res.append([f"Invalid {cert_type1} found in SADT found at {round(sadt1[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.FAIL])
                for chks in bits_resp[1:]:
                    res.append(chks)

                # Cloak
                clk1 = self.PktMethod.GetPacketDetails(packet='Cloak',limit=[sadt1[2], end],Type="Packet")
                if len(clk1)>2:
                    clk_rsn1 = self.PktMethod.GetPayloadDetails(clk1[2],'Reason')[0]['sDescription'].split(":")[-1].strip()
                    res.append([f"Cloak initiated with {clk_rsn1} reason at {round(clk1[0],3)} sec", Enums.TestResult.PASS])

                    clk_exit = self.PktMethod.GetPacketDetails(packet='MPP_Cloak_Exit',limit=[sadt1[2], end],Type="TesterMsg")
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
                            res.append([f"SADC Open Stream packet found at {round(sadc_open2[0],3)} sec after cloak exit", Enums.TestResult.PASS])
                            sadco2_resp = self.PktMethod.GetPacketResponse2(sadc_open2[2], [sadc_open2[2]+1, end])
                            if sadco2_resp is not None and self.file_list[sadco2_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadco2_resp]['value']:
                                res.append([f"SDSR/ACK response found at {round(self.file_list[sadco2_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.PASS])
                            else:
                                SDSR_ACK_flag = False
                                res.append([f"{self.file_list[sadco2_resp]['pktType']}_{self.file_list[sadco2_resp]['value']} found at {round(self.file_list[sadco2_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.FAIL])
                            
                            sadt2 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open2[2], end],Type="Packet")
                            if len(sadt2)>2:
                                sadco2_resp = self.PktMethod.GetPacketResponse2(sadt2[2], [sadt2[2]+1, end])
                                
                                cert_type2 = self.PktMethod.GetPayloadDetails(sadt2[2],'Get_Certificate')[0]['sDescription'].strip()
                                print("cert_type2:",cert_type2)
                                
                                
                                normal_chk2 = {"ChecksList": [{"packet": ["SADT",None],"Checks": {"OffsetA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"LengthA8": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Offset70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Length70": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},"Slot_Number": {"expected": 0,"flag": "sRawData","comp": "EQL","units": " "},},"PacketType": "Packet","refPrevious": False}],"flow": 2,"Result_check": False,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 3}
                                bits_resp = self.CTSMethod.BitsCheck_New([sadc_open2[2],end],normal_chk2)
                                print("bits_resp:", bits_resp)
                                res.append(bits_resp[0])

                                if cert_type2 == "Get_Certificate":
                                    res.append([f"{cert_type2} found in SADT found at {round(sadt2[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.PASS])
                                else:
                                    res.append([f"Invalid {cert_type2} found in SADT found at {round(sadt2[0],3)} sec, Expected: Get_Certificate", Enums.TestResult.FAIL])
                                for chks in bits_resp[1:]:
                                    res.append(chks)

                                sadc_close2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[sadc_open2[2], end],Type="Packet")
                                if len(sadc_close2)>2:
                                    res.append([f"SADC Close Stream packet found at {round(sadc_close2[0],3)} sec after SADT", Enums.TestResult.PASS])
                                    sadccl2_resp = self.PktMethod.GetPacketResponse2(sadc_close2[2], [sadc_close2[2]+1, end])
                                    if sadccl2_resp is not None and self.file_list[sadccl2_resp]['pktType'] == "SDSR" and "ACK" in self.file_list[sadccl2_resp]['value']:
                                        res.append([f"SDSR/ACK response found at {round(self.file_list[sadccl2_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.PASS])
                                    else:
                                        SDSR_ACK_flag = False
                                        res.append([f"{self.file_list[sadccl2_resp]['pktType']}_{self.file_list[sadccl2_resp]['value']} found at {round(self.file_list[sadccl2_resp]['startTime'],3)} sec, Expected: SDSR/ACK", Enums.TestResult.FAIL])

                                    # CERTIFICATE
                                    sadc_open3 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[clk_exit[2], end],Type="Response")
                                    if len(sadc_open3)>2:
                                        res.append([f"SADC Open Stream Response found at {round(sadc_open3[0],3)} sec after cloak exit", Enums.TestResult.PASS])
                                        
                                        sadt3 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open3[2], end],Type="Response")
                                        if len(sadt3)>2:
                                            res.append([f"SADT Response found at {round(sadt3[0],3)} sec", Enums.TestResult.PASS])
                                            cert_type3 = self.PktMethod.GetPayloadDetails(sadt3[2],'Certificate')[0]['sDescription'].strip()
                                            print("cert_type3:",cert_type3)
                                            if cert_type3 == "Certificate":
                                                res.append([f"{cert_type3} found in SADT response at {round(sadt3[0],3)} sec", Enums.TestResult.PASS])
                                            else:
                                                res.append([f"Invalid {cert_type3} found in SADT response at {round(sadt3[0],3)} sec", Enums.TestResult.FAIL])

                                            header_val = self.file_list[sadt3[2]]['header_Payload']['sFieldType'].split()[4].strip()
                                            print("header_val:", header_val)
                                            if header_val == "0x12":
                                                res.append([f"Certificate response started with header {header_val}, Expected: 0x12", Enums.TestResult.PASS])
                                            else:res.append([f"Certificate response started with header {header_val}, Expected: 0x12", Enums.TestResult.FAIL])
                                        else:res.append([f"SADT Response not found", Enums.TestResult.FAIL])
                                    else:res.append([f"SADC Open Stream Response not found", Enums.TestResult.FAIL])
                                else:res.append([f"SADC Close Stream packet not found", Enums.TestResult.FAIL])
                            else:res.append([f"SADT packet not found", Enums.TestResult.FAIL])
                        else:res.append([f"SADC Open Stream packet not found", Enums.TestResult.FAIL])
                    else: res.append([f"MPP_Cloak_Exit not found", Enums.TestResult.FAIL])
                else: res.append([f"Cloak not found", Enums.TestResult.FAIL])
            else:res.append([f"SADT packet not found", Enums.TestResult.FAIL])
        else:res.append([f"SADC Open Stream packet not found", Enums.TestResult.FAIL])

        if SDSR_ACK_flag:
            res.append([f"PTx DUT responded with SDSR/ACK to all request messages in GET_CERTIFICATE", Enums.TestResult.PASS])
        else:
            res.append([f"PTx DUT not responded with SDSR/ACK to all request messages in GET_CERTIFICATE", Enums.TestResult.FAIL])

        return res

    
        
        

    def OffsetReneg(self,Flow_limit,Check):
        # print("OffsetReneg started")
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)

        res = []
        Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
        # print("Excapres:",Excapres)
        if len(Excapres)> 2:
            EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
            for ck in EXCAP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
            # print("EXCAP:",EXCAP)
            mode1 = sorted(EXCAP, key=EXCAP.get, reverse=True)[1]  # second highest potential load power
            mode2 = max(EXCAP, key=EXCAP.get)    # highest potential load power
            # print("mode1:",mode1, "mode2:",mode2)

            end = len(self.file_list)-1
            pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=Flow_limit)
            if len(pkt_exit)>2:
                #Check for power level reached to Nominal_Power_Mode potential load power
                ideal_pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[pkt_exit[2],Flow_limit[1]],Type="TesterMsg")
                print("ideal_pkt:",ideal_pkt)
                if len(ideal_pkt)>2:
                    stable_pla2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[ideal_pkt[2]+10,ideal_pkt[2]-20],Type="Packet")
                    print("stable_pla2:",stable_pla2)
                    if len(stable_pla2)>2:
                        # res.append([f"PLA_2 packet found at {round(stable_pla2[0],3)} sec after cloak exit", Enums.TestResult.PASS])
                        Prect_chk2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(stable_pla2[2],"PRECT")[0]['sDescription'])[0]
                        print("Prect_chk2:",Prect_chk2)
                        print("EXCAP[\"Nominal_Power_Mode\"]:",EXCAP["Nominal_Power_Mode"])
                        if Prect_chk2 >= EXCAP["Nominal_Power_Mode"]:
                            res.append([f"Power level reached to Nominal_Power_Mode potential load power i.e, {Prect_chk2}W at {round(stable_pla2[0],3)} sec, Expected: {EXCAP['Nominal_Power_Mode']}W", Enums.TestResult.PASS])
                        else:
                            pass

                        

                MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=[pkt_exit[2],end],Type="Packet")
                if len(MSRreq2)> 2:
                    PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                    # print("PrefMode2:",PrefMode2)
                    res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: High_Power_Mode", Enums.TestResult.PASS if PrefMode2 == "High_Power_Mode" else Enums.TestResult.FAIL])
                    MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],end],Type="Response")
                    if len(MSS2)> 2:
                        res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", Enums.TestResult.PASS])
                        # Latest capabilities from DUT
                        load_set_done = self.PktMethod.GetPacketDetails(packet="Load Set Done",limit=[MSS2[2],end],Type="TesterMsg")
                        if len(load_set_done)>2:
                            ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[load_set_done[2],MSS2[2]],Type="Response")
                            if len(ECAP)>2:
                                renegpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                res.append([f"Negotiable_Load_Power in ECAP is {renegpwr}W", Enums.TestResult.PASS])

                                reqload = renegpwr*(Check['TargetLoadPercent'])/100
                                res.append([f"{Check['TargetLoadPercent']}% of Negotiable_Load_Power is {reqload}W", Enums.TestResult.PASS])

                                renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(reqload*1000)}mW",limit=[ECAP[2],end],Type='TesterMsg')
                                print("renegload:",renegload)
                                if len(renegload)>2:
                                    res.append([f"Set_Load {int(reqload*1000)}mW found at {round(renegload[0],3)}sec",Enums.TestResult.PASS])
                                    self.GetInitailVoltage(Check['flow'],[renegload[2],end])
                                    
                                    irect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                                    vrect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData)
                                    power = round(vrect[0]*irect[0],3)
                                    # print("vrect:",vrect,"irect:",irect,"power:",power)
                                    res.append([f"Prect after control stabilization is {power} W at {round(self.file_list[self.stability]['startTime'],3)} sec, Expected: >= {reqload}W", Enums.TestResult.PASS if power>=reqload else Enums.TestResult.FAIL])
                                # else: res.append([f"Set_Load {int(reqload*1000)}mW not found", Enums.TestResult.FAIL])

                                    duration_flag = False
                                    removepwr = False
                                    #2.Find PLA packts has power offset
                                    id = self.stability#renegload[2]
                                    while id < end:
                                        TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,end])
                                        # # print("TempPkt2:",TempPkt2)
                                        if len(TempPkt2)>2:
                                            Pktresp = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,end])
                                            if Pktresp is not None:
                                                
                                                res.append([f"{self.file_list[Pktresp]['pktType']} response received to PLA_2 packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                                                

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
                                                PLARes = Enums.TestResult.PASS if Prect_Rcv == round((Prect_Actual+(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual+(RP_Offset)),3) else Enums.TestResult.FAIL
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
                                                
                                                
                                                
                                                if Pktresp is not None:
                                                    if self.file_list[Pktresp]['pktType'] in ['ATN']:
                                                        id = Pktresp
                                                        break
                                            else: 
                                                res.append([f"Removed the applied POFFSET from {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                                                break
                                            id = TempPkt2[2]
                                        id += 1
                                    
                                    ECAP2 = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[self.stability,end],Type="Response")
                                    if len(ECAP2)>2:
                                        negpwr2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP2[2],'Negotiable_Load_Power')[0]['sDescription'])[0]
                                        # print("negpwr2:",negpwr2)
                                        res.append([f"RENEG_POWER in {self.ECAP_pkt} is {negpwr2}W found at index@{ECAP2[2]}", Enums.TestResult.PASS])
                                        reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[ECAP2[2],end],Type="Packet")
                                        
                                        if len(reneg)>2:
                                            res.append([f"Renegotiate packet found at index@{reneg[2]}", Enums.TestResult.PASS])
                                            respid = self.PktMethod.GetPacketResponse(reneg,[reneg[2]+1,end])
                                            if respid is not None:
                                                if self.file_list[respid]['pktType'] =="ACK":
                                                    res.append([f"ACK response found at index@{respid}", Enums.TestResult.PASS])
                                                    srqepl = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=[respid,end],Type="Packet")
                                                    if len(srqepl)>2:
                                                        res.append([f"SRQ(Extended Power Level Selection) found at index@{srqepl[2]}", Enums.TestResult.PASS])
                                                        respid2 = self.PktMethod.GetPacketResponse(srqepl,[srqepl[2]+1,end])
                                                        if respid2 is not None:
                                                            if self.file_list[respid2]['pktType'] =="ACK":
                                                                res.append([f"ACK response found at index@{respid2}", Enums.TestResult.PASS])
                                                                srqen = self.PktMethod.GetPacketDetails(packet="SRQ",value="End Negotiation",limit=[respid2,end],Type="Packet")
                                                                if len(srqen)>2:
                                                                    res.append([f"SRQ(End Negotiation) found at index@{srqen[2]}", Enums.TestResult.PASS])
                                                                    respid3 = self.PktMethod.GetPacketResponse(srqen,[srqen[2]+1,end])
                                                                    if respid3 is not None:
                                                                        if self.file_list[respid3]['pktType'] =="ACK":
                                                                            res.append([f"ACK response found at index@{respid3}", Enums.TestResult.PASS])

                                                                            renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(negpwr2*1000)}mW",limit=[respid3,end],Type='TesterMsg')
                                                                            # print("renegload:",renegload)
                                                                            if len(renegload)>2:
                                                                                
                                                                                pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[renegload[2],end],Type="Response")
                                                                                if len(pkt_DPM)>2:
                                                                                    alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                                                                    beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                                                                    invalid = float(self.PktMethod.GetPayloadDetails(pkt_DPM[2],"Invalid")[0]['sDescription'].split(":")[1].strip())
                                                                                    res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0],2)} sec with Invalid: {invalid}, dPLoss-Alpha:{alpha}, dPLoss-Beta:{beta}",Enums.TestResult.PASS if invalid == 1 and alpha == 0 and beta == 0 else Enums.TestResult.FAIL])
                                                                                else:res.append([f"DPCAL_PARAM packet not recevied",Enums.TestResult.FAIL])
                                                                            
                                                                            else: res.append([f"Set_Load {int(negpwr2*1000)}mW not found", Enums.TestResult.FAIL])
                        else: res.append([f"Load Set Done packet not observed",Enums.TestResult.FAIL])
        return res


    def t_CAL_OP_PROC(self,Flow_limit,Check):
        id = Flow_limit[0]
        res = []
        while id < Flow_limit[1]:
            if 'CAL_OP' in self.file_list[id]['pktType'] and "CMT" in self.file_list[id]['value']:
                res.append([f"CAL_OP[COMMIT] packet found at {round(self.file_list[id]['startTime'],2)} sec", Enums.TestResult.PASS])
                respid = self.PktMethod.GetPacketResponse2(id,[id+1,Flow_limit[1]])
                if respid is not None:
                    if 'CAL_OP_RSP' in self.file_list[respid]['pktType'] and ("ACCEPTED" or "ERR_MODE_VALIDATION_FAIL" in self.file_list[respid]['value']):
                        res.append([f"CAL_OP_RSP[{self.file_list[respid]['value']}] response found at {round(self.file_list[respid]['startTime'],2)} sec, Expected: CAL_OP_RSP[ACCEPTED] or CAL_OP_RSP[ERR_MODE_VALIDATION_FAIL]", Enums.TestResult.PASS])
                        # t_CAL_OP_PROC
                        t_gap = round((self.file_list[respid]['startTime']-self.file_list[id]['stopTime'])*1000,3)
                        # print(f"t_gap:{t_gap}")
                        # print(f"self.file_list[respid]['startTime']:{self.file_list[respid]['startTime']}")
                        # print(f"self.file_list[id]['stopTime']:{self.file_list[id]['stopTime']}")
                        ChkRes1 = CommonMethods.check_measure([5000],t_gap,"LT")
                        res.append([f"The t_CAL_OP_PROC is {ChkRes1[3]} ms, Expected: Less than 5000ms",ChkRes1[1]])
                    
                    else: res.append([f"{self.file_list[respid]['pktType']}[{self.file_list[respid]['value']}] response recevied at {round(self.file_list[respid]['startTime'],2)} sec, Expected: CAL_OP_RSP[ACCEPTED] or CAL_OP_RSP[ERR_MODE_VALIDATION_FAIL]", Enums.TestResult.FAIL])
                else: res.append([f"CAL_OP_RSP response not recevied", Enums.TestResult.FAIL])
               
            id+=1
        return res
    
    def Cal_Preserve(self,Flow_limit,Check):
        res = []
        Flow_limit = Flow_limit
        Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
        if len(Excapres)> 2:
            EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
            for ck in EXCAP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
            # print("EXCAP:",EXCAP)
            mode1 = sorted(EXCAP, key=EXCAP.get, reverse=True)[1]  # second highest potential load power
            mode2 = max(EXCAP, key=EXCAP.get)  # highest potential load power
            # print("mode1:",mode1, "mode2:",mode2)

            ideal = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
            if len(ideal)>2:
                pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[ideal[2],Flow_limit[1]],Type="Response")
                if len(pkt_DPM)>2:
                    alpha1 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                    beta1 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                    if any(res1 == 0 for res1 in [alpha1,beta1]):
                        res.append([f"The DPCAL_PARAM packet wit Alpha1: {alpha1}, Beta1: {beta1} received at {round(pkt_DPM[0],2)}sec",Enums.TestResult.FAIL])
                    else:res.append([f"The DPCAL_PARAM packet with Alpha1: {alpha1}, Beta1: {beta1} received at {round(pkt_DPM[0],2)}sec",Enums.TestResult.PASS])

                    templmt = [pkt_DPM[2],len(self.file_list)-1]
                    MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=templmt,Type="Packet")
                    if len(MSRreq2)> 2:
                        PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                        # print("PrefMode2:",PrefMode2)
                        res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: High_Power_Mode", Enums.TestResult.PASS if PrefMode2 == "High_Power_Mode" else Enums.TestResult.FAIL])
                        MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],templmt[1]],Type="Response")
                        if len(MSS2)> 2:
                            res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", Enums.TestResult.PASS])
                            ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[MSS2[2],templmt[1]],Type="Response")
                            if len(ECAP)>2:
                                renegpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                res.append([f"Negotiable_Load_Power in ECAP is {renegpwr}W, Expected: 25W", Enums.TestResult.PASS if renegpwr == 25 else Enums.TestResult.FAIL])
                                pkt_DPM2 = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[ECAP[2],templmt[1]],Type="Response")
                                if len(pkt_DPM2)>2:
                                    alpha2 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM2[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                    beta2 = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM2[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                    if any(res2 == 0 for res2 in [alpha2,beta2]):
                                        res.append([f"The DPCAL_PARAM packet wit Alpha2: {alpha2}, Beta2: {beta2} received at {round(pkt_DPM2[0],2)}sec",Enums.TestResult.FAIL])
                                    else:res.append([f"The DPCAL_PARAM packet with Alpha2: {alpha2}, Beta2: {beta2} received at {round(pkt_DPM2[0],2)}sec",Enums.TestResult.PASS])
                                    res.append([f"Alpha1:{alpha1} , Alpha2:{alpha2} , Beta1:{beta1} , Beta2:{beta2} , Expected: Alpha1=Alpha2, Beta1=Beta2", Enums.TestResult.PASS if alpha1==alpha2 and beta1==beta2 else Enums.TestResult.FAIL])

                                    renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(renegpwr*1000)}mW",limit=[ECAP[2],templmt[1]],Type='TesterMsg')
                                    # print("renegload:",renegload)
                                    if len(renegload)>2:
                                        res.append([f"Set_Load {int(renegpwr*1000)}mW found at {round(renegload[0],3)} sec", Enums.TestResult.PASS])
                                        ideal2 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[renegload[2],templmt[1]],Type="TesterMsg")
                                        if len(ideal2)>2:
                                            res.append([f"MPP_XCEV_Ideal found at {round(ideal2[0],3)} sec", Enums.TestResult.PASS])
                                            x = ideal2[2]
                                            Pwrs = []
                                            cnt = 0
                                            while x < templmt[1]:
                                                pla2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[x,templmt[1]],Type="Packet")
                                                if len(pla2)>2:
                                                    prect = float(self.PktMethod.GetPayloadDetails(pla2[2],"PRECT")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                                    Pwrs.append(prect)
                                                    cnt += 1
                                                    if cnt >= 10: break
                                                x += 1
                                            if len(Pwrs) > 0:
                                                Pavg = sum(Pwrs)/len(Pwrs)
                                                if len(Pwrs) < 10:
                                                    res.append([f"Only {len(Pwrs)} PLA_2 packets found after MPP_XCEV_Ideal, Expected: >=10", Enums.TestResult.FAIL])
                                                res.append([f"Average of {len(Pwrs)} PLA_2 packets Prect's is {Pavg} W, Expected: > 24.5 W", Enums.TestResult.PASS if Pavg > 24.5 else Enums.TestResult.FAIL])
                                        else: res.append([f"MPP_XCEV_Ideal not found", Enums.TestResult.FAIL])
                                    else: res.append([f"Set_Load {int(renegpwr*1000)}mW not found", Enums.TestResult.FAIL])
                                else:res.append([f"DPCAL_PARAM packet not recevied",Enums.TestResult.FAIL])
                            else:res.append([f"{self.ECAP_pkt} packet not recevied",Enums.TestResult.FAIL])
                        else:res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response not recevied",Enums.TestResult.FAIL])
                    else:res.append([f"MSR(Main Mode) packet not recevied",Enums.TestResult.FAIL])
                else:res.append([f"DPCAL_PARAM packet not recevied",Enums.TestResult.FAIL])
            else: res.append([f"MPP_XCEV_Ideal not found", Enums.TestResult.FAIL])

        return res

    def MODEXCAPCheck(self,Flow_limit,Check):
        res=[]
        # MODECAP
        Ecapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Capabilities",limit=Flow_limit,Type="Packet")
        if len(Ecapreq)> 2:
            res.append([f"Get Request-PTx Power Modes Capabilities Packet found at {round(Ecapreq[0],3)} sec", Enums.TestResult.PASS])
            Ecapres = self.PktMethod.GetPacketDetails(packet="MODECAP",value="Active Main Mode:",limit=[Ecapreq[2],Flow_limit[1]],Type="Response")
            if len(Ecapres)> 2:
                res.append([f"MODECAP {self.file_list[Ecapres[2]]['value']} response found at {round(Ecapres[0],3)} sec with following values", Enums.TestResult.PASS])
                ECAP = {"LPM":"","NPM":"","HPM":"","CPM":""}
                for ck in ECAP.keys():
                    payloadDetails = self.PktMethod.GetPayloadDetails(Ecapres[2],ck)
                    # print(ck,":",self.PktMethod.hex_to_decimal(payloadDetails[0]['sRawData']))
                    ECAP[ck] = self.PktMethod.hex_to_decimal(payloadDetails[0]['sRawData'])
                # print(ECAP)
                res.append([f"MODECAP values: {ECAP}", Enums.TestResult.PASS])
            else: res.append([f"MODECAP Packet not found", Enums.TestResult.FAIL])
        else: res.append([f"Get Request-PTx Power Modes Capabilities Packet not found", Enums.TestResult.FAIL])

        # MODEXCAP
        Excapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Extended Capabilities",limit=Flow_limit,Type="Packet")
        if len(Excapreq)> 2:
            res.append([f"Get Request-PTx Power Modes Extended Capabilities Packet found at {round(Excapreq[0],3)} sec", Enums.TestResult.PASS])
            Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=[Excapreq[2],Flow_limit[1]],Type="Response")
            if len(Excapres)> 2:
                res.append([f"MODEXCAP {self.file_list[Excapres[2]]['value']} response found at {round(Excapres[0],3)} sec with following values", Enums.TestResult.PASS])
                EXCAP = {"LPMVoltage_Ref0":"","LPMVoltage_Ref1":"","Low_Power_Mode":"","NPMVoltage_Ref0":"","NPMVoltage_Ref1":"","Nominal_Power_Mode":"","HPMVoltage_Ref0":"","HPMVoltage_Ref1":"","High_Power_Mode":"","CPMVoltage_Ref0":"","CPMVoltage_Ref1":"","Continuous_Power_Mode":""}
                for ck in EXCAP.keys():
                    payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                    # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                    EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
                # print(EXCAP)
                res.append([f"MODEXCAP values: {EXCAP}", Enums.TestResult.PASS])
            else: res.append([f"MODEXCAP Packet not found", Enums.TestResult.FAIL])
        else: res.append([f"Get Request-PTx Power Modes Extended Capabilities Packet not found", Enums.TestResult.FAIL])

        # GMP
        GMPreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Gain Measurement Parameters",limit=Flow_limit,Type="Packet")
        if len(GMPreq)> 2:
            res.append([f"Get Request-PTx Gain Measurement Parameters Packet found at {round(GMPreq[0],3)} sec", Enums.TestResult.PASS])
            GMPres = self.PktMethod.GetPacketDetails(packet="GMP",limit=[Ecapreq[2],Flow_limit[1]],Type="Response")
            if len(GMPres)> 2:
                res.append([f"GMP {self.file_list[GMPres[2]]['value']} response found at {round(GMPres[0],3)} sec with following values", Enums.TestResult.PASS])
                GMP = {"G_NPM_CO":"","G_HPM_CO":"","G_CPM_CO":""}
                for ck in GMP.keys():
                    payloadDetails = self.PktMethod.GetPayloadDetails(GMPres[2],ck)
                    # print(ck,":",float(payloadDetails[0]['sDescription'].split(":")[1].strip()))
                    GMP[ck] = float(payloadDetails[0]['sDescription'].split(":")[1].strip())
                # print(GMP)
                res.append([f"GMP values: {GMP}", Enums.TestResult.PASS])
            else: res.append([f"GMP Packet not found", Enums.TestResult.FAIL])
        else: res.append([f"Get Request-PTx Gain Measurement Parameters Packet not found", Enums.TestResult.FAIL])


        # if ECAP == {'LPM': 1, 'NPM': 0, 'HPM': 0, 'CPM': 0}:
        #     res.append([f"Power modes in MODECAP packet are {ECAP}", Enums.TestResult.PASS])
        #     if EXCAP["LPMVoltage_Ref0"] != 0:
        #         res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.PASS])
        #     else: res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.FAIL])

        #     if EXCAP["LPMVoltage_Ref1"] != 0:
        #         res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.PASS])
        #     else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.FAIL])
            
        #     if EXCAP["Low_Power_Mode"] != 0 and EXCAP["Low_Power_Mode"] <= 10:
        #         res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: != 0 W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", Enums.TestResult.PASS])
        #     else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: != 0 W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", Enums.TestResult.FAIL])

        #     if all(EXCAP[key] == 0 for key in EXCAP if key not in ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]):
        #         res.append([f'All values are equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]', Enums.TestResult.PASS])
        #     else: res.append([f'All values are not equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]', Enums.TestResult.FAIL])

        #     if all(GMP[key] == 0 for key in GMP):
        #         res.append([f'All values are equal to zero in GMP', Enums.TestResult.PASS])
        #     else: res.append([f'All values are not equal to zero in GMP', Enums.TestResult.FAIL])

        res.append([f"Test results validation starts from here:", Enums.TestResult.PASS])

        if ECAP == {'LPM': 1, 'NPM': 1, 'HPM': 0, 'CPM': 0}:
            res.append([f"Power modes in MODECAP packet are {ECAP}", Enums.TestResult.PASS])
            if EXCAP["LPMVoltage_Ref0"] != 0:
                res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.FAIL])

            if EXCAP["LPMVoltage_Ref1"] != 0:
                res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.FAIL])  

            if EXCAP["Low_Power_Mode"] != 0 and EXCAP["Low_Power_Mode"] <= 10:
                res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: != 0 and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: <= 10", Enums.TestResult.PASS])
            else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: != 0 and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]}, Expected: <= 10", Enums.TestResult.FAIL])

            if EXCAP["NPMVoltage_Ref0"] != 0:
                res.append([f"NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.FAIL])

            if EXCAP["NPMVoltage_Ref1"] != 0:
                res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.FAIL])  

            if EXCAP["Nominal_Power_Mode"] != 0:
                res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, Expected: != 0 W", Enums.TestResult.PASS])
            else: res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, Expected: != 0 W", Enums.TestResult.FAIL]) 

            if all(EXCAP[key] == 0 for key in EXCAP if key not in ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode","NPMVoltage_Ref0","NPMVoltage_Ref1","Nominal_Power_Mode"]):
                res.append([f'All values are equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode","NPMVoltage_Ref0","NPMVoltage_Ref1","Nominal_Power_Mode"]', Enums.TestResult.PASS])
            else: res.append([f'All values are not equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode","NPMVoltage_Ref0","NPMVoltage_Ref1","Nominal_Power_Mode"]', Enums.TestResult.FAIL])

            if EXCAP["LPMVoltage_Ref1"] >= EXCAP["NPMVoltage_Ref0"]:
                res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", Enums.TestResult.PASS])
            else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", Enums.TestResult.FAIL])

            if EXCAP["Nominal_Power_Mode"] > EXCAP["Low_Power_Mode"]:
                res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: NPM Potential Load Power > LPM Potential Load Power", Enums.TestResult.PASS])
            else: res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: NPM Potential Load Power > LPM Potential Load Power", Enums.TestResult.FAIL])

            if GMP["G_NPM_CO"] != 0:
                res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", Enums.TestResult.PASS])
            else: res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", Enums.TestResult.FAIL])

            if GMP["G_HPM_CO"] == 0:
                res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", Enums.TestResult.PASS])
            else: res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", Enums.TestResult.FAIL])

            if GMP["G_CPM_CO"] == 0:
                res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", Enums.TestResult.PASS])
            else: res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", Enums.TestResult.FAIL])

        elif ECAP == {'LPM': 1, 'NPM': 1, 'HPM': 1, 'CPM': 0}:
            res.append([f"Power modes in MODECAP packet are {ECAP}", Enums.TestResult.PASS])
            if EXCAP["CPMVoltage_Ref0"] == 0:
                res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: = 0 V", Enums.TestResult.PASS])
            else: res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: = 0 V", Enums.TestResult.FAIL])
            if EXCAP["CPMVoltage_Ref1"] == 0:
                res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: = 0 V", Enums.TestResult.PASS])
            else: res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: = 0 V", Enums.TestResult.FAIL])  
            if EXCAP["Continuous_Power_Mode"] == 0:
                res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", Enums.TestResult.PASS])
            else: res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", Enums.TestResult.FAIL]) 
            if all(EXCAP[key] != 0 for key in EXCAP if key not in ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]):
                res.append([f'All values are NOT equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', Enums.TestResult.PASS])
            else: res.append([f'All values are equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', Enums.TestResult.FAIL])
            if EXCAP["LPMVoltage_Ref1"] >= EXCAP["NPMVoltage_Ref0"]:
                res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", Enums.TestResult.PASS])
            else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V and NPMVoltage_Ref0 is {EXCAP["NPMVoltage_Ref0"]} V, Expected: LPMVoltage_Ref1 >= NPMVoltage_Ref0", Enums.TestResult.FAIL])
            if EXCAP["NPMVoltage_Ref1"] >= EXCAP["HPMVoltage_Ref0"]:
                res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V and HPMVoltage_Ref0 is {EXCAP["HPMVoltage_Ref0"]} V, Expected: NPMVoltage_Ref1 >= HPMVoltage_Ref0", Enums.TestResult.PASS])
            else: res.append([f"NPMVoltage_Ref1 is {EXCAP["NPMVoltage_Ref1"]} V and HPMVoltage_Ref0 is {EXCAP["HPMVoltage_Ref0"]} V, Expected: NPMVoltage_Ref1 >= HPMVoltage_Ref0", Enums.TestResult.FAIL])
            if EXCAP["High_Power_Mode"] > EXCAP["Nominal_Power_Mode"] > EXCAP["Low_Power_Mode"]:
                res.append([f"HPM Potential Load Power is {EXCAP["High_Power_Mode"]} W, NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W Expected: HPM Potential Load Power > NPM Potential Load Power > HPM Potential Load Power", Enums.TestResult.PASS])
            else: res.append([f"HPM Potential Load Power is {EXCAP["High_Power_Mode"]} W, NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W Expected: HPM Potential Load Power > NPM Potential Load Power > HPM Potential Load Power", Enums.TestResult.FAIL])
            if EXCAP["Low_Power_Mode"] <= 10:
                res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", Enums.TestResult.PASS])
            else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", Enums.TestResult.FAIL]) 
            if EXCAP["Nominal_Power_Mode"] >= 15:
                res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, Expected: >= 15 W", Enums.TestResult.PASS])
            else: res.append([f"NPM Potential Load Power is {EXCAP["Nominal_Power_Mode"]} W, Expected: >= 15 W", Enums.TestResult.FAIL]) 
            if GMP["G_NPM_CO"] != 0:
                res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", Enums.TestResult.PASS])
            else: res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: != 0", Enums.TestResult.FAIL])
            if GMP["G_HPM_CO"] != 0:
                res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: != 0", Enums.TestResult.PASS])
            else: res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: != 0", Enums.TestResult.FAIL])
            if GMP["G_CPM_CO"] == 0:
                res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", Enums.TestResult.PASS])
            else: res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: = 0", Enums.TestResult.FAIL])

        elif ECAP == {'LPM': 0, 'NPM': 0, 'HPM': 0, 'CPM': 1}:
            res.append([f"Power modes in MODECAP packet are {ECAP}", Enums.TestResult.PASS])
            if EXCAP["CPMVoltage_Ref0"] != 0:
                res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"CPMVoltage_Ref0 is {EXCAP["CPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.FAIL])
            if EXCAP["CPMVoltage_Ref1"] != 0:
                res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"CPMVoltage_Ref1 is {EXCAP["CPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.FAIL])  
            if EXCAP["Continuous_Power_Mode"] != 0:
                res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", Enums.TestResult.PASS])
            else: res.append([f"CPM Potential Load Power is {EXCAP["Continuous_Power_Mode"]} W, Expected: != 0 W", Enums.TestResult.FAIL]) 
            if all(EXCAP[key] == 0 for key in EXCAP if key not in ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]):
                res.append([f'All values are equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', Enums.TestResult.PASS])
            else: res.append([f'All values are not equal to zero in EXCAP except ["CPMVoltage_Ref0","CPMVoltage_Ref1","Continuous_Power_Mode"]', Enums.TestResult.FAIL])
            if GMP["G_NPM_CO"] == 0:
                res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: = 0", Enums.TestResult.PASS])
            else: res.append([f"G_NPM_CO is {GMP["G_NPM_CO"]} , Expected: = 0", Enums.TestResult.FAIL])
            if GMP["G_HPM_CO"] == 0:
                res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", Enums.TestResult.PASS])
            else: res.append([f"G_HPM_CO is {GMP["G_HPM_CO"]} , Expected: = 0", Enums.TestResult.FAIL])
            if GMP["G_CPM_CO"] != 0:
                res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: != 0", Enums.TestResult.PASS])
            else: res.append([f"G_CPM_CO is {GMP["G_CPM_CO"]} , Expected: != 0", Enums.TestResult.FAIL])
        else: res.append([f"This is an unexpected {ECAP} power mode sequence in MODECAP packet", Enums.TestResult.FAIL])  
        return res

    def Txce_interval(self,Flow_limit,Check):
        res = []
        xcecnt = 0
        start = 0
        xceids = []
        
        dumppkt = self.PktMethod.GetPacketDetails(packet="Set_Load 400mA",limit=Flow_limit,Type="TesterMsg")
        if len(dumppkt)>2:
            res.append([f"Load dump 400mA found at {self.PktMethod.Timeconvert(dumppkt[0])}", Enums.TestResult.PASS])
            id = dumppkt[2]
            # end = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[id,Flow_limit[1]],Type="TesterMsg")[2]
            stable_pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[id,Flow_limit[1]],Type="TesterMsg")
            if len(stable_pkt)>2:
                
                end = stable_pkt[2]

                while id < end:
                    TempPkt1 =  self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[id,end])
                    # print("TempPkt1:",TempPkt1)
                    if len(TempPkt1) > 2:
                        # xcecnt += 1
                        xceids.append(TempPkt1[2])
                        TempPkt2 =  self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[TempPkt1[2]+1,end+1])
                        # # print("TempPkt2:",TempPkt2)
                        if len(TempPkt2) > 2:
                            xceids.append(TempPkt2[2])
                            skippkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt1[2],TempPkt2[2]],Type="Packet")
                            if len(skippkt)>2:
                                
                                id = TempPkt1[2] + 1
                                continue
                            res.append([f"{self.file_list[TempPkt1[2]]['pktType']} packet found at {self.PktMethod.Timeconvert(TempPkt1[0])}", Enums.TestResult.PASS])
                            res.append([f"{self.file_list[TempPkt2[2]]['pktType']} packet found at {self.PktMethod.Timeconvert(TempPkt2[0])}", Enums.TestResult.PASS])
                            Tresult = round((TempPkt2[0]-TempPkt1[0])*1000,3)
                            ChkRes = CommonMethods.check_measure([70,90],Tresult,0)
                            res.append([f"The Measured Txce_interval from start of Extended Control Error to start of next Extended Control Error is: {ChkRes[3]} ms, Limit: {ChkRes[2]} ms", ChkRes[1]])
                            
                            id = TempPkt1[2]
                    id += 1
                res.append([f"MPP_XCEV_Ideal stabilization found at {self.PktMethod.Timeconvert(stable_pkt[0])}", Enums.TestResult.PASS])
                # print("xcecnt:",len(set(xceids)))
                res.append([f"Total number of XCE packets received: {len(set(xceids))}", Enums.TestResult.PASS])
                res.append([f"After subtracting 5 from the count of the XCE data packets", Enums.TestResult.PASS])
                XceRes = CommonMethods.check_measure(Check['expected'],len(set(xceids))-5,"LTEQL")  # Subtract 5 from the count of the XCE data packets
                res.append([f"Total {XceRes[3]} Extended Control Error packets received, Expected: {XceRes[2]}",XceRes[1]])
            else: res.append([f"MPP_XCEV_Ideal stabilization not found.", Enums.TestResult.FAIL])
        else: res.append([f"Load dump 400mA not found.", Enums.TestResult.FAIL])
        return res

    def PrectFall(self,Flow_limit,Check):
        res=[]
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
        x = 1
        for chk in Check['expected']:
            if "LimitType" in chk:
                Limit = self.PktMethod.GetLimits(chk['LimitType'],chk,Flow_limit)
            else: Limit = Flow_limit
            SRQ = self.PktMethod.GetPacketDetails(packet="SRQ",value="Control Gain",limit=Limit)
            if len(SRQ)>2:
                resp = self.PktMethod.GetPacketResponse(SRQ,[SRQ[2]+1,Limit[1]])
                if resp is not None:
                    if self.file_list[resp]['pktType'] =="ACK":
                        res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(SRQ[0],3)}sec",Enums.TestResult.PASS])
                    else:res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(SRQ[0],3)}sec",Enums.TestResult.FAIL])
                else:res.append([f"Response not found for SRQ_Control Gain packet at {round(SRQ[0],3)}sec",Enums.TestResult.FAIL])
                gtarget = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(SRQ[2],'G_TARGET')[0]['sDescription'])[0]

                #1. Get potential load power
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Limit,Type="Response")
                # print("TempPkt1:",TempPkt1)
                PotLoad = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],"Potential Load Power value: 25W")[0]['sDescription'])[0]*1000)
                # print("PotLoad:",PotLoad)
                res.append([f"Potential load power in {self.ECAP_pkt} is {PotLoad}mW", Enums.TestResult.PASS])
                if len(TempPkt1)>2:
                    TempLimit = [TempPkt1[2],Limit[1]]
                    TempPkt2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {PotLoad}mW:ILim:Enabled",limit=TempLimit,Type="TesterMsg")
                    # print("PrecLimit:",TempPkt2)
                    if len(TempPkt2) > 2:
                        res.append([f"Set_load found for {PotLoad}mW @index {TempPkt2[2]}, Expected power: {PotLoad}mW i.e, ECAP[potential load power].", Enums.TestResult.PASS])
                        #find the stabilization
                        TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Limit[1]],Type="TesterMsg")
                        # print("TempPkt3:",TempPkt3)
                        if len(TempPkt3)>2:
                            res.append([f"Control stabilized at @index {TempPkt3[2]}", Enums.TestResult.PASS])
                            TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2]-15,TempPkt3[2]+15],Type="Packet")
                            Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                            # print("Prect:",Prect)
                            ChkRes = CommonMethods.check_measure([(PotLoad/1000)-0.5],Prect,"GTEQL")
                            res.append([f"Found PLA_2 packet at {round(TempPkt4[0],3)}sec with Prect {Prect}W, Expected power in ECAP:{PotLoad}mW", ChkRes[1]])
                            # TPR ramp its load power within a 50 microsecond period down to ECAP[Potential Load Power]/2
                            TempPkt5 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(PotLoad/2)}mW:ILim:Disabled",limit=[TempPkt3[2],Limit[1]],Type="TesterMsg")
                            # print("TempPkt5:",TempPkt5)


                            if len(TempPkt5)>2:
                                res.append([f"Set_load found for {int(PotLoad/2)}mW @index {TempPkt5[2]}, Expected power: {int(PotLoad/2)}mW, i.e, ECAP[potential load power]/2.", Enums.TestResult.PASS])
                                if "t_gap" in chk:
                                    CEx = self.PktMethod.GetPacketDetails(packet=f"Extended Control Error",limit=[TempPkt5[2],TempPkt2[2]],Type="Packet")
                                    if len(CEx)>2:
                                        res.append([f"Required time period is 51 ms ± 2 ms, i.e, (t_xceresponsetimeout = 20 ms + t_delay = 5 ms + t_active = 21 ms + 5 ms ± 2 ms)", Enums.TestResult.PASS])
                                        t_req = round((TempPkt5[0]-CEx[1])*1000,3)
                                        chk_resx = CommonMethods.check_measure(chk['t_gap'],t_req,0)
                                        res.append([f"The time between Extended Control Error and Set_load {int(PotLoad/2)}mW is {chk_resx[3]} ms, Expected: {chk_resx[2]} ms",chk_resx[1]])
                                    else: res.append([f"Extended Control Error packet not found before Set_load {int(PotLoad/2)}mW",""])

                                VrectTarget = [] #V
                                # Vrect1 = self.PktMethod.GetPacketDetails(packet="Vrect_VTarget",limit=[TempPkt5[2],Flow_limit[1]],Type="TesterMsg")
                                id = TempPkt5[2]
                                Vrect = []

                                cnt = 0
                                while id != Limit[1]:
                                    if "Vrect_VTarget" in self.file_list[id].get('pktType'):
                                        # print("Vrect_VTarget:",self.file_list[id].get('value'))
                                        match = re.search(r"Target_voltage:\s*([\d.]+)V.*Rectified_voltage:\s*([\d.]+)V", self.file_list[id].get('value'))
                                        VrectTarget.append(float(match.group(1)))
                                        Vrect.append(float(match.group(2)))
                                        
                                        cnt += 1
                                        if cnt == 2: break
                                    id += 1
                                # print("match:",VrectTarget,Vrect)
                                Vrectdel = round(Vrect[1]-Vrect[0],3)
                                validation = round(abs(Vrectdel/(VrectTarget[0]-Vrect[0])-gtarget),3)
                                
                                # print("validation:",validation)
                                res.append([f"∆Vrect_{x}: {Vrectdel}V, Vrect_target_{x}: {VrectTarget[0]}V, Vrect_{x}: {Vrect[0]}V, Vrect_after_{x}: {Vrect[1]}V", Enums.TestResult.PASS])
                                ChkRes = CommonMethods.check_measure([0.4],validation,"LTEQL")
                                res.append([f"|∆Vrect_{x} / (Vrect_target_{x}- Vrect_{x})- g_target_{x}| = {ChkRes[3]}, Expected: {ChkRes[2]}", ChkRes[1]])
                                
                                CE = self.PktMethod.GetPacketDetails(packet=f"Extended Control Error",limit=[Limit[1],TempPkt5[2]],Type="Packet")
                                # print("Extended Control Error:",CE)
                                if len(CE) > 2:
                                    voltage = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                                    current = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData3)
                                    # # print("TIME:",self.AllChannelData["Interval"]*voltage[1])
                                    # print("power(W):",voltage[0]*current[0])
                                    if voltage[0]*current[0] >= float(PotLoad/2000):
                                        res.append([f"After control stabilization, power is {round((voltage[0]*current[0]),3)}W, Limit: >= {float(PotLoad/2000)}W", Enums.TestResult.PASS])
                                    else: res.append([f"After control stabilization, power is {voltage[0]*current[0]}W Limit: >= {float(PotLoad/2000)}W", Enums.TestResult.FAIL])
                                else: res.append([f"Control not stabilized for {int(PotLoad/2)}mW", Enums.TestResult.FAIL])

                            else: res.append([f"Set_Load {int(PotLoad/2)}mW packet not found", Enums.TestResult.FAIL])   
                        else: res.append([f"MPP_XCEV_Ideal packet not found", Enums.TestResult.FAIL])
                    else: res.append([f"Set_Load {PotLoad}mW packet not found", Enums.TestResult.FAIL])
                else: res.append([f"{self.ECAP_pkt} packet not found", Enums.TestResult.FAIL])
            else: res.append([f"SRQ Control Gain packet not found", Enums.TestResult.FAIL])
            x += 1
        return res

    # Helper methods
    def GetInitailVoltage(self,index,limit):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        self.initialVoltage = None
        self.stability = None
        
        limit = limit
        # print("limit:",limit)
        # limit = flows[index]['Limit']
        id = limit[0]
        while id < limit[1]:
            if 'MPP_XCEV_Ideal' in self.file_list[id]['pktType']:
                # print(id)
                revid = id
                while revid > limit[0]:
                    if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                        self.stability=revid
                        # print('stability:',self.stability)
                        #GetIntital Voltage
                        # # print(self.Json_TC['other_checks_details'])
                        # if 'InitialVoltage' in self.Json_TC['other_checks_details'][str(index)]:
                        window_res = self.PktMethod.CalculateVoltTwindow(revid,self.AllChannelData)
                        self.initialVoltage =  window_res[0]
                        res = [self.initialVoltage,revid]
                        return res
                        # # print('stability',self.stability,self.initialVoltage)
                        
                    revid-=1
                break
            id+=1
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

    
                
      
            

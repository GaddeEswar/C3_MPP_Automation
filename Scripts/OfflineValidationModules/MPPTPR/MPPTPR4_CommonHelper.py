import traceback
import io
import zipfile, re
import os
import csv
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums
from pathlib import Path
import pandas as pd1


class CommonCTSChecks():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson,flows):
        #Define Global variables
        CTS = JsonOperations('json/CTSvalidation/MPPTPR.json')
        self.JCTSData =CTS.read_file()
        self.flows = flows

        # self.JCTSData = JCTSData
        self.JapiData = JapiData
        self.Header = Header
        self.Product = self.Header['Product']
        self.Mode = self.Header['Mode']
        self.TestCaseName = self.Header['TestcaseName']
        self.ProjectJson = ProjectJson
        self.file_list = file_list
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
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

        # Certificate wise packet names
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        
        if self.Certification in ["2.0.1","2.1.0","2.2.1","2.3.0"]:
            self.ECAP_pkt = "Extended_Power_Transmitter_Extended_Capabilities"
            self.XID_pkt = "MPP_Extended_Identification"
            self.Kest_pkt = "Estimated_K"
            self.Inv_vol_pkt = "Inverter_Voltage"
        else:
            self.ECAP_pkt = "Power Transmitter Extended Capabilities"
            self.XID_pkt = "Extended Identification"
            self.Kest_pkt = "Estimated K"
            self.Inv_vol_pkt = "Inverter Voltage"
    
    def InitialVoltage(self,Flow_limit,Check):
        res = []
        if self.initialVoltage is not None:
            
            ChkRes = CommonMethods.check_measure(Check['expected'],self.initialVoltage,Check['comp'])
            res.append([f"The Measured voltage is {self.initialVoltage}V at {round(self.file_list[self.stability]['startTime'],2)}sec,limit {ChkRes[2]}V",ChkRes[1]])
            
        else:res.append(["Stabilization not found",Enums.TestResult.FAIL])
        return res

    def PTPhase(self,Flow_limit,Check):
        res = []
        #check for PT phase in the flow
        id = Flow_limit[0]
        while id < Flow_limit[1]:
            if self.file_list[id]['pktType'] in ["Extended Control Error","Control Error"]:
                
                res.append([f'PT Phase started from {round(self.file_list[id]['startTime'],3)} sec', Enums.TestResult.PASS])
                break
            id+=1
        if len(res) == 0 : res.append([f'PT Phase not found.',Enums.TestResult.INCONCLUSIVE])

        if "Load_apply" in Check:
            if "ECAPLimit" in Check:
                limit2 = self.PktMethod.GetLimits(Check['ECAPLimit'],Check,Flow_limit)
            else: limit2 = [Flow_limit[1],Flow_limit[0]]
            print("ECAPLimit:",limit2)
            ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=limit2,Type="Response")
            if len(ECAP) > 2:
                # print("Load_pwr:",self.PktMethod.GetPayloadDetails(ECAP[2],prect["ECAP"]))
                Load_pwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],Check['Load_apply']["ECAP"])[0]['sDescription'].split(":")[1].split("W")[0].strip())
                # print("Load_pwr:",Load_pwr)
                res.append([f"{Check['Load_apply']['ECAP']}: {Load_pwr}W is observed in {self.ECAP_pkt} packet at index @{ECAP[2]}", "pass"])
                load = int(Load_pwr*1000) #mW

                TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {load}mW", limit=[ECAP[2], Flow_limit[1]], Type="TesterMsg")
                if len(TempPkt1) > 2:
                    res.append([f"Set_Load {load} mW is observed in {self.ECAP_pkt} packet at index @{ECAP[2]}", "pass"])
                else:
                    res.append([f"Set_Load {load} mW is not observed in {self.ECAP_pkt} packet at index @{ECAP[2]}", Enums.TestResult.FAIL])
            else:
                res.append([f"{self.ECAP_pkt} not recevied", Enums.TestResult.FAIL])




        return res
        

    def DPlossCalibration1(self,Flow_limit,Check):
        res = []
        calbPoints = None
        #1. Check for CAL_ENTER  packet
        Pkt = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",limit=Flow_limit)
        if len(Pkt)>2:
            CAL_ENTER_STOP = Pkt[1]
            res.append([f"Received CAL_ENTER packet at {round(Pkt[0],2)} sec",Enums.TestResult.PASS])
        else:res.append([f"CAL_ENTER packet not recevied",Enums.TestResult.FAIL])
        #2. Get the of.of Calib points from CAL_ENTER_RSP packet
        Pkt_res = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=Flow_limit)
        if len(Pkt_res)>2:
            calduration =int(GeneralMethods.GetFloatFromStr(self.file_list[Pkt_res[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0])
            if self.Mode=="TPT":calduration=calduration*60
            calbPoints = int(GeneralMethods.GetFloatFromStr(self.file_list[Pkt_res[2]]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])[0])
            res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec, with Calib points of {calbPoints}",Enums.TestResult.PASS])
        else:res.append([f"CAL_ENTER_RSP packet not recevied",Enums.TestResult.FAIL])
        #3.ensure the CAL_CAPTURE with count of calib points.
        id = Pkt[2] if len(Pkt)>0 else Flow_limit[0]
        CAL_CAPTURE_cnt = 0
        CalStart = 0
        CalEnd = 0
        CalLevels = []
        prevIndex = 0
        #Get the calexit packet and set the liimit else consider flow limit
        pkt_cmt = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="CMT ",limit=Flow_limit)
        TempLimit = [id,pkt_cmt[2]] if len(pkt_cmt)>2 else [id,Flow_limit[1]]
        # # print('TempLimit',TempLimit)
        while id < TempLimit[1]:
            if 'CAL_CAPTURE' in self.file_list[id]['pktType']:
                if self.PktMethod.GetPacketType(id)=="Response" if self.Mode=="TPT" else self.PktMethod.GetPacketType(id)=="Packet":
                    if CAL_CAPTURE_cnt == 1: CalStart =round(self.file_list[id]['startTime'],2)
                    CalEnd = round(self.file_list[id]['stopTime'],2)
                    #Find the levels, if the diff of prect in 2 CAL_cap pkts more that 1.5W then its a break.
                    # # print('prevIndex',prevIndex,id)
                    if CAL_CAPTURE_cnt >0:
                        # # print("ID",id)
                        if abs(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id,"PRECT")[0]['sDescription'])[0] - GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(prevIndex,"PRECT")[0]['sDescription'])[0]) >= 1.5:
                            # # print(prevIndex,id)
                            if len(CalLevels)==0:CalLevels.append([TempLimit[0],prevIndex])
                            else:CalLevels.append([CalLevels[len(CalLevels)-1][1]+1,prevIndex])
                    CAL_CAPTURE_cnt+=1
                    prevIndex = id
            id+=1
        #add last cal cap level
        if len(CalLevels)>0:CalLevels.append([CalLevels[len(CalLevels)-1][1]+1,prevIndex])
        if calbPoints is not None:
            if CAL_CAPTURE_cnt == calbPoints:
                res.append([f"Recived all the {calbPoints} CAL_CAPTURE packets between {CalStart}sec to {CalEnd}sec",Enums.TestResult.PASS])
            else: 
                #If all calib points not recvd, then check for the renego happened for 15W else it's Fail

                res.append([f"Mismatch in CAL_CAPTURE packet count, No,of Calib points={calbPoints} and Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}",Enums.TestResult.FAIL])
        else: res.append([f"CAL_ENTER_RSP packet not recevied, Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}",Enums.TestResult.FAIL])
        #4.cHECK FOR cal cmt ON CAL_OP PACKET
        # pkt_cmt = self.PktMethod.GetPacketDetails(packet="CAL_OP",limit=Flow_limit)
        if len(pkt_cmt)>2:
            res.append([f"Received CAL_OP packet at {round(pkt_cmt[0],2)} sec",Enums.TestResult.PASS])
        else:res.append([f"CAL_OP packet not recevied",Enums.TestResult.FAIL])
        #5.Check for Renegotiation for 25W in ECAP packet.
        Renego = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=Flow_limit)
        if len(Renego)>2:
            Renegoval = GeneralMethods.GetFloatFromStr(self.file_list[Renego[2]]['value'])[0]
            if Check['Renego_LoadPower'] == Renegoval:
                res.append([f"The applied Load power value in ECAP is {Renegoval}W @index {Renego[2]} and CTS is {Check['Renego_LoadPower']}W",Enums.TestResult.PASS])
            else:res.append([f"The applied Load power value in ECAP is {Renegoval}W @index {Renego[2]} and CTS is {Check['Renego_LoadPower']}W",Enums.TestResult.FAIL])
        else: res.append([f"The ECAP packet not received to apply {Check['Renego_LoadPower']}W",Enums.TestResult.FAIL])
        #6.Verify CAL_EXIT packet
        pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=Flow_limit)
        if len(pkt_exit)>2:
            res.append([f"Received CAL_EXIT packet at {round(pkt_exit[0],2)} sec",Enums.TestResult.PASS])
            #6b, Ensure the CAlib duration which is mentioned on the CAL_ENTER_RSP packet , and calculate the interval btw CAL_ENTER to CAL_EXIT
            if CAL_ENTER_STOP and calduration:
                if (pkt_exit[0]-CAL_ENTER_STOP) > calduration:
                    res.append([f"Calculated Calib duration is {round(pkt_exit[0]-CAL_ENTER_STOP,2)}S, which is not in limit of {calduration}",Enums.TestResult.FAIL])
                else:res.append([f"Calculated Calib duration is {round(pkt_exit[0]-CAL_ENTER_STOP,2)}S, which is in limit of {calduration}",Enums.TestResult.PASS])
            else:res.append([f"CAL_ENTER Packet or CAL duration not found",Enums.TestResult.PASS])
        else:res.append([f"CAL_EXIT packet not recevied",Enums.TestResult.FAIL])
        #7.Check the Alpha and Beta values from the DPCAL_PARAM packet.
        pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=Flow_limit)
        if len(pkt_DPM)>2:
            alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
            beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
            if any(res == 0 for res in [alpha,beta]):
                res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0],2)}sec,Alpha:{alpha},Beta:{beta}",Enums.TestResult.FAIL])
            else:res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0],2)}sec,Alpha:{alpha},Beta:{beta}",Enums.TestResult.PASS])
        else:res.append([f"DPCAL_PARAM packet not recevied",Enums.TestResult.FAIL])
        #8. Additional checks 
        if 'AddChecks' in Check:
            # if len(Check['AddChecks'])>0:
            for addcheck in Check['AddChecks']:
                if addcheck == 'CAL_CAP_Level_counts':
                    Level = 0
                    for CALLVL in CalLevels:
                        Level+=1
                        CalLvlCnt = 0
                        id = CALLVL[0]
                        while id <= CALLVL[1]:
                            TempPkt = self.PktMethod.GetPacketDetails(packet="CAL_CAPTURE",limit=[id,CALLVL[1]])
                            if len(TempPkt)>2:
                                if self.PktMethod.GetPacketType(id)=="Packet" if self.Mode=="TPT" else self.PktMethod.GetPacketType(id)=="Response":
                                    CalLvlCnt+=1
                                id = TempPkt[2]+1
                            else:break
                        reslt = CommonMethods.check_measure(Check['AddChecks'][addcheck][f'Level{Level}']['expected'],CalLvlCnt,Check['AddChecks'][addcheck][f'Level{Level}']['comp'])
                        res.append([f"Received {CalLvlCnt} packets in Level{Level} in {round(self.file_list[CALLVL[0]]['startTime'],3)}Sec-{round(self.file_list[CALLVL[1]]['stopTime'],3)}sec, limit {reslt[2]}",reslt[1]])
                elif addcheck == 'CAL_CAP_Level_Prect':
                    Level = 0
                    for CALLVL in CalLevels:
                        Level+=1
                        CalLvlPrect = []
                        id = CALLVL[0]
                        while id <= CALLVL[1]:
                            TempPkt = self.PktMethod.GetPacketDetails(packet="CAL_CAPTURE",limit=[id,CALLVL[1]])
                            if len(TempPkt)>2:
                                if self.PktMethod.GetPacketType(id)=="Packet" if self.Mode=="TPT" else self.PktMethod.GetPacketType(id)=="Response":
                                    CalLvlPrect.append(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt[2],'PRECT')[0]['sDescription'])[0])
                                    reslt = CommonMethods.check_measure(Check['AddChecks'][addcheck][f'Level{Level}']['expected'],CalLvlPrect[len(CalLvlPrect)-1])
                                    res.append([f"Level{Level}: Received PRECT is {CalLvlPrect[len(CalLvlPrect)-1]}W on {TempPkt[0]}sec, Limit:{reslt[2]}",reslt[1]])
                                id = TempPkt[2]+1
                            else:break 
                elif addcheck == 'DiffMaxMinPRECT':
                        TempLimit = [CalLevels[0][0],CalLevels[len(CalLevels)-1][1]]
                        id = TempLimit[0]
                        TempValList = []
                        while id <= TempLimit[1]:
                            TempPkt = self.PktMethod.GetPacketDetails(packet="CAL_CAPTURE",limit=[id,TempLimit[1]])
                            if len(TempPkt)>2:
                                if self.PktMethod.GetPacketType(TempPkt[2])=="Packet" if self.Mode=="TPT" else self.PktMethod.GetPacketType(TempPkt[2])=="Response": 
                                    TempValList.append(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt[2],'PRECT')[0]['sDescription'])[0])
                                id = TempPkt[2]+1
                            else:break
                        if len(TempValList)>0:
                            reslt = CommonMethods.check_measure(Check['AddChecks'][addcheck]['expected'],max(TempValList)-min(TempValList),Check['AddChecks'][addcheck]['comp']) 
                            res.append([f"Max PRECT={max(TempValList)}W and Min PRECT={min(TempValList)}W and the Difference is {round(max(TempValList)-min(TempValList),3)}W, Limit {reslt[2]}",reslt[1]])
                        else:res.append([f"Level{Level} :No PRECT values oberved for the calculations","FAIL"])
        return res

    # def PacketCustomTimeOut1(self,Flow_limit,Check):
    #     res = []
        
    #     # # print(Flow_limit)
    #     Spkt = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0],value=Check['StartPacket'][1],limit=Flow_limit)
    #     if len(Spkt)>2:
    #         if 'Test_Stop' in Check['EndPacket'][0]:
    #             Epkt=[self.file_list[Flow_limit[1]]['startTime'],self.file_list[Flow_limit[1]]['stopTime'],Flow_limit[1]]
    #         else:
    #             Epkt = self.PktMethod.GetPacketDetails(packet=Check['EndPacket'][0],value=Check['EndPacket'][1],limit=[Flow_limit[0],Flow_limit[1]+1])
    #         if len(Epkt)>2:
    #             ChkRes = CommonMethods.check_measure(Check['expected'],AllMeasures[CTSCheck],Check['comp'])
    #             res=[f"The Measured timeout between {Check['StartPacket'][0]} and {Check['EndPacket'][0]} is {AllMeasures[CTSCheck]} sec, Limit {ChkRes[2]}Sec",ChkRes[1]]
    #         else:res=[f"{Check['EndPacket'][0]} not found for the calculation",Enums.TestResult.FAIL]
    #     else:res=[f"{Check['StartPacket'][0]} not found for the calculation",Enums.TestResult.FAIL]

    # def PLAOffsetCheck(self,Flow_limit,Check):
    #     res = []
    #     #ensure the PLA packets with offset values for the given conditions in the setup
    #     res=self.PLAOffsetCheck(flwID,Check,AllMeasures)

    # def PLAOffsetCheck2(self,Flow_limit,Check):
    #     res = []
    #     #ensure the PLA packets with offset values for the given conditions in the setup
    #     res=self.PLAOffsetCheck2(flwID,Check,AllMeasures)

    # def OffsetReneg(self,Flow_limit,Check):
    #     res = []
    #     res=self.OffsetReneg(flwID,Check,AllMeasures)

    # def OffsetReneg2(self,Flow_limit,Check):
    #     res = []
    #     res=self.OffsetReneg2(flwID,Check,AllMeasures)

    # def Thermal(self,Flow_limit,Check):
    #     res = []
    #     res=self.Thermal(flwID,Check,AllMeasures)


    # def Cal_Preserve(self,Flow_limit,Check):
    #     res = []
    #     res=self.Cal_Preserve(flwID,Check,AllMeasures)

        

    def RenegoCheck(self,Flow_limit,Check):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        #1.Get the Limit to find the PLA 
        CustomLimit = self.PktMethod.GetLimits(Check['LimitType'],Check['LimitDetails'],Flow_limit)
        if CustomLimit is not None:
            res.append([f"Found {Check['LimitDetails']['Packet'][0]} with response {Check['LimitDetails']['Response']} @{CustomLimit[0]}",Enums.TestResult.PASS])
            #2. check for the Renego  for 15W in ECAP packet.
            Renego = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=CustomLimit)
            if len(Renego)>2:
                Renegoval = GeneralMethods.GetFloatFromStr(self.file_list[Renego[2]]['value'])[0]
                if Check['Power'] == Renegoval:
                    res.append([f"The applied Load power value in ECAP is {Renegoval}W @{Renego[2]} and CTS is {Check['Power']}W",Enums.TestResult.PASS])
                    #3. Ensure the 15W in stabilization
                    #Get the stablization after the renego
                    XCEIdel =  self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Renego[2],CustomLimit[1]],Type="TesterMsg")
                    if len(XCEIdel)>2:
                        CE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[XCEIdel[2],CustomLimit[0]])
                        if len(CE)>2:
                            reslt = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                            if reslt[0]>=Check['Power']-(Check['Power']*5)/100 and reslt[0]<=Check['Power']+(Check['Power']*5)/100:
                                res.append([f"The Mesure voltage {reslt[0]}V @{reslt[1]} is in the limit of {Check['Power']-(Check['Power']*5)/100} to {Check['Power']+(Check['Power']*5)/100}",Enums.TestResult.PASS])
                            else:res.append([f"The Mesure voltage {reslt[0]}V @{reslt[1]} is not in the limit of {Check['Power']-(Check['Power']*5)/100} to {Check['Power']+(Check['Power']*5)/100}",Enums.TestResult.FAIL])
                        else:res.append("Control Error pacekt not found above the MPP_XCEV_Ideal packet",Enums.TestResult.FAIL)
                    else:res.append(["MPP_XCEV_Ideal packet not found after the Renego",Enums.TestResult.FAIL])
                else:res.append([f"The applied Load power value in ECAP is {Renegoval}W @{Renego[2]} and CTS is {Check['Power']}W",Enums.TestResult.FAIL])
            else: res.append([f"The ECAP packet not received to applied {Check['Power']}W",Enums.TestResult.FAIL])
        else: res.append([f"Coudn't find the {Check['LimitDetails']['Packet'][0]} with response {Check['LimitDetails']['Response']} from the flow {'-'.join(map(str,Flow_limit))}",Enums.TestResult.FAIL])
        return res

    def LoadForNegoPower(self,Flow_limit,Check):
        res = []
        #Get the nego. power from ECAP packet and ensure the same / CTS% value updated as load in PT phase
        negoval = None
        TmpPkt = None
        TmpPkt = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit)
        if len(TmpPkt)>2:
            res.append([f"The {self.ECAP_pkt} pacekt found at {round(TmpPkt[0],3)}sec ",Enums.TestResult.PASS])
            EcapPayload = self.PktMethod.GetPayloadDetails(TmpPkt[2],"Negotiable_Load_Power")
            if len(EcapPayload)>0:
                # print(EcapPayload[0]['sDescription'])
                negoval = int(GeneralMethods.GetFloatFromStr(EcapPayload[0]['sDescription'])[0])
                res.append([f"The Negotiable_Load_Power is {negoval}",Enums.TestResult.PASS])
            else:res.append([f"Negotiable_Load_Power payload not found the for packet",Enums.TestResult.FAIL])
        else:res.append([f"The {self.ECAP_pkt} pacekt not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.FAIL])
        #Check the load for negload
        #check for the set_load packet from reverse order
        if negoval is not None:
            TmpPkt = self.PktMethod.GetPacketDetails(packet="Set_Load",limit=[Flow_limit[1],Flow_limit[0]])
            if len(TmpPkt)>2:
                load = int(GeneralMethods.GetFloatFromStr(self.file_list[TmpPkt[2]]['pktType'])[0])
                if Check['Type']=='value':
                    if load == Check['value']:
                        res.append([f"The applied load {load}mW is same as expected value of {Check['value']}",Enums.TestResult.PASS])
                    else:res.append([f"The applied load {load}mW is not same as expected value of {Check['value']}",Enums.TestResult.FAIL])
                elif Check['Type']=='Percentage':
                    if load == int(((negoval*1000)*Check['value'])/100):
                        res.append([f"The applied load {load}mW is same as expected value of {Check['value']}% of {negoval} i.e. {int((negoval*Check['value'])/100)}",Enums.TestResult.PASS])
                    else:res.append([f"The applied load {load}mW is not same as expected value of {Check['value']}% of {negoval} i.e. {int((negoval*Check['value'])/100)}",Enums.TestResult.FAIL])
            else:res.append([f"The Set_Load pacekt not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.FAIL])
        else:res.append([f"Since the Negotiable_Load_Power not found load check not performed",Enums.TestResult.FAIL])
        return res

    def RenegoPRECTInterval(self,Flow_limit,Check):
        res = []
        #Get the neg. pwr from ECAP enusre the value reached
        TempPkt1 = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[Flow_limit[1],Flow_limit[0]])
        if len(TempPkt1)>2:
            Value = round(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],'Negotiable_Load_Power')[0]['sRawData'])[0],3)
            res.append([f"ECAP packet found at {round(TempPkt1[0],3)}sec with Negotiable_Load_Power:{Value}W",Enums.TestResult.PASS])
            id = TempPkt1[2]
            TempPktStatus = False
            while id<Flow_limit[1]:
                TempPkt2=self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    #check for the PLA PRECT value
                    if round(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],'PRECT')[0]['sDescription'])[0],3) >= (Value*Check['PRECTPercentage'])/100:
                        TempPktStatus=True
                        res.append([f"The PLA packet recevied at {round(TempPkt2[0],3)}, with PRECT value of {round(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],'PRECT')[0]['sDescription'])[0],3)}",Enums.TestResult.PASS])
                        #Get the PT start after ECAP
                        PTstart = self.PktMethod.GetPacketDetails(packet="Extended Control Error", limit=[TempPkt1[2],Flow_limit[1]])
                        if len(PTstart)>2:
                            #calculate intervel, and apply on the result
                            result = CommonMethods.check_measure(Check['expected_value'],round(TempPkt2[0]-PTstart[0],3),Check['comp'])
                            res.append([f"PT phase started after ECAP on {round(PTstart[0],3)}sec and Found the PLA packet on {TempPkt2[0]}, The calculated intervel is {round(TempPkt2[0]-PTstart[0],3)}sec, Limit:{result[2]}sec",result[1]])
                        break
                    id = TempPkt2[2]+1
                #Check for stabilization 
                else:break
            if TempPktStatus==False:res.append([f"PLA packet with expected PRECT value not found",Enums.TestResult.FAIL])
        else:res.append([f"ECAP packet not found",Enums.TestResult.FAIL])
        return res
        

    def CAL_Timeout(self,Flow_limit,Check):
        res = []
        Flow_limit1 = self.flows[1]['Limit']
        Flow_limit2 = self.flows[2]['Limit']
        PD = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=Flow_limit1,Type = "TesterMsg")
        if len(PD)>2:
            CAL_ENTER = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",limit=Flow_limit2,Type = "Packet")
            if len(CAL_ENTER)>2:
                res.append([f"Received CAL_ENTER packet at {round(CAL_ENTER[0],2)} sec",Enums.TestResult.PASS])
                
                t_ref = round(CAL_ENTER[0]-PD[0],3) #sec
                ChkRes = CommonMethods.check_measure(Check['expected'][0]['t_ref'],t_ref,Check['expected'][0]['comp'])
                res.append([f"T_ref from the start of the last 128 kHz digital ping to the beginning of Delta Ploss calibration is {ChkRes[3]} sec, Expected:{ ChkRes[2]} sec", ChkRes[1]])

                CAL_ENTER_RSP = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=[CAL_ENTER[2],Flow_limit2[1]],Type = "Response")
                if len(CAL_ENTER_RSP)>2:
                    Parameter_B = int(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP[2],"Parameter_B")[0]['sRawData'],16)
                    Parameter_A = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP[2],"Parameter_A")[0]['sDescription'])[0])
                    response = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP[2],"Response")[0]['sRawData'])[1]
                    # print("response:",response)
                    Reason = self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP[2],"Reason")[0]['sDescription'].split(":")[1].strip()
                    # print("Reason:",Reason)
                    # print("Parameter_A:",Parameter_A)
                    # print("Parameter_B:",Parameter_B)

                    if t_ref <= 30:
                        if response == 1 and Reason == 'NO_ERR' and Parameter_A >= 80 and Parameter_B == 10:
                            res.append([f"Received CAL_ENTER_RSP packet at {round(CAL_ENTER_RSP[0],2)} sec with Response: {response}, Expected: 1, Reason: {Reason}, Expected: NO_ERR, Parameter_A: {Parameter_A}, Expected:>=80, and Parameter_B: {Parameter_B}, Expected: 10",Enums.TestResult.PASS])
                        else:
                            res.append([f"Received CAL_ENTER_RSP packet at {round(CAL_ENTER_RSP[0],2)} sec with Response: {response}, Expected: 1, Reason: {Reason}, Expected: NO_ERR, Parameter_A: {Parameter_A}, Expected:>=80, and Parameter_B: {Parameter_B}, Expected: 10",Enums.TestResult.FAIL])
                    else:
                        if response == 0 and Reason == 'FOD_REFRESH_SEQ' and Parameter_A == 0 and Parameter_B == 0:
                            res.append([f"Received CAL_ENTER_RSP packet at {round(CAL_ENTER_RSP[0],2)} sec with Response: {response}, Expected: 0, Reason: {Reason}, Expected: FOD_REFRESH_SEQ, Parameter_A: {Parameter_A}, Expected:=0, and Parameter_B: {Parameter_B}, Expected: 0",Enums.TestResult.PASS])
                        else:
                            res.append([f"Received CAL_ENTER_RSP packet at {round(CAL_ENTER_RSP[0],2)} sec with Response: {response}, Expected: 0, Reason: {Reason}, Expected: FOD_REFRESH_SEQ, Parameter_A: {Parameter_A}, Expected:=0, and Parameter_B: {Parameter_B}, Expected: 0",Enums.TestResult.FAIL])

                        CLK = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[CAL_ENTER_RSP[2],Flow_limit2[1]],Type = "Packet")
                        if len(CLK)>2:
                            clk_reason = self.PktMethod.GetPayloadDetails(CLK[2],'Reason')[0]["sDescription"].split(":")[-1].strip()
                            if clk_reason == "Foreign Object Detection":
                                res.append([f"Received Cloak packet at {round(CLK[0],2)} sec with Reason: {clk_reason}, Expected: Foreign Object Detection",Enums.TestResult.PASS])
                            else:
                                res.append([f"Received Cloak packet at {round(CLK[0],2)} sec with Reason: {clk_reason}, Expected: Foreign Object Detection",Enums.TestResult.FAIL])
                            
                            clk_exit = self.PktMethod.GetPacketDetails(packet="MPP_Cloak_Exit",limit=[CLK[2],len(self.file_list)-1],Type = "TesterMsg")
                            if len(clk_exit)>2:
                                
                                res.append([f"Received Cloak Exit packet at {round(clk_exit[0],2)} sec",Enums.TestResult.PASS])
                                
                                CAL_ENTER2 = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",limit=[clk_exit[2],len(self.file_list)-1],Type = "Packet")
                                if len(CAL_ENTER2)>2:
                                    res.append([f"Received CAL_ENTER packet at {round(CAL_ENTER2[0],2)} sec",Enums.TestResult.PASS])
                                    CAL_ENTER_RSP2 = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=[CAL_ENTER2[2],len(self.file_list)-1],Type = "Response")
                                    if len(CAL_ENTER_RSP2)>2:
                                        Parameter_B2 =int(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP2[2],"Parameter_B")[0]['sRawData'],16)
                                        Parameter_A2 = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP2[2],"Parameter_A")[0]['sDescription'])[0])
                                        response2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP2[2],"Response")[0]['sRawData'])[1]
                                        # print("response2:",response2)
                                        Reason2 = self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP2[2],"Reason")[0]['sDescription'].split(":")[1].strip()
                                        # print("Reason2:",Reason2) 
                                        # print("Parameter_A2:",Parameter_A2)
                                        # print("Parameter_B2:",Parameter_B2)
                                        if response2 == 1 and Reason2 == 'NO_ERR' and Parameter_A2 >= 80 and Parameter_B2 == 10:
                                            res.append([f"Received CAL_ENTER_RSP packet at {round(CAL_ENTER_RSP2[0],2)} sec with Response: {response2}, Expected: 1, Reason: {Reason2}, Expected: NO_ERR, Parameter_A: {Parameter_A2}, Expected:>=80, and Parameter_B: {Parameter_B2}, Expected: 10",Enums.TestResult.PASS])
                                        else:
                                            res.append([f"Received CAL_ENTER_RSP packet at {round(CAL_ENTER_RSP2[0],2)} sec with Response: {response2}, Expected: 1, Reason: {Reason2}, Expected: NO_ERR, Parameter_A: {Parameter_A2}, Expected:>=80, and Parameter_B: {Parameter_B2}, Expected: 10",Enums.TestResult.FAIL])    
                                    
                                    else:res.append([f"CAL_ENTER_RSP packet not recevied",Enums.TestResult.FAIL])
                                else:res.append([f"CAL_ENTER packet not recevied",Enums.TestResult.FAIL])
                            else:res.append([f"MPP_Cloak_Exit packet not recevied",Enums.TestResult.FAIL])
                        else:res.append([f"Cloak packet not recevied",Enums.TestResult.FAIL])
                else:res.append([f"CAL_ENTER_RSP packet not recevied",Enums.TestResult.FAIL])

            else: res.append([f"CAL_ENTER packet not found", Enums.TestResult.FAIL])
        else: res.append([f"Ping Detected assertion not found", Enums.TestResult.FAIL])
        return res
                

    def ChargeStatus(self,Flow_limit,Check):
        res = []
        InitialVal = None
        Value = None
        #.1 Get initial charge status
        TempPkt1 = self.PktMethod.GetPacketDetails(packet="Charge Status",limit=Flow_limit)
        if len(TempPkt1)>2:
            InitialVal = round(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],"Charger_Status_Value")[0]['sRawData'])[0],3)
            res.append([f"Charge Status packet found at {round(TempPkt1[0],3)}Sec, With Initial charge value {InitialVal}",Enums.TestResult.PASS])
            id = TempPkt1[2]+1
            while id < Flow_limit[1]:
                TempPkt2 =  self.PktMethod.GetPacketDetails(packet="Charge Status",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    Value = round(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Charger_Status_Value")[0]['sRawData'])[0],3)
                    if Value >= InitialVal+Check['ExpectedValue']:
                        res.append([f"Charge Status packet found at {round(TempPkt2[0],3)}sec with charge value {Value} and reached the charge value of initial charge value + {Check['ExpectedValue']}",Enums.TestResult.PASS])
                        #check for shutdown
                        tid = TempPkt2[2]+1
                        while tid < Flow_limit[1]:
                            if self.PktMethod.GetPacketType(tid)=="Packet":
                                res.append([f"Found packets after reaching the charge status limit",Enums.TestResult.FAIL])
                                break
                            tid+=1
                        if tid==Flow_limit[1]:res.append([f"Test terminated after reaching the charge limit",Enums.TestResult.PASS])
                        break
                    id = TempPkt2[2]+1
                else:
                    res.append([f"Last Received Charge Status packet value {Value}",Enums.TestResult.PASS])
                    break
            if Value is None:res.append([f"No further chanrge status packets Received after the first packet",Enums.TestResult.FAIL])
        else:res.append([f"Charge Status packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)} to {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
        return res

    def Linearization(self,Flow_limit,Check):
        res = [] 
        x = 1
        for chk in Check['expected']:
            if "LimitType" in chk:
                Limit = self.PktMethod.GetLimits(chk['LimitType'],chk,Flow_limit)
            else: Limit = Flow_limit
            res.append([f"Sequence {x} started ------------------------------------------------------------------------------------------------------------------------------------------------",Enums.TestResult.PASS])
            #1.Get The Load power value
            TempPkt1 =  self.PktMethod.GetPacketDetails(packet="SRQ",value="Load Power",limit=Limit)
            if len(TempPkt1)>2:
                Value = round(GeneralMethods.GetFloatFromStr((self.PktMethod.GetPayloadDetails(TempPkt1[2],'Load_Power_low')[0]['sDescription']))[0],2)
                res.append([f"SRQ Load Power packet found at {round(TempPkt1[0],3)}sec with load power value {Value}W",Enums.TestResult.PASS])
                #2.Get SRQ/ce packet 
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="SRQ",value="Control Error Calculation Method",limit=[TempPkt1[2]+1,Limit[1]])
                if len(TempPkt2)>2:
                    Value1 = self.PktMethod.GetPayloadDetails(TempPkt2[2],'Request')[0]['sRawData']
                    Value2 = self.PktMethod.GetPayloadDetails(TempPkt2[2],'CE_Calculation_Method')[0]['sRawData']
                    if Value1 =="0xA1" and Value2=="0x02":
                        res.append([f"SRQ_Control Error Calculation Method packet found at @index {round(TempPkt2[2],3)} with payload value Request:{Value1} and CE_Calculation_Method:{Value2} ",Enums.TestResult.PASS])
                    else:res.append([f"SRQ_Control Error Calculation Method packet found at @index {round(TempPkt2[2],3)}, with payload value Request:{Value1} and CE_Calculation_Method:{Value2} ",Enums.TestResult.FAIL])
                    #3Get the SRQ Control Gain
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="SRQ",value="Control Gain",limit=[TempPkt2[2]+1,Limit[1]])
                    if len(TempPkt3)>2:
                        resp = self.PktMethod.GetPacketResponse(TempPkt3,[TempPkt3[2]+1,Limit[1]])
                        if resp is not None:
                            if self.file_list[resp]['pktType'] =="ACK":
                                res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS])
                            else:res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(TempPkt3[0],3)}sec",Enums.TestResult.FAIL])
                        else:res.append([f"Response not found for SRQ_Control Gain packet at {round(TempPkt3[0],3)}sec",Enums.TestResult.FAIL])
                        #4. SRQ_Control Gain gtarget
                        gtarget = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt3[2],'G_TARGET')[0]['sDescription'])[0]
                        gscale = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt3[2],'G_SCALE')[0]['sDescription'])[0]
                        gtargetChkRes = CommonMethods.check_measure(chk['gtarget'],gtarget,'EQL')
                        gscaleChkRes = CommonMethods.check_measure(chk['gscale'],gscale,'EQL')
                        res.append([f"The Received g_target_{x} is {gtargetChkRes[3]}, Expected: {gtargetChkRes[2]}", gtargetChkRes[1]])
                        res.append([f"The Received g_scale_{x} is {gscaleChkRes[3]}, Expected: {gscaleChkRes[2]}", gscaleChkRes[1]])
                        # if 0.1 <= gtarget <= 0.9 and gscale == 4:
                        #     res.append([f"The Received G_TARGET is {gtarget}, which is in limit of 0.1-0.9, ",Enums.TestResult.PASS])
                        # else:res.append([f"The Received G_TARGET is {gtarget}, which is not in limit of 0.1-0.9",Enums.TestResult.FAIL])


                        if "DPlossCalibration" in chk:
                            ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Limit,Type="Response")
                            # print('ECAP:',ECAP)
                            if len(ECAP)>2:
                                ECAPppwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Potential_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                # print("ECAPppwr:",ECAPppwr)
                                res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt} at {round(ECAP[0],3)} sec", Enums.TestResult.PASS])
                                if ECAPppwr > 15:
                                    res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt} i.e, > 15W", Enums.TestResult.PASS])
                                    tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                                    dplosschks = self.DPlossCalibration(Limit,tempcheck)
                                    # # print(chk for chk in dplosschks)
                                    # res.append(chk for chk in dplosschks)
                                    for chk in dplosschks:
                                        res.append(chk)
                                else: 
                                    res.append([f"Potential_Load_Power is {ECAPppwr} W, so DPLOSS calibration won't perform, Expected: > 15 W", Enums.TestResult.PASS])
                            else: res.append([f"{self.ECAP_pkt} packet not found", Enums.TestResult.FAIL])


                    else:res.append([f"SRQ_Control Gain packet not found",Enums.TestResult.FAIL])
                else:res.append([f"SRQ_Control Error Calculation Method packet not found",Enums.TestResult.FAIL])
            else:res.append([f"SRQ Load Power packet not found",Enums.TestResult.FAIL])
            x += 1
        return res

    def POW_G_C0(self,Flow_limit,Check):
        print("POW_G_C0")
        res = []
        Limit = Flow_limit
        #2.Get SRQ/ce packet 
        TempPkt2 = self.PktMethod.GetPacketDetails(packet="SRQ",value="Control Error Calculation Method",limit=Flow_limit)
        if len(TempPkt2)>2:
            Value1 = self.PktMethod.GetPayloadDetails(TempPkt2[2],'Request')[0]['sRawData']
            Value2 = self.PktMethod.GetPayloadDetails(TempPkt2[2],'CE_Calculation_Method')[0]['sRawData']
            if Value1 =="0xA1" and Value2=="0x02":
                res.append([f"SRQ_Control Error Calculation Method packet found at @index {round(TempPkt2[2],3)} with payload value Request:{Value1} and CE_Calculation_Method:{Value2} ",Enums.TestResult.PASS])
            else:res.append([f"SRQ_Control Error Calculation Method packet found at @index {round(TempPkt2[2],3)}, with payload value Request:{Value1} and CE_Calculation_Method:{Value2} ",Enums.TestResult.FAIL])
            #3Get the SRQ Control Gain
            TempPkt3 = self.PktMethod.GetPacketDetails(packet="SRQ",value="Control Gain",limit=[TempPkt2[2]+1,Limit[1]])
            if len(TempPkt3)>2:
                resp = self.PktMethod.GetPacketResponse(TempPkt3,[TempPkt3[2]+1,Limit[1]])
                if resp is not None:
                    if self.file_list[resp]['pktType'] =="ACK":
                        res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS])
                    else:res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(TempPkt3[0],3)}sec",Enums.TestResult.FAIL])
                else:res.append([f"Response not found for SRQ_Control Gain packet at {round(TempPkt3[0],3)}sec",Enums.TestResult.FAIL])
                #4. SRQ_Control Gain gtarget
                gtarget = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt3[2],'G_TARGET')[0]['sDescription'])[0]
                gscale = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt3[2],'G_SCALE')[0]['sDescription'])[0]
                gtargetChkRes = CommonMethods.check_measure([0.5],gtarget,'EQL')
                gscaleChkRes = CommonMethods.check_measure([4],gscale,'EQL')
                res.append([f"The Received g_target is {gtargetChkRes[3]}, Expected: {gtargetChkRes[2]}", gtargetChkRes[1]])
                res.append([f"The Received g_scale is {gscaleChkRes[3]}, Expected: {gscaleChkRes[2]}", gscaleChkRes[1]])

                Powers = {"Prect1": "PotentialLoad", "Prect2": "Ptarget"}
                cnt = 1
                G_values = []
                Prect_values = []
                templimit = Flow_limit
                for pwr in Powers:
                    load = 0
                    EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
                    if Powers[pwr] == "PotentialLoad":
                        Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
                        if len(Excapres)> 2:
                            for ck in EXCAP.keys():
                                payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                                # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                                EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
                            # print("EXCAP:",EXCAP)
                            MSRreq = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=Flow_limit,Type="Packet")
                            if len(MSRreq)> 2:
                                PrefMode = self.PktMethod.GetPayloadDetails(MSRreq[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                                # print("PrefMode:",PrefMode)
                                load =int(EXCAP[PrefMode])
                                res.append([f"Potential Load Power of {PrefMode} is {load} W in MODEXCAP", Enums.TestResult.PASS])           
                    else: 
                        load = Check["expected"][0]['Ptarget']
                        res.append([f"P_target is {load} W", Enums.TestResult.PASS])   
                    # print(f"Set_Load {load*1000}", templimit)
                    
                    # TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {load*1000}mW",limit=templimit,Type="TesterMsg")
                    TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {load*1000}mW",limit=[templimit[1],templimit[0]],Type="TesterMsg")
                    # print("TempPkt2:",TempPkt2)
                    if len(TempPkt2)>2:
                        res.append([f"Found Set_Load {load*1000}mW packet at {round(TempPkt2[0],3)}Sec",Enums.TestResult.PASS])
                        #find the stabilization
                        TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],templimit[1]],Type="TesterMsg")
                        # print("TempPkt3:",TempPkt3)
                        if len(TempPkt3)>2:
                            res.append([f"Stabilization found at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS])

                            id = TempPkt3[2]
                            incr_id = 0
                            while id <= templimit[1]:
                                pkt1 = self.PktMethod.GetPacketDetails(packet="Increase_radial_position_0_5mm",limit=[id,templimit[1]],Type="TesterMsg")
                                if len(pkt1)>2:
                                    res.append([f"Increase_radial_position_0_5mm TesterMsg found at {round(pkt1[0],3)}sec",Enums.TestResult.PASS])
                                    id = pkt1[2]
                                    incr_id = id
                                id += 1

                            j = TempPkt3[2]
                            pwr_start = 0
                            while j <= templimit[1]:
                                pkt_type = self.file_list[j]['pktType']
                                pkt_value = self.file_list[j]['value']

                                # -------- Extended Control Error --------
                                if pkt_type == "Extended Control Error":
                                    respid = self.PktMethod.GetPacketResponse2(j, [j+1, templimit[1]])
                                    if respid is not None and self.file_list[respid]['pktType'] == "NAK":
                                        res.append([f"Extended Control Error packet with NAK response found at {round(self.file_list[j]['startTime'],3)}sec",Enums.TestResult.PASS])
                                        # print("XCE NAK found at:", j)

                                # -------- Get Request {PTx Regulation Control Status}--------
                                if pkt_type == "Get Request":
                                    if pkt_value == "{PTx Regulation Control Status}":
                                        respid = self.PktMethod.GetPacketResponse2(j, [j+1, templimit[1]])
                                        if respid is not None and self.file_list[respid]['pktType'] == "Regulation Control Status":
                                            res.append([f"Get Request (PTx Regulation Control Status) packet with Regulation Control Status response found at {round(self.file_list[j]['startTime'],3)}sec",Enums.TestResult.PASS])
                                            # print("RCS response found at:", j)
                                            status_val = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(respid,"Status")[0]['sRawData'])[1]
                                            status = self.PktMethod.GetPayloadDetails(respid,"Status")[0]['sDescription']
                                            # # print("status_val:",status_val)
                                            # # print("status:",status)    
                                            if pwr_start == 0: pwr_start = j 
                                            if status_val in [1,3] and status in ["Reached maximum allocated power","Reached maximum supported voltage"]:
                                                res.append([f"Regulation Control Status received with status: {status_val} ({status}) at {round(self.file_list[respid]['startTime'],3)} sec, Expected: status: 1 (Reached maximum allocated power) or 3 (Reached maximum supported voltage)",Enums.TestResult.PASS])
                                            else: res.append([f"Regulation Control Status received with status: {status_val} ({status}) at {round(self.file_list[respid]['startTime'],3)} sec, Expected: status: 1 (Reached maximum allocated power) or 3 (Reached maximum supported voltage)",Enums.TestResult.FAIL])
                                j += 1

                            #Get Prect from PLA
                            TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[pwr_start,templimit[1]])
                            # print("TempPkt4:",TempPkt4)
                            if len(TempPkt4)>2:
                                Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                                Prect_values.append(Prect)
                                results = CommonMethods.check_measure([(load-(load*0.04)),(load+(load*0.04))],Prect,"BTW")
                                
                                res.append([f"Measured Prect_{cnt}: {results[3]} W in PLA_2 packet at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {results[2]} W", results[1]])
                                
                                # EPT/rst
                                TempPkt5 = self.PktMethod.GetPacketDetails(packet="End Power Transfer",value="EPT/rst",limit=[TempPkt4[2],templimit[1]])
                                # print("TempPkt5:",TempPkt5)
                                if len(TempPkt5)>2:
                                    res.append([f"End Power Transfer (EPT/rst) found at {round(TempPkt5[0],3)} sec", Enums.TestResult.PASS])
                                else: res.append([f"End Power Transfer (EPT/rst) not found", Enums.TestResult.FAIL])
                                
                                # 360 PHASE
                                phase2_pkt = self.PktMethod.GetPacketDetails(packet="MPP_Runtime_Info",value="360kHz",limit=[TempPkt4[2],len(self.file_list)-1], Type="TesterMsg")
                                # print("phase2_pkt:",phase2_pkt)
                                if len(phase2_pkt)>2:
                                    templimit = [phase2_pkt[2],len(self.file_list)-1]

                                # MSR AUX = 1
                                TempPkt6 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode:",limit=templimit)
                                # print("TempPkt6:",TempPkt6)
                                if len(TempPkt6)>2:
                                    AUX = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt6[2],"AuxMode")[0]['sRawData'])[1]
                                    aux_result = CommonMethods.check_measure([1],AUX,"EQL")
                                    res.append([f"MSR packet with AUX: {aux_result[3]} is found at {round(TempPkt6[0],3)} sec, Expected: {aux_result[2]}", aux_result[1]])

                                    # Get inv voltage
                                    TempPkt8 = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Inverter Voltage",limit=[TempPkt6[2],templimit[1]])
                                    # print("TempPkt8:",TempPkt8)
                                    if len(TempPkt8)>2:
                                        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
                                        load2 = int((5/Check["expected"][0]['Vrect_target'])*1000) #mA
                                        res.append([f"Target power is 5W, Vrect_target is {Check["expected"][0]['Vrect_target']}V, so expected Irect is {load2}mA", Enums.TestResult.PASS])
                                        
                                        # Control stability 5W
                                        k = TempPkt8[2]
                                        sta_cnt = 0
                                        stability = []
                                        vrectx_result = Irect_result = Prect_result = []
                                        while k > TempPkt6[2]:
                                            TempPkt7 = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[k,TempPkt6[2]])
                                            # print("TempPkt7:",TempPkt7)
                                            if len(TempPkt7)>2:
                                                if sta_cnt == 0:
                                                    stability = TempPkt7
                                                    self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
                                                    self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)

                                                    vrectx = self.PktMethod.CalculateVoltTwindow(TempPkt7[2],self.AllChannelData)[0]
                                                    Vrect_target = Check["expected"][0]['Vrect_target']
                                                    vrectx_result = CommonMethods.check_measure([(Vrect_target*0.99),(Vrect_target*1.01)],vrectx,0)

                                                    Irect = self.PktMethod.CalculateVoltTwindow(TempPkt7[2],self.AllChannelData3)[0] #Amp
                                                    Irect_result = CommonMethods.check_measure([load2],Irect*1000,"GTEQL")

                                                    Prect = vrectx*Irect
                                                    Prect_result = CommonMethods.check_measure([4.9],Prect,"GTEQL")
                                        
                                                xce_val = self.file_list[TempPkt7[2]]['value']
                                                # print("xce_val:",xce_val)
                                                if xce_val in ["-1","0","+1"]:
                                                    sta_cnt += 1
                                                else: break
                                                if sta_cnt >= 5:
                                                    break
                                                k = TempPkt7[2]
                                            k -= 1
                                        if sta_cnt >= 5: 
                                            res.append([f"Control stabilized at {round(stability[0],3)} Sec, received {sta_cnt} Extended control error ['-1','0','+1'] packets before requesting inverter voltage, Expected: >=5",Enums.TestResult.PASS])
                                        else: res.append([f"Control not stabilized, received only {sta_cnt} Extended control error ['-1','0','+1'] packets before requesting inverter voltage, Expected: >=5",Enums.TestResult.FAIL])

                                        res.append([f"Measured Vrect is {round(vrectx_result[3],3)} V at {round(stability[0],3)} Sec, Expected: {vrectx_result[2]} V", vrectx_result[1]])
                                        # res.append([f"Measured Irect is {round(Irect_result[3],3)} mA at {round(stability[0],3)} Sec, Expected: {Irect_result[2]} mA", Irect_result[1]])
                                        res.append([f"Measured Irect is {round(Irect*1000,3)} mA at {round(stability[0],3)} Sec", Enums.TestResult.PASS])
                                        res.append([f"Measured Prect is {round(Prect_result[3],3)} W at {round(stability[0],3)} Sec, Expected: {Prect_result[2]} W", Prect_result[1]])

                                        res.append([f"Get Request (PTx Inverter Voltage) packet found at {round(TempPkt8[0],3)}Sec",Enums.TestResult.PASS])
                                        TempPkt9 = self.PktMethod.GetPacketDetails(packet=self.Inv_vol_pkt,limit=[TempPkt6[2],templimit[1]],Type="Response")
                                        # print("TempPkt9:",TempPkt9)
                                        if len(TempPkt9)>2:
                                            Vinv = float(self.PktMethod.GetPayloadDetails(TempPkt9[2],"Vinv")[0]['sDescription'].split(":")[1].replace("V","").strip())
                                            res.append([f"Inverter_Voltage response with Inverter_Voltage: {Vinv} V found at {round(TempPkt9[0],3)}Sec",Enums.TestResult.PASS])
                                            # print("Vinv:",Vinv)

                                            # Vrect
                                            TempPkt10 = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[TempPkt9[2],templimit[1]])
                                            # print("TempPkt10:",TempPkt10)
                                            if len(TempPkt10)>2:
                                                vrect = self.PktMethod.CalculateVoltTwindow(TempPkt10[2],self.AllChannelData)[0]
                                                # print("vrect:",vrect)

                                                # G calculation
                                                G = vrect/Vinv
                                                # print("G:",G)
                                                G_values.append(G)
                                                res.append([f"Calculated G_{cnt} is {round(G,4)}, Vrect is {vrect} V, Vinv is {Vinv} V",Enums.TestResult.PASS])
                                                

                                                # print("TempPkt10[2],templimit[1]:",TempPkt10[2],templimit[1])
                                                # MSR AUX = 1
                                                TempPkt11 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode:",limit=[TempPkt10[2],templimit[1]])
                                                # print("TempPkt11:",TempPkt11)
                                                if len(TempPkt11)>2:
                                                    AUX = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt11[2],"AuxMode")[0]['sRawData'])[1]
                                                    aux_result = CommonMethods.check_measure([0],AUX,"EQL")
                                                    res.append([f"MSR packet with AUX: {aux_result[3]} is found at {round(TempPkt11[0],3)} sec, Expected: {aux_result[2]}", aux_result[1]])
                                                else:res.append([f"MSR Main Mode packet not found after calculating G_{cnt}", Enums.TestResult.FAIL])
                                                cnt += 1
                                            else:res.append([f"Extended Control Error packet not found", Enums.TestResult.FAIL])
                                        else:res.append([f"Inverter_Voltag response not found", Enums.TestResult.FAIL])
                                    else:res.append([f"Get Request (PTx Inverter Voltage) packet not found", Enums.TestResult.FAIL])
                                else:res.append([f"MSR Main Mode packet not found", Enums.TestResult.FAIL])
                                                
                            else:res.append([f"PLA packet not found between {round(TempPkt3[0],3)}Sec - {round(self.file_list[templimit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                        else:res.append([f"Stabilization is not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[templimit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                    else: res.append([f"Set_Load {load*1000}mW packet not found", Enums.TestResult.FAIL])
                
                #Final calculations
                if len(Prect_values) == 2 and len(G_values) == 2:
                    G4c0 = ((Prect_values[1]+Check["expected"][0]['ref2'])/Check["expected"][0]['ref1'])/G_values[1]
                    # print("G4c0:",G4c0)
                    res.append([f"G4c0 = {round(G4c0,4)}, Formula: (Prect_2+ref2)/refl/G2, Prect_2 : {Prect_values[1]} W, ref2 : {Check["expected"][0]['ref2']}, refl : {Check["expected"][0]['ref1']}, G2 : {round(G_values[1],4)}", Enums.TestResult.PASS])
                    Prect1_cal = min(Check["expected"][0]['A'],max(Check["expected"][0]['B'],((Check["expected"][0]['ref1']*G_values[0]*G4c0)-Check["expected"][0]['ref2'])))
                    # print("Prect1_cal:",Prect1_cal)
                    res.append([f"Prect1_cal = {Prect1_cal}, Formula: min(A,max(B,[refl*G1*G4co-ref2])), A : {Check["expected"][0]['A']}, B : {Check["expected"][0]['B']}, ref1 : {Check["expected"][0]['ref1']}, G1 : {round(G_values[0],4)}, G4c0 : {round(G4c0,4)}, ref2 : {Check["expected"][0]['ref2']}", Enums.TestResult.PASS])
                    Error_val = abs(100*((Prect1_cal-Prect_values[0])/Prect_values[0]))
                    # print("Error_val:",Error_val)
                    Error_ChkRes = CommonMethods.check_measure([4],Error_val,"LTEQL")
                    res.append([f"Error = {round(Error_val,4)} %, Formula: |100*((Prect1_cal-Prect_1)/Prect_1)|, Prect1_cal : {Prect1_cal}, Prect_1 : {Prect_values[0]}, Expected: Error < 4%", Error_ChkRes[1]])
                else: res.append([f"Prect_values and G_values are not measured properly", Enums.TestResult.FAIL])

            else:res.append([f"SRQ_Control Gain packet not found",Enums.TestResult.FAIL])
        else:res.append([f"SRQ_Control Error Calculation Method packet not found",Enums.TestResult.FAIL])
        return res

    def FastRecovery(self,Flow_limit,Check):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        id = 0
        end = len(self.file_list)-1
        ssvrect = {"z_0mm":[],"z_1mm":[],"z_2mm":[]}
        EXcntpkt = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station",limit=[id,end],Type="TesterMsg")
        if len(EXcntpkt)>2:
            # ssvrect['z_0mm'] = EXcntpkt[2]
            IncZ1 = self.PktMethod.GetPacketDetails(packet="Increase_z_By_1mm",limit=[EXcntpkt[2],end],Type="TesterMsg")
            if len(IncZ1)>2:
                ssvrect['z_0mm'] = [EXcntpkt[2],IncZ1[2]]
                # ssvrect['z_1mm'] = IncZ1[2]
                IncZ2 = self.PktMethod.GetPacketDetails(packet="Increase_z_By_1mm",limit=[IncZ1[2]+1,end],Type="TesterMsg")
                if len(IncZ2)>2:
                    ssvrect['z_1mm'] = [IncZ1[2],IncZ2[2]]
                    # ssvrect['z_2mm'] = IncZ2[2]
                    ssvrect['z_2mm'] = [IncZ2[2],end]
                    
                else: res.append([f"Increase_z_By_1mm assertion_2 not found", Enums.TestResult.FAIL])
            else: res.append([f"Increase_z_By_1mm assertion_1 not found", Enums.TestResult.FAIL])
        else: res.append([f"Execution_count_no not found", Enums.TestResult.FAIL])
        vrectmax = {"z_0mm":0,"z_1mm":0,"z_2mm":0}
        print("ssvrect:",ssvrect)
        for key,value in ssvrect.items():
            if value:
                res.append([f"{self.file_list[value[0]]['pktType']} found at {round(self.file_list[value[0]]['startTime'],3)} sec", Enums.TestResult.PASS])
                cnt = 0
                start = value[0]
                end1 = value[1]
                vmax = 0
                # while cnt <= 5:
                #     ss = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[start,end1])
                #     if len(ss)>2:
                #         vrect = float(round(self.PktMethod.CalculateVoltTwindow(ss[2],self.AllChannelData,winsize=[9,11])[0],3))
                #         res.append([f"At {key}, Vrect at Signal strength_{cnt} is {vrect} V, found at {round(ss[0],3)} sec", Enums.TestResult.PASS])
                #         if vrect>vmax:
                #             vmax = vrect
                #         start = ss[2]+1
                #     else: res.append([f"Signal strength not found", Enums.TestResult.FAIL])
                #     cnt += 1

                while start < end1:
                    pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[start, end1], Type="TesterMsg")
                    print("pd",pd)
                    if len(pd) > 2:
                        sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], end1+1], Type="TesterMsg")
                        ts = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Test_Stop", limit=[pd[2], end1+1], Type="TesterMsg")
                        if len(sd) > 2 or len(ts) > 2:
                            fop_pkt = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd[2], sd[2] if len(sd) > 2 else ts[2]], Type="TesterMsg")
                            print("fop_pkt",fop_pkt)
                            if len(fop_pkt) > 2:
                                fop = float(self.file_list[fop_pkt[2]]['value'].split(":")[1].split(" ")[0])
                                if 127.5 < fop < 128.5:
                                    # res.append([f"FOP: {fop} kHz found at {round(fop_pkt[0],3)} sec, Expected: 127.5 kHz < fop <128.5 kHz", Enums.TestResult.PASS])
                                    ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[fop_pkt[2], end1], Type="Packet")
                                    print("ss",ss)
                                    if len(ss) > 2:
                                        cnt += 1
                                        vrect = float(round(self.PktMethod.CalculateVoltTwindow(ss[2],self.AllChannelData,winsize=[9,11])[0],3))
                                        res.append([f"At {key}, Vrect at Signal strength_{cnt} is {vrect} V, found at {round(ss[0],3)} sec", Enums.TestResult.PASS])
                                        if vrect>vmax:
                                            vmax = vrect
                                        start = sd[2] if len(sd) > 2 else ts[2]
                                        if cnt == 5: break
                    #                 else: start = fop_pkt[2]+1
                    #             else: start = fop_pkt[2]+1
                    #         else: start = sd[2]+1 if len(sd) > 2 else ts[2]+1
                    #     else: start = pd[2]+1
                    # else: start += 1
                    start += 1


                vrectmax[key] = vmax
                res.append([f"Vrect_{list(ssvrect.keys()).index(key)}_max at {key} is {vmax} V", Enums.TestResult.PASS])
                if cnt == 5:
                    res.append([f"5 Digital pings 128kHz are received", Enums.TestResult.PASS])
                else: res.append([f"{cnt} Digital pings 128kHz are received, Expected: 5", Enums.TestResult.FAIL])
        # max(vrectmax.values())
        maxkey = max(vrectmax, key=vrectmax.get)
        res.append([f"Final Maximum voltage is {max(vrectmax.values())} V at {maxkey}", Enums.TestResult.PASS])
        return res







        # res = []
        # self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        # id = 0
        # end = len(self.file_list)-1
        # ssvrect = {"z_0mm":"","z_1mm":"","z_2mm":""}
        # EXcntpkt = self.PktMethod.GetPacketDetails(packet="Execution_count_no",limit=[end,id],Type="TesterMsg")
        # if len(EXcntpkt)>2:
        #     ssvrect['z_0mm'] = EXcntpkt[2]
        #     IncZ1 = self.PktMethod.GetPacketDetails(packet="Increase_z_By_1mm",limit=[EXcntpkt[2],end],Type="TesterMsg")
        #     if len(IncZ1)>2:
        #         ssvrect['z_1mm'] = IncZ1[2]
        #         IncZ2 = self.PktMethod.GetPacketDetails(packet="Increase_z_By_1mm",limit=[IncZ1[2]+1,end],Type="TesterMsg")
        #         if len(IncZ2)>2:
        #             ssvrect['z_2mm'] = IncZ2[2]
                    
        #         else: res.append([f"Increase_z_By_1mm assertion_2 not found", Enums.TestResult.FAIL])
        #     else: res.append([f"Increase_z_By_1mm assertion_1 not found", Enums.TestResult.FAIL])
        # else: res.append([f"Execution_count_no not found", Enums.TestResult.FAIL])
        # vrectmax = {"z_0mm":0,"z_1mm":0,"z_2mm":0}
        # for key,value in ssvrect.items():
        #     if value:
        #         res.append([f"{self.file_list[value]['pktType']} found at {round(self.file_list[value]['startTime'],3)} sec", Enums.TestResult.PASS])
        #         cnt = 1
        #         start = value
        #         vmax = 0
        #         while cnt <= 5:
        #             ss = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[start,end])
        #             if len(ss)>2:
        #                 vrect = float(round(self.PktMethod.CalculateVoltTwindow(ss[2],self.AllChannelData,winsize=[9,11])[0],3))
        #                 res.append([f"At {key}, Vrect at Signal strength_{cnt} is {vrect} V, found at {round(ss[0],3)} sec", Enums.TestResult.PASS])
        #                 if vrect>vmax:
        #                     vmax = vrect
        #                 start = ss[2]+1
        #             else: res.append([f"Signal strength not found", Enums.TestResult.FAIL])
        #             cnt += 1
        #         vrectmax[key] = vmax
        #         res.append([f"Vrect_{list(ssvrect.keys()).index(key)}_max at {key} is {vmax} V", Enums.TestResult.PASS])
        # # max(vrectmax.values())
        # maxkey = max(vrectmax, key=vrectmax.get)
        # res.append([f"Final Maximum voltage is {max(vrectmax.values())} V at {maxkey}", Enums.TestResult.PASS])
        # return res

    def Txce_interval(self,Flow_limit,Check):
        res = []
        xcecnt = 0
        start = 0
        xceids = []

        new_limit = Flow_limit
        stable1 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=Flow_limit,Type="TesterMsg")
        if len(stable1)>2:
            new_limit = [stable1[2],Flow_limit[1]]
        else:
            res.append(["Stabilization not found for Potential load", Enums.TestResult.INCONCLUSIVE])
            new_limit = [Flow_limit[1],Flow_limit[0]]
            
        
        dumppkt = self.PktMethod.GetPacketDetails(packet="Set_Load 400mA",limit=new_limit,Type="TesterMsg")
        if len(dumppkt)>2:
            res.append([f"Load dump 400mA found at {round(dumppkt[0],3)} sec", Enums.TestResult.PASS])
            id = dumppkt[2]
            end_pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[id,Flow_limit[1]],Type="TesterMsg")
            if len(end_pkt)>2:
                end = end_pkt[2]
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
                # print("xcecnt:",len(set(xceids)))
                XceRes = CommonMethods.check_measure(Check['expected'],len(set(xceids)),"LTEQL")
                res.append([f"Total {XceRes[3]} Extended Control Error packets received, Expected: {XceRes[2]}",XceRes[1]])
            else: res.append([f"Stabilization not found for 400mA load", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"Load dump 400mA not found.", Enums.TestResult.INCONCLUSIVE])
        return res

    def PMpreference(self,Flow_limit,Check):
        res = []
        MSR = self.PktMethod.GetPacketDetails(packet="MSR",limit=Flow_limit,Type="Packet")
        if len(MSR)>2:
            PM = self.PktMethod.GetPayloadDetails(MSR[2],'MainMode')[0]['sDescription'].split(":")[1].strip()
            if Check['expected'] == PM:
                res.append([f"TPR set power mode to {PM}, Expected: {Check['expected']} ",Enums.TestResult.PASS])
            else: res.append([f"TPR set power mode to {PM}, Expected: {Check['expected']} ",Enums.TestResult.INCONCLUSIVE])
            MSS = self.PktMethod.GetPacketDetails(packet="MSS",limit=[MSR[2],Flow_limit[1]],Type="Response")
            if len(MSS)>2:
                status = self.PktMethod.GetPayloadDetails(MSS[2],'Status')[0]['sDescription'].split(":")[1].strip()
                

            else: res.append([f"MSS not found",Enums.TestResult.FAIL])
        return res

    def KestCheck(self,Flow_limit,Check):
        res = []
        if 'SLIDING' not in self.Header['TestcaseID']:
            #1. Get K_est Value from Estimated_K packet.
            TempPkt1 = self.PktMethod.GetPacketDetails(packet=self.Kest_pkt,limit=Flow_limit,Type="Response")
            # print("TempPkt1:",TempPkt1)
            if len(TempPkt1)>2:
                # print(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],'Estimated_K_Value')[0]['sDescription'])[0])
                Kest = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],'Estimated_K_Value')[0]['sDescription'])[0]
                if 'P1' in self.Header['TestcaseID']:
                    Kiactual = self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel']['kiActual_P1']
                elif 'P2' in self.Header['TestcaseID']:
                    Kiactual = self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel']['kiActual_P2']
            
                        
                else:Kiactual = self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel']['kiActual_P3']
                res.append([f"The Estimated_K packet found at {round(TempPkt1[0],3)}sec, with Kest value :{Kest}, Ki_actual from SDF :{Kiactual}",Enums.TestResult.PASS])
                #.check the calculations
                if Kiactual !=0:
                    results = CommonMethods.check_measure(Check['ExpectedValue'],round(abs((Kiactual-Kest)/Kiactual),3),Check['comp'])
                    res.append([f"The value of (Kiactual-Kest)/Kiactual is {round(abs((Kiactual-Kest)/Kiactual),3)}, Expected: {results[2]}",results[1]])
                    
                else: res.append([f"The Kiactual set to 0 in SDF",Enums.TestResult.FAIL])
            else:res.append([f"The Estimated_K pacekt not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])

            if Check.get("Main_mode"):
                # Inconclusive
                Modecap = self.PktMethod.GetPacketDetails(packet="MODECAP",value="Active Main Mode",limit=Flow_limit,Type="Response")
                if len(Modecap)>2:
                    mode = self.PktMethod.GetPayloadDetails(Modecap[2], "Active_Main_Mode")[0]['sDescription'].split(":")[1].strip()
                    if mode == "High Power Mode":
                        res.append([f"{mode} is observed in MODECAP packet at {round(Modecap[0],3)} sec, Expected: != High Power Mode", Enums.TestResult.INCONCLUSIVE])
                    else:res.append([f"{mode} is observed in MODECAP packet at {round(Modecap[0],3)} sec, Expected: != High Power Mode", Enums.TestResult.PASS])
                else: res.append([f"MODECAP packet not found", Enums.TestResult.FAIL])

        # SLIDING
        else:
            Kiactual = self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel']['kiActual_P1']
            firstpkt = self.PktMethod.GetPacketDetails(packet="Execution_count_no",limit=[0,len(self.file_list)],Type='TesterMsg')
            lastpkt = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[firstpkt[2],len(self.file_list)],Type='TesterMsg')
            if len(firstpkt)>2 and len(lastpkt)>2:
                start = firstpkt[2]
                end = lastpkt[2]
                cnt=1
                passcnt = 0
                while cnt <= 10:

                    TempPkt1 = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Estimated K",limit=[start,end],Type="Packet")
                    # print("TempPkt1:",TempPkt1)
                    if len(TempPkt1)>2:
                        res.append([f"TPR sent Get Request(PTx Estimated K) packet in seq_{cnt} at {round(TempPkt1[0],3)} sec", Enums.TestResult.PASS])
                        Estimated_K1 = self.PktMethod.GetPacketDetails(packet=self.Kest_pkt,limit=[TempPkt1[2],end],Type='Response')
                        if len(Estimated_K1) > 2:
                            Kest_sliding = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Estimated_K1[2],'Estimated_K_Value')[0]['sDescription'])[0]
                            res.append([f"PTx sent Estimated_K value is {Kest_sliding} in seq_{cnt} at {round(Estimated_K1[0],3)} sec", Enums.TestResult.PASS])
                            
                            if Check.get("Main_mode"):
                                # Inconclusive
                                Modecap = self.PktMethod.GetPacketDetails(packet="MODECAP",value="Active Main Mode",limit=[start,end],Type="Response")
                                if len(Modecap)>2:
                                    mode = self.PktMethod.GetPayloadDetails(Modecap[2], "Active_Main_Mode")[0]['sDescription'].split(":")[1].strip()
                                    if mode == "High Power Mode":
                                        res.append([f"{mode} is observed in MODECAP packet in seq_{cnt} at {round(Modecap[0],3)} sec, Expected: != High Power Mode", Enums.TestResult.INCONCLUSIVE])
                                    else:res.append([f"{mode} is observed in MODECAP packet in seq_{cnt} at {round(Modecap[0],3)} sec, Expected: != High Power Mode", Enums.TestResult.PASS])
                                else: res.append([f"MODECAP packet not found in seq_{cnt}", Enums.TestResult.FAIL])

                            
                            result = CommonMethods.check_measure(Check['ExpectedValue'],round(abs((Kest_sliding-Kiactual)/Kiactual),3),Check['comp'])
                            if result[1] == Enums.TestResult.PASS: passcnt += 1
                            res.append([f"For seq_{cnt}, the value of (Kest_sliding-Kiactual)/Kiactual is {round(abs((Kest_sliding-Kiactual)/Kiactual),3)}, limit: {result[2]}",result[1]])
                            shutdwnpkt = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Estimated_K1[2],end],Type='TesterMsg')
                            if len(shutdwnpkt) > 2:
                                ssvalpkt = self.PktMethod.GetPacketDetails(packet="Signal_Strength_Value",limit=[shutdwnpkt[2],end],Type='TesterMsg')
                                if len(ssvalpkt)>2:
                                    pingpkt = self.PktMethod.GetPacketDetails(packet="Ping Detected",value='TPR_MPP4',limit=[ssvalpkt[2],shutdwnpkt[2]],Type='TesterMsg')
                                    if len(pingpkt)>2:
                                        resu = CommonMethods.check_measure([5],round(pingpkt[0]-shutdwnpkt[1],3),'GTEQL')
                                        res.append([f"The time between seq_{cnt}&seq_{cnt+1} is {resu[3]}sec, limit: {resu[2]}sec",resu[1]])
                                        start = pingpkt[2]
                                    else: res.append([f"Ping detected packet not found in seq_{cnt+1}", Enums.TestResult.FAIL])
                                else: 
                                    if cnt < 10: 
                                        res.append([f"Signal_Strength_Value packet not found in seq_{cnt+1}", Enums.TestResult.FAIL])
                            else: res.append([f"Shutdown packet not found in seq_{cnt}", Enums.TestResult.FAIL])
                        else: res.append([f"Estimated_K packet not found in seq_{cnt}", Enums.TestResult.FAIL])
                        cnt += 1
                    else: 
                        res.append([f"Get Request(PTx Estimated K) packet not found in seq_{cnt}", Enums.TestResult.FAIL])
                        cnt += 1
            else: res.append([f"Test stop not found", Enums.TestResult.FAIL])
            if passcnt >=7:
                res.append([f"Kest_err < 0.06 for {passcnt} out of 10 sequences, Limit: >= 7 sequences", Enums.TestResult.PASS])
            else: res.append([f"Kest_err < 0.06 for {passcnt} out of 10 sequences, Limit: >= 7 sequences", Enums.TestResult.FAIL])
        return res

    def Transition_check(self, Flow_limit, Check):
        res = []
        if Check['flow'] == 1:
            coil_place = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station", limit=[Flow_limit[0],0], Type="TesterMsg")
            if len(coil_place)>2:
                UA = self.PktMethod.GetPacketDetails(packet='User Action status',limit=[coil_place[2],Flow_limit[0]],Type = "TesterMsg")
                if len(UA)>2:
                    res.append([f"PTx DUT is mated to TPR at {round(UA[0],3)} sec", Enums.TestResult.PASS])
                    if "bitscheck" in Check:
                        bits_resp = self.BitsCheck_New(Flow_limit,Check["bitscheck"])
                        # print("bits_resp:",bits_resp)
                        for temp_resp in bits_resp:
                            res.append(temp_resp)
                else:
                    res.append([f"User Action status packet not found", Enums.TestResult.FAIL])
            else: 
                res.append([f"Coil Place On Base Station packet not found", Enums.TestResult.FAIL])

        elif Check['flow'] == 2:
            id = Flow_limit[0]
            while id < Flow_limit[1]:
                if self.file_list[id]['pktType'] in ["Extended Control Error","Control Error"]:
                    res.append([f'PT Phase started from {round(self.file_list[id]['startTime'],3)} sec', Enums.TestResult.PASS])
                    nego = self.PktMethod.GetPacketDetails(packet='Renegotiate',limit=[id,Flow_limit[1]],Type = "Packet")
                    if len(nego) > 2:
                        tdiff = round(nego[0] - self.file_list[id]['startTime'],3)
                        if tdiff >= 5:
                            res.append([f"TPR sent Renegotiate Packet at {round(nego[0],3)} sec (within {tdiff} sec of PT Phase start), Expected: >= 5 sec", Enums.TestResult.PASS])
                        else:
                            res.append([f"TPR sent Renegotiate Packet at {round(nego[0],3)} sec (within {tdiff} sec of PT Phase start), Expected: >= 5 sec", Enums.TestResult.FAIL])
                    else: 
                        res.append([f"Renegotiate packet not found", Enums.TestResult.FAIL])  
                    break
                id+=1
            else: 
                res.append([f'PT Phase not found.',Enums.TestResult.INCONCLUSIVE])

        return res

    def Eyetest(self,Flow_limit,Check):
        res = []
        # print('EyeTest')
        results = self.EyeTestFetchDataFromCSV(Flow_limit,Check)
        # # print(results)
        if len(results)>0:
            res=results
        return res
            

    def MatedQ(self,Flow_limit,Check):
        res = []
        id = Flow_limit[0]
        end = Flow_limit[1]
        ECAP =  self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[id,end],Type="Response")
        if len(ECAP)>2:
            CAL = self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'cal')[0]['sRawData'])
            if CAL == 1:

                matedq = self.PktMethod.GetPacketDetails(packet="MATEDQ_RES",value="Foreign Object",limit=[id,end],Type="Response")
                if len(matedq)>2:
                    matedq_value = int(self.PktMethod.GetPayloadDetails(matedq[2],"Foreign_Object")[0]['sRawData'],16)
                    matedq_status = self.PktMethod.GetPayloadDetails(matedq[2],"Foreign_Object")[0]['sDescription'].split(":")[-1].strip()
                    if matedq_value == 2 and matedq_status.lower() == "foreign object detected":
                        res.append([f"MATEDQ_RES contains: {matedq_value} ({matedq_status}) at {round(matedq[0],3)} sec, Expected: 2 (Foreign object detected)", Enums.TestResult.PASS])
                    else:
                        res.append([f"MATEDQ_RES contains: {matedq_value} ({matedq_status}) at {round(matedq[0],3)} sec, Expected: 2 (Foreign object detected)", Enums.TestResult.FAIL])
                else: res.append([f"MATEDQ_RES response not found", Enums.TestResult.FAIL])


                res.append([f"Received CAL = 1(Calibration supported) in ECAP packet at {round(ECAP[0],2)} sec", Enums.TestResult.PASS])
                CAL_ENTER =  self.PktMethod.GetPacketDetails(packet="CAL_ENTER",limit=[ECAP[2],end],Type="Packet")
                if len(CAL_ENTER)>2:
                    CAL_ENTER_RSP =  self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=[CAL_ENTER[2],end],Type="Response")
                    if len(CAL_ENTER_RSP)>2:
                        data = {"Response":[],"Reason":[],"Parameter_A":[],"Parameter_B":[]}
                        idealdata = {'Response': [0, 'REJECT'], 'Reason': [3, 'FO_DETECTED'], 'Parameter_A': [0, '0'], 'Parameter_B': [0, '0min']}
                        for k,v in data.items():
                            data[k] = [self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP[2],k)[0]['sRawData']),self.PktMethod.GetPayloadDetails(CAL_ENTER_RSP[2],k)[0]['sDescription'].split(":")[-1].strip()]
                        # print(", ".join(f"{k}: {v[0]}({v[1]})" for k, v in data.items()))
                        if data == idealdata:
                            # res.append([", ".join(f"{k}: {v[0]}({v[1]})" for k, v in data.items()), Enums.TestResult.PASS])
                            res.append([", ".join([", ".join(f"{k}: {v[0]}({v[1]})" for k, v in data.items()), "Expected:",", ".join(f"{k}: {v[0]}({v[1]})" for k, v in idealdata.items())]), Enums.TestResult.PASS])
                        else: res.append([", ".join([", ".join(f"{k}: {v[0]}({v[1]})" for k, v in data.items()), "Expected:",", ".join(f"{k}: {v[0]}({v[1]})" for k, v in idealdata.items())]), Enums.TestResult.FAIL])
                        
            elif CAL == 0:
                res.append([f"Received CAL = 0(Calibration not supported) in ECAP packet at {round(ECAP[0],2)} sec", Enums.TestResult.PASS])
        return res
            

    def Tresponse(self,Flow_limit,Check):
        res = []
        for pkt in Check['expected']:
            id = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0],limit=Flow_limit,Type=pkt['refpkt'][1])[2]
            end = Flow_limit[1]
            # print("id:",id)
            TempPkt1 =  self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0],limit=[id,end],Type=pkt['packet1'][1])
            # print("TempPkt1:",TempPkt1)
            if len(TempPkt1) > 2:
                res.append([f"{pkt['packet1'][0]} packet found at {round(TempPkt1[0],3)} sec", Enums.TestResult.PASS])
                TempPkt2 =  self.PktMethod.GetPacketDetailswithPhase(packet=pkt['packet2'][0],limit=[TempPkt1[2]+1,end+1],Type=pkt['packet2'][1])
                # print("TempPkt2:",TempPkt2)
                if len(TempPkt2) > 2:
                    res.append([f"{pkt['packet2'][0]} packet found at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                    # TempPkt2_resp = self.GetPacketType(id)
                    if 'Response' in self.PktMethod.GetPacketType(TempPkt2[2]+1) and self.file_list[TempPkt2[2]+1]['pktType'] in ['ACK', 'NAK']:
                        Tresult = round((self.file_list[TempPkt2[2]+1]['startTime']-TempPkt1[1])*1000,3)
                        # print(f"{pkt['chk']}:", round((self.file_list[TempPkt2[2]+1]['startTime']-TempPkt1[1])*1000,3))
                        ChkRes = CommonMethods.check_measure(pkt['exp'],Tresult,pkt['comp'])
                        res.append([f"{self.file_list[TempPkt2[2]+1]['pktType']} response to {pkt['packet2'][0]} packet is received in: {ChkRes[3]} ms from 360kHz digital ping, Limit: {ChkRes[2]} ms", ChkRes[1]])
                    elif 'TesterMsg'in self.PktMethod.GetPacketType(TempPkt2[2]+1) and 'Response' in self.PktMethod.GetPacketType(TempPkt2[2]+2) and self.file_list[TempPkt2[2]+2]['pktType'] in ['ACK', 'NAK']:
                        Tresult = round((self.file_list[TempPkt2[2]+2]['startTime']-TempPkt1[1])*1000,3)
                        # print(f"{pkt['chk']}:", round((self.file_list[TempPkt2[2]+2]['startTime']-TempPkt1[1])*1000,3))
                        ChkRes = CommonMethods.check_measure(pkt['exp'],Tresult,pkt['comp'])
                        res.append([f"{self.file_list[TempPkt2[2]+2]['pktType']} response to {pkt['packet2'][0]} packet is received in: {ChkRes[3]} ms from 360kHz digital ping, Limit: {ChkRes[2]} ms", ChkRes[1]])
        return res

    def DisableASK(self,Flow_limit,Check):
        res = []
        #ensure the tinterval of Shutdown to previous ASK packet
        id = Flow_limit[1]-1
        while id > Flow_limit[0]:
            if self.PktMethod.GetPacketType(id)=="Packet":
                #calculate interval
                results = CommonMethods.check_measure(Check['expected_value'],round((self.file_list[Flow_limit[1]]['stopTime']-self.file_list[id]['startTime'])*1000,3),Check['comp'])
                res.append([f"Measured last ASK to shutdown interval is {results[3]}ms, expected value:{results[2]}ms",results[1]])     
                break
            id-=1
        return res

    def Repinged(self,Flow_limit,Check):
        res = []
        for pkt in Check['expected']:
            if 'PktLimit' in pkt:
                limit = self.PktMethod.GetLimits(pkt['PktLimit'],pkt,Flow_limit)
            else: limit = Flow_limit
            end = limit[1]

            TempPkt1 =  self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0],value=pkt['packet1'][2] if len(pkt['packet1']) == 3 else None,limit=[limit[0],end],Type=pkt['packet1'][1])
            # print("TempPkt1:",TempPkt1)
            if len(TempPkt1) > 2:
                fop = float(self.file_list[TempPkt1[2]]['value'].split(":")[1].split(" ")[0].strip())
                ChkRes = CommonMethods.check_measure(pkt['exp'],fop,pkt['comp'])
                res.append([f"{pkt['chkname'] if "chkname" in pkt else ""} {self.file_list[TempPkt1[2]]['value']} assertion with FOP {ChkRes[3]} kHz is found at {round(TempPkt1[0],3)} sec, Limit: {ChkRes[2]} kHz", ChkRes[1]])

                if "Phasechk" in pkt:
                    x = TempPkt1[2]
                    while x < end:
                        if self.file_list[x]['description'] == pkt['Phasechk']:
                            res.append([f'{pkt['Phasechk']} Phase started at {round(self.file_list[x]['startTime'],3)}sec after re-attach',Enums.TestResult.PASS])
                            break
                        x += 1
                    else: res.append([f'{pkt['Phasechk']} Phase not started after re-attach', Enums.TestResult.FAIL])
        return res

    def PacketPeak(self,Flow_limit,Check):
        res = []
        ept =self.PktMethod.GetPacketDetails(packet="End Power Transfer",value="EPT/rep",limit=Flow_limit,Type="Packet")
        if len(ept) > 2:
            res.append([f"End Power Transfer/rep packet found in 128kHz PT phase at {round(ept[0],3)} sec", Enums.TestResult.PASS])
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[ept[2],Flow_limit[1]+1],Type="TesterMsg")
            if len(sd) > 2:
                res.append([f"Shutdown packet found at {round(sd[0],3)} sec", Enums.TestResult.PASS])
                AllChannelData3 = self.PlotMethod.GetAllChannelData('3',self.JapiData)
                AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        
                if 'PktLimit' in Check:
                    tmplimit = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
                else: tmplimit = Flow_limit
                # print("tmplimit:",tmplimit)

                id = tmplimit[0]
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=Check['Packet1'][0],value=Check['Packet1'][1],limit=[id,tmplimit[1]],Type=Check['Packet1'][2])
                # print("TempPkt1:",TempPkt1)
                if len(TempPkt1)>2:
                    crx = self.PktMethod.GetPacketDetails(packet="CRx_Status",value="_174nF: 1",limit=[ept[2],TempPkt1[2]],Type="TesterMsg")
                    if len(crx) > 2:
                        res.append([f"CRX: 174 nF found at {round(crx[0],3)} sec", Enums.TestResult.PASS])
                    else: res.append([f"CRX: 174 nF not found from {round(ept[1],3)} sec to {round(TempPkt1[0],3)} sec", Enums.TestResult.FAIL])


                    sindex2 = int(((ept[1]*1000)+5)/AllChannelData3['Interval'])
                    eindex2 = int(((TempPkt1[0])*1000)/AllChannelData3['Interval'])
                    # cnt += 1

                    # # print("irects2:",irects2)
                    load_values = []
                    x = sindex2
                    while x <= eindex2:
                        if 50 > AllChannelData3['RV']['displayDataChunk'][x]*1000 >= 0:
                            # res.append([f"In ping_{cnt}, Irect: {round(AllChannelData3['RV']['displayDataChunk'][x]*1000,2)} mA is found at {self.PktMethod.ms_to_time(x*AllChannelData3['Interval'])}, Expected: {Check['Set_load']} mA", Enums.TestResult.PASS])
                            load_values.append(round(AllChannelData3['RV']['displayDataChunk'][x]*1000,3))
                        else:
                            res.append([f"Load current of {round(AllChannelData3['RV']['displayDataChunk'][x]*1000,3)} mA observed, Expected: 0 mA", Enums.TestResult.FAIL])
                            break
                        x += 1

                    irect_max = max(load_values)
                    if irect_max<50:
                        res.append([f"Maximum load current observed from shutdown to ping detected is {irect_max} mA, Expected: 0 mA", Enums.TestResult.PASS])
                    # else:
                    #     res.append([f"Maximum load current observed from shutdown to ping detected is {irect_max} mA, Expected: 0 mA", Enums.TestResult.FAIL])
                 




                    TempPkt2 = self.PktMethod.GetPacketDetails(packet=Check['Packet2'][0],value=Check['Packet2'][1],limit=[TempPkt1[2]+1,tmplimit[1]],Type=Check['Packet2'][2])
                    # print("TempPkt2:",TempPkt2)
                    if len(TempPkt2)>2:
                        sindex = int((TempPkt1[0]*1000)/AllChannelData['Interval'])
                        eindex = int((TempPkt2[1]*1000)/AllChannelData['Interval'])
                        id1 = sindex
                        Vrectpeak = 0
                        Tatpeak = 0
                        while id1 <= eindex:
                            value = round(abs(AllChannelData['RV']['displayDataChunk'][id1]),3)
                            # # print("value:",value,"id:",id)
                            if value > Vrectpeak:
                                Vrectpeak = value
                                Tatpeak = (id1*AllChannelData['Interval'])/1000  #sec
                            id1 += 1
                        # print("MaxValue:",Vrectpeak)
                        # print("Tatpeak:",Tatpeak)
                        results = CommonMethods.check_measure(Check['expected'],Vrectpeak,Check['comp'])
                        res.append([f"Found {Check['Packet1'][0]} packet at {round(TempPkt1[0],3)}sec with Vrect_peak {Vrectpeak}V measured at {round(Tatpeak,3)}sec, Limit :{results[2]}V ",results[1]])
                        #FOP
                        fop = self.PktMethod.GetPacketDetails(value='FOP:',limit=[id,tmplimit[1]],Type="TesterMsg")
                        if len(fop)>2:
                            fopres = CommonMethods.check_measure([359.46,360.54],float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]),0)
                            res.append([f"Found FOP: {fopres[3]}kHz packet at @{fop[2]}, Limit: {fopres[0]} kHz", fopres[1]])
                        else: res.append([f"FOP packet not found",Enums.TestResult.FAIL])
                    else: res.append([f"{Check['Packet2'][0]} packet not found",Enums.TestResult.INCONCLUSIVE])
                else: res.append([f"{Check['Packet1'][0]} packet not found",Enums.TestResult.FAIL])


            else:
                res.append([f"Shutdown packet not found", Enums.TestResult.FAIL])
        else:
            res.append([f"End Power Transfer/rep packet not found in 128kHz PT phase", Enums.TestResult.FAIL])




        # AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        
        # if 'PktLimit' in Check:
        #     tmplimit = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
        # else: tmplimit = Flow_limit
        # print("tmplimit:",tmplimit)

        # id = tmplimit[0]
        # TempPkt1 = self.PktMethod.GetPacketDetails(packet=Check['Packet1'][0],value=Check['Packet1'][1],limit=[id,tmplimit[1]],Type=Check['Packet1'][2])
        # print("TempPkt1:",TempPkt1)
        # if len(TempPkt1)>2:
        #     TempPkt2 = self.PktMethod.GetPacketDetails(packet=Check['Packet2'][0],value=Check['Packet2'][1],limit=[TempPkt1[2]+1,tmplimit[1]],Type=Check['Packet2'][2])
        #     print("TempPkt2:",TempPkt2)
        #     if len(TempPkt2)>2:
        #         sindex = int((TempPkt1[0]*1000)/AllChannelData['Interval'])
        #         eindex = int((TempPkt2[1]*1000)/AllChannelData['Interval'])
        #         id1 = sindex
        #         Vrectpeak = 0
        #         Tatpeak = 0
        #         while id1 <= eindex:
        #             value = round(abs(AllChannelData['RV']['displayDataChunk'][id1]),3)
        #             # # print("value:",value,"id:",id)
        #             if value > Vrectpeak:
        #                 Vrectpeak = value
        #                 Tatpeak = (id1*AllChannelData['Interval'])/1000  #sec
        #             id1 += 1
        #         # print("MaxValue:",Vrectpeak)
        #         # print("Tatpeak:",Tatpeak)
        #         results = CommonMethods.check_measure(Check['expected'],Vrectpeak,Check['comp'])
        #         res.append([f"Found {Check['Packet1'][0]} packet at {round(TempPkt1[0],3)}sec with Vrect_peak {Vrectpeak}V measured at {round(Tatpeak,3)}sec, Limit :{results[2]}V ",results[1]])
        #         #FOP
        #         fop = self.PktMethod.GetPacketDetails(value='FOP:',limit=[id,tmplimit[1]],Type="TesterMsg")
        #         if len(fop)>2:
        #             fopres = CommonMethods.check_measure([359.46,360.54],float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]),0)
        #             res.append([f"Found FOP: {fopres[3]}kHz packet at @{fop[2]}, Limit: {fopres[0]} kHz", fopres[1]])
        #         else: res.append([f"FOP packet not found",Enums.TestResult.FAIL])
        #     else: res.append([f"{Check['Packet2'][0]} packet not found",Enums.TestResult.INCONCLUSIVE])
        # else: res.append([f"{Check['Packet1'][0]} packet not found",Enums.TestResult.FAIL])
        return res
        
    def VrectPing360(self,Flow_limit,Check):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        #get vrect of 10cloak pings after 2nd flow
        cnt = 0
        if "PktLimit" in Check:
            tmplimit=self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
        else: tmplimit = Flow_limit
        
        id = tmplimit[0]
        # print("VrectPing128flow:",tmplimit)
        while id < tmplimit[1]:
            fop = self.PktMethod.GetPacketDetails(value='FOP:',limit=[id,tmplimit[1]],Type="TesterMsg")
            if len(fop)> 2:
                # # print("fop:",[fop[2],float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]),fop[0],fop[1]])
                fopres = CommonMethods.check_measure([359.46,360.54],float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]),0)
                # # print("fopres:",fopres)
                res.append([f"Found FOP: {fopres[3]}kHz packet at @{fop[2]}, Limit: {fopres[0]} kHz", fopres[1]])
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=Check['Packet'][0],value=Check['Packet'][1],limit=[id,tmplimit[1]],Type=Check['Packet'][2])
                if len(TempPkt1)>2:
                    cnt+=1
                    sigtime = (TempPkt1[0]*1000)-10
                    index = int((sigtime)/self.AllChannelData['Interval'])
                    Vrect  = round(abs(self.AllChannelData['RV']['displayDataChunk'][index]),3)
                    results = CommonMethods.check_measure(Check['expected'],Vrect,Check['comp'])
                    res.append([f"Found {Check['Packet'][0]} packet at {round(TempPkt1[0],3)}sec with Vrect {Vrect}V measured at {round(sigtime/1000,3)}sec, Limit :{results[2]}V ",results[1]])
                    id = TempPkt1[2]
                    if cnt == Check['PacketCount']:break
                # else:break
            id += 1
        if cnt==Check['PacketCount']:
            res.append([f"Received {cnt} {Check['Packet'][0]} amoung expected of {Check['PacketCount']}",Enums.TestResult.PASS])
        else:res.append([f"Received {cnt} {Check['Packet'][0]} amoung expected of {Check['PacketCount']}",Enums.TestResult.FAIL])
        return res

    def VrectPing128(self,Flow_limit,Check):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        #get vrect of 10cloak pings after 2nd flow
        cnt = 0
        if "PktLimit" in Check:
            tmplimit=self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
        else: tmplimit = Flow_limit
        
        id = tmplimit[0]
        # print("VrectPing128flow:",tmplimit)
        while id < tmplimit[1]:
            fop = self.PktMethod.GetPacketDetails(value='FOP:',limit=[id,tmplimit[1]],Type="TesterMsg")
            if len(fop)> 2:
                # # print("fop:",[fop[2],float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]),fop[0],fop[1]])
                fopres = CommonMethods.check_measure([127.5,128.5],float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]),0)
                # # print("fopres:",fopres)
                res.append([f"Found FOP: {fopres[3]}kHz packet at @{fop[2]}, Limit: {fopres[0]} kHz", fopres[1]])
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=Check['Packet'][0],value=Check['Packet'][1],limit=[id,tmplimit[1]],Type=Check['Packet'][2])
                if len(TempPkt1)>2:
                    cnt+=1
                    sigtime = (TempPkt1[0]*1000)-10
                    index = int((sigtime)/self.AllChannelData['Interval'])
                    Vrect  = round(abs(self.AllChannelData['RV']['displayDataChunk'][index]),3)
                    results = CommonMethods.check_measure(Check['expected'],Vrect,Check['comp'])
                    res.append([f"Found {Check['Packet'][0]} packet at {round(TempPkt1[0],3)}sec with Vrect {Vrect}V measured at {round(sigtime/1000,3)}sec, Limit :{results[2]}V ",results[1]])
                    id = TempPkt1[2]
                    if cnt == Check['PacketCount']:break
                # else:break
            id += 1
        if cnt==Check['PacketCount']:
            res.append([f"Received {cnt} {Check['Packet'][0]} amoung expected of {Check['PacketCount']}",Enums.TestResult.PASS])
        else:res.append([f"Received {cnt} {Check['Packet'][0]} amoung expected of {Check['PacketCount']}",Enums.TestResult.FAIL])
        return res
        

    def MatedQ_Coeff(self,Flow_limit,Check):
        res = []
        exe = self.PktMethod.GetPacketDetails(packet='Execution_count_no',limit = [0,len(self.file_list)-1],Type = "TesterMsg")
        if len(exe)>2:
            gf_values = []
            for templmt in [[exe[2],Flow_limit[0]],[Flow_limit[0],Flow_limit[1]+1]]:
                id = templmt[0]
                end = templmt[1]
                while id < end:
                    iden = self.PktMethod.GetPacketDetails(packet='Identification',limit=[id,end],Type = "Packet")
                    if len(iden)>2:
                        sd = self.PktMethod.GetPacketDetails(packet='Shutdown',limit=[iden[2]+1,end],Type = "TesterMsg")
                        if len(sd)>2:
                            MQ = self.PktMethod.GetPacketDetails(packet='MATEDQ-COEFF',limit=[iden[2],sd[2]],Type = "Packet")
                            if len(MQ)>2:
                                g0 = float(self.PktMethod.GetPayloadDetails(MQ[2],"g0")[0]['sDescription'].split(":")[-1]) 
                                FO =  self.PktMethod.GetPacketDetails(packet='MATEDQ_RES',limit=[MQ[2],sd[2]],Type = "Response")
                                if len(FO)>2:
                                    FO_value = self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(FO[2],"Foreign_Object")[0]['sRawData'])
                                    gf_values.append([g0,MQ[2],FO_value,FO[2]])

                            id = sd[2]+1
                    id += 1
            
            # print("gf_values:",gf_values)
            if len(gf_values) > 0:
                for i,val in enumerate(gf_values):
                    res.append([f"Measured MatedQ_Coeff values g0: {val[0]}, g1: {round(val[0]-0.1,3)} in MATEDQ-COEFF packet at index@{val[1]}", Enums.TestResult.PASS])                                       
                    results = CommonMethods.check_measure([2],val[2],"EQL" if i >= len(gf_values)-2 else "NEQ")
                    res.append([f"Foreign_Object: {results[3]} found in MATEDQ_RES response at index@{val[3]}, Expected: {results[2]}", results[1]])
                if gf_values[-2][0] == gf_values[-1][0]:
                    res.append([f"TPR used most recent measurement of g0: {gf_values[-1][0]}, Expected: g0: {gf_values[-2][0]}", Enums.TestResult.PASS])
                else: res.append([f"TPR not used most recent measurement of g0: {gf_values[-1][0]}, Expected: g0: {gf_values[-2][0]}", Enums.TestResult.FAIL])
            else: res.append([f"MatedQ_Coeff not found", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"Execution_count_no not found", Enums.TestResult.FAIL])
        return res

    def FOPresent(self,Flow_limit,Check):
        res = []
        limit = Flow_limit
        id1 = limit[0]

        UA = self.PktMethod.GetPacketDetails(packet='User Action status',limit=[id1,limit[1]],Type = "TesterMsg")
        if len(UA)> 2:
            # print("UA ID:",UA[2])
            end1 = UA[2]
        else: end1 = limit[1]

        respid = 0
        nakcnt = 0
        while id1 < end1: 
            PLA = self.PktMethod.GetPacketDetails(packet='PLA_2',limit=[id1,end1])
            # # print("PLA:",PLA)
            if len(PLA)> 2:
                respid = self.PktMethod.GetPacketResponse2(PLA[2],[PLA[2]+1,limit[1]])
                # # print("respid:",respid)
                if respid is not None:
                    if self.file_list[respid]['pktType'] == "NAK":  
                        nakcnt += 1
                        res.append([f"NAK response received for PLA_2 packet at {round(PLA[0],3)} sec", Enums.TestResult.PASS])
                        # print("NAK ID:",respid)
                        res.append([f"NAK received for PLA_2 packet before RFO inserting at {self.PktMethod.Timeconvert(self.file_list[respid]['startTime'])}", Enums.TestResult.INCONCLUSIVE])
                        break
                id1 = PLA[2]
            id1 += 1

        if nakcnt == 0:
            res.append([f"NAK not received for PLA_2 packet before RFO inserting", Enums.TestResult.PASS])
        else: res.append([f"{nakcnt} NAK's received for PLA_2 packet before RFO inserting", Enums.TestResult.FAIL])


        # After inserting RFO
        if len(UA)> 2:
            res.append([f'RFO insertion started from {round(UA[0],3)} sec', Enums.TestResult.PASS])
            self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
            self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
            id = UA[2]
            Consecutive_NAK_cnt = 0
            throttle_cnt = 0
            print("new limit:",id,limit[1])
            # Vrect_drop_data = []
            t_start = 0
            max_drop_PLA = 0
            v1x = 0
            v2x = 0
            max_drop = 0
            tx = 0
            last_NAK = 0
            while id < limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,limit[1]])
                # print("TempPkt2:",TempPkt2)
                if len(TempPkt2)>2:
                    Pktresp = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,limit[1]])
                    # if Pktresp is not None:
                    #     res.append([f"{self.file_list[Pktresp]['pktType']} response received to PLA_2 packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                        
 
                    # PLA response
                    x = TempPkt2[2]+1
                    if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                        x += 1
            
                    # Throttle check
                    if 'NAK' in self.file_list[x]['pktType']:
                        # print("NAK:",x)
                        last_NAK = x
                        Consecutive_NAK_cnt += 1
                        nak_chk = True
                        vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                        irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                        Prect1 = vrect1*irect1

                        vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                        irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],self.AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                        Prect2 = vrect2*irect2

                        pwr_diff = round((Prect2-Prect1)*1000,3)
                        
                        
                        if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                            # last_NAK = x
                            throttle_cnt += 1
                            if throttle_cnt == 1:
                                t_start = TempPkt2[0]
                            res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA_2 packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                        else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA_2 packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])

                        if Consecutive_NAK_cnt >= 2:
                            # print("vrect1:",vrect1)
                            # print("vrect2:",vrect2)
                            # print("Vrect drop1:",abs(vrect1-vrect2))

                            # During throttling check for vrect drop
                            if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                index1 = int((((TempPkt2[1]*1000)+19))/self.AllChannelData['Interval'])
                                v1 = self.AllChannelData['RV']['displayDataChunk'][index1]
                                index2 = int((((TempPkt2[1]*1000)+40))/self.AllChannelData['Interval'])
                                v2 = self.AllChannelData['RV']['displayDataChunk'][index2]

                                # print("Vrect(end+19):",v1)
                                # print("Vrect(end+40):",v2)
                                # print("Vrect drop:",abs(v2-v1))
                                if abs(v2-v1) > max_drop or max_drop == 0:
                                    v1x = v1
                                    v2x = v2
                                    max_drop = abs(v2-v1)
                                    tx = TempPkt2[1]*1000
                                    max_drop_PLA = TempPkt2[2]
                    else:
                        Consecutive_NAK_cnt = 0
                    
                    id = TempPkt2[2]
                else:
                    # res.append([f"Removed the applied POFFSET from {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS]) 
                    break
                id += 1

            # print("v1x:",v1x,"v2x:",v2x,"max_drop:",max_drop,"tx:",tx,"t1:",(tx+19)/1000,"t2:",(tx+40)/1000)
            # print("throttle_cnt:",throttle_cnt)
            if max_drop < 1:
                res.append([f"During PTx-DUT power throttling, Maximum Vrect drop: {round(max_drop,3)} V found at PLA @index {max_drop_PLA}, with the following measurements:, Limit: Vrect drop < 1V", Enums.TestResult.PASS]) 
            else: 
                res.append([f"During PTx-DUT power throttling, Maximum Vrect drop: {round(max_drop,3)} V found at PLA @index {max_drop_PLA}, with the following measurements:, Limit: Vrect drop < 1V", Enums.TestResult.FAIL])
            res.append([f"Vrect_1 :{round(v1x,3)}V measured at {(tx+19)/1000}s , Vrect_2 :{round(v2x,3)}V measured at {(tx+40)/1000}s", Enums.TestResult.PASS])
            res.append([f"PLA_2 packets count where PTx throttled: {throttle_cnt}", Enums.TestResult.PASS])

            #Check for execution time from Throttling # min 1 min
            t_diff = self.file_list[Flow_limit[1]]['startTime'] - t_start
            print("t_diff:",t_diff)
            if t_diff >= 60:
                res.append([f"Testing continued for more than 1 min from the point of stopping RFO movement.",Enums.TestResult.PASS])

            elif t_diff < 60:
                atn = self.PktMethod.GetPacketDetails(packet="ATN",limit=[last_NAK,limit[1]],Type="Response")
                if len(atn) > 2:
                    res.append([f"PTx sent ATN packet after power throttling at {round(atn[0],3)} sec", Enums.TestResult.PASS])
                    reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[atn[2],limit[1]])
                    if len(reneg) > 2:
                        res.append([f"TPR sent Renegotiate packet after power throttling at {round(reneg[0],3)} sec", Enums.TestResult.PASS])
                        respid = self.PktMethod.GetPacketResponse2(reneg[2],[reneg[2]+1,limit[1]])
                        if respid is not None:
                            if 'ACK' in self.file_list[respid]['pktType']:
                                res.append([f"PTx sent ACK response to Renegotiate packet after power throttling at {round(self.file_list[respid]['startTime'],3)} sec", Enums.TestResult.PASS])
                            else:
                                res.append([f"PTx not sent ACK response to Renegotiate packet after power throttling at {round(self.file_list[respid]['startTime'],3)} sec", Enums.TestResult.FAIL])
                        else:
                            res.append([f"No response received for Renegotiate packet after power throttling", Enums.TestResult.FAIL])
                    else:
                        res.append([f"PTx not sent Renegotiate packet after power throttling", Enums.TestResult.FAIL])
                else:
                    res.append([f"PTx not initiated renegotiation with ATN after power throttling", Enums.TestResult.FAIL])
            else: 
                res.append([f"Testing continued for more than 1 min from the point of stopping RFO movement and PTx not initiated renegotiation with ATN after power throttling", Enums.TestResult.FAIL])

            if last_NAK != 0:
                id2 = last_NAK
                while id2 < limit[1]:
                    safe_pla = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id2,limit[1]])
                    if len(safe_pla) > 2:
                        respid2 = self.PktMethod.GetPacketResponse2(safe_pla[2],[safe_pla[2]+1,limit[1]])
                        if respid2 is not None:
                            if "ACK" in self.file_list[respid2]['pktType']:
                                res.append([f"PTx-DUT sends NAKs to PLA_2 until a new stable power level is reached, then sends an ACK at {round(safe_pla[0],3)} sec", Enums.TestResult.PASS])
                                break
                        else:
                            res.append([f"No response received for PLA_2 at {round(safe_pla[0],3)} sec", Enums.TestResult.FAIL])
                        id2 = safe_pla[2]
                    else:
                        res.append([f"Stable power is not reached.", Enums.TestResult.FAIL])
                    id2 += 1
                else: 
                    res.append([f"ACK is not received to PLA_2 after renegotiation", Enums.TestResult.FAIL])
            else:
                res.append([f"No NAK Response received to PLA_2 packets while inserting RFO", Enums.TestResult.FAIL])

        return res

    def PowerModes_Advertised(self,Flow_limit,Check):
        res = []
        # MODECAP
        ECAP = {"LPM":"","NPM":"","HPM":"","CPM":""}
        Ecapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Capabilities",limit=Flow_limit,Type="Packet")
        if len(Ecapreq)> 2:
            res.append([f"Get Request-PTx Power Modes Capabilities Packet found at {round(Ecapreq[0],3)} sec", Enums.TestResult.PASS])
            Ecapres = self.PktMethod.GetPacketDetails(packet="MODECAP",value="Active Main Mode:",limit=[Ecapreq[2],Flow_limit[1]],Type="Response")
            if len(Ecapres)> 2:
                res.append([f"MODECAP {self.file_list[Ecapres[2]]['value']} Packet found at {round(Ecapres[0],3)} sec", Enums.TestResult.PASS])
                
                for ck in ECAP.keys():
                    payloadDetails = self.PktMethod.GetPayloadDetails(Ecapres[2],ck)
                    # print(ck,":",self.PktMethod.hex_to_decimal(payloadDetails[0]['sRawData']))
                    ECAP[ck] = self.PktMethod.hex_to_decimal(payloadDetails[0]['sRawData'])
                # print("ECAP:",ECAP)
                res.append([f"ECAP values: {ECAP}", Enums.TestResult.PASS])
            else: res.append([f"MODECAP Packet not found", Enums.TestResult.FAIL])
        else: res.append([f"Get Request-PTx Power Modes Capabilities Packet not found", Enums.TestResult.FAIL])

        EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
        Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
        if len(Excapres)> 2:
            for ck in EXCAP.keys():
                payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                # print(ck,":",payloadDetails[0]['sDescription'].split(":")[-1], float(payloadDetails[0]['sDescription'].split(":")[-1].strip("W")))
                EXCAP[ck] = payloadDetails[0]['sDescription'].split(":")[-1]
        
        if ECAP["NPM"] == 1:
            res.append([f"NPM is supported in MODECAP packet at {round(Excapres[0],3)} sec", Enums.TestResult.PASS])
            res.append([f"Potential load power of NPM: {EXCAP['Nominal_Power_Mode']} in MODEXCAP packet at {round(Excapres[0],3)} sec", Enums.TestResult.PASS])
        else: res.append([f"NPM is not supported", Enums.TestResult.PASS])

        if ECAP["HPM"] == 1:
            res.append([f"HPM is supported in MODECAP packet at {round(Excapres[0],3)} sec", Enums.TestResult.PASS])
            res.append([f"MODEXCAP[NPM Potential Load Power] is {EXCAP['Nominal_Power_Mode']} in MODEXCAP packet at {round(Excapres[0],3)} sec, Expected: >= 15W", Enums.TestResult.PASS if float(EXCAP['Nominal_Power_Mode'].strip("W")) >= 15 else Enums.TestResult.FAIL])
        else: res.append([f"HPM is not supported", Enums.TestResult.PASS])
        return res

    def PowerModes(self,Flow_limit,Check):
        res = []
        TempLimit = Flow_limit
        cnt = 0
        for chk in Check["expected"]:
            pkt = self.PktMethod.GetPacketDetails(packet="MODECAP",value="Active Main Mode",limit=TempLimit,Type="Response")
            if len(pkt)>2:
                APM = self.PktMethod.GetPayloadDetails(pkt[2],"Active_Main_Mode")[0]['sDescription'].split(":")[1].strip()
                ChkRes1 = CommonMethods.check_measure(chk['Pmode'],APM,chk['comp'])
                res.append([f"PowerMode_{cnt} in MODECAP[Active Main Mode] is {ChkRes1[3]} found at {round(pkt[0],3)} Sec, Expected: {ChkRes1[2]}", ChkRes1[1]])

                TempLimit = [len(self.file_list)-1,Flow_limit[1]]
                cnt += 1
            else: res.append([f"MODECAP not found in 360 kHz flow",  Enums.TestResult.FAIL])
        return res

    def Vrect_Irect(self,Flow_limit,Check):
        res = []
        TempLimit = Flow_limit
        for prect in Check['expected']:
            load = 0
            if prect.get("LoadPercent"):
                if prect["LoadPercent"] != "NA":
                    negload_pkt = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
                    if len(negload_pkt) > 2:
                        # print("nego:",self.PktMethod.GetPayloadDetails(negload_pkt[2],"Negotiable_Load_Power"))
                        negload = float(self.PktMethod.GetPayloadDetails(negload_pkt[2],"Negotiable_Load_Power")[0]['sDescription'].split("Negotiable Load Power value:")[1].split("W")[0].strip())
                        # print("negload:",negload)
                        res.append([f"Negotiable_Load_Power: {negload}W is observed in {self.ECAP_pkt} packet at index @{negload_pkt[2]}", "pass"])
                        load = int(prect["LoadPercent"]*0.01*negload*1000) #mW
                else: load = 50 #Minimum load 600mW

            elif prect.get("ECAP"):
                limit2 = [Flow_limit[1],Flow_limit[0]]
                if "ECAPLimit" in prect:
                    limit2 = self.PktMethod.GetLimits(prect['ECAPLimit'],prect,Flow_limit)
                else: limit2 = [Flow_limit[1],Flow_limit[0]]
                print("ECAPLimit:",limit2)
                ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=limit2,Type="Response")
                if len(ECAP) > 2:
                    # print("Load_pwr:",self.PktMethod.GetPayloadDetails(ECAP[2],prect["ECAP"]))
                    Load_pwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],prect["ECAP"])[0]['sDescription'].split(":")[1].split("W")[0].strip())
                    # print("Load_pwr:",Load_pwr)
                    res.append([f"{prect["ECAP"]}: {Load_pwr}W is observed in {self.ECAP_pkt} packet at index @{ECAP[2]}", "pass"])
                    load = int(Load_pwr*1000) #mW
            else: load = int(prect[prect['setting']]['set'])


            if prect.get("PktLimit"):
                TempLimit = self.PktMethod.GetLimits(prect['PktLimit'],prect,Flow_limit)
            else: TempLimit = Flow_limit
                            
            # load = int(prect[prect['setting']]['set'])
            TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {load}",limit=TempLimit,Type="TesterMsg")
            # print("TempPkt2:",TempPkt2)
            if len(TempPkt2)>2:
                # res.append([f"Found set load {load}{"mW" if prect['setting'] == "Prect" else "mA"} packet at {round(TempPkt2[0],3)}Sec",Enums.TestResult.PASS])
                if prect.get("LoadPercent"):
                    if prect["LoadPercent"] != "NA":
                        res.append([f"{prect["LoadPercent"]}% of Negotiable load: {load} mW is applied in {self.file_list[TempPkt2[2]].get('pktType')} packet at index @{TempPkt2[2]}", Enums.TestResult.PASS])
                    else: res.append([f"Minimum load: {load} mA is applied in {self.file_list[TempPkt2[2]].get('pktType')} packet at index @{TempPkt2[2]}", Enums.TestResult.PASS])
                else: res.append([f"{self.file_list[TempPkt2[2]].get('pktType')} packet is found at index @{TempPkt2[2]}", "pass"])
                
                #find the stabilization
                if prect.get("XCE_Stabilisation"):
                    id = TempPkt2[2]
                    sta_cnt = 0
                    while id < TempLimit[1]:
                        if self.file_list[id].get('pktType') == "Extended Control Error":
                            if self.file_list[id].get("value") in ["-1","0","+1"]:
                                sta_cnt += 1
                            else:
                                sta_cnt = 0
                            if sta_cnt >= 5:
                                TempPkt3 = [self.file_list[id]['startTime'],self.file_list[id]['stopTime'],id]
                                break
                        id += 1
                else:
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Flow_limit[1]],Type="TesterMsg")
                # print("TempPkt3:",TempPkt3)
                if len(TempPkt3)>2:
                    
                    if prect.get("XCE_Stabilisation"):
                        res.append([f"Target load reduced at {self.PktMethod.Timeconvert(TempPkt3[0])}",Enums.TestResult.PASS])
                        TempPkt4 = TempPkt3.copy()
                    else:
                        res.append([f"Stabilization found at {self.PktMethod.Timeconvert(TempPkt3[0])}",Enums.TestResult.PASS])
                        #Get Prect from PLA
                        # TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2]-15,Flow_limit[1]])
                        TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2],Flow_limit[1]])
                    # print("TempPkt4:",TempPkt4)
                    if len(TempPkt4)>2:
                        if prect.get("XCE_Stabilisation"):
                            AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
                            AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
                            Vrect = self.PktMethod.CalculateVoltTwindow(TempPkt4[2], AllChannelData)[0]
                            Irect = self.PktMethod.CalculateVoltTwindow(TempPkt4[2], AllChannelData3)[0]
                            Pwr = round(Vrect*Irect,3)
                        else:
                            Pwr = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                            Vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"VRECT")[0]['sDescription'])[0]
                            Irect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"IRECT")[0]['sDescription'])[0]

                        if prect.get("LoadPercent"):
                            if prect.get("LoadPercent") and prect["LoadPercent"] != "NA":
                                ChkRes4 = CommonMethods.check_measure([(load-100)/1000],Pwr,"GTEQL")
                                res.append([f"Measured Prect is {Pwr} W, Limit: {ChkRes4[2]} W, Vrect is: {Vrect} V, Irect: {Irect} A", ChkRes4[1]])
                            elif prect.get("LoadPercent") and prect["LoadPercent"] == "NA":
                                ChkRes4 = CommonMethods.check_measure([(abs(load-100)/1000)-0.001],Irect,"GTEQL")
                                # print("ChkRes4:",ChkRes4)
                                res.append([f"Measured Irect is {Irect} A, Limit: {ChkRes4[2]} A, Vrect is: {Vrect} V, Prect: {Pwr} W", ChkRes4[1]])
                        elif prect.get("ECAP"):
                            ChkRes5 = CommonMethods.check_measure(prect['exp'] if prect.get("exp") else [(load-100)/1000],Pwr,"GTEQL")
                            res.append([f"Measured Prect is {Pwr} W, Vrect is: {Vrect} V, Irect: {Irect} A, Limit: Prect: {ChkRes5[2]} W,", ChkRes5[1]])
                        else:
                            if prect.get('irect'):
                                ChkRes1 = CommonMethods.check_measure(prect['irect']['exp'],Irect,prect['irect']['comp'])
                                if prect['setting'] == "irect":
                                    res.append([f"Measured Irect is {ChkRes1[3]} A at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {ChkRes1[2]} A", ChkRes1[1]])
                                else: res.append([f"Measured Irect is {ChkRes1[3]} A at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                            else: res.append([f"Measured Irect is {Irect} A at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                            if prect.get('vrect'):   
                                ChkRes2 = CommonMethods.check_measure(prect['vrect']['exp'],Vrect,prect['vrect']['comp'])
                                # print("ChkRes2:",ChkRes2)
                                res.append([f"Measured Vrect is {ChkRes2[3]} V at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {ChkRes2[2]} V", ChkRes2[1]])
                            else: res.append([f"Measured Vrect is {Vrect} V at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                            if prect.get('Prect'):
                                ChkRes3 = CommonMethods.check_measure(prect['Prect']['exp'],Pwr,prect['Prect']['comp'])
                                # print("ChkRes3:",ChkRes3)
                                res.append([f"Measured Prect is {ChkRes3[3]} W at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {ChkRes3[2]} W", ChkRes3[1]])  
                            else: res.append([f"Measured Prect is {Pwr} W at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                    else:res.append([f"PLA packet not found between {round(TempPkt3[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                else:res.append([f"Stabilization is not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.INCONCLUSIVE])
                TempLimit=[TempPkt2[2]+1,Flow_limit[1]]
            # else:res.append([f"Set load {prect['Load']}mA packet not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
            else:
                if prect.get("LoadPercent") and prect["LoadPercent"] != "NA":
                    res.append([f"{prect["LoadPercent"]}% of Negotiable load is not applied", Enums.TestResult.FAIL])
                else: res.append([f"Set_Load {load}mW packet not found", Enums.TestResult.INCONCLUSIVE])
        return res
            
    def Load_Ramp(self,Flow_limit,Check):
        res = []
        TempLimit = Flow_limit
        for prect in Check['expected']:
            load = int(prect[prect['setting']]['set'])
            TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {load}",limit=TempLimit,Type="TesterMsg")
            # print("TempPkt2:",TempPkt2)
            if len(TempPkt2)>2:
                res.append([f"Set_Load {load}mA packet found at {self.PktMethod.Timeconvert(TempPkt2[0])}", Enums.TestResult.PASS])
                ts = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[TempPkt2[2],len(self.file_list)],Type="TesterMsg")
                # print("ts:",ts)
                if len(ts)>2:
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],TempLimit[1]],Type="TesterMsg")
                    if len(TempPkt3)>2:
                        TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2]-15,TempLimit[1]])
                        if len(TempPkt4)>2:
                            Pwr = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                            Vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"VRECT")[0]['sDescription'])[0]
                            Irect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"IRECT")[0]['sDescription'])[0]

                            if prect.get('irect'):
                                ChkRes1 = CommonMethods.check_measure(prect['irect']['exp'],Irect,prect['irect']['comp'])
                                if prect['setting'] == "irect":
                                    res.append([f"Measured Irect is {ChkRes1[3]} A at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {ChkRes1[2]} A", ChkRes1[1]])
                                else: res.append([f"Measured Irect is {ChkRes1[3]} A at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                            else: res.append([f"Measured Irect is {Irect} A at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                            if prect.get('vrect'):   
                                ChkRes2 = CommonMethods.check_measure(prect['vrect']['exp'],Vrect,prect['vrect']['comp'])
                                # print("ChkRes2:",ChkRes2)
                                res.append([f"Measured Vrect is {ChkRes2[3]} V at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {ChkRes2[2]} V", ChkRes2[1]])
                            else: res.append([f"Measured Vrect is {Vrect} V at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                            if prect.get('Prect'):
                                ChkRes3 = CommonMethods.check_measure(prect['Prect']['exp'],Pwr,prect['Prect']['comp'])
                                # print("ChkRes3:",ChkRes3)
                                res.append([f"Measured Prect is {ChkRes3[3]} W at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {ChkRes3[2]} W", ChkRes3[1]])  
                            else: res.append([f"Measured Prect is {Pwr} W at {self.PktMethod.Timeconvert(TempPkt4[0])}", Enums.TestResult.PASS])
                        else: res.append([f"PLA_2 packet not found", Enums.TestResult.FAIL])


                    else:
                        sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[TempPkt2[2],ts[2]],Type="TesterMsg")
                        if len(sd)>2:
                            res.append([f"Power signal Removed before applying complete load{load}mA.", Enums.TestResult.PASS])
                        else: 
                            res.append([f"MPP_XCEV_Ideal not found for {load}mA", Enums.TestResult.FAIL])
                       
                    

                else:res.append([f"Test stop signal not found", Enums.TestResult.FAIL])
            else:res.append([f"Set load {load}mA packet not found", Enums.TestResult.FAIL])
        return res

                
        

    def CalibThrottle(self,Flow_limit,Check):
        res = []

        id = Flow_limit[0]
        offset = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=Flow_limit,Type="TesterMsg")
        if len(offset)>2:
            AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
            AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)

            end = offset[2]
            CAL_CAP_cnt = 0
            while id <= end:
                CAL_CAP = self.PktMethod.GetPacketDetails(packet="CAL_CAPTURE",limit=[id,end],Type="Packet")
                if len(CAL_CAP)>2:
                    CAL_CAP_cnt += 1
                    # res.append([f"CAL_CAPTURE_{CAL_CAP_cnt} packet found at {self.PktMethod.Timeconvert(CAL_CAP[0])} ", Enums.TestResult.PASS])
                    id = CAL_CAP[2]
                id += 1

            if CAL_CAP_cnt >= 10:
                res.append([f"Offset applied after {CAL_CAP_cnt}th CAL_CAPTURE packet at {self.PktMethod.Timeconvert(offset[0])}, Expected: After 10th CAL_CAPTURE", Enums.TestResult.PASS])
            else: res.append([f"Offset applied after {CAL_CAP_cnt} CAL_CAPTURE packet at {self.PktMethod.Timeconvert(offset[0])}, Expected: After 10th CAL_CAPTURE", Enums.TestResult.FAIL])

            # DUAL OFFSET APPLY
            id = offset[2]
            packetCount = 0
            throttle_cnt = 0
            nothrottle_cnt = 0
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    # # print("TempPkt2:",TempPkt2)
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    
                    if len(TempPkt3)>2 and len(TempPkt4)>2:
                        packetCount+=1

                        Rectified = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['pktType'])[0]
                        Received = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['pktType'])[1]
                        
                        Prect_Offset =  GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['value'])[0]
                        RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['value'])[1]
                        
                        
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"PRECT")[0]['sDescription'])[0]
                        RP = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'])[0]

                        # print("Rectified:",Rectified,"Received:",Received,"RP_Offset:","Prect_Offset:",Prect_Offset,RP_Offset,"Prect:",Prect,"RP:",RP)

                        # check for offset value are applied as like mentioned in the CTS
                        if 'FixedOffsetValues' in Check:
                            # # print("FixedOffsetValues:",RP_Offset,Prect_Offset)
                            if RP_Offset!=Check['FixedOffsetValues']['RP'] or Prect_Offset!=Check['FixedOffsetValues']['Prect']:
                                    res.append([f"PLA offset issue at {round(TempPkt2[0],3)}: RP Offset:{RP_Offset}W Expected :{Check['FixedOffsetValues']['RP']}, Prect Offset:{Prect_Offset}W Expected :{Check['FixedOffsetValues']['Prect']}W",Enums.TestResult.FAIL])
                        # Ensure that the offset calculations are correct
                        PLARes = Enums.TestResult.PASS if Prect == round((Rectified-Prect_Offset),3) and RP == round((Received-RP_Offset),3) else Enums.TestResult.FAIL
                        if PLARes==Enums.TestResult.FAIL: res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect}W and RP={RP}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Rectified = {Rectified}W and Received={Received}W",PLARes])
                        else: res.append([f"PLA Power Calculation at {round(TempPkt2[0],3)}sec RP: {RP} W and Prect: {Prect} W in PLA_2 is matching with Received: {Received} W and Rectified: {Rectified} W after appling RP_Offset: {RP_Offset} W and Prect_Offset: {Prect_Offset} W offsets respectively",PLARes])
                        # # print("PLARes:",PLARes)

                        # PLA response
                        x = TempPkt2[2]+1
                        if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                            x += 1
                        if 'Response' in self.PktMethod.GetPacketType(x):
                            res.append([f"{self.file_list[x]['pktType']} response received for PLA packet", Enums.TestResult.PASS])
                                
                        # Throttle check
                        if 'NAK' in self.file_list[x]['pktType']:
                            vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                            irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                            Prect1 = vrect1*irect1

                            vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                            irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                            Prect2 = vrect2*irect2
                            
                            if (Prect2-Prect1)*1000 <= 50:    #P2-P1 <= 50mW --> Throttle
                                throttle_cnt += 1
                                res.append([f"PTx throttled while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                            else:
                                nothrottle_cnt += 1
                                res.append([f"PTx not throttled while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.FAIL])
                    id = TempPkt2[2]+1
                else:break
            # print("throttle_cnt:",throttle_cnt)

            if packetCount == 0: 
                res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
            else: res.append([f"Received {packetCount} PLA_2 Packets with offset value between {round(offset[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.PASS])
            if nothrottle_cnt == 0 and throttle_cnt > 0:
                res.append([f"PTx Throttled at all {throttle_cnt} PLA_2 packets",Enums.TestResult.PASS])
            else: res.append([f"PTx Throttled at {throttle_cnt} and not throttled at {nothrottle_cnt} PLA_2 packets",Enums.TestResult.FAIL])

            # Power remove
            sd = self.PktMethod.GetPacketDetails(packet='Test_Status',value="Test_Stop",limit=[len(self.file_list)-1,Flow_limit[0]],Type="TesterMsg")
            if len(sd)> 2:
                res.append([f"PTx removed power at {self.PktMethod.Timeconvert(sd[0])}", Enums.TestResult.PASS])
            else: res.append([f"PTx does not removed power", Enums.TestResult.FAIL])

        else: res.append([f"Offset not applied", Enums.TestResult.FAIL])
        return res
        

    def Cloak(self,Flow_limit,Check):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        end = len(self.file_list)
        ss =  self.PktMethod.GetPacketDetails(packet="Signal strength",limit=Flow_limit,Type="Packet")
        if len(ss) > 2:

            if "DPL" in Check["expected"][0]["chks"]:
                dpl = round(self.PktMethod.CalculateVoltTwindow(ss[2],self.AllChannelData,winsize=[9,11])[0],3)
                # print("dpl(v):",dpl)
                dpl_lmt = [(dpl-(dpl/20)),(dpl+(dpl/20))]  #+-5%
                # print("dpl_lmt:",dpl_lmt)
                res.append([f"Measured DPL voltage is: {dpl} V", Enums.TestResult.PASS])

            #Cloak enter
            clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[ss[2],Flow_limit[1]],Type="Packet")
            if len(clk_ping) > 2:
                reason =self.PktMethod.GetPayloadDetails(clk_ping[2],'Reason')[0]["sDescription"].split(":")[-1]
                rsn_chk =  CommonMethods.check_measure(Check["expected"][0]["clk_reason"],reason,"EQL")
                # print("reason:",rsn_chk)
                clk_resp = self.file_list[clk_ping[2]+1].get('pktType')
                res.append([f"Cloak enter found with reason:{reason} at {round(clk_ping[0],3)} sec and received {self.file_list[clk_ping[2]+1].get('pktType')}", rsn_chk[1]])
                id = clk_start = clk_ping[2]+1  
                cnt = 1
                # Next 5 cloak pings
                while id < end:
                    if "Timing" in Check["expected"][0]["chks"]:
                        # Tterminate between cloak response and shutdown
                        sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[clk_ping[2],end],Type="TesterMsg")
                        if len(sd) > 2:
                            # print("Tterminate(ms):",round((sd[0]-self.file_list[clk_ping[2]+1].get('stopTime'))*1000,3), [clk_ping[2]+1,sd[2]])
                            Tterm = round((sd[0]-self.file_list[clk_ping[2]+1].get('stopTime'))*1000,3)
                            ChkRes1 = CommonMethods.check_measure([28],Tterm,"LTEQL")
                            res.append([f"Measured Tterminate {cnt} at {round(self.file_list[clk_ping[2]+1].get('stopTime'),3)} Sec is: {ChkRes1[3]} ms, Limit: [{ChkRes1[2]}] ms", ChkRes1[1]])
            
                        pd = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[sd[2],end],Type="TesterMsg")
                        if len(pd) > 2:
                            # print("Tcloak:", round((self.file_list[pd[2]].get('startTime')-self.file_list[clk_ping[2]+1].get('stopTime'))*1000,3),[clk_ping[2]+1,pd[2]] )
                            Tcloak = round((self.file_list[pd[2]].get('startTime')-self.file_list[clk_ping[2]+1].get('stopTime'))*1000,3)
                            ChkRes2 = CommonMethods.check_measure([475,525],Tcloak,"GTEQL")
                            res.append([f"Measured Tcloak {cnt} at {round(self.file_list[clk_ping[2]+1].get('stopTime'),3)} sec is: {ChkRes2[3]} ms, Limit: [{ChkRes2[2]}] ms", ChkRes2[1]])
                    # Cloak ping
                    clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[id,end],Type="Packet")
                    if len(clk_ping) > 2:
                        reason =self.PktMethod.GetPayloadDetails(clk_ping[2],'Reason')[0]["sDescription"].split(":")[-1]
                        rsn_chk =  CommonMethods.check_measure(Check["expected"][0]["clk_reason"],reason,"EQL")
                        clk_resp = self.file_list[clk_ping[2]+1].get('pktType')
                        if "ACK" in clk_resp:
                            res.append([f"Cloak Ping {cnt} found with reason:{reason} at {round(clk_ping[0],3)} sec and received {self.file_list[clk_ping[2]+1].get('pktType')}", rsn_chk[1]])
                            cpl = round(self.PktMethod.CalculateVoltTwindow(clk_ping[2],self.AllChannelData,winsize=[9,11])[0],3)
                            # print("cpl:",cpl)

                            if "Timing" in Check["expected"][0]["chks"]:
                                ChkRes3 = CommonMethods.check_measure(dpl_lmt,cpl,0)
                                # print("ChkRes:",ChkRes3)
                                res.append([f"Measured CPL voltage in Cloak sequence {cnt} is: {ChkRes3[3]} V, Limit: [{ChkRes3[2]}] V", ChkRes3[1]])

                            if cnt == 5: break
                            id = clk_ping[2]
                            cnt += 1
                    id += 1
        return res

    def SGC_Check(self,Flow_limit,Check):
        res = []
        MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=[Flow_limit[1],Flow_limit[0]],Type="Packet")
        if len(MSRreq2)> 2:
            Mode_type = self.file_list[MSRreq2[2]]['value'].split(":")[-1].strip(" }")
            if Mode_type != "LPM":
                ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
                if len(ECAP)>2:
                    ECAPppwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Potential_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                    # print("ECAPppwr:",ECAPppwr)
                    res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt} at {round(ECAP[0],3)} sec", Enums.TestResult.PASS])
                    if ECAPppwr >= 15:
                        res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt}, so DPLOSS calibration will perform, Expected: >= 15 W", Enums.TestResult.PASS])
                        tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                        if Mode_type == "NPM":
                            tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","skiplevel": ["Level4"],"flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                        dploss_res=self.DPlossCalibration(Flow_limit,tempcheck)
                        for tempres in dploss_res: res.append(tempres)
                    else: res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt}, so DPLOSS calibration won't perform, Expected: >= 15 W", Enums.TestResult.PASS])





                    # Nego = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'])[0]
                    # # print("Nego:",Nego)
                    # if Nego >= 15:
                    #     res.append([f"Negotiable_Load_Power is {Nego} W in {self.ECAP_pkt}, so DPLOSS calibration will perform, Expected: >= 15 W", Enums.TestResult.PASS])
                    #     tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                    #     if Mode_type == "NPM":
                    #         tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","skiplevel": ["Level4"],"flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                    #     dploss_res=self.DPlossCalibration(Flow_limit,tempcheck)
                    #     for tempres in dploss_res: res.append(tempres)
                    # else: res.append([f"Negotiable_Load_Power is {Nego} W in {self.ECAP_pkt}, so DPLOSS calibration won't perform, Expected: >= 15 W", Enums.TestResult.PASS])
                else: res.append([f"{self.ECAP_pkt} response is not observed", Enums.TestResult.FAIL])
        else:
            res.append([f"MSR packet is not observed", Enums.TestResult.FAIL])
        
        
        
        for tests in self.BKjsonData['testBkpTestResultsandPath']:
            if self.Header['TestcaseID'] == tests['testcaseDetails']['m_TestId']:
                basepath = Path(os.path.dirname(self.ProjectJson))
                path1 = Path(tests["actualIndividualTestcaseFolder"])
                # # print("\\".join(path1.parts[-2:]))
                csv_path = basepath/"\\".join(path1.parts[-2:])/"XCE_VrectMeasuremetData.csv"
                # print(csv_path)

                # Load CSV
                df = pd1.read_csv(csv_path)
                df.columns = (df.columns.str.strip().str.replace(r"[^\w]", "_", regex=True))
                # print(df.columns.tolist())

                # Ensure numeric columns
                df["VRECT_MIN_V_"] = pd1.to_numeric(df["VRECT_MIN_V_"], errors="coerce")
                df["VRECT_INITIAL_V_"] = pd1.to_numeric(df["VRECT_INITIAL_V_"], errors="coerce")
                df["XCE_Value"] = pd1.to_numeric(df["XCE_Value"], errors="coerce")

                # Filter only rows where XCE Value is non-negative
                df_valid = df[df["XCE_Value"] >= 0]

                # Apply condition only on valid rows
                # condition = df_valid["VRECT_MIN_V_"] < (df_valid["VRECT_INITIAL_V_"] - 0.5)
                condition = df_valid["VRECT_MIN_V_"] < (df_valid["VRECT_INITIAL_V_"] - 2)

                failed_rows1 = df_valid[condition & (df_valid["Response"] != "SGC")]
                failed_rows2 = df_valid[~condition & (df_valid["Response"] == "SGC")]
                passed_rows1 = df_valid[condition & (df_valid["Response"] == "SGC")]
                passed_rows2 = df_valid[~condition & (df_valid["Response"] != "SGC")]

                any_failures = False

                # Results
                if not passed_rows1.empty:
                    # print("passed_rows1")
                    for row in passed_rows1.itertuples(index=False):
                        # # print(row)
                        res.append([f"Vrect_min < Vrect_ini - 2 is satisfied with Vrect_min = {row.VRECT_MIN_V_} V, "f"Vrect_ini = {row.VRECT_INITIAL_V_} V at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec", Enums.TestResult.PASS])
                        res.append([f"PTx responded with {row.Response} at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec, Expected: SGC response", Enums.TestResult.PASS])
                
                if not passed_rows2.empty:
                    # print("passed_rows2")
                    for row in passed_rows2.itertuples(index=False):
                        # # print(row)
                        res.append([f"Vrect_min < Vrect_ini - 2 is not satisfied with Vrect_min = {row.VRECT_MIN_V_} V, "f"Vrect_ini = {row.VRECT_INITIAL_V_} V at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec", Enums.TestResult.PASS])
                        res.append([f"PTx responded with {row.Response} at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec, Expected: Not SGC response", Enums.TestResult.PASS])

                if not failed_rows1.empty:
                    # print("failed_rows1")
                    for row in failed_rows1.itertuples(index=False):
                        # # print(row)
                        res.append([f"Vrect_min < Vrect_ini - 2 is satisfied with Vrect_min = {row.VRECT_MIN_V_} V, "f"Vrect_ini = {row.VRECT_INITIAL_V_} V at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec", Enums.TestResult.PASS])
                        res.append([f"PTx responded with {row.Response} at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec, Expected: SGC response", Enums.TestResult.FAIL])

                if not failed_rows2.empty:
                    # other_condi = True
                    # print("failed_rows2")
                    for row in failed_rows2.itertuples(index=False):
                        # # print(row)
                        res.append([f"Vrect_min < Vrect_ini - 2 is not satisfied with Vrect_min = {row.VRECT_MIN_V_} V, "f"Vrect_ini = {row.VRECT_INITIAL_V_} V at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec", Enums.TestResult.FAIL])
                        res.append([f"PTx responded with {row.Response} at {round(row.VRECT_INITIAL_TimeStamp_S_,3)} sec, Expected: Not SGC response", Enums.TestResult.FAIL])
        return res

    def PNG_ILL(self,Flow_limit,Check):
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
                                res.append([f"Uro drops below 200 mV within {round((sd[0]-t1)*1000,3)} ms from the end of the illegal SIG data packet, Expected: <= 28 ms", Enums.TestResult.PASS])
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
            else: res.append([f"Shutdown TesterMsg not found", Enums.TestResult.FAIL])
        else: res.append([f"{self.XID_pkt} Packet not found", Enums.TestResult.FAIL])
        return res

    def X_value(self,Flow_limit,Check):
        res = []
        if 'PktLimit' in Check:
            limit = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
            id = limit[0]
            end = limit[1]
            # print("limit:",limit)
            # print("Flow_limit:",Flow_limit)
            totalsteps = 0
            while id <= end:
                TempPkt1 = self.PktMethod.GetPacketDetails(packet="z_By_",limit=[id,end],Type="TesterMsg")  
                if len(TempPkt1)>2:
                    # print("TempPkt1:",TempPkt1)
                    data = self.file_list[TempPkt1[2]]['pktType'].split(";")[-2].split("_")
                    movement = data[0].strip()
                    step = float(data[3].split("m")[0])
                    if movement == "Increase":
                        totalsteps += step
                    elif movement == "Decrease":
                        totalsteps -= step
                    id = TempPkt1[2]
                id += 1
            # # print("totalsteps(mm):",totalsteps)
            res.append([f"Recorded X_FO,max is {totalsteps} mm", Enums.TestResult.PASS])
        return res

    def Tinterval(self,Flow_limit,Check):
        res = []
        for pkt in Check['expected']:
            id = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0],value=pkt['refpkt'][2] if len(pkt['refpkt']) == 3 else None,limit=Flow_limit,Type=pkt['refpkt'][1])[2]

            if 'CLOAK' in self.Header['TestcaseID']:
                end = len(self.file_list)
            elif "PktLimit" in pkt:
                if pkt['PktLimit'] == "refCustom":
                    pass
                elif pkt['PktLimit'] == "refPrevious":
                    limit = [0,Flow_limit[0]]
                elif pkt['PktLimit'] == "refNextAll":
                    limit = [Flow_limit[1],len(self.file_list)-1]
                elif pkt['PktLimit'] == "refAll":
                    limit=[0,len(self.file_list)-1]
                elif pkt['PktLimit'] == "Flow":
                    limit = Flow_limit
                elif pkt['PktLimit'] == 'FromExncnt':
                    excnt = self.GetPacketDetails(packet="Execution_count_no",limit=[0,Flow_limit[0]-1])
                    limit=[excnt[2],Flow_limit[1]] if len(excnt)>2 else Flow_limit
                elif pkt['PktLimit'] == 'ExncntToEnd':
                    excnt = self.GetPacketDetails(packet="Execution_count_no",limit=[0,Flow_limit[0]-1])
                    limit=[excnt[2],len(self.file_list)-1] if len(excnt)>2 else Flow_limit
                elif pkt['PktLimit'] == "FromCustomPacket":
                    CP = self.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0],value=pkt['CustomLimit']['Packet'][1],limit=Flow_limit)
                    limit=[CP[2],Flow_limit[1]] if len(CP)>2 else Flow_limit
                end = limit[1]
            else: end = Flow_limit[1]
            # # print("Flow_limit:",Flow_limit)
            # print("id:",id)
            start = 0
            Tmin = 0
            Tmax = 0
            cnt_end = pkt['cnt']
            while id < end:
                TempPkt1 =  self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0],value=pkt['packet1'][2] if len(pkt['packet1']) == 3 else None,limit=[id,end],Type=pkt['packet1'][1])
                # print("TempPkt1:",TempPkt1)
                if len(TempPkt1) > 2:
                    res.append([f"{pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ""} packet found at {round(TempPkt1[0],3)} sec", Enums.TestResult.PASS])
                    for nxt_pkt in pkt['packet2']:
                        TempPkt2 =  self.PktMethod.GetPacketDetails(packet=nxt_pkt[0],value=nxt_pkt[2] if len(nxt_pkt) == 3 else None,limit=[TempPkt1[2]+1,end+1],Type=nxt_pkt[1])
                        # print("TempPkt2:",TempPkt2)
                        if len(TempPkt2) > 2:
                            res.append([f"{nxt_pkt[0]} {nxt_pkt[2] if len(nxt_pkt) == 3 else ""} packet found at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])

                            Tresult = round((TempPkt2[0]-TempPkt1[1])*1000,3)
                            # print(f"{pkt['chk']}:", round((TempPkt2[0]-TempPkt1[1])*1000,3))
                            ChkRes = CommonMethods.check_measure(pkt['exp'],Tresult,pkt['comp'])
                            Tmin = min(Tmin,Tresult) if start != 0 else Tresult
                            Tmax = max(Tmax,Tresult)
                            if Enums.TestResult.FAIL in ChkRes[1]: res.append(ChkRes)
                            res.append([f"The Measured {pkt['chk']} between {pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ""} and {nxt_pkt[0]} {nxt_pkt[2] if len(nxt_pkt) == 3 else ""} is: {ChkRes[3]} ms, Limit: {ChkRes[2]} ms", ChkRes[1]])
                            
                            start += 1
                            id = TempPkt2[2]
                        else: res.append([f"{nxt_pkt[0]} packet not found", Enums.TestResult.FAIL])
                else: res.append([f"{pkt['packet1'][0]} packet not found", Enums.TestResult.FAIL])
                id += 1
                # print("start:",start)
                if start==cnt_end: break
            
            # print("Tmin:",Tmin)
            # print("Tmax:",Tmax)
            # print('failures:',res)
        return res

    def Set_Load(self,Flow_limit,Check):
        res = []
        id = 0
        end = len(self.file_list)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  
        cnt = 0

        refpkt = self.PktMethod.GetPacketDetails(packet=Check['refpkt'][0],value=Check['refpkt'][2] if len(Check['refpkt']) == 3 else None,limit=Flow_limit,Type=Check['refpkt'][1])
        if len(refpkt)>2:
            id = refpkt[2]
        else:
            id = 0

        while id < end:
            TempPkt1 = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[id,end],Type="TesterMsg")
            if len(TempPkt1)>2:
                setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Set_load']}mA",limit=[TempPkt1[2],id],Type="TesterMsg")
                # print("setload:",setload)
                if len(setload)>2:
                    res.append([f"Set_Load: {Check['Set_load']} mA found at index@{setload[2]}, Expected: {Check['Set_load']} mA", Enums.TestResult.PASS])

                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[TempPkt1[2]+1,end],Type="TesterMsg")
                    ts = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[TempPkt1[2]+1,end],Type="TesterMsg")
                    if len(sd)>2 or len(ts)>2:
                        sindex2 = int(((TempPkt1[1]*1000))/AllChannelData3['Interval'])
                        eindex2 = int(((sd[0] if len(sd)>2 else ts[0])*1000)/AllChannelData3['Interval'])
                        cnt += 1

                        # # print("irects2:",irects2)
                        x = sindex2
                        while x <= eindex2:
                            if (Check['Set_load']+1) >= AllChannelData3['RV']['displayDataChunk'][x]*1000 >= (Check['Set_load']-0.2):
                                res.append([f"In ping_{cnt}, Irect: {round(AllChannelData3['RV']['displayDataChunk'][x]*1000,2)} mA is found at {self.PktMethod.ms_to_time(x*AllChannelData3['Interval'])}, Expected: {Check['Set_load']} mA", Enums.TestResult.PASS])
                                break
                            x += 1
                        else:
                            res.append([f"In {cnt}th cloak ping, Irect is not reached to {Check['Set_load']} mA", Enums.TestResult.FAIL])
                        id = sd[2] if len(sd)>2 else ts[2]
                else: res.append([f"Set_Load: {Check['Set_load']} mA not found", Enums.TestResult.FAIL])
            id += 1
        return res

    def Tramp(self,Flow_limit,Check):
        res = []
        # print("Tramp")
        #find the max voltage received for 10 PD after the 2nd flow
        AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        cnt = 0
        if "PktLimit" in Check:
            tmplimit=self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
        else: tmplimit = Flow_limit
        id = tmplimit[0]
        print("flow:",tmplimit)
        if "Set_load" in Check: AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  
        while id < tmplimit[1]:
            TempPkt1 = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[id,tmplimit[1]],Type="TesterMsg")
            print(TempPkt1)
            if len(TempPkt1)>2:
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[TempPkt1[2]+1,tmplimit[1]],Type="TesterMsg")
                print("sd:",sd)
                ts = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[TempPkt1[2]+1,tmplimit[1]+1],Type="TesterMsg")
                print("ts:",ts)
                if len(sd)>2 or len(ts)>2:
                    # print("sd[2]-TempPkt1[2]>2:",sd[2]-TempPkt1[2])
                    if (sd[2] if len(sd)>2 else ts[2])-TempPkt1[2]>=2:



                        if 'Cloak_Ping' in self.Header['TestcaseID']:
                            TempPkt2 = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[id,tmplimit[1]],Type="Packet")
                        else: TempPkt2 = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[id,tmplimit[1]],Type="Packet")
                        if len(TempPkt2)> 2:

                            
                            # # print("start:",TempPkt1)
                            # MaxValue = 0
                            # MaxIndex = 0
                            cnt+=1
                            if "Set_load" in Check:
                                sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[TempPkt1[2]+1,tmplimit[1]],Type="TesterMsg")
                                ts = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[TempPkt1[2]+1,tmplimit[1]+1],Type="TesterMsg")
                                if len(sd)>2 or len(ts)>2:
                                        
                                    # buff = 1 #ms  
                                    sindex2 = int(((self.file_list[TempPkt1[2]+1]["startTime"]) * 1000)/AllChannelData3['Interval'])
                                    eindex2 = int(((sd[0] if len(sd)>2 else ts[0])*1000)/AllChannelData3['Interval'])
                                    # irects2 = list(AllChannelData3['RV']['displayDataChunk'][sindex2:eindex2]) 

                                    # # print("irects2:",irects2)
                                    # break 
                                    # print("setload limits:",TempPkt2[2],sd[2])
                                    x = sindex2
                                    while x <= eindex2:
                                        value = AllChannelData3['RV']['displayDataChunk'][x]*1000
                                        # print("value:",value)
                                        if (Check['Set_load'] - 1.3) <= value <= (Check['Set_load'] + 1):
                                        # if (Check['Set_load']+1) >= value >= (Check['Set_load']-0.2):
                                            res.append([f"In {cnt}th {Check['Ping_type'] if 'Ping_type' in Check else ''} ping, Irect: {round(value,2)} mA is found at {self.PktMethod.ms_to_time(x*AllChannelData3['Interval'])}, Expected: {Check['Set_load']} mA", Enums.TestResult.PASS])
                                            break
                                        if value > (Check['Set_load']+2):
                                            res.append([f"In {cnt}th {Check['Ping_type'] if 'Ping_type' in Check else ''} ping, Irect: {round(value,2)} mA is found at {self.PktMethod.ms_to_time(x*AllChannelData3['Interval'])}, Expected: {Check['Set_load']} mA", Enums.TestResult.FAIL])
                                            break
                                        x += 1
                                    else:
                                        res.append([f"In {cnt}th {Check['Ping_type'] if 'Ping_type' in Check else ''} ping, Irect is not reached to {Check['Set_load']} mA", Enums.TestResult.FAIL])
                                    
                                    
                                    
                            # Test code  
                            sindex = int((TempPkt1[0]*1000)/AllChannelData['Interval'])-5
                            eindex = int((self.file_list[TempPkt2[2]]['startTime']*1000)/AllChannelData['Interval'])
                            id1 = sindex
                            vrects = list(AllChannelData['RV']['displayDataChunk'][sindex:eindex]) 
                            # # print("vrects:",vrects)

                            # 200mV vrect
                            closest = min(vrects, key=lambda x: (abs(x - 0.2), -x))
                            cindex = sindex+vrects.index(closest)+1
                            t1 = AllChannelData['Interval']*cindex
                            # # print("closest:",closest,cindex,"time1:",t1)

                            # Vrect_max
                            maxvrect = max(vrects)
                            max_index = sindex+vrects.index(maxvrect)+1
                            # # print("maxvrect:",maxvrect, "max_index:",max_index)

                            # 95% of Vrect_max
                            maxvrect2 = 0.95*maxvrect
                            max2_closest = min(vrects[:vrects.index(maxvrect)],key=lambda x: abs(x - maxvrect2))
                            # max2_closest = min(vrects[:max_index],key=lambda x: abs(x - maxvrect2))
                            
                            max2_index = sindex+vrects.index(max2_closest)+1
                            t2 = AllChannelData['Interval']*max2_index
                            # # print("95% of Vrect_max:",maxvrect2)
                            # # print("max2_closest:",max2_closest,max2_index,"time2:",t2)
                            # # print("Tramp:",t2-t1)
                            
                            id = TempPkt2[2]+1
                            results = CommonMethods.check_measure(Check['expected'],round(abs(t2-t1),3),Check['comp'])
                            # # print("results:",results)
                            res.append([f"Found Vrect_max: {round(maxvrect,3)} V at {self.PktMethod.ms_to_time(AllChannelData['Interval']*max_index)}, 95% of Vrect_max: {round(maxvrect2,3)} V at {self.PktMethod.ms_to_time(t2)}, 200mV at {self.PktMethod.ms_to_time(t1)}, The Tramp to reach 95% of peak volatge is {results[3]}ms : limit {results[2]}ms",results[1]])

                            if cnt == Check['packetCount']:break

                    else: id = TempPkt1[2]+1
                    
            else:break
            id += 1
        return res




















        # res = []
        # # print("Tramp")
        # #find the max voltage received for 10 PD after the 2nd flow
        # AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        # cnt = 0
        # if "PktLimit" in Check:
        #     tmplimit=self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
        # else: tmplimit = Flow_limit
        # id = tmplimit[0]
        # # print("flow:",tmplimit)
        # if "Set_load" in Check: AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  
        # while id < tmplimit[1]:
        #     TempPkt1 = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[id,tmplimit[1]],Type="TesterMsg")
        #     # # print(TempPkt1)
        #     if len(TempPkt1)>2:
        #         if 'Cloak_Ping' in self.Header['TestcaseID']:
        #             TempPkt2 = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[id,tmplimit[1]],Type="Packet")
        #         else: TempPkt2 = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[id,tmplimit[1]],Type="Packet")
        #         if len(TempPkt2)> 2:

                    
        #             # # print("start:",TempPkt1)
        #             # MaxValue = 0
        #             # MaxIndex = 0
        #             cnt+=1
        #             if "Set_load" in Check:
        #                 sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[TempPkt1[2]+1,tmplimit[1]],Type="TesterMsg")
        #                 if len(sd)>2:
                                
        #                     # buff = 1 #ms  
        #                     sindex2 = int(((self.file_list[TempPkt1[2]+1]["stopTime"]) * 1000)/AllChannelData3['Interval'])
        #                     eindex2 = int(((sd[0]*1000))/AllChannelData3['Interval'])
        #                     # irects2 = list(AllChannelData3['RV']['displayDataChunk'][sindex2:eindex2]) 

        #                     # # print("irects2:",irects2)
        #                     # break 
        #                     # print("setload limits:",TempPkt2[2],sd[2])
        #                     x = sindex2
        #                     while x <= eindex2:
        #                         value = AllChannelData3['RV']['displayDataChunk'][x]*1000
        #                         # print("value:",value)
        #                         if (Check['Set_load'] - 1) <= value <= (Check['Set_load'] + 1):
        #                         # if (Check['Set_load']+1) >= value >= (Check['Set_load']-0.2):
        #                             res.append([f"In {cnt}th cloak ping, Irect: {round(value,2)} mA is found at {self.PktMethod.ms_to_time(x*AllChannelData3['Interval'])}, Expected: {Check['Set_load']} mA", Enums.TestResult.PASS])
        #                             break
        #                         if value > (Check['Set_load']+2):
        #                             res.append([f"In {cnt}th cloak ping, Irect: {round(value,2)} mA is found at {self.PktMethod.ms_to_time(x*AllChannelData3['Interval'])}, Expected: {Check['Set_load']} mA", Enums.TestResult.FAIL])
        #                             break
        #                         x += 1
        #                     else:
        #                         res.append([f"In {cnt}th cloak ping, Irect is not reached to {Check['Set_load']} mA", Enums.TestResult.FAIL])
                            
                            
        #             # Test code  
        #             sindex = int((TempPkt1[0]*1000)/AllChannelData['Interval'])-5
        #             eindex = int((self.file_list[TempPkt2[2]]['startTime']*1000)/AllChannelData['Interval'])
        #             id1 = sindex
        #             vrects = list(AllChannelData['RV']['displayDataChunk'][sindex:eindex]) 
        #             # # print("vrects:",vrects)

        #             # 200mV vrect
        #             closest = min(vrects, key=lambda x: (abs(x - 0.2), -x))
        #             cindex = sindex+vrects.index(closest)+1
        #             t1 = AllChannelData['Interval']*cindex
        #             # # print("closest:",closest,cindex,"time1:",t1)

        #             # Vrect_max
        #             maxvrect = max(vrects)
        #             max_index = sindex+vrects.index(maxvrect)+1
        #             # # print("maxvrect:",maxvrect, "max_index:",max_index)

        #             # 95% of Vrect_max
        #             maxvrect2 = 0.95*maxvrect
        #             max2_closest = min(vrects[:vrects.index(maxvrect)],key=lambda x: abs(x - maxvrect2))
        #             # max2_closest = min(vrects[:max_index],key=lambda x: abs(x - maxvrect2))
                    
        #             max2_index = sindex+vrects.index(max2_closest)+1
        #             t2 = AllChannelData['Interval']*max2_index
        #             # # print("95% of Vrect_max:",maxvrect2)
        #             # # print("max2_closest:",max2_closest,max2_index,"time2:",t2)
        #             # # print("Tramp:",t2-t1)
                    
        #             id = TempPkt2[2]+1
        #             results = CommonMethods.check_measure(Check['expected'],round(abs(t2-t1),3),Check['comp'])
        #             # # print("results:",results)
        #             res.append([f"Found Vrect_max: {round(maxvrect,3)} V at {self.PktMethod.ms_to_time(AllChannelData['Interval']*max_index)}, 95% of Vrect_max: {round(maxvrect2,3)} V at {self.PktMethod.ms_to_time(t2)}, 200mV at {self.PktMethod.ms_to_time(t1)}, The Tramp to reach 95% of peak volatge is {results[3]}ms : limit {results[2]}ms",results[1]])

        #             if cnt == Check['packetCount']:break
                    
        #     else:break
        #     id += 1
        # return res
        

    def NegPhase(self,Flow_limit,Check):
        res = []
        id = Flow_limit[0]
        # end = Flow_limit[1]
        while id < Flow_limit[1]:
            if "Nego" in self.file_list[id]['description']:
                res.append([f"Entered to Negotiation phase at {round(self.file_list[id]['startTime'],3)} sec", Enums.TestResult.PASS])
                break
            id += 1
        else: res.append([f"Negotiation phase not observed", Enums.TestResult.FAIL])
        return res

    def Protocol_Prect(self,Flow_limit,Check):
        res = []
        srq_ver = self.PktMethod.GetPacketDetails(packet="SRQ",value="Version select:",limit=Flow_limit,Type="Packet")
        if len(srq_ver)>2:
            Pktresp1 = self.PktMethod.GetPacketResponse2(srq_ver[2],[srq_ver[2]+1,Flow_limit[1]])
            srq_en = self.PktMethod.GetPacketDetails(packet="SRQ",value="End Negotiation:",limit=Flow_limit,Type="Packet")
            if len(srq_en)>2:
                Pktresp2 = self.PktMethod.GetPacketResponse2(srq_en[2],[srq_en[2]+1,Flow_limit[1]])
                if self.file_list[Pktresp1]['pktType'] in ["NAK", "ND"] and self.file_list[Pktresp2]['pktType'] == "NAK":
                    res.append([f"SRQ/Versel is found at {round(srq_ver[0],3)} Sec", Enums.TestResult.PASS])
                    res.append([f"{self.file_list[Pktresp1]['pktType']} response received for SRQ/Versel", Enums.TestResult.PASS])
                    res.append([f"SRQ/en is found at {round(srq_en[0],3)} Sec", Enums.TestResult.PASS])
                    res.append([f"{self.file_list[Pktresp2]['pktType']} response received for SRQ/en", Enums.TestResult.PASS])
                else:
                    Powers = {"Prect1": 15, "Prect2": "PotentialLoad"}
                    cnt = 1
                    templimit = Flow_limit
                    prev_load_pkt = []
                    for pwr in Powers:
                        load = 0
                        
                        # templimit = Flow_limit
                        # EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
                        if Powers[pwr] == "PotentialLoad":
                            ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[Flow_limit[1],Flow_limit[0]],Type="Response")
                            # print("ECAP:",ECAP,self.ECAP_pkt,templimit)
                            if len(ECAP) > 2:
                                load = int(self.PktMethod.GetPayloadDetails(ECAP[2],"Potential_Load_Power")[0]['sDescription'].split(":")[-1].replace("W", "").strip())
                                res.append([f"Potential Load Power in ECAP is {load} W found at {round(ECAP[0],3)} Sec", Enums.TestResult.PASS])
                                print("load:",load)

                            # # templimit = [Flow_limit[1],len(self.file_list)-1]
                            # Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
                            # if len(Excapres)> 2:
                                
                            #     for ck in EXCAP.keys():
                            #         payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                            #         # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                            #         EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
                            #     # print("EXCAP:",EXCAP)

                            #     MSRreq = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=Flow_limit,Type="Packet")
                            #     if len(MSRreq)> 2:
                            #         PrefMode = self.PktMethod.GetPayloadDetails(MSRreq[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                            #         # print("PrefMode:",PrefMode)
                            #         load =int(EXCAP[PrefMode])
                            #         res.append([f"Potential Load Power of {PrefMode} is {load} W in MODEXCAP", Enums.TestResult.PASS])           
                        else: 
                            load = 15
                            # templimit = Flow_limit
                        
                        # print(f"Set_Load {load*1000}", templimit)
                        TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {load*1000}mW",limit=templimit,Type="TesterMsg")
                        # print("TempPkt2:",TempPkt2)
                        if len(TempPkt2)>2:
                            res.append([f"Found Set_Load {load*1000}mW packet at {round(TempPkt2[0],3)}Sec",Enums.TestResult.PASS])
                            #find the stabilization
                            TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],templimit[1]],Type="TesterMsg")
                            # print("TempPkt3:",TempPkt3)
                            if len(TempPkt3)>2:
                                res.append([f"Stabilization found at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS])
                                #Get Prect from PLA
                                TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2]-10,templimit[1]])
                                # print("TempPkt4:",TempPkt4)
                                if len(TempPkt4)>2:
                                    Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                                    
                                    results = CommonMethods.check_measure([14.7 if pwr == "Prect1" else (load-(load*0.02))],Prect,"GTEQL")
                                    
                                    res.append([f"Measured Prect_{cnt} is {results[3]} W at {self.PktMethod.Timeconvert(TempPkt4[0])}, Limit: {results[2]} W", results[1]])
                                    if cnt == 1: templimit = [TempPkt3[2],len(self.file_list)-1]
                                    cnt += 1

                                else:res.append([f"PLA packet not found between {round(TempPkt3[0],3)}Sec - {round(self.file_list[templimit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                            else:res.append([f"Stabilization is not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[templimit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                        else: res.append([f"Set_Load {load*1000}mW packet not found", Enums.TestResult.FAIL])
        return res
                        

    def SetLoad_NegoPwr(self,Flow_limit,Check):
        res = []
        #check for the set load with respective type mentioned in the setup
        exp = "NA"
        try:
            #Get Nego power from ECAP
            TempPkt1 = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
            if len(TempPkt1)>2:
                Nego = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt1[2],"Negotiable_Load_Power")[0]['sDescription'])[0]
                res.append([f"Found {self.ECAP_pkt} with Negotiable_Load_Power:{Nego}W",Enums.TestResult.PASS])
                #check for the load
                if Check['Type']=="Percentage":
                    Loadvalue = int((Nego/100)*Check['expected']*1000)
                    exp = f"{Check['expected']}% of Negotiable_Load_Power"
                elif Check['Type']=="Actual":
                    Loadvalue = Check['expected']
                    exp = "50mA"
                #check for Load applied
                if Loadvalue:
                    # # print(f"Set_Load {Loadvalue}")
                    TempPkt2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Loadvalue}",limit=[TempPkt1[2],Flow_limit[1]],Type="TesterMsg")
                    if len(TempPkt2)>2:
                        res.append([f"Set_Load {Loadvalue}mW packet found at {round(TempPkt2[0],3)}sec.({exp})",Enums.TestResult.PASS])
                    else:res.append([f"Set_Load {Loadvalue}mW packet not found",Enums.TestResult.FAIL])
            else:res.append([f"{self.ECAP_pkt} packet not found",Enums.TestResult.FAIL])
        except Exception as e:
            res.append([f"Exception:{e}",Enums.TestResult.FAIL])
        
        return res
        



    # Add 'return res' manually at end of each function if missing
    #get first initial voltage after the stabilization
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
        
    def PacketCheck_New(self,Flow_limit,Check):
        res = []
        expvalues=[]
        # print("PKTSck")
        for pkt in Check['ChecksList']:
            expval = ""
            Pktcount = 0
            limit=Flow_limit
            if 'PktLimit' in pkt:
                limit = self.PktMethod.GetLimits(pkt['PktLimit'],pkt,Flow_limit)
            # # print("limit:",limit)
            ExpPacket = pkt['packet'] if pkt['packet'][1] is not None else [pkt['packet'][0]]
            expval=expval+f"{'_'.join(ExpPacket)}:"
            if 'Pkt_response' in pkt : 
                if 'Pkt_response_Reverse' in pkt:
                    if pkt['Pkt_response_Reverse'] == True:
                        expval=expval+f"Response not in {','.join(pkt['Pkt_response'])}"
                    else:expval=expval+f"Response in {','.join(pkt['Pkt_response'])}"
                else:expval=expval+f"Response in {','.join(pkt['Pkt_response'])}"
            if 'Pkt_count' in pkt : expval=expval+f"Pacekt Count= {pkt['Pkt_count']}"
            if limit != None:
                res.append([f"Packet check for {'_'.join(ExpPacket)} initiated on limit {round(self.file_list[limit[0]]['startTime'],2)}Sec to {round(self.file_list[limit[1]]['startTime'],2)}Sec",Enums.TestResult.PASS])
                #Iterate on limit and get the matching packets
                id = limit[0]
                while id<=limit[1]:
                    # if self.PktMethod.GetPacketType(id) =="Packet":
                    #check for the phase
                    if pkt['phase'] in self.file_list[id]['description']:
                        if ExpPacket[0].lower() in self.file_list[id]['pktType'].lower() and  ExpPacket[1].lower() in self.file_list[id]['value'].lower() if len(ExpPacket)==2 else ExpPacket[0].lower() in self.file_list[id]['pktType'].lower():
                            #check for the packet type
                            if self.PktMethod.GetPacketType(id) == pkt['PktType'] if 'PktType' in pkt else "Packet":
                                Pktcount+=1
                                # res.append([f"{ExpPacket[0]} Packet found at {round(self.file_list[id]['startTime'],2)}Sec",Enums.TestResult.PASS])
                                res.append([f"{self.file_list[id]['pktType']} {self.file_list[id]['value']} Packet found at {round(self.file_list[id]['startTime'],2)}Sec",Enums.TestResult.PASS])
                                #Apply additional checks for the packet
                                #############################################################
                                if 'Pkt_response' in pkt:
                                    Pktresp = self.PktMethod.GetPacketResponse2(id,[id+1,limit[1]])
                                    if Pktresp is not None:
                                        if 'Pkt_response_Reverse' in pkt:
                                            if pkt['Pkt_response_Reverse']==True:
                                                if any(r in self.file_list[Pktresp]['pktType'] for r in pkt['Pkt_response']):
                                                    res.append([f"Found response {self.file_list[Pktresp]['pktType']}_{self.file_list[Pktresp]['value']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which is not expected amoung: {','.join(pkt['Pkt_response'])}",Enums.TestResult.FAIL])
                                                else:res.append([f"Found response {self.file_list[Pktresp]['pktType']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which is not expected amoung: {','.join(pkt['Pkt_response'])}",Enums.TestResult.PASS])
                                        else:
                                            if any(r in self.file_list[Pktresp]['pktType'] for r in pkt['Pkt_response']):
                                                res.append([f"Found response {self.file_list[Pktresp]['pktType']}_{self.file_list[Pktresp]['value']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which is expected amoung: {','.join(pkt['Pkt_response'])}",Enums.TestResult.PASS])
                                            else:res.append([f"Found response {self.file_list[Pktresp]['pktType']} at {round(self.file_list[Pktresp]['startTime'],2)}sec, Which not is expected amoung: {','.join(pkt['Pkt_response'])}",Enums.TestResult.FAIL])
                                    else:res.append([f"Response not found for received packet.",Enums.TestResult.FAIL])
                                    if not pkt.get('Pkt_count'):
                                        break
                                    # tmpid = id+1
                                    # RespFlag = False
                                    # while tmpid < limit[1]:
                                    #     if self.PktMethod.GetPacketType(tmpid) =="Response":
                                    #         if any(res in self.file_list[tmpid]['pktType'] for res in pkt['Pkt_response']):
                                    #             RespFlag=True
                                    #             res.append([f"found response {self.file_list[tmpid]['pktType']} at {round(self.file_list[tmpid]['startTime'],2)}sec, Which is expected amoung {','.join(pkt['Pkt_response'])}",Enums.TestResult.PASS])
                                    #         else: res.append([f"found response {self.file_list[tmpid]['pktType']} at {round(self.file_list[tmpid]['startTime'],2)}sec, Which is not expected amoung {','.join(pkt['Pkt_response'])}",Enums.TestResult.FAIL])
                                    #     elif self.PktMethod.GetPacketType(tmpid) =="Packet":break
                                    #     tmpid+=1
                                    # if RespFlag == False:res.append([f"Response not found for received for the packet.",Enums.TestResult.FAIL])
                                    ############################################################
                                elif not pkt.get('Pkt_count'):break
                    id+=1
                else:
                    # Packet not found
                    if (not pkt.get('Pkt_count')) or (pkt.get('Pkt_count') and Pktcount==0):
                        res.append([f"{ExpPacket[0]} {f'({ExpPacket[1]})' if len(ExpPacket)==2 else ""} not found",Enums.TestResult.INCONCLUSIVE])
            else:res.append([f"Packet check for {'_'.join(ExpPacket)} not initiated, limit not found",Enums.TestResult.FAIL])
            if Pktcount !=0:
                #check for pacekt count
                if 'Pkt_count' in pkt:
                    if Pktcount >= pkt['Pkt_count']:
                        res.append([f"The received pacekt count is {Pktcount},Which is >= of expected count of {pkt['Pkt_count']}",Enums.TestResult.PASS])
                    else:res.append([f"The received pacekt count is {Pktcount},Which is not expected count of {pkt['Pkt_count']}",Enums.TestResult.FAIL])
            else:res.append([f"{ExpPacket[0]} Packet not found",Enums.TestResult.FAIL])
            expvalues.append(expval)
        # AllMeasures['PacketCheck_exp'] = ';'.join(expvalues)
        # AllMeasures['PacketCheck'] = 'Found Issues' if any(r[1]==Enums.TestResult.FAIL for r in res) else 'No Issues'
        # AllMeasures['PacketCheck_res'] = Enums.TestResult.FAIL if any(r[1]==Enums.TestResult.FAIL for r in res) else Enums.TestResult.PASS
        # AllMeasures['PacketCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
        # AllMeasures['PacketCheck_Details']=res
        return res

    def BitsCheck_New(self,Flow_limit,Check):
        # print("BITSck")
        # # print(Flow_limit)
        res = []
        expvalues=[]
        
        for BITSck in Check['ChecksList']:
            PktCount = 0
            # # print(BITSck)
            limit = Flow_limit
            if 'PktLimit' in  BITSck:
                limit=self.PktMethod.GetLimits(BITSck['PktLimit'],BITSck,Flow_limit)
            ExpPacket = BITSck['packet'] if BITSck['packet'][1] is not None else [BITSck['packet'][0]]
            expvalue=f"{'_'.join(ExpPacket)}"
            comp = None
            for ck in BITSck['Checks']:
                if BITSck['Checks'][ck]['comp']=="str":
                    expvalue=expvalue+f":{ck}={BITSck['Checks'][ck]['expected']}"
                elif BITSck['Checks'][ck]['comp']=="str_Reverse":
                    expvalue=expvalue+f":{ck} Not {BITSck['Checks'][ck]['expected']}"
                elif BITSck['Checks'][ck]['comp']=="btw":
                    expvalue=expvalue+f":{ck} between {'-'.join(map(str,BITSck['Checks'][ck]['expected']))}"
                elif BITSck['Checks'][ck]['comp']=="Present":
                    expvalue=expvalue+f":{ck} should available"
                else:
                    if BITSck['Checks'][ck]['comp'] == "GTEQL": comp = ">="
                    if BITSck['Checks'][ck]['comp'] == "LTEQL": comp = "<="
                    if BITSck['Checks'][ck]['comp'] == "EQL": comp = "=="
                    expvalue=expvalue+f":{ck} {comp} {BITSck['Checks'][ck]['expected']}"
            PktType = BITSck['PacketType'] if 'PacketType' in BITSck else 'Packet'
            #check for multiple packet or signle packet based on the requirement
            print('bitsLimit',limit)
            tmpID = limit[0]
            while tmpID < limit[1]:
                PktFlag = False
                pktres = self.PktMethod.GetPacketDetails(packet=BITSck['packet'][0],value=BITSck['packet'][1],limit=[tmpID,limit[1]],Type=PktType)
                # print("pktres:",pktres)
                if len(pktres)>2:
                    #check for packet phase
                    if 'phase' in BITSck:
                        if BITSck['phase'] in self.file_list[pktres[2]]['description']:PktFlag=True
                    else:PktFlag=True
                    if PktFlag==True:
                        PktCount+=1
                        #count check    
                        res.append([f"The expected packet {self.file_list[pktres[2]]['pktType']}_{self.file_list[pktres[2]]['value']} found at {round(pktres[0],3)}sec",Enums.TestResult.PASS]) # res.append([f"The expected packet {'_'.join(ExpPacket)} found at {round(pktres[0],3)}sec",Enums.TestResult.PASS])
                        #Get the payload values results
                        for ck in BITSck['Checks']:
                            # # print(ck)
                            #get the payload details
                            payloadDetails = self.PktMethod.GetPayloadDetails(pktres[2],ck)
                            # # print(payloadDetails)
                            if len(payloadDetails)>0:
                                # print("payloadDetails:",payloadDetails)
                                for pyload in payloadDetails:
                                    if BITSck['Checks'][ck]['comp']=="str":
                                        if BITSck['Checks'][ck]['expected'] in pyload[BITSck['Checks'][ck]['flag']]:
                                            res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}",Enums.TestResult.PASS])
                                        elif 'random' in BITSck['Checks'][ck]['expected']:
                                            if BITSck['Checks'][ck].get('except'):
                                                if pyload[BITSck['Checks'][ck]['flag']] not in BITSck['Checks'][ck]['except']:
                                                    res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}",Enums.TestResult.PASS])
                                                else: res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}",Enums.TestResult.FAIL])
                                            else: res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random value",Enums.TestResult.PASS])
                                        else:
                                            if "0x" in BITSck['Checks'][ck]['expected'] and pyload[BITSck['Checks'][ck]['flag']].startswith("0x"):
                                                if int(BITSck['Checks'][ck]['expected'], 16) == int(pyload[BITSck['Checks'][ck]['flag']], 16):
                                                    res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}",Enums.TestResult.PASS])
                                                else:
                                                    res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}",Enums.TestResult.FAIL])
                                            else:
                                                res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}",Enums.TestResult.FAIL])
                                    elif BITSck['Checks'][ck]['comp']=="str_Reverse":
                                        if BITSck['Checks'][ck]['expected'] in pyload[BITSck['Checks'][ck]['flag']]:
                                            res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}",Enums.TestResult.FAIL])
                                        else:res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}",Enums.TestResult.PASS])
                                    elif BITSck['Checks'][ck]['comp']=="btw":
                                        # # print(int(pyload[BITSck['Checks'][ck]['flag']]),BITSck['Checks'][ck]['expected'])
                                        if int(pyload[BITSck['Checks'][ck]['flag']]) >= BITSck['Checks'][ck]['expected'][0] and int(pyload[BITSck['Checks'][ck]['flag']]) <= BITSck['Checks'][ck]['expected'][1]:
                                            res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}",Enums.TestResult.PASS])
                                        else:res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}",Enums.TestResult.FAIL])
                                    elif BITSck['Checks'][ck]['comp'] == "NEQL":
                                        if BITSck['Checks'][ck]['expected'] not in pyload[BITSck['Checks'][ck]['flag']]:
                                            res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: != {BITSck['Checks'][ck]['expected']}",Enums.TestResult.PASS])
                                        else: res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: != {BITSck['Checks'][ck]['expected']}",Enums.TestResult.FAIL])

                                    elif BITSck['Checks'][ck]['comp']=="Present":
                                        res.append([f"Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}",Enums.TestResult.PASS])
                                    else:
                                        if ':' in pyload[BITSck['Checks'][ck]['flag']]:
                                            pyaloadli = pyload[BITSck['Checks'][ck]['flag']].split(':')
                                            # print("pyaloadli:",pyaloadli)
                                            payloadActual = '_'.join(pyaloadli[1:])
                                        else:payloadActual=pyload[BITSck['Checks'][ck]['flag']]
                                        revdval = GeneralMethods.GetFloatFromStr(payloadActual)
                                        if BITSck['Checks'][ck].get("units"):
                                            revdval = [int(str(int(revdval[1])),16)]
                                        # print("revdval:",revdval)
                                        if BITSck['Checks'][ck]['comp'] == 'GTEQL':
                                            if  revdval[0] >= float(BITSck['Checks'][ck]['expected']):
                                                res.append([f"Recevied value of {ck} is {int(revdval[0]) if "Major_Version" or "Minor_Version" in ck else revdval[0]}, which is >={BITSck['Checks'][ck]['expected']}",Enums.TestResult.PASS])
                                            else:res.append([f"Recevied value of {ck} is {int(revdval[0]) if "Major_Version" or "Minor_Version" in ck else revdval[0]}, which is not >={BITSck['Checks'][ck]['expected']}",Enums.TestResult.FAIL])
                                        elif BITSck['Checks'][ck]['comp'] == 'LTEQL':
                                            if  revdval[0] <= float(BITSck['Checks'][ck]['expected']):
                                                res.append([f"Recevied value of {ck} is {revdval[0]}, which is <={BITSck['Checks'][ck]['expected']}",Enums.TestResult.PASS])
                                            else:res.append([f"Recevied value of {ck} is {revdval[0]}, which is not <={BITSck['Checks'][ck]['expected']}",Enums.TestResult.FAIL])
                                        elif BITSck['Checks'][ck]['comp'] == 'EQL':
                                            if revdval[0] == float(BITSck['Checks'][ck]['expected']):
                                                res.append([f"Recevied value of {ck} is {revdval[0]} {BITSck['Checks'][ck].get("units","")}, Expected: {BITSck['Checks'][ck]['expected']} {BITSck['Checks'][ck].get("units","")}",Enums.TestResult.PASS])
                                            else:res.append([f"Recevied value of {ck} is {revdval[0]} {BITSck['Checks'][ck].get("units","")}, Expected: {BITSck['Checks'][ck]['expected']} {BITSck['Checks'][ck].get("units","")}",Enums.TestResult.FAIL])
                            else:res.append([f"The payload {ck} for packet {'_'.join(ExpPacket)} not found for the packet {'_'.join(ExpPacket)}",Enums.TestResult.FAIL])
                    if 'PacketCount' not in BITSck:
                        break
                    if 'PacketCount' in BITSck:
                        if BITSck['PacketCount']==PktCount:break
                    tmpID = pktres[2]+1
                else:
                    if 'PacketCount' in BITSck:
                        if PktCount < BITSck['PacketCount']:
                            res.append([f"Out of {BITSck['PacketCount']} Received only {PktCount} {'_'.join(ExpPacket)} packets",Enums.TestResult.FAIL])
                    else:
                        if PktCount==0:
                            res.append([f"The expected packet {'_'.join(ExpPacket)} not found between {round(self.file_list[limit[0]]['startTime'],3)}sec to {round(self.file_list[limit[1]]['stopTime'],3)}sec ",Enums.TestResult.FAIL])
                    break
            expvalues.append(expvalue)
        # AllMeasures['BitsCheck_exp'] = ';'.join(expvalues)
        # AllMeasures['BitsCheck'] = 'Found Issues' if any(r[1]==Enums.TestResult.FAIL for r in res) else 'No Issues'
        # AllMeasures['BitsCheck_res'] = Enums.TestResult.FAIL if any(r[1]==Enums.TestResult.FAIL for r in res) else Enums.TestResult.PASS
        # AllMeasures['BitsCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
        # AllMeasures['BitsCheck_Details']=res
        # print("res:",res)
        return res

    def EyeTestFetchDataFromCSV(self,Flow_limit,check):
        res = []
        try:
            Ntotal = 0
            Npass = 0
            # Npass_meg = 0
            # Npass_pha = 0
            ExtractedFiles=None
            #After Stabilization find the XCE and PLA packets, fetch the corresponding values from the CSV files extracted from the EyeDebugInfo.GrlEyeInfo
            #1. Extract EyeDebugInfo.GrlEyeInfo file 
            PathList = self.Header['CapturePath'].split('\\')
            EyeInfoPath = CommonMethods.find_file('/'.join(PathList[0:len(PathList)-1]),'EyeDebugInfo.GrlEyeInfo')
            if EyeInfoPath is not None:
                if any (r in ["Extended Control Error"] for r in check['Packets']):
                    RangeLimit = [1,check['Range']] if 'Range' in check else [1,1]
                    rid = RangeLimit[0]
                    TempLimit = Flow_limit
                    while rid <= RangeLimit[1]:
                        # ExtractedFiles = CommonMethods.extract_zip_in_memory(EyeInfoPath)
                        #2.Get XCE and PLA packets after Stabilization find for 2 range
                        # print(TempLimit)
                        Stb_Pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCE_Stabilized",limit=TempLimit,Type="TesterMsg")
                        # # print(Stb_Pkt)
                        if len(Stb_Pkt)>2:
                            res.append([f"Stabilization {rid} found at:{round(Stb_Pkt[0],3)}sec",Enums.TestResult.PASS])
                            #Get XCE packets___________________________________________________________________________________________________________________
                            id = Stb_Pkt[2]
                            while id < Flow_limit[1]:
                                CEPkt = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[id,TempLimit[1]],Type="Response")
                                if len(CEPkt)>2:
                                    #Get packets for 5sec
                                    if CEPkt[0] - Stb_Pkt[1] >= 5: break
                                    Ntotal+=1
                                    Npass_meg = 0
                                    Npass_pha = 0
                                    for PktType in ['Magnitude','Phase']:
                                        df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'XCE',str(CEPkt[2]),'Results'])
                                        # # print(df)
                                        if df is not None:
                                            ckres = []
                                            #Find each checks
                                            for chk in check['Checks'][PktType]:
                                                if 'EyeAmplitude' in chk:
                                                    AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                                    AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                                elif 'SNR' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                                elif 'Fclk' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                                elif 'HalfBitPeriod' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                                elif 'EyeWidth' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                            #Update result for Packet
                                            subcheckres = Enums.TestResult.FAIL if any(r[1]==Enums.TestResult.FAIL for r in ckres) else Enums.TestResult.PASS
                                            if PktType == "Magnitude" and subcheckres==Enums.TestResult.PASS: Npass_meg+=1
                                            if PktType == "Phase" and subcheckres==Enums.TestResult.PASS: Npass_pha+=1
                                            res.append([f"{PktType} Extended_Control_Error at index:{CEPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                                        else: res.append([f"CSV file not found for the {PktType} packet Extended_Control_Error at {CEPkt[2]}",Enums.TestResult.FAIL])
                                    if Npass_meg == 1 or Npass_pha == 1: Npass+=1
                                else:break
                                id = CEPkt[2]+1
                            #Get PLA packets___________________________________________________________________________________________________________________
                            id = Stb_Pkt[2]
                            while id < Flow_limit[1]:
                                CEPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,TempLimit[1]],Type="Response")
                                if len(CEPkt)>2:
                                    #Get packets for 5sec
                                    if CEPkt[0] - Stb_Pkt[1] >= 5:break
                                    Ntotal+=1
                                    Npass_meg = 0
                                    Npass_pha = 0
                                    for PktType in ['Magnitude','Phase']:
                                        df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'PLA_2',str(CEPkt[2]),'Results'])
                                        # # print(df)
                                        if df is not None:
                                            ckres = []
                                            #Find each checks
                                            for chk in check['Checks'][PktType]:
                                                if 'EyeAmplitude' in chk:
                                                    AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                                    AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                                elif 'SNR' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                                elif 'Fclk' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                                elif 'HalfBitPeriod' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                                elif 'EyeWidth' in chk:
                                                    result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                                    ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                            #Update result for Packet
                                            # # print(ckres)
                                            subcheckres = Enums.TestResult.FAIL if any(r[1]==Enums.TestResult.FAIL for r in ckres) else Enums.TestResult.PASS
                                            if PktType == "Magnitude" and subcheckres==Enums.TestResult.PASS: Npass_meg+=1
                                            if PktType == "Phase" and subcheckres==Enums.TestResult.PASS: Npass_pha+=1
                                            res.append([f"{PktType} PLA_2 at index:{CEPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                                        else: res.append([f"CSV file not found for the {PktType} packet PLA_2 at {CEPkt[2]}",Enums.TestResult.FAIL])
                                    if Npass_meg==1 or Npass_pha == 1: Npass+=1
                                else:break
                                id = CEPkt[2]+1
                            TempLimit = [Stb_Pkt[2]+1,Flow_limit[1]]
                        else:res.append([f"Stabilization {rid} not found",Enums.TestResult.FAIL])
                        rid+=1
                    # print(res)
                    if Npass !=0 and Ntotal !=0:
                        if (Npass/(Ntotal/100))>=95:
                            res.append([f"Caluclated Npass {Npass} and Received Ntotal {Ntotal}: Pass Percentage:{round((Npass/(Ntotal/100)),3)}%",Enums.TestResult.PASS])
                        else:res.append([f"Caluclated Npass {Npass} and Received Ntotal {Ntotal}: Pass Percentage:{round((Npass/(Ntotal/100)),3)}%",Enums.TestResult.FAIL])
                    else:res.append([f"No packets received to calculate Npass",Enums.TestResult.FAIL])
                else:
                    if self.XID_pkt in check["Packets"]:
                        Ntotal+=1
                        XIDPkt = self.PktMethod.GetPacketDetails(packet=self.XID_pkt,limit=Flow_limit,Type="Response")
                        if len(XIDPkt)>2:
                            Npass_meg = 0
                            Npass_pha = 0
                            for PktType in ['Magnitude','Phase']:
                                df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'XID',str(XIDPkt[2]),'Results'])
                                if df is not None:
                                    ckres = []
                                    #Find each checks
                                    for chk in check['Checks'][PktType]:
                                        if 'EyeAmplitude' in chk:
                                            AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                            AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                        elif 'SNR' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                        elif 'Fclk' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                        elif 'HalfBitPeriod' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                        elif 'EyeWidth' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                    #Update result for Packet
                                    subcheckres = Enums.TestResult.FAIL if any(r[1]==Enums.TestResult.FAIL for r in ckres) else Enums.TestResult.PASS
                                    if PktType == "Magnitude" and subcheckres==Enums.TestResult.PASS: Npass_meg+=1
                                    if PktType == "Phase" and subcheckres==Enums.TestResult.PASS: Npass_pha+=1
                                    res.append([f"{PktType} Extended Identification at index:{XIDPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                                else: res.append([f"CSV file not found for the {PktType} packet Extended Identification at {XIDPkt[2]}",Enums.TestResult.FAIL])
                            if Npass_meg==1 or Npass_meg==1 :Npass+=1
                        else:res.append([f"Extended Identification not found",Enums.TestResult.FAIL])
                    if "Configuration" in check["Packets"]:
                        Ntotal+=1
                        CNFPkt = self.PktMethod.GetPacketDetails(packet="Configuration",limit=Flow_limit,Type="Response")
                        if len(CNFPkt)>2:
                            Npass_meg = 0
                            Npass_pha = 0
                            for PktType in ['Magnitude','Phase']:
                                df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'CFG',str(CNFPkt[2]),'Results'])
                                # df = self.extract_and_read_csv_from_zip(EyeInfoPath,[PktType,'CFG',"_",'Results'])
                                if df is not None:
                                    ckres = []
                                    #Find each checks
                                    for chk in check['Checks'][PktType]:
                                        if 'EyeAmplitude' in chk:
                                            AmpHigh = float(self.MatchCSVvalues(df,"AmplitudeHigh"))
                                            AmpLow = float(self.MatchCSVvalues(df,"AmplitudeLow"))
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],round(float(AmpHigh-AmpLow)*1000,4),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"EyeAmplitude:{round(float(AmpHigh-AmpLow)*1000,4)} Expected:{result[2]}",result[1]])
                                        elif 'SNR' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"SNR")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"SNR:{float(self.MatchCSVvalues(df,"SNR"))} Expected:{result[2]}",result[1]])
                                        elif 'Fclk' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"Fclk")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"Fclk:{float(self.MatchCSVvalues(df,"Fclk"))} Expected:{result[2]}",result[1]])
                                        elif 'HalfBitPeriod' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"HalfBitPeriod")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"HalfBitPeriod"))} Expected:{result[2]}",result[1]])
                                        elif 'EyeWidth' in chk:
                                            result = CommonMethods.check_measure(check['Checks'][PktType][chk]['Expected'],float(self.MatchCSVvalues(df,"EyeWidth")),check['Checks'][PktType][chk]['comp'])
                                            ckres.append([f"HalfBitPeriod:{float(self.MatchCSVvalues(df,"EyeWidth"))} Expected:{result[2]}",result[1]])
                                    #Update result for Packet
                                    subcheckres = Enums.TestResult.FAIL if any(r[1]==Enums.TestResult.FAIL for r in ckres) else Enums.TestResult.PASS
                                    if PktType == "Magnitude" and subcheckres==Enums.TestResult.PASS: Npass_meg+=1
                                    if PktType == "Phase" and subcheckres==Enums.TestResult.PASS: Npass_pha+=1
                                    res.append([f"{PktType} Configuration at index:{CNFPkt[2]} : {'|'.join(item[0] for item in ckres)}",subcheckres])
                                else: res.append([f"CSV file not found for the {PktType} packet Configuration at {CNFPkt[2]}",Enums.TestResult.FAIL])
                            if Npass_meg==1 or Npass_meg==1 :Npass+=1
                        else:res.append([f"Configuration not found",Enums.TestResult.FAIL])
                    else:res.append([f"The File EyeDebugInfo.GrlEyeInfo file not found in Trace path :{'/'.join(PathList[0:len(PathList)-1])}",Enums.TestResult.FAIL])
                    if Npass == 2:
                        res.append([f"Caluclated Npass {Npass}",Enums.TestResult.PASS])
                    else:res.append([f"Caluclated Npass {Npass}",Enums.TestResult.FAIL])
            # # print(res)
            return res 
        except Exception as e:
            traceback.print_exc()
            res.append([f"Exception:{str(e)}",Enums.TestResult.FAIL])
            return res

    def PrectVrectRamp(self,Flow_limit,Check):
        res = []
        if 'NPM' in self.Header['TestcaseName']:
            TypeSD = "NPM"
            TyepDscr = "Nominal_Power_Mode"
        elif 'LPM' in self.Header['TestcaseName']:
            TypeSD = "LPM"
            TyepDscr = "Low_Power_Mode"
        elif 'HPM' in self.Header['TestcaseName']:
            TypeSD = "HPM"
            TyepDscr = "High_Power_Mode"
        elif 'CPM' in self.Header['TestcaseName']:
            TypeSD = "CPM"
            TyepDscr = "Continuous_Power_Mode"
        #1. Find the MODEXCAP packet
        TempPkt1 = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
        if len(TempPkt1)>2:
            # # print(TypeSD,TyepDscr)
            TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref0")[0]['sDescription']
            if ':' in TempVal:TempVal = TempVal.split(':')[1]
            Vrect_target = {'LPM':12.5,'NPM':12.5,'CPM':12.5,'HPM':18}
            # ref0 = GeneralMethods.GetFloatFromStr(TempVal)[0]
            ref2 = Vrect_target[TypeSD]
            if '_CAP_360.LPM' in self.Header['TestcaseName']: ref2 = 9.6
            if '_CAP.LPM' in self.Header['TestcaseName']: ref2 = 9.6
            
            TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref1")[0]['sDescription']
            if ':' in TempVal:TempVal = TempVal.split(':')[1]
            ref1 = GeneralMethods.GetFloatFromStr(TempVal)[0]
            
            TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],TyepDscr)[0]['sDescription']
            if ':' in TempVal:TempVal = TempVal.split(':')[1]
            Pwr = GeneralMethods.GetFloatFromStr(TempVal)[0]
            # if '_P3' in self.Header['TestcaseName']: MaxW=15 if MaxW>15 else MaxW
            # if '_P4' in self.Header['TestcaseName']: MaxW=5 if MaxW>5 else MaxW
            # print("Header['TestcaseName']:",self.Header['TestcaseName'])
            if '.P3' in self.Header['TestcaseName']: Pwr = min(Pwr,15)
            if '.P4' in self.Header['TestcaseName']: Pwr = min(Pwr,5)
            # print("MinW:",Pwr)
            res.append([f"Found MODEXCAP at {round(TempPkt1[0],3)}sec, with {TypeSD} Voltage Ref1: {ref1} V and {TypeSD} Potential load power: {Pwr} W",Enums.TestResult.PASS])
            #Condition 1
            #2. Set Prect and Vrect targets
            cnt = 0
            # Conditions = [{"TPrect":1,"TVrect":ref0},{"TPrect":MaxW,"TVrect":ref1}]
            Conditions = [{"TPrect":Pwr,"TVrect":ref1},{"TPrect":1,"TVrect":ref2}]
            # print("Conditions:",Conditions)
            for cond in Conditions:
                cnt+=1
                TPrect = cond['TPrect']
                TVrect = cond['TVrect']
                res.append([f"Condition {cnt}: Prect Target{cnt} set to {TPrect}W and Vrect Target{cnt} set to {TVrect}V",Enums.TestResult.PASS])
                #Find Load
                TempPkt2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(TPrect*1000)}mW",limit=[Flow_limit[1],TempPkt1[2]],Type="TesterMsg")
                if len(TempPkt2)>2:
                    res.append([f"Set_Load {int(TPrect*1000)}mW packet found at {round(TempPkt2[0],3)}sec",Enums.TestResult.PASS])
                    #3.Get Stablization
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Flow_limit[1]],Type="TesterMsg")
                    if len(TempPkt3)>2:
                        res.append([f"Stablization found at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS])
                        #get for next set load or consider the end
                        TempPkt4 = self.PktMethod.GetPacketDetails(packet="Set_Load",limit=[TempPkt3[2],Flow_limit[1]],Type="TesterMsg")
                        PLAlimit = TempPkt4[2] if len(TempPkt4)>2 else Flow_limit[1]
                        #Get PLA2 packets for 1 mins
                        id = TempPkt3[2]
                        PrectLi = []
                        VrectLi = []
                        while id < PLAlimit:
                            TempPkt5 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,PLAlimit])
                            if len(TempPkt5)>2:
                                if (TempPkt5[0] - TempPkt3[0]) >= 60: break
                                Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt5[2],"PRECT")[0]['sDescription'])[0]
                                Vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt5[2],"VRECT")[0]['sDescription'])[0]
                                res.append([f"Found PLA_2 packet at {round(TempPkt5[0],3)}sec with Prect: {Prect} W and Vrect: {Vrect} V",Enums.TestResult.PASS])
                                PrectLi.append(Prect)
                                VrectLi.append(Vrect)
                                id=TempPkt5[2]+1
                            else:break
                        if id == PLAlimit:res.append([f"No PLA_2 found between {round(TempPkt3[0],3)}sec - {round(TempPkt4[1],3)}sec"])
                        #Find the average Vrect and Prect
                        if len(VrectLi)>2:
                            results = CommonMethods.check_measure(obsr_val=sum(VrectLi)/len(VrectLi),exp_val=[round((TVrect-0.25),3),round((TVrect+0.25),3)],comp=0)
                            res.append([f"The calculated average Vrect{cnt} : {round(results[3],3)} V, Limit: {results[2]} V",results[1]])
                            # results = CommonMethods.check_measure(obsr_val=sum(VrectLi)/len(VrectLi),exp_val=[round((TVrect/100)*95,3),round((TVrect/100)*105,3)])
                            # res.append([f"The calculated average Vrect : {round(results[3],3)}V, Limit +/-5% of Target Vrect {TVrect}V i.e {results[2]}V",results[1]])

                        if len(PrectLi)>0:
                            if cnt == 2:
                                results = CommonMethods.check_measure(obsr_val=sum(PrectLi)/len(PrectLi),exp_val=[0.9],comp="GTEQL")
                                res.append([f"The calculated average Prect{cnt} : {round(results[3],3)} W, Limit: {results[2]} W",results[1]])
                            else:
                                # results = CommonMethods.check_measure(obsr_val=sum(PrectLi)/len(PrectLi),exp_val=[round((TPrect/100)*95,3),round((TPrect/100)*105,3)])
                                # res.append([f"The calculated average Prect : {round(results[3],3)}W, Limit +/-5% of Target Prect {TPrect}W i.e {results[2]}W",results[1]])
                                results = CommonMethods.check_measure(obsr_val=sum(PrectLi)/len(PrectLi),exp_val=[round((TPrect-0.1),3)],comp="GTEQL")
                                res.append([f"The calculated average Prect{cnt} : {round(results[3],3)} W, Limit: {results[2]} W",results[1]])

                    else:res.append([f"Stablization not found for the Condition 1 between {round(self.file_list[TempPkt3[2]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
                else:res.append([f"Set_Load {int(TPrect*1000)}mA not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        else:res.append([f"The MODEXCAP packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res

    def MPLA2_PARAM(self,Flow_limit,Check):
        res =[]
        # limit = Flow_limit
        #try for all flows
        AllLimits = []
        PrevFo = None
        Offsets = []
        id = 0
        while id < len(self.file_list):
            FOpkt = self.PktMethod.GetPacketDetails(packet="",value="FOP:3",limit=[id,len(self.file_list)],Type="TesterMsg")
            if len(FOpkt)>2:
                fop = float(self.file_list[FOpkt[2]]['value'].split(":")[-1].split("kHz")[0].strip())
                if 359.46 < fop <360.54:
                    if PrevFo != None:
                        AllLimits.append([PrevFo,FOpkt[2]-1])
                    PrevFo=FOpkt[2]
                    id = FOpkt[2]+1
                else:id+=1
            else:
                if PrevFo != None:AllLimits.append([PrevFo,len(self.file_list)-1])
                break
        if len(AllLimits)==3:
            res.append([f"Found 3 flows as expected",Enums.TestResult.PASS])
        else:res.append([f"Found {len(AllLimits)} out of 3 flows",Enums.TestResult.FAIL])
        if len(AllLimits)>0:
            # # print(AllLimits)
            cond = 0
            for lim in AllLimits:
                cond+=1
                limit=lim
                res.append([f"Condition:{cond} started between {round(self.file_list[limit[0]]['startTime'],3)}sec to {round(self.file_list[limit[1]]['stopTime'],3)}sec",Enums.TestResult.PASS])
                #Check for the PLAP_2 [0x88] packet g_coil_Rx_pla2 value
                TempPkt6 = self.PktMethod.GetPacketDetails(packet="PLAP_2 [0x88]",limit=limit,Type="Response")
                if len(TempPkt6)>2:
                    value = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt6[2],Check['PRx_coil_key'])[0]['sDescription'].split(':')[1])[0]
                    if value ==1:
                        res.append([f"The PLAP_2 [0x88] packet found at {round(TempPkt6[0],3)}sec with {Check['PRx_coil_key']} value {value}, expected 1",Enums.TestResult.PASS])
                    else:res.append([f"The PLAP_2 [0x88] packet found at {round(TempPkt6[0],3)}sec with {Check['PRx_coil_key']} value {value}, expected 1",Enums.TestResult.FAIL])
                else:res.append([f"PLAP_2 [0x88] not found for condition {cond}",Enums.TestResult.FAIL])
                TempPkt7 = self.PktMethod.GetPacketDetails(packet="PLAP_2 [0x90]",limit=limit)
                # # print("Check:",Check)
                if cond == 1:
                    plap2_default_values = {"Alpha_FM_ITX_pla2": 0,"Alpha_FM_Vrect_Pla2": 0,"Alpha_FM_Irect_Pla2": 0,f"{Check['PTx_coil_key']}": 0}
                if len(TempPkt7)>2:
                    try:
                        # value4 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"gb_coil_Tx_pla2")[0]['sDescription'].split(':')[1])[0]
                        value1 = self.truncate_by_3_digit_groups(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"Alpha_FM_ITX_pla2")[0]['sDescription'].split(':')[1])[0])
                        value2 = self.truncate_by_3_digit_groups(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"Alpha_FM_Vrect_Pla2")[0]['sDescription'].split(':')[1])[0])
                        value3 = self.truncate_by_3_digit_groups(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],"Alpha_FM_Irect_Pla2")[0]['sDescription'].split(':')[1])[0])
                        value4 = self.truncate_by_3_digit_groups(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt7[2],Check['PTx_coil_key'])[0]['sDescription'].split(':')[1])[0])

                        res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec with the following values", Enums.TestResult.PASS])
                        if cond == 1:
                            plap2_default_values['Alpha_FM_ITX_pla2'] = value1
                            plap2_default_values['Alpha_FM_Vrect_Pla2'] = value2
                            plap2_default_values['Alpha_FM_Irect_Pla2'] = value3
                            plap2_default_values[Check['PTx_coil_key']] = value4
                            res.append([f"Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}",Enums.TestResult.PASS])
                        elif cond == 2:
                            res.append([f"Default values are: Alpha_FM_ITX_pla2 : {plap2_default_values['Alpha_FM_ITX_pla2']}, Alpha_FM_Vrect_Pla2 : {plap2_default_values['Alpha_FM_Vrect_Pla2']}, Alpha_FM_Irect_Pla2 : {plap2_default_values['Alpha_FM_Irect_Pla2']}, {Check['PTx_coil_key']} : {plap2_default_values[Check['PTx_coil_key']]}",Enums.TestResult.PASS])
                            # if value1 == plap2_default_values["Alpha_FM_ITX_pla2"] and value2 == plap2_default_values["Alpha_FM_Vrect_Pla2"] and value3 == plap2_default_values["Alpha_FM_Irect_Pla2"] and value4 == (1.2*plap2_default_values[Check['PTx_coil_key']]):
                            #     res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {plap2_default_values["Alpha_FM_ITX_pla2"]} (default value), Alpha_FM_Vrect_Pla2 == {plap2_default_values["Alpha_FM_Vrect_Pla2"]} (default value), Alpha_FM_Irect_Pla2 == {plap2_default_values["Alpha_FM_Irect_Pla2"]} (default value), {Check['PTx_coil_key']} == {1.2*plap2_default_values[Check['PTx_coil_key']]} (1.2 * default value)",Enums.TestResult.PASS])
                            # else:
                            #     res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec With Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {plap2_default_values["Alpha_FM_ITX_pla2"]} (default value), Alpha_FM_Vrect_Pla2 == {plap2_default_values["Alpha_FM_Vrect_Pla2"]} (default value), Alpha_FM_Irect_Pla2 == {plap2_default_values["Alpha_FM_Irect_Pla2"]} (default value), {Check['PTx_coil_key']} == {1.2*plap2_default_values[Check['PTx_coil_key']]} (1.2 * default value)",Enums.TestResult.FAIL])
                            if value1 == plap2_default_values["Alpha_FM_ITX_pla2"] and value2 == plap2_default_values["Alpha_FM_Vrect_Pla2"] and value3 == plap2_default_values["Alpha_FM_Irect_Pla2"] and value4 == self.truncate_by_3_digit_groups(1.2*plap2_default_values[Check['PTx_coil_key']]):
                                res.append([f"Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {plap2_default_values["Alpha_FM_ITX_pla2"]} (default value), Alpha_FM_Vrect_Pla2 == {plap2_default_values["Alpha_FM_Vrect_Pla2"]} (default value), Alpha_FM_Irect_Pla2 == {plap2_default_values["Alpha_FM_Irect_Pla2"]} (default value), {Check['PTx_coil_key']} == {self.truncate_by_3_digit_groups(1.2*plap2_default_values[Check['PTx_coil_key']])} (1.2 * default value)",Enums.TestResult.PASS])
                            else:
                                res.append([f"Mismatch in values, Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {plap2_default_values["Alpha_FM_ITX_pla2"]} (default value), Alpha_FM_Vrect_Pla2 == {plap2_default_values["Alpha_FM_Vrect_Pla2"]} (default value), Alpha_FM_Irect_Pla2 == {plap2_default_values["Alpha_FM_Irect_Pla2"]} (default value), {Check['PTx_coil_key']} == {1.2*plap2_default_values[Check['PTx_coil_key']]} (1.2 * default value)",Enums.TestResult.FAIL])
                        elif cond == 3:
                            res.append([f"Default values are: Alpha_FM_ITX_pla2 : {plap2_default_values['Alpha_FM_ITX_pla2']}, Alpha_FM_Vrect_Pla2 : {plap2_default_values['Alpha_FM_Vrect_Pla2']}, Alpha_FM_Irect_Pla2 : {plap2_default_values['Alpha_FM_Irect_Pla2']}, {Check['PTx_coil_key']} : {plap2_default_values[Check['PTx_coil_key']]}",Enums.TestResult.PASS])
                            if value1 == self.truncate_by_3_digit_groups((1.2*plap2_default_values["Alpha_FM_ITX_pla2"])) and value2 == self.truncate_by_3_digit_groups((1.2*plap2_default_values["Alpha_FM_Vrect_Pla2"])) and value3 == self.truncate_by_3_digit_groups((0.8*plap2_default_values["Alpha_FM_Irect_Pla2"])) and value4 == plap2_default_values[Check['PTx_coil_key']]:
                                res.append([f"Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {self.truncate_by_3_digit_groups(1.2*plap2_default_values["Alpha_FM_ITX_pla2"])} (1.2 * default value), Alpha_FM_Vrect_Pla2 == {self.truncate_by_3_digit_groups(1.2*plap2_default_values["Alpha_FM_Vrect_Pla2"])} (1.2 * default value), Alpha_FM_Irect_Pla2 == {self.truncate_by_3_digit_groups(0.8*plap2_default_values["Alpha_FM_Irect_Pla2"])} (0.8 * default value), {Check['PTx_coil_key']} == {plap2_default_values[Check['PTx_coil_key']]} (default value)",Enums.TestResult.PASS])
                            else:
                                res.append([f"Mismatch in values, Alpha_FM_ITX_pla2 : {value1}, Alpha_FM_Vrect_Pla2 : {value2}, Alpha_FM_Irect_Pla2 : {value3}, {Check['PTx_coil_key']} : {value4}, Expected: Alpha_FM_ITX_pla2 == {1.2*plap2_default_values["Alpha_FM_ITX_pla2"]} (1.2 * default value), Alpha_FM_Vrect_Pla2 == {round((1.2*plap2_default_values["Alpha_FM_Vrect_Pla2"]),7)} (1.2 * default value), Alpha_FM_Irect_Pla2 == {round((0.8*plap2_default_values["Alpha_FM_Irect_Pla2"]),5)} (0.8 * default value), {Check['PTx_coil_key']} == {plap2_default_values[Check['PTx_coil_key']]} (default value)",Enums.TestResult.FAIL])
                    
                    except Exception as e:
                        res.append([f"The PLAP_2 [0x90] packet found at {round(TempPkt7[0],3)}sec, Exception:{e}",Enums.TestResult.FAIL])
                else:res.append([f"The PLAP_2 [0x90] packet not found for condition {cond}",Enums.TestResult.FAIL])
                #1. find the Load 15000
                TempPkt1 = self.PktMethod.GetPacketDetails(packet="Set_Load 15000mW",limit=limit,Type="TesterMsg")
                if len(TempPkt1)>2:
                    res.append([f"Set Load 15000mW found at {round(TempPkt1[0],3)}ms",Enums.TestResult.PASS])
                    #2. find stabiliZATION
                    TempPkt2 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt1[2]+1,limit[1]],Type="TesterMsg")
                    if len(TempPkt2)>2:
                        #3. Get Vrect value
                        results = self.GetInitailVoltage(Check['flow'],[TempPkt1[2],TempPkt2[2]+1])
                        if results is not None and len(results) > 0:
                            resultsMes = CommonMethods.check_measure([13.3,14.7],results[0])
                            res.append([f"Stabilization found at {round(TempPkt2[0],3)}Sec,with caluclate Voltage {results[0]}V measured at {round(self.file_list[results[1]]['startTime'],3)}Sec, limit:{resultsMes[2]}",resultsMes[1]])
                        else:res.append([f"Stabilization found at {round(TempPkt2[0],3)}Sec, Voltage calculation not performed",Enums.TestResult.FAIL])
                        #4.check PLA packet by increaring offset values until PLA gets NAk
                        PLAID = TempPkt2[2]
                        NAK_Flag = False
                        PrevRPoffset = None
                        PLAcount = 0
                        maxoffset = 0
                        while PLAID < limit[1]:
                            TempPkt3 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[PLAID,limit[1]])
                            if len(TempPkt3)>2:
                                PLAcount+=1
                                
                                #Get Prect & RP offset values
                                TempPkt4 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt3[2],TempPkt3[2]-4],Type="TesterMsg")
                                if len(TempPkt4)>2:
                                    Prect_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['value'])[0]
                                    maxoffset = RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['value'])[1]
                                    if Prect_Offset != RP_Offset: res.append([f"The applied Prect_offset {Prect_Offset}W and RP_Offset{RP_Offset} are not same for PLA packet at {round(TempPkt3[0],3)}ms",Enums.TestResult.FAIL])
                                else:res.append([f"Power offset not found for the PLA packet at {round(TempPkt3[0],3)}",Enums.TestResult.FAIL])
                                
                                #get Acutal RP and Prect values
                                TempPkt5 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt3[2],TempPkt3[2]-4],Type="TesterMsg")
                                if len(TempPkt5)>2:
                                    Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt5[2]]['pktType'])[0]
                                    RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt5[2]]['pktType'])[1]
                                else: res.append([f"Rectified not found for the PLA packet at {round(TempPkt3[0],3)}",Enums.TestResult.FAIL])
                                Prect_Final = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                                RP_Final = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                                
                                if len(TempPkt4)>2 and len(TempPkt5)>2:
                                    # result = Enums.TestResult.PASS if Prect_Final == round((Prect_Actual-Prect_Offset),3) and RP_Final == round((RP_Actual-RP_Offset),3) else Enums.TestResult.FAIL
                                    # #add only if PLA_2 checks fails to reduce the report length 
                                    # if result==Enums.TestResult.FAIL: res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec with Perct={Prect_Final}W and RP={RP_Final}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",result])
                                    if Prect_Final == round((Prect_Actual-Prect_Offset),3) and RP_Final == round((RP_Actual-RP_Offset),3):
                                        res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec with Prect={Prect_Final}W, RP={RP_Final}W | Prect_actual = {Prect_Actual}W, RP_actual={RP_Actual} | Prect_Offset={Prect_Offset}W, RP_offset={RP_Offset}W, Expected: Prect = Prect_actual - P_offset and RP = RP_Actual - RP_offset",Enums.TestResult.PASS])
                                    else:
                                        res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec with Prect={Prect_Final}W, RP={RP_Final}W | Prect_actual = {Prect_Actual}W, RP_actual={RP_Actual} | Prect_Offset={Prect_Offset}W, RP_offset={RP_Offset}W, Expected: Prect = Prect_actual - P_offset and RP = RP_Actual - RP_offset",Enums.TestResult.FAIL])


                                    #ensure offset increment
                                    if PrevRPoffset is not None:
                                        if round(abs(RP_Offset-PrevRPoffset),3)!=0.01:
                                            res.append([f"The RP_offset not increased by 0.01W from previous offset value",Enums.TestResult.FAIL])
                                    
                                    #Check for PLA_with NAK response
                                    PLAresp = self.PktMethod.GetPacketResponse(TempPkt3[2],[TempPkt3[2]+1,limit[1]])
                                    # # print(cond,PLAresp,TempPkt3,[TempPkt3[2]+1,Flow_limit[1]])
                                    if PLAresp is not None:
                                        if self.file_list[PLAresp]['pktType'] == "NAK":
                                            res.append([f"NAK response found to the PLA packet for P_offset: {Prect_Offset} W  at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS]) 
                                            NAK_Flag=True
                                            break
                                    PrevRPoffset = RP_Offset
                                else:res.append([f"PLA_2 packet found at {round(TempPkt3[0],3)}sec, offset calculations not performed!",Enums.TestResult.FAIL])
                                PLAID = TempPkt3[2]+1
                            else:break
                        if NAK_Flag==False:res.append([f"PLA packet with NAK not found for Condition {cond}",Enums.TestResult.FAIL])
                        res.append([f"Found {PLAcount} PLA packets for the Condition {cond} and the applied last offset is {maxoffset}W",Enums.TestResult.PASS])
                        Offsets.append(maxoffset)
                    else:res.append([f"The Stabilization not found",Enums.TestResult.FAIL])
                else:res.append([f"Set load for 15000mW not found",Enums.TestResult.FAIL])
                # break
        if len(Offsets)==3:
            if Offsets[1] > Offsets[0]:
                res.append([f"Max offset for condition B ({Offsets[1]}W) is grater than the Condition A max offset value({Offsets[0]}W)",Enums.TestResult.PASS])
            else:res.append([f"Max offset for condition B ({Offsets[1]}W) is not grater than the Condition A max offset value({Offsets[0]}W)",Enums.TestResult.FAIL])
            if Offsets[2] > Offsets[0]:
                res.append([f"Max offset for condition C ({Offsets[2]}W) is grater than the Condition A max offset value({Offsets[0]}W)",Enums.TestResult.PASS])
            else:res.append([f"Max offset for condition C ({Offsets[2]}W) is not grater than the Condition A max offset value({Offsets[0]}W)",Enums.TestResult.FAIL])
        else:res.append([f"Not all 3 conditions applied",Enums.TestResult.FAIL])
        return res
    
    def truncate_by_3_digit_groups(self,value):
        value_str = f"{value:.15f}".rstrip('0').rstrip('.')

        if '.' not in value_str:
            return float(value_str)

        integer_part, decimal_part = value_str.split('.')

        for i in range(0, len(decimal_part), 3):
            group = decimal_part[i:i+3]

            if group and int(group) != 0:
                return float(f"{integer_part}.{decimal_part[:i+3]}")

        return float(integer_part)




    def extract_and_read_csv_from_zip(self,zip_path, csv_match):
        res = []
        # # print(csv_match)
        with open(zip_path, "rb") as file:
            zip_bytes = io.BytesIO(file.read())  # Load ZIP into memory
        with zipfile.ZipFile(zip_bytes, "r") as zip_file:
            # Find CSV file by matching name
            matched_csv = [name for name in zip_file.namelist() if all(r in name for r in csv_match)]
            # # print(matched_csv)
            if not matched_csv:
                # # print(f"No CSV file matching '{csv_match}' found.")
                return res
            # Read the first matched CSV file
            with zip_file.open(matched_csv[0]) as csv_file:
                reader = csv.reader(io.TextIOWrapper(csv_file, encoding="utf-8"))
                data_list = [row for row in reader]
                res = data_list
                return res

    def MatchCSVvalues(self,CSVlist,name):
        res = []
        for row in CSVlist:
            # if name =="Fclk":# print(row)
            # # print(row)
            if len(row)>2:
                if name in row[0]:
                    res = row[1]
                    return res
        return res

    def OffsetReneg(self,Flow_limit,Check):
        print("OffsetReneg started")
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
                
                MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=[pkt_exit[2],end],Type="Packet")
                if len(MSRreq2)> 2:
                    PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                    # print("PrefMode2:",PrefMode2)
                    res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: Mode2: {mode2}", Enums.TestResult.PASS if mode2 == PrefMode2 else Enums.TestResult.FAIL])
                    MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],end],Type="Response")
                    if len(MSS2)> 2:
                        res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", Enums.TestResult.PASS])

                        ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[MSS2[2],end],Type="Response")
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
                                # print("self.stability:",self.stability)
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
                                            # PLARes = Enums.TestResult.PASS if Prect_Rcv == round((Prect_Actual+(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual+(RP_Offset)),3) else Enums.TestResult.FAIL
                                            # if PLARes==Enums.TestResult.FAIL:res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect_Rcv}W and RP={RP_Rcvd}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
                                            # else: res.append([f"Prect_Actual:{Prect_Actual}W is matching with Prect_Rcv:{Prect_Rcv}W after applying Prect_Offset:{Prect_Offset}W and RP_Actual:{RP_Actual}W is matching with RP_Rcvd:{RP_Rcvd}W after applying RP_Offset:{RP_Offset}W",Enums.TestResult.PASS])
                                            if 'Operation' in Check:
                                                if Check['Operation'] == "-":
                                                    PLARes = Enums.TestResult.PASS if Prect_Rcv == round((Prect_Actual-(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual-(RP_Offset)),3) else Enums.TestResult.FAIL
                                                    # print("Prect_Rcv:",Prect_Rcv,"Prect_Offset:",Prect_Offset,"Prect_Actual:",Prect_Actual)
                                                    # print("Prect_Actual-Prect_Offset:",Prect_Actual-(Prect_Offset))

                                                    # print("RP_Rcvd:",RP_Rcvd,"RP_Offset:",RP_Offset,"RP_Actual:",RP_Actual)
                                                    # print("RP_Actual-RP_Offset:",RP_Actual-(RP_Offset))
                                           
                                                    if PLARes == Enums.TestResult.FAIL:
                                                        res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect_Rcv}W and RP={RP_Rcvd}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
                                                    else: res.append([f"Prect_Actual:{Prect_Actual}W is matching with Prect_Rcv:{Prect_Rcv}W after applying Prect_Offset:{Prect_Offset}W and RP_Actual:{RP_Actual}W is matching with RP_Rcvd:{RP_Rcvd}W after applying RP_Offset:{RP_Offset}W",Enums.TestResult.PASS])
                                                
                                            else: 
                                                PLARes = Enums.TestResult.PASS if Prect_Rcv == round((Prect_Actual+(Prect_Offset)),3) and RP_Rcvd == round((RP_Actual+(RP_Offset)),3) else Enums.TestResult.FAIL
                                                if PLARes == Enums.TestResult.FAIL:
                                                    res.append([f"PLA Power Calculation issue at {round(TempPkt2[0],3)}sec with Perct={Prect_Rcv}W and RP={RP_Rcvd}W,Prect_Offset={Prect_Offset}W and RP_offset={RP_Offset}W, Prect_Actual = {Prect_Actual}W and RP_Actual={RP_Actual}W",PLARes])
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
                                        id = TempPkt2[2]
                                    else:
                                        res.append([f"Removed the applied POFFSET from {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS]) 
                                        break
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
        return res

    def OffsetReneg2(self,Flow_limit,Check):
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
                    offset_cnt = 0
                    id = self.stability#renegload[2]
                    while id < end:
                        TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,end])
                        # # print("TempPkt2:",TempPkt2)
                        if len(TempPkt2)>2:
                            # print("TempPkt2:",TempPkt2)
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
                                # print("TempPkt3:",TempPkt3)
                                # print("TempPkt4:",TempPkt4)
                                offset_cnt += 1
                                # print("offset_cnt:",offset_cnt)
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

                    if offset_cnt > 0:
                        res.append([f"{int(Check['FixedOffsetValues']['Prect']*1000)} mW POFFSET is removed and TPR started sending PPR,est = PPR and Prect,est = Prect", Enums.TestResult.PASS])
                    else:
                        res.append([f"{int(Check['FixedOffsetValues']['Prect']*1000)} mW POFFSET is not applied in the execution.", Enums.TestResult.FAIL])

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
            
                    ECAP2 = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[id,end],Type="Response")
                    
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

                                                                if negpwr2 == 15:
                                                                    res.append([f"Renegotiate Load is {negpwr2}W found at index@{renegload[2]}, Expected: 15W", Enums.TestResult.PASS])
                                                                else: res.append([f"Renegotiate Load is {negpwr2}W found at index@{renegload[2]}, Expected: 15W", Enums.TestResult.FAIL])
                                                                
                                                                if 'Remove_offset' in Check:
                                                                    # Remove applied offsets
                                                                    offset_pkt = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[renegload[2],end],Type="TesterMsg")
                                                                    # print("offset_pkt:",offset_pkt)
                                                                    if len(offset_pkt)<2:
                                                                        res.append([f"Offset is removed and TPR set PPR,est = PPR and Prect,est = Prect", Enums.TestResult.PASS])
                                                                    else: res.append([f"Offset is not removed", Enums.TestResult.FAIL])
                                                                
                                                                pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=[renegload[2],end],Type="Response")
                                                                if len(pkt_DPM)>2:
                                                                    alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                                                    beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                                                    invalid = float(self.PktMethod.GetPayloadDetails(pkt_DPM[2],"Invalid")[0]['sDescription'].split(":")[1].strip())
                                                                    res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0],2)} sec with Invalid: {invalid}, dPLoss-Alpha:{alpha}, dPLoss-Beta:{beta}",Enums.TestResult.PASS if invalid == 1 and alpha == 0 and beta == 0 else Enums.TestResult.FAIL])
                                                                else:res.append([f"DPCAL_PARAM packet not recevied",Enums.TestResult.INCONCLUSIVE])
                                    
                                                            else: res.append([f"Set_Load {int(negpwr2*1000)}mW not found", Enums.TestResult.FAIL])
                    else: res.append(["Renegotiation sequence was not observed, after power stabilize", Enums.TestResult.INCONCLUSIVE])

                    
                        

        return res

    
        

    def Thermal(self,Flow_limit,Check):
        print("Thermal checking")
        res = []
        Flow_limit = Flow_limit
        for tests in self.BKjsonData['testBkpTestResultsandPath']:
            if self.Header['TestcaseID'] == tests['testcaseDetails']['m_TestId']:
                basepath = Path(os.path.dirname(self.ProjectJson))
                path1 = tests["actualIndividualTestcaseFolder"]
                # print(path1.split("\\")[-2])
                run_path = basepath/path1.split("\\")[-2]
                for file in os.listdir(run_path):
                    if file.startswith("MPP_PTX_THERMAL") and file.endswith(".csv"):
                        csv_path = os.path.join(run_path, file)
                        # print("csv_path:",csv_path)

                        #csv read
                        df = pd1.read_csv(csv_path)

                        ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
                        # print('ECAP:',ECAP)
                        if len(ECAP)>2:
                            ECAPppwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],"Potential_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                            # print("ECAPppwr:",ECAPppwr)
                            res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt} at {round(ECAP[0],3)} sec", Enums.TestResult.PASS])
                            XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[ECAP[2],Flow_limit[1]],Type="Packet")
                            # print('XCE:',XCE)
                            pwr_mtrid = 0
                            if len(XCE)>2:
                                res.append([f"PT phase started at {round(XCE[0],3)} sec", Enums.TestResult.PASS])

                                start = XCE[2]
                                # t0 = XCE[0]
                                self.AllChannelData11 = self.PlotMethod.GetAllChannelData('11',self.JapiData)
                                self.AllChannelData12= self.PlotMethod.GetAllChannelData('12',self.JapiData)
                                sindex = int((XCE[0]*1000)/self.AllChannelData12['Interval'])
                                fotemp0 = self.AllChannelData12['RV']['displayDataChunk'][sindex]
                                ambtemp0 = self.AllChannelData11['RV']['displayDataChunk'][sindex]
                                res.append([f"Measured Puck_temp_t0: {fotemp0}℃, Ambient_temp_t0: {ambtemp0}℃ at t0: {round(XCE[0],3)} sec", Enums.TestResult.PASS])
                                # print("fotemp0:",fotemp0,"ambtemp0:",ambtemp0)

                                # Absolute Max puck temp
                                sindex3 = int((self.file_list[Flow_limit[0]]['startTime'])/self.AllChannelData12['Interval'])
                                alltempdata = self.AllChannelData12['RV']['displayDataChunk'][sindex3:]
                                
                                Maxtemp = max(alltempdata)
                                Temp_max_t = ((self.AllChannelData12['RV']['displayDataChunk'].index(Maxtemp))*self.AllChannelData12['Interval']) #millisec
                                # print("Maxtemp:", Maxtemp, "time:",self.PktMethod.ms_to_time(Temp_max_t))
                                if Maxtemp <= 48:
                                    res.append([f"Absolute maximum puck_temp is {Maxtemp}℃ at {self.PktMethod.ms_to_time(Temp_max_t)}, Expected: <= 48℃", Enums.TestResult.PASS])
                                else:
                                    res.append([f"Absolute maximum puck_temp is {Maxtemp}℃ at {self.PktMethod.ms_to_time(Temp_max_t)}, Expected: <= 48℃", Enums.TestResult.FAIL])

                                if ECAPppwr > 15:
                                    res.append([f"Potential_Load_Power is {ECAPppwr} W in {self.ECAP_pkt} i.e, > 15W", Enums.TestResult.PASS])
                                    tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                                    dplosschks = self.DPlossCalibration(Flow_limit,tempcheck)
                                    # # print(chk for chk in dplosschks)
                                    # res.append(chk for chk in dplosschks)
                                    for chk in dplosschks:
                                        res.append(chk)
                                    calexit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=[ECAP[2],Flow_limit[1]],Type="Packet")
                                    # print('calexit:',calexit)
                                    if len(calexit)>2:
                                        nxt_start = calexit[2]
                                        pwr_mtrid = calexit[2]
                                else: 
                                    res.append([f"Potential_Load_Power is {ECAPppwr} W, so DPLOSS calibration won't perform, Expected: > 15 W", Enums.TestResult.PASS])
                                    setload2 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(ECAPppwr*1000)}mW",limit=[ECAP[2],Flow_limit[1]],Type='TesterMsg')
                                    # print('setload2:',setload2)
                                    if len(setload2)>2:
                                        res.append([f"Set_Load {int(ECAPppwr*1000)}mW packet found at {round(setload2[0],3)}sec",Enums.TestResult.PASS])
                                    else:
                                        res.append([f"Set_Load {int(ECAPppwr*1000)}mW packet not found",Enums.TestResult.FAIL])
                                    pwr_mtrid = XCE[2]
                                
                                pla_cnt1 = 1
                                pla_cnt2 = 0
                                t_start = 0
                                prect_min = []
                                prect_max = []
                                while start < Flow_limit[1]:
                                    pla2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[start,Flow_limit[1]],Type="Packet")
                                    if len(pla2)>2:
                                        prect = float(self.PktMethod.GetPayloadDetails(pla2[2],"PRECT")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                                        if prect >= 14.5:
                                            if pla_cnt1 == 1:
                                                # print("First PLA_2 packet with prect >= 14.5 W:",pla2)
                                                res.append([f"First PLA_2 packet with Prect: {prect} found at {round(pla2[0],3)} sec, Expected: Prect >= 14.5 W", Enums.TestResult.PASS])
                                                t1 = pla2[0]
                                                print("t1:",t1)
                                                res.append([f"t1 is {round(t1,3)} sec", Enums.TestResult.PASS])
                                                tempdata2 = self.Thermaldata(csv_path,t1,max_delT=True)
                                                print("tempdata2:",tempdata2)
                                                if tempdata2:
                                                    if tempdata2['Temp_Rise'] <= 25:
                                                        res.append([f"Max Δtemp: {tempdata2['Temp_Rise']}℃ found at {round(tempdata2['startTime'],3)} sec (t1+15min), Expected: <= 25℃", Enums.TestResult.PASS])
                                                    else:
                                                        res.append([f"Max Δtemp: {tempdata2['Temp_Rise']}℃ found at {round(tempdata2['startTime'],3)} sec (t1+15min), Expected: <= 25℃", Enums.TestResult.FAIL])
                                                else:
                                                    res.append([f"Max Δtemp not found", Enums.TestResult.FAIL])
                                                nxt_start = pla2[2]
                                                # break
                                            pla_cnt1 += 1

                                        # TPRPLA_2[PRECT] >= PTx ECAP[Potential Load Power]- 2%
                                        if pla2[2] >= pwr_mtrid: 
                                            if prect >= (0.98*ECAPppwr):  
                                                pla_cnt2 += 1
                                                if pla_cnt2 == 1:
                                                    t_start = pla2[0]
                                                    prect_min = [prect,pla2[0]]
                                                    prect_max = [prect,pla2[0]]
                                                else:
                                                    if prect < prect_min[0]:
                                                        prect_min = [prect,pla2[0]]
                                                    if prect > prect_max[0]:
                                                        prect_max = [prect,pla2[0]]
                                                
                                                # 150 sec
                                                if pla2[0] - t_start >= 150:
                                                    res.append([f"TPR PLA_2 Prect >= PTx ECAP[Potential Load Power]- 2% for greatert than 150 sec",Enums.TestResult.PASS])
                                                    res.append([f"Minimum Prect: {prect_min[0]} W at {round(prect_min[1],3)} sec",Enums.TestResult.PASS])
                                                    res.append([f"Maximum Prect: {prect_max[0]} W at {round(prect_max[1],3)} sec",Enums.TestResult.PASS])
                                                    break
                                            else:
                                                pla_cnt2 = 0
                                                t_start = 0
                                                prect_min = []
                                                prect_max = []
                                        start = pla2[2]+1
                                    start += 1
                                
                                pwrs = [10,1]
                                temp_lmts = [15,10]
                                for pwr,temp_lmt in zip(pwrs,temp_lmts):
                                    setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(pwr*1000)}mW",limit=[nxt_start,Flow_limit[1]],Type='TesterMsg')
                                    print('nxt_start:',nxt_start)
                                    print('setload:',setload)
                                    if len(setload)>2:
                                        res.append([f"Set_Load {int(pwr*1000)}mW packet found at {round(setload[0],3)}sec",Enums.TestResult.PASS])
                                        tempdata3 = self.Thermaldata(csv_path,setload[1]+900)  # after 15 min
                                        print("tempdata3:",tempdata3)
                                        if tempdata3:
                                            if float(tempdata3['Temp_Rise']) <= temp_lmt:
                                                res.append([f"Max Δtemp: {tempdata3['Temp_Rise']}℃ found at {round(tempdata3['startTime'],3)} sec {"(t1+30)" if pwr == 10 else "(t1+45)"}, Expected: <= {temp_lmt}℃", Enums.TestResult.PASS])
                                            else:
                                                res.append([f"Max Δtemp: {tempdata3['Temp_Rise']}℃ found at {round(tempdata3['startTime'],3)} sec {"(t1+30)" if pwr == 10 else "(t1+45)"}, Expected: <= {temp_lmt}℃", Enums.TestResult.FAIL])
                                        else:
                                            res.append([f"Max Δtemp not found", Enums.TestResult.FAIL])
                                        nxt_start = setload[2]
                                    else:
                                        res.append([f"Set_Load {int(pwr*1000)}mW packet not found", Enums.TestResult.FAIL])
                                # cloak
                                #Cloak enter
                                clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[Flow_limit[1],len(self.file_list)-1],Type="Packet")
                                print("clk_ping:",clk_ping)
                                if len(clk_ping) > 2:
                                    reason =self.PktMethod.GetPayloadDetails(clk_ping[2],'Reason')[0]["sDescription"].split(":")[-1].strip()
                                    rsn_chk =  CommonMethods.check_measure(["Generic"],reason,"EQL")
                                    # print("reason:",rsn_chk)
                                    clk_resp = self.file_list[clk_ping[2]+1].get('pktType')
                                    res.append([f"Cloak enter found with reason:{reason} at {round(clk_ping[0],3)} sec and received {self.file_list[clk_ping[2]+1].get('pktType')}", rsn_chk[1]])
                                    tempdata4 = self.Thermaldata(csv_path,clk_ping[1]+1800)  # after 30 min
                                    print("tempdata4:",tempdata4)
                                    if tempdata4:
                                        if float(tempdata4['Temp_Rise']) <= 6:
                                            res.append([f"Max Δtemp: {tempdata4['Temp_Rise']}℃ found at {round(tempdata4['startTime'],3)} sec (t1+75min), Expected: <= 6℃", Enums.TestResult.PASS])
                                        else:
                                            res.append([f"Max Δtemp: {tempdata4['Temp_Rise']}℃ found at {round(tempdata4['startTime'],3)} sec (t1+75min), Expected: <= 6℃", Enums.TestResult.FAIL])
                                    else:
                                        res.append([f"Max Δtemp not found", Enums.TestResult.FAIL])
                                else: res.append([f"Cloak enter not found", Enums.TestResult.FAIL])

                                    
                        break            
                                        

        return res

    def Thermaldata(self,file_path,t,max_delT=False):
        res = []
        df = pd1.read_csv(file_path, header=None)

        # Detect header row
        header_row = None
        for i, row in df.iterrows():
            row_str = " ".join(row.astype(str)).lower()
            if "starttime" in row_str and "ambient" in row_str:
                header_row = i
                break

        # Load actual table
        clean_df = pd1.read_csv(file_path, skiprows=header_row)

        # Remove empty columns (FIX)
        clean_df = clean_df.dropna(axis=1, how='all')
        clean_df.columns = ["startTime","Ambient_Temp","Puck_Temp","Temp_Rise"]

        # Clean all columns properly
        clean_df = clean_df.replace("℃", "", regex=True)
        for col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()
            clean_df[col] = pd1.to_numeric(clean_df[col], errors='coerce')

        # Drop invalid rows
        clean_df = clean_df.dropna(subset=["startTime", "Ambient_Temp", "Puck_Temp"])

        input_start_time = t

        closest_idx = (clean_df["startTime"] - input_start_time).abs().idxmin()
        closest_row = clean_df.loc[closest_idx]

        if max_delT:
            t0 = closest_row["startTime"]
            t_end = t0 + 900

            window_df = clean_df[(clean_df["startTime"] >= t0) &(clean_df["startTime"] <= t_end)]

            window_df = window_df.dropna(subset=["Temp_Rise"])

            if not window_df.empty:
                max_row = window_df.loc[window_df["Temp_Rise"].idxmax()]

                res = {
                    "startTime": float(max_row["startTime"]),
                    "Ambient_Temp": float(max_row["Ambient_Temp"]),
                    "Puck_Temp": float(max_row["Puck_Temp"]),
                    "Temp_Rise": float(max_row["Temp_Rise"])
                }
                return res

            return res

        else:
            res = {
                "startTime": float(closest_row["startTime"]),
                "Ambient_Temp": float(closest_row["Ambient_Temp"]),
                "Puck_Temp": float(closest_row["Puck_Temp"]),
                "Temp_Rise": float(closest_row["Temp_Rise"])
            }
            return res

        # input_start_time = t
        # # filtered_df = clean_df[round(clean_df["startTime"],0) == round(input_start_time,0)]
        # closest_idx = (clean_df["startTime"] - input_start_time).abs().idxmin()
        # closest_row = clean_df.loc[closest_idx]
        
        # # Max_tisr in 15 min
        # if max_delT:
        #     # t0 = filtered_df.iloc[0]["startTime"]
        #     # t_end = t0 + 900
        #     t0 = closest_row["startTime"]
        #     t_end = t0 + 900

        #     window_df = clean_df[(clean_df["startTime"] >= t0) &(clean_df["startTime"] <= t_end)]
        #     window_df = window_df.dropna(subset=["Temp_Rise"])
        #     if not window_df.empty:
        #         max_row = window_df.loc[window_df["Temp_Rise"].idxmax()]

        #         # print("Max Temp Rise:", max_row["Temp_Rise"])
        #         # print("At Time:", max_row["startTime"])
        #         res = {"startTime":float(max_row["startTime"]),"Ambient_Temp":float(max_row["Ambient_Temp"]),"Puck_Temp":float(max_row["Puck_Temp"]),"Temp_Rise":float(max_row["Temp_Rise"])}
        #         return res
        #     else:
        #         # print("No valid data in window")
        #         return res

        # else:
        #     if not filtered_df.empty:
        #         matched_index = filtered_df.index[0]
        #         if matched_index > 0:
        #             exact_match_df = clean_df[clean_df["startTime"] == input_start_time]
        #             if not exact_match_df.empty:
        #                 row = exact_match_df.iloc[0]
        #                 res = {"startTime": float(row["startTime"]),"Ambient_Temp": float(row["Ambient_Temp"]),"Puck_Temp": float(row["Puck_Temp"]),"Temp_Rise": float(row["Temp_Rise"])}
        #                 return res
        #             else:
        #                 matched_index = filtered_df.index[0]
        #                 if matched_index > 0:
        #                     prev_row = clean_df.loc[matched_index - 1]
        #                     res = {"startTime": float(prev_row["startTime"]),"Ambient_Temp": float(prev_row["Ambient_Temp"]),"Puck_Temp": float(prev_row["Puck_Temp"]),"Temp_Rise": float(prev_row["Temp_Rise"])}
        #                     return res
        #                 else:
        #                     return res
        #     return res
                    
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
                        res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: Mode2: {mode2}", Enums.TestResult.PASS if mode2 == PrefMode2 else Enums.TestResult.FAIL])
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

    def PLAOffsetCheck(self,Flow_limit,Check):
        res = []
        duration_flag = False
        removepwr = False
        duration = None
        nak_chk =False
        AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        Flow_limit = Flow_limit
        # print("Flow_limit:",Flow_limit)

        if "after" in Check:
            TempPkt = Check['after']
        else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]
        #1.check for stabilizaton
        TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
        if len(TempPkt1)>2:
            res.append([f"Prect offset: {Check['FixedOffsetValues']['Prect']} W and RP offset: {Check['FixedOffsetValues']['RP']} W applied from {TempPkt[0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}",Enums.TestResult.PASS])
            packetCount = 0
            #2.Find PLA packts has power offset
            id = TempPkt1[2]
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    if len(TempPkt3)>2 and len(TempPkt4)>2:
                        packetCount+=1
                        RP_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[1]
                        Prect_Actual = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt4[2]]['pktType'])[0]

                        RP_Offset = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[1]
                        Prect_Offset =  GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['value'])[0]
                        
                        Prect_Rcv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"PRECT")[0]['sDescription'])[0]
                        RP_Rcvd = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'])[0]
                        
                    
                        #check for offset value are applied as like mentioned in the CTS
                        if 'FixedOffsetValues' in Check:
                            # # print(RP_Offset,Prect_Offset)
                            if RP_Offset!=Check['FixedOffsetValues']['RP'] or Prect_Offset!=Check['FixedOffsetValues']['Prect']:
                                res.append([f"PLA offset issue at {round(TempPkt2[0],3)}: RP Offset:{RP_Offset}W Expected :{Check['FixedOffsetValues']['RP']}, Prect Offset:{Prect_Offset}W Expected :{Check['FixedOffsetValues']['Prect']}W",Enums.TestResult.FAIL])
                        
                        
                        res.append([f"PLA_2 packet found at {round(TempPkt2[0],3)}sec with following values", Enums.TestResult.PASS])
                        #Ensure that the offset calculations are correct
                        Prect_Calcluated = round((Prect_Actual-Prect_Offset),3)
                        RP_Calculated = round((RP_Actual-RP_Offset),3)

                        if Prect_Rcv == Prect_Calcluated and RP_Rcvd == RP_Calculated:
                            res.append([f"Calculated Prect = {Prect_Calcluated} W, Obtained Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and Calculated RP = {RP_Calculated} W, Obtained RP={RP_Rcvd}W, RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.PASS])
                        elif Prect_Calcluated < 0 and Prect_Rcv == 0 and RP_Rcvd == RP_Calculated:
                            res.append([f"Calculated Prect = {Prect_Calcluated} W is considered as 0 W as it is < 0 W, Obtained Prect={Prect_Rcv} W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and Calculated RP = {RP_Calculated} W, Obtained RP={RP_Rcvd}W, RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.PASS])
                            # res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW and calculated power {calculated_pwr} mW is considered as 0 mW as it is < 0 mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                        elif Prect_Rcv == Prect_Calcluated and RP_Calculated < 0 and RP_Rcvd == 0:
                            res.append([f"Calculated Prect = {Prect_Calcluated} W, Obtained Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and Calculated RP = {RP_Calculated} W is considered as 0 W as it is < 0 W, Obtained RP={RP_Rcvd}W, RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.PASS])
                        elif Prect_Calcluated < 0 and Prect_Rcv == 0 and RP_Calculated < 0 and RP_Rcvd == 0:
                            res.append([f"Calculated Prect = {Prect_Calcluated} W is considered as 0 W as it is < 0 W, Obtained Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and Calculated RP = {RP_Calculated} W is considered as 0 W as it is < 0 W, Obtained RP={RP_Rcvd}W, RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.PASS])
                        else:
                            res.append([f"Mismatch in calculated and obtained power values. Calculated Prect = {Prect_Calcluated} W, Obtained Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and Calculated RP = {RP_Calculated} W, Obtained RP={RP_Rcvd}W, RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.FAIL])
                        # if Prect_Rcv == round((Prect_Actual-Prect_Offset),3) and RP_Rcvd == round((RP_Actual-RP_Offset),3):
                        #     res.append([f"PLA_2 packet found at {round(TempPkt2[0],3)}sec with Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and RP={RP_Rcvd}W,RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.PASS])
                        # else: res.append([f"Mismatch with power values in PLA_2 packet found at {round(TempPkt2[0],3)}sec with Prect={Prect_Rcv}W, Prect_Actual = {Prect_Actual}W, Prect_Offset={Prect_Offset}W and RP={RP_Rcvd}W,RP_Actual={RP_Actual}W, RP_offset={RP_Offset}W", Enums.TestResult.FAIL])
                        
                        # PLA response
                        x = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                        if x is not None:
                            if 'exp_resp' in Check:
                                if 'Response' in self.PktMethod.GetPacketType(x):
                                    if Check["exp_resp"]["resp_comp"] == "EQL":
                                        if self.file_list[x]['pktType'] in Check["exp_resp"]["resp_value"]:
                                            res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", Enums.TestResult.PASS])
                                        else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", Enums.TestResult.FAIL])
                                    elif Check["exp_resp"]["resp_comp"] == "NEQL":
                                        if self.file_list[x]['pktType'] not in Check["exp_resp"]["resp_value"]:
                                            res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", Enums.TestResult.PASS])
                                        else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", Enums.TestResult.FAIL])
                            else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}", Enums.TestResult.PASS])
                            
                            # Throttle check
                            if 'Throttle' in Check:
                                if 'NAK' in self.file_list[x]['pktType']:
                                    nak_chk = True
                                    vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                    irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                    Prect1 = vrect1*irect1

                                    vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                    irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                    Prect2 = vrect2*irect2
                                    
                                    pwr_diff = round((Prect2-Prect1)*1000,3)
                                
                                    if Check['Throttle']:
                                        if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                            res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                                        else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                                    else:
                                        if pwr_diff <= 50:
                                            res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                                        else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                                elif 'ACK' in self.file_list[x]['pktType']:
                                    res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                        
                        #check PLA until
                        if 'CheckDuration' in Check:
                            # # print('diff',TempPkt2[0] - TempPkt1[0])
                            duration = (TempPkt2[0] - TempPkt1[0])
                            if (TempPkt2[0] - TempPkt1[0]) >= Check['CheckDuration']:
                                duration_flag = True
                                break
                    id = TempPkt2[2]+1
                else:break
            # Power remove
            if 'Remove_Power' in Check:
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
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

            if packetCount == 0: 
                res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
            elif not nak_chk:
                res.append([f"Received {packetCount} PLA Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.PASS])
            else:res.append([f"Received {packetCount} PLA Packets with offset value between {self.PktMethod.Timeconvert(TempPkt1[0])} - {self.PktMethod.Timeconvert(self.file_list[Flow_limit[1]]['stopTime'])}",Enums.TestResult.PASS])
        else:res.append([f"{TempPkt[0]} packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res

        
    def PLAOffsetCheck2(self,Flow_limit,Check):
        print("PLAOffsetCheck2")
        res = []
        duration_flag = False
        removepwr = False
        duration = None
        nak_chk =False
        AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        Flow_limit = Flow_limit
        # print("Flow_limit:",Flow_limit)

        if "after" in Check:
            TempPkt = Check['after']
        else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]
        #1.check for stabilizaton
        TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
        if len(TempPkt1)>2:
            res.append([f"{Check['ReceivedPower_offset']} offset applied from {TempPkt[0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}",Enums.TestResult.PASS])
            packetCount = 0
            #2.Find PLA packts has power offset
            id = TempPkt1[2]
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    if len(TempPkt3)>2 and len(TempPkt4)>2:
                        packetCount += 1
                        Received_Power = float(self.file_list[TempPkt4[2]]['value'].split("Received:")[1].split("mW")[0].strip())
                        RP_offset = float(self.file_list[TempPkt3[2]]['value'].split("RP offset:")[1].split("W")[0].strip())*1000

                        PLA_ReceivedPower = round(float(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'].split(":")[1].split("W")[0].strip())*1000,1)
                        # print("PLA_ReceivedPower:",PLA_ReceivedPower)

                        # print("Received_Power:",Received_Power,"RP_offset:",RP_offset)
                        if abs(Check['ReceivedPower_offset']) == RP_offset:
                            # print("same offset applied")
                            pass
                        else: res.append([f"Mismatch in offset applied: {RP_offset} mW, Expected offset: {abs(Check['ReceivedPower_offset'])}", Enums.TestResult.FAIL])
                        
                        # if PLA_ReceivedPower == (Received_Power + Check['ReceivedPower_offset']):
                        #     res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW is matching to calculated power: {(Received_Power + Check['ReceivedPower_offset'])} mW after applying {Check['ReceivedPower_offset']} mW offset at {self.PktMethod.Timeconvert(TempPkt2[0])}", Enums.TestResult.PASS])
                        # else: res.append([f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {(Received_Power + Check['ReceivedPower_offset'])} mW after applying {Check['ReceivedPower_offset']} mW offset at {self.PktMethod.Timeconvert(TempPkt2[0])}", Enums.TestResult.FAIL])

                        calculated_pwr = (Received_Power + Check['ReceivedPower_offset'])
                        if calculated_pwr > 0:
                            if PLA_ReceivedPower == calculated_pwr:
                                res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW is matching to calculated power: {calculated_pwr} mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                            else: res.append([f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {calculated_pwr} mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", Enums.TestResult.FAIL])
                        else:
                            if PLA_ReceivedPower == 0:
                                res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW and calculated power {calculated_pwr} mW is considered as 0 mW as it is < 0 mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])
                            else: res.append([f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {calculated_pwr} mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", Enums.TestResult.FAIL])
                        


                        # PLA response
                        x = TempPkt2[2]+1
                        if 'TesterMsg'in self.PktMethod.GetPacketType(x):
                            x += 1
                        if 'exp_resp' in Check:
                            if 'Response' in self.PktMethod.GetPacketType(x):
                                if self.file_list[x]['pktType'] in Check["exp_resp"]:
                                    res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", Enums.TestResult.PASS])
                                else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", Enums.TestResult.FAIL])

                        # Throttle check
                        if 'Throttle' in Check:
                            if 'NAK' in self.file_list[x]['pktType']:
                                nak_chk = True
                                vrect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                irect1 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                Prect1 = vrect1*irect1

                                vrect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                irect2 = self.PktMethod.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                Prect2 = vrect2*irect2
                                
                                pwr_diff = round((Prect2-Prect1)*1000,3)
                                
                                if Check['Throttle']:
                                    if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                                else:
                                    if pwr_diff <= 50:
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                            elif 'ACK' in self.file_list[x]['pktType']:
                                res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])

                        #check PLA until
                        if 'CheckDuration' in Check:
                            # # print('diff',TempPkt2[0] - TempPkt1[0])
                            duration = (TempPkt2[0] - TempPkt1[0])
                            if (TempPkt2[0] - TempPkt1[0]) >= Check['CheckDuration']:
                                duration_flag = True
                                break
                    id = TempPkt2[2]+1    
                else:break

            # Power remove
            if 'Remove_Power' in Check:
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
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

            if packetCount == 0: 
                res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
            elif not nak_chk:
                res.append([f"Received {packetCount} PLA Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.PASS])
            else:res.append([f"Received {packetCount} PLA Packets with offset value between {self.PktMethod.Timeconvert(TempPkt1[0])} - {self.PktMethod.Timeconvert(self.file_list[Flow_limit[1]]['stopTime'])}",Enums.TestResult.PASS])
        else:res.append([f"{TempPkt[0]} packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res

    def PLAThrottleCheck(self,Flow_limit,Check):
        res=[]
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
        #check for the PLA packets after stabilization and ensure no throttle for ACK res and Throttle should happen for the NAK res
        #1.check for stabilizaton
        TempPkt1 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=Flow_limit,Type="TesterMsg")
        if len(TempPkt1)>2:
            res.append([f"Stabilization found at {round(TempPkt1[0],3)}sec",Enums.TestResult.PASS])
            packetCount = 0
            PLANAK_count = 0
            #2.Find PLA packts has power offset
            id = TempPkt1[2]
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    packetCount+=1
                    PktResponse = self.PktMethod.GetPacketResponse(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                    if PktResponse is not None:
                        if 'NAK' in self.file_list[PktResponse]['pktType'] :PLANAK_count+=1
                        #find throttle voltages
                        v1 = self.PlotMethod.CalculateAVGPowerTimePeriod(self.AllChannelData,self.AllChannelData3,(TempPkt2[1]*1000)+Check['V1'], (TempPkt2[1]*1000)+Check['V1']+Check['Average'])
                        v2 = self.PlotMethod.CalculateAVGPowerTimePeriod(self.AllChannelData,self.AllChannelData3,(TempPkt2[1]*1000)+Check['V2'], (TempPkt2[1]*1000)+Check['V2']+Check['Average'])
                        # print(v1,v2) 
                        if v2-v1 <= 50:
                            #found throttle exp for NAK response
                            if "NAK" not in self.file_list[PktResponse]['pktType']:
                                res.append([f"Observed Throttle for PLA packet at {round(TempPkt2[0],3)}sec with {self.file_list[PktResponse]['pktType']} response.P1={round(v1,3)}mW Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms, P2={round(v2,3)}W Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms",Enums.TestResult.FAIL])
                        else:
                            if 'NAK' in self.file_list[PktResponse]['pktType']:
                                res.append([f"Not Observed Throttle for PLA packet at {round(TempPkt2[0],3)}sec with {self.file_list[PktResponse]['pktType']} response.P1={round(v1,3)}mW Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms, P2={round(v2,3)}W Measured between {round((TempPkt2[1]*1000)+Check['V1'],3)}sec-{round((TempPkt2[1]*1000)+Check['V1']+Check['Average'],3)}ms",Enums.TestResult.FAIL])
                    else:res.append([f"Response not found for the PLA packet at {round(TempPkt2[0],3)}sec",Enums.TestResult.FAIL])
                    id = TempPkt2[2]+1
                else:break
            if packetCount == 0:
                res.append([f"No PLA packets found after the stabilization",Enums.TestResult.FAIL])
            else:res.append([f"Found {packetCount} PLA packets after the stabilization",Enums.TestResult.PASS])
            if Check['Throttle']==True:
                if PLANAK_count==0: res.append([f"PLA packet with NAK response not found",Enums.TestResult.FAIL])
            elif Check['Throttle']==False:
                if PLANAK_count!=0: res.append([f"PLA packet with NAK response found",Enums.TestResult.FAIL])
            
        else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res

    def PLA_Throttle2(self,Flow_limit,Check):
        res = []
        duration_flag = False
        removepwr = False
        duration = None
        nak_chk =False
        AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        
        Flow_limit = Flow_limit
        
        # print("Flow_limit:",Flow_limit)

        if "after" in Check:
            TempPkt = Check['after']
        else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]

        #1.check for stabilizaton
        TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
        if len(TempPkt1)>2:
            packetCount = 0
            #2.Find PLA packts has power offset
            id = TempPkt1[2]
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    packetCount+=1
                    # PLA response
                    x = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                    if x is not None:
                        if 'exp_resp' in Check:
                            if 'Response' in self.PktMethod.GetPacketType(x):
                                if Check["exp_resp"]["resp_comp"] == "EQL":
                                    if self.file_list[x]['pktType'] in Check["exp_resp"]["resp_value"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", Enums.TestResult.PASS])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", Enums.TestResult.FAIL])
                                elif Check["exp_resp"]["resp_comp"] == "NEQL":
                                    if self.file_list[x]['pktType'] not in Check["exp_resp"]["resp_value"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", Enums.TestResult.PASS])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", Enums.TestResult.FAIL])
                        else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}", Enums.TestResult.PASS])

                    # Throttle check
                    if 'Throttle' in Check:
                        if 'NAK' in self.file_list[x]['pktType']:
                            nak_chk = True
                            vrect1 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                            irect1 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                            Prect1 = vrect1*irect1

                            vrect2 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                            irect2 = self.CalculateVoltTwindow(TempPkt2[2],AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                            Prect2 = vrect2*irect2

                            pwr_diff = round((Prect2-Prect1)*1000,3)
                            
                            if Check['Throttle']:
                                if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                            else:
                                if pwr_diff <= 50:
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.FAIL])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", Enums.TestResult.PASS])
                        elif 'ACK' in self.file_list[x]['pktType']:
                            res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", Enums.TestResult.PASS])

                    #check PLA until
                    if 'CheckDuration' in Check:
                        # # print('diff',TempPkt2[0] - TempPkt1[0])
                        duration = (TempPkt2[0] - TempPkt1[0])
                        if (TempPkt2[0] - TempPkt1[0]) >= Check['CheckDuration']:
                            duration_flag = True
                            break
                    id = TempPkt2[2]+1    
                else:break

            # Power remove
            if 'Remove_Power' in Check:
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[1],Flow_limit[0]],Type="TesterMsg")
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

            if packetCount == 0: 
                res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
            elif not nak_chk:
                res.append([f"Received {packetCount} PLA Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.PASS])
            else:res.append([f"Received {packetCount} PLA Packets with offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.PASS])
        else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res

    def PLAThrottleCheck_2(self,Flow_limit,Check):
        #Since the PLA thrittle calculations makes issues , only check for the PLA response
        res = []
        PLA_count = 0
        PLA_NAK = 0
        #1.check for stabilizaton
        TempPkt1 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=Flow_limit,Type="TesterMsg")
        if len(TempPkt1)>2:
            res.append([f"Stabilization found at {round(TempPkt1[0],3)}sec",Enums.TestResult.PASS])
            #check for PLA with NAK response
            id =  TempPkt1[2]
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    PLA_count+=1
                    #get response
                    PLAResp = self.PktMethod.GetPacketResponse(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                    if PLAResp is not None:
                        if "NAK" in self.file_list[PLAResp]['pktType']:
                            PLA_NAK+=1
                            respres = Enums.TestResult.PASS if Check["Throttle"]==True else Enums.TestResult.FAIL
                            res.append([f"Found NAK response for the PLA packet at {round(TempPkt2[0],3)}sec",respres])
                    else:res.append([f"Response not found for the PLA_2 packet at {round(TempPkt2[0],3)}sec",Enums.TestResult.FAIL])
                    id=TempPkt2[2]+1
                else:break
            if Check["Throttle"]==True:
                respres= Enums.TestResult.PASS if PLA_NAK>0 else Enums.TestResult.FAIL
            else:respres= Enums.TestResult.FAIL if PLA_NAK>0 else Enums.TestResult.PASS
            res.append([f"Found {PLA_NAK} PLA_2 packet with NAK response out of {PLA_count} PLA_2 packets between {round(self.file_list[TempPkt1[2]]['startTime'],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",respres])
        else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res

    def DPlossCalibration(self,Flow_limit,Check):
        res = []
        if 'PktLimit' in Check:
            Flow_Limit = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
        else: Flow_Limit = Flow_limit

        # PRE CHECK
        # MODEXCAP
        Excapreq = self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Power Modes Extended Capabilities",limit=Flow_limit,Type="Packet")
        if len(Excapreq)> 2:
            # res.append([f"Get Request-PTx Power Modes Extended Capabilities Packet found at {round(Excapreq[0],3)} sec", Enums.TestResult.PASS])
            Excapres = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=[Excapreq[2],Flow_limit[1]],Type="Response")
            if len(Excapres)> 2:
                # res.append([f"MODEXCAP {self.file_list[Excapres[2]]['value']} Packet found at {round(Excapres[0],3)} sec", Enums.TestResult.PASS])
                EXCAP = {"Low_Power_Mode":"","Nominal_Power_Mode":"","High_Power_Mode":"","Continuous_Power_Mode":""}
                for ck in EXCAP.keys():
                    payloadDetails = self.PktMethod.GetPayloadDetails(Excapres[2],ck)
                    # print(ck,":",float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip()))
                    EXCAP[ck] = float(re.split(r"[VW]",payloadDetails[0]['sDescription'].split(":")[1])[0].strip())
                # print("EXCAP:",EXCAP)

                MSRreq = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=Flow_limit,Type="Packet")
                if len(MSRreq)> 2:
                    PrefMode = self.PktMethod.GetPayloadDetails(MSRreq[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                    # print("PrefMode:",PrefMode)
                    # if "chks" in Check:
                    #     if "ModeSwitch" in Check['chks']:
                    if Check.get('ModeSwitch'):
                        if Check["ModeSwitch"]:
                            mode1 = sorted(EXCAP, key=EXCAP.get, reverse=True)[1]  # second highest potential load power
                            mode2 = max(EXCAP, key=EXCAP.get)    # highest potential load power
                            
                            # print("mode1:",mode1, "mode2:",mode2)
                            res.append([f"Potential powers in MODEXCAP is {EXCAP}", Enums.TestResult.PASS])
                            res.append([f"Mode 1 should be {mode1} and Mode 2 should be {mode2}", Enums.TestResult.PASS])
                            res.append([f"Main mode in MSR packet is {PrefMode}, Expected: Mode1: {mode1}", Enums.TestResult.PASS if mode1 == PrefMode else Enums.TestResult.FAIL])

                    if Check.get('New_Modes'):
                        if Check["New_Modes"]:
                            res.append([f"Main mode in MSR packet is {PrefMode}, Expected: Nominal_Power_Mode", Enums.TestResult.PASS if PrefMode =="Nominal_Power_Mode" else Enums.TestResult.FAIL])
                        


                    # DPlossCalibrationCheck started
                    calbPoints = None
                    ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
                    if len(ECAP)>2:
                        # print("cal:",self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'cal')[0]['sRawData']))
                        CAL = self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'cal')[0]['sRawData'])
                        if CAL == 1:
                            res.append([f"Received CAL = 1(Calibration supported) in ECAP packet at {round(ECAP[0],2)} sec, expected: 1", Enums.TestResult.PASS])
                        
                            #1. Check for CAL_ENTER  packet
                            Pkt = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",limit=Flow_limit)
                            if len(Pkt)>2:
                                if CAL == 0 or CAL != 1: res.append([f"Calibration started even though CAL = {CAL} in ECAP packet at {round(ECAP[0],2)} sec, expected: 1", Enums.TestResult.FAIL])
                                CAL_ENTER_STOP = Pkt[1]
                                
                                resume = abs(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt[2],"Resume")[0]['sRawData'])[1])
                                if resume == 0:
                                    res.append([f"Received CAL_ENTER packet at {round(Pkt[0],2)} sec with resume: 0, expected: 0", Enums.TestResult.PASS])
                                else: res.append([f"Received CAL_ENTER packet at {round(Pkt[0],2)} sec with resume: {resume}, expected: 0", Enums.TestResult.FAIL])
                            else:res.append([f"CAL_ENTER packet not recevied",Enums.TestResult.FAIL])

                            #2. Get the of.of Calib points from CAL_ENTER_RSP packet
                            Pkt_res = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=Flow_limit,Type="Response")
                            if len(Pkt_res)>2:
                                calduration =int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_B")[0]['sDescription'])[0])*60
                                calbPoints = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_A")[0]['sDescription'])[0])
                                response = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Response")[0]['sRawData'])[1]
                                # print("response:",response)
                                Reason = self.PktMethod.GetPayloadDetails(Pkt_res[2],"Reason")[0]['sDescription'].split(":")[1].strip()
                                if calduration == 300 and calbPoints >= 80 and response == 1:
                                    res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec",Enums.TestResult.PASS])
                                else: res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec",Enums.TestResult.FAIL])
                            else:res.append([f"CAL_ENTER_RSP packet not recevied",Enums.TestResult.FAIL])

                            if len(Pkt)>2 and len(Pkt_res)>2:
                                #3.ensure the CAL_CAPTURE with count of calib points.
                                id = Pkt[2] if len(Pkt)>2 else Flow_limit[0]
                                CAL_CAPTURE_cnt = 0
                                CalStart = 0
                                CalEnd = 0
                                CalLevels = []
                                prevIndex = 0
                                #Get the calexit packet and set the liimit else consider flow limit
                                pkt_cmt = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="CMT",limit=Flow_limit)
                                
                                DPLC_type = {"DPLC1":{"Level1":{"Power":10,"Voltage":18.5},"Level2":{"Power":12.5,"Voltage":18},"Level3":{"Power":15,"Voltage":16.25},"Level4":{"Power":25,"Voltage":18}},"DPLC2":{"Level1":{"Power":10,"Voltage":18.5},"Level2":{"Power":12.5,"Voltage":18},"Level3":{"Power":15,"Voltage":16.25},"Level4":{"Power":25,"Voltage":18}},"DPLC3":{"Level1":{"Power":8,"Voltage":18},"Level2":{"Power":10,"Voltage":18.5},"Level3":{"Power":12.5,"Voltage":18},"Level4":{"Power":15,"Voltage":16.5}},"DPLC4":{"Level1":{"Power":9,"Voltage":15.4},"Level2":{"Power":12,"Voltage":15.6},"Level3":{"Power":15,"Voltage":15.8},"Level4":{"Power":20,"Voltage":16.1}}}
                                TempLimit = [id,len(self.file_list)-1]#[id,Flow_limit[1]]
                                # print('TempLimit',TempLimit)
                                sts_chk = []
                                
                                newlmt = TempLimit
                                for level,pwr in DPLC_type[Check["DPLC"]].items():
                                    if Check.get('skiplevel'):
                                        if level in Check["skiplevel"]:
                                            # print("skipping")
                                            continue
                                    res.append([f"{Check["DPLC"]}, {level}: {pwr['Power']} W, {pwr['Voltage']} V calibration started ",Enums.TestResult.PASS])
                                    set_load = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(pwr['Power']*1000)}mW",limit=newlmt,Type='TesterMsg')
                                    # print("set_load:",set_load)
                                    if len(set_load)>2:
                                        res.append([f"Set_Load {int(pwr['Power']*1000)}mW packet found at {round(set_load[0],3)} sec",Enums.TestResult.PASS])
                                        id = set_load[2]
                                        ccnt = 0
                                        while id < newlmt[1]:
                                            if 'CAL_CAPTURE' in self.file_list[id]['pktType']:
                                                # # print("ID:",id)
                                                if self.PktMethod.GetPacketType(id)=="Packet":
                                                    ccnt += 1
                                                    prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id,"PRECT")[0]['sDescription'])[0]
                                                    vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id,"VRECT")[0]['sDescription'])[0]
                                                    # print("prect:",prect, ccnt)
                                                    # if abs(prect - pwr['Power']) > 0.01 * pwr['Power'] or abs(vrect - pwr['Voltage']) > 0.01 * pwr['Voltage']:
                                                    if prect <= (pwr['Power']-(pwr['Power']*0.01)) or vrect <= (pwr['Voltage']-(pwr['Voltage']*0.01)):
                                                        res.append([f"CAL_CAPTURE power:{prect}W, voltage:{vrect}W is out range found at {round(self.file_list[id]['startTime'],3)} sec, Expected: Prect>={pwr['Power']*(1-0.01)}W and Vrect>={pwr['Voltage']*(1-0.01)}V",Enums.TestResult.FAIL])
                                                        break
                                                    if CAL_CAPTURE_cnt == 1: CalStart = round(self.file_list[id]['startTime'],3)
                                                    CAL_CAPTURE_cnt+=1
                                
                                                if 'CAL_CAPTURE_RSP' in self.file_list[id+1]['pktType']:
                                                    status = abs(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(id+1,"Status")[0]['sRawData'])[0])
                                                    if status != 0:
                                                        sts_chk.append(status)
                                                        res.append([f"CAL_CAPTURE_RSP response is received with status:{status} for CAL_CAPTURE packet at index@{id+1}, expected:0", Enums.TestResult.FAIL])
                                                if ccnt >= 20: 
                                                    newlmt = [id,TempLimit[1]]
                                                    res.append([f"All CAL_CAPTURE packets have Prect in {round(pwr['Power']-(0.01*pwr['Power']),3)} W - {round(pwr['Power']+(0.01*pwr['Power']),3)} W, Vrect in {round(pwr['Voltage']-(0.01*pwr['Voltage']),3)} V - {round(pwr['Voltage']+(0.01*pwr['Voltage']),3)} V, Expected: 1% of {pwr['Power']}W and 1% of {pwr['Voltage']} V", Enums.TestResult.PASS])
                                                    res.append([f"Received {ccnt} CAL_CAPTURE packets in {level}, Expected: 20", Enums.TestResult.PASS])
                                                    
                                                    break
                                            id+=1

                                        # Renegotiation
                                        if (Check["DPLC"] != "DPLC3" and level == "Level3") or (Check["DPLC"] == "DPLC3" and level == "Level4"):
                                            calop = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="CMT",limit=newlmt)
                                            if len(calop)>2:
                                                res.append([f"CAL_OP(CMT) found at index@{calop[2]}", Enums.TestResult.PASS])
                                                calop_rsp = self.PktMethod.GetPacketDetails(packet="CAL_OP_RSP",limit=[calop[2],newlmt[1]],Type='Response')
                                                if len(calop_rsp)>2:
                                                    res.append([f"CAL_OP_RSP found at index@{calop_rsp[2]}", Enums.TestResult.PASS])
                                                    ECAP2 = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[calop_rsp[2],newlmt[1]],Type="Response")
                                                    if len(ECAP2)>2:
                                                        negpwr2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP2[2],'Negotiable_Load_Power')[0]['sDescription'])[0]
                                                        # print("negpwr2:",negpwr2)
                                                        res.append([f"{self.ECAP_pkt} with Negotiable_Load_Power: {negpwr2}W found at index@{ECAP2[2]}", Enums.TestResult.PASS])
                                                        reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[ECAP2[2],newlmt[1]])
                                                        if len(reneg)>2:
                                                            res.append([f"Renegotiate packet found at index@{reneg[2]}", Enums.TestResult.PASS])
                                                            respid = self.PktMethod.GetPacketResponse(reneg,[reneg[2]+1,newlmt[1]])
                                                            if respid is not None:
                                                                if self.file_list[respid]['pktType'] =="ACK":
                                                                    res.append([f"ACK response found at index@{respid}", Enums.TestResult.PASS])
                                                                    srqepl = self.PktMethod.GetPacketDetails(packet="SRQ",value="Extended Power Level Selection",limit=[respid,newlmt[1]])
                                                                    if len(srqepl)>2:
                                                                        res.append([f"SRQ(Extended Power Level Selection) found at index@{srqepl[2]}", Enums.TestResult.PASS])
                                                                        respid2 = self.PktMethod.GetPacketResponse(srqepl,[srqepl[2]+1,newlmt[1]])
                                                                        if respid2 is not None:
                                                                            if self.file_list[respid2]['pktType'] =="ACK":
                                                                                res.append([f"ACK response found at index@{respid2}", Enums.TestResult.PASS])
                                                                                srqen = self.PktMethod.GetPacketDetails(packet="SRQ",value="End Negotiation",limit=[respid2,newlmt[1]])
                                                                                if len(srqen)>2:
                                                                                    res.append([f"SRQ(End Negotiation) found at index@{srqen[2]}", Enums.TestResult.PASS])
                                                                                    respid3 = self.PktMethod.GetPacketResponse(srqen,[srqen[2]+1,newlmt[1]])
                                                                                    if respid3 is not None:
                                                                                        if self.file_list[respid3]['pktType'] =="ACK":
                                                                                            res.append([f"ACK response found at index@{respid3}", Enums.TestResult.PASS])

                                                                                            if Check["DPLC"] == "DPLC1" and level == "Level3":
                                                                                                continue
                                                                                            renegload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(negpwr2*1000)}mW",limit=[respid3,newlmt[1]],Type='TesterMsg')
                                                                                            # print("renegload:",renegload)
                                                                                            if len(renegload)>2:
                                                                                                res.append([f"Set_Load {int(negpwr2*1000)}mW is found at index@{renegload[2]}", Enums.TestResult.PASS])
                                                                                                self.GetInitailVoltage(Check['flow'],[renegload[2],newlmt[1]])
                                                                                                self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
                                                                                                self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
                                                                                                irect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData3)
                                                                                                vrect = self.PktMethod.CalculateVoltTwindow(self.stability,self.AllChannelData)
                                                                                                power = round(vrect[0]*irect[0],3)
                                                                                                # print("vrect:",vrect,"irect:",irect,"power:",power)
                                                                                                res.append([f"Prect after control stabilization is {power} W at {round(self.file_list[self.stability]['startTime'],3)} sec, Expected: >= {(negpwr2-0.1)}W", Enums.TestResult.PASS if power>=(negpwr2-0.1) else Enums.TestResult.FAIL])
                                                                                            else: res.append([f"Set_Load {int(negpwr2*1000)}mW not found", Enums.TestResult.FAIL])



                                                                                            if Check.get('ModeSwitch'):
                                                                                                if Check["ModeSwitch"]:
                                                                                                    if Check.get('skiplevel'):
                                                                                                        # if level in Check["skiplevel"]:
                                                                                                        index = list(DPLC_type[Check["DPLC"]].keys()).index(level)
                                                                                                        # print("index:",index,list(DPLC_type[Check["DPLC"]].keys())[index+1])
                                                                                                        if list(DPLC_type[Check["DPLC"]].keys())[index+1] in Check["skiplevel"]:
                                                                                                            # newlmt = [renegload[2],TempLimit[1]]
                                                                                                            continue
                                                                                                
                                                                                                    calext = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",value="Clear: Retain CAL points",limit=[respid3,newlmt[1]])
                                                                                                    if len(calext)>2:
                                                                                                        clear = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(calext[2],"clear")[0]['sRawData'])[0]
                                                                                                        res.append([f"CAL_EXIT(Clear: Retain CAL points) with clear: {clear} found at index@{calext[2]}, Expected: 0", Enums.TestResult.PASS if clear == 0 else Enums.TestResult.FAIL])
                                                                                                    else: res.append([f"CAL_EXIT(Clear: Retain CAL points) not found", Enums.TestResult.FAIL])
                                                                                                    MSRreq2 = self.PktMethod.GetPacketDetails(packet="MSR",value="Main Mode",limit=[respid3,newlmt[1]],Type="Packet")
                                                                                                    if len(MSRreq2)> 2:
                                                                                                        PrefMode2 = self.PktMethod.GetPayloadDetails(MSRreq2[2],"MainMode")[0]['sDescription'].split(":")[-1].strip().replace(" ","_")
                                                                                                        # print("PrefMode2:",PrefMode2)
                                                                                                        res.append([f"Main mode in MSR packet is {PrefMode2}, Expected: Mode2: {mode2}", Enums.TestResult.PASS if mode2 == PrefMode2 else Enums.TestResult.FAIL])
                                                                                                        MSS2 = self.PktMethod.GetPacketDetails(packet="MSS",value="Status: SUCCESS | Error Code: NO_ERR",limit=[MSRreq2[2],newlmt[1]],Type="Response")
                                                                                                        if len(MSS2)> 2:
                                                                                                            res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response found at {round(MSS2[0],3)} sec", Enums.TestResult.PASS])

                                                                                                            Pkt = self.PktMethod.GetPacketDetails(packet="CAL_ENTER",value="Resume: 1",limit=[MSS2[2],newlmt[1]])
                                                                                                            if len(Pkt)>2:
                                                                                                                Resume = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt[2],"Resume")[0]['sRawData'])[1]
                                                                                                                # print("Resume:",Resume)
                                                                                                                res.append([f"CAL_ENTER(Resume: 1) with Resume: {Resume} found at index@{Pkt[2]}, Expected: 1", Enums.TestResult.PASS if Resume == 1 else Enums.TestResult.FAIL])
                                                                                                                Pkt_res = self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP",limit=[Pkt[2],newlmt[1]],Type="Response")
                                                                                                                if len(Pkt_res)>2:
                                                                                                                    calduration =int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_B")[0]['sDescription'])[0])*60
                                                                                                                    calbPoints = int(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Parameter_A")[0]['sDescription'])[0])
                                                                                                                    response = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt_res[2],"Response")[0]['sRawData'])[1]
                                                                                                                    # print("response:",response)
                                                                                                                    Reason = self.PktMethod.GetPayloadDetails(Pkt_res[2],"Reason")[0]['sDescription'].split(":")[1].strip()
                                                                                                                    if calduration == 300 and calbPoints >= 80 and response == 1:
                                                                                                                        res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec",Enums.TestResult.PASS])
                                                                                                                    else: res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0],2)} sec with Response: {response}, expected: 1, Reason: {Reason}, Calib points of {calbPoints}, expected:>=80, and Calib Duration of {calduration}sec, expected; 300sec",Enums.TestResult.FAIL])
                                                                                                                    Pktop = self.PktMethod.GetPacketDetails(packet="CAL_OP",value="Operation: INIT",limit=[Pkt_res[2],newlmt[1]])
                                                                                                                    if len(Pktop)>2:
                                                                                                                        res.append([f"CAL_OP(Operation: INIT) found at index@{Pktop[2]}", Enums.TestResult.PASS])
                                                                                                                        Pktop_res = self.PktMethod.GetPacketDetails(packet="CAL_OP_RSP",limit=[Pktop[2],newlmt[1]],Type="Response")
                                                                                                                        if len(Pktop_res)>2:
                                                                                                                            newlmt = [Pktop_res[2],TempLimit[1]]
                                                                                                                            res.append([f"CAL_OP_RSP found at index@{Pktop_res[2]}", Enums.TestResult.PASS])
                                                                                                                        else: res.append([f"CAL_OP_RSP not found", Enums.TestResult.FAIL])
                                                                                                                    else: res.append([f"CAL_OP(Operation: INIT) not found", Enums.TestResult.FAIL])
                                                                                                                else: res.append([f"CAL_OP_RSP not found", Enums.TestResult.FAIL])
                                                                                                            else: res.append([f"CAL_ENTER(Resume: 1) not found", Enums.TestResult.FAIL])

                                                                                                        else: res.append([f"MSS(Status: SUCCESS | Error Code: NO_ERR) response not received", Enums.TestResult.FAIL])
                                                                                                    else: res.append([f"MSR(Main mode) packet not found", Enums.TestResult.FAIL])

                                                                                        else: res.append([f"NAK response received", Enums.TestResult.FAIL])
                                                                                    else: res.append([f"Response not found for SRQ(End Negotiation)", Enums.TestResult.FAIL])
                                                                                else: res.append([f"SRQ(End Negotiation) not found", Enums.TestResult.FAIL])
                                                                            else: res.append([f"NAK response received", Enums.TestResult.FAIL])
                                                                        else: res.append([f"Response not found for SRQ(Extended Power Level Selection)", Enums.TestResult.FAIL])
                                                                    else: res.append([f"SRQ(Extended Power Level Selection) not found", Enums.TestResult.FAIL])
                                                                else: res.append([f"NAK response received", Enums.TestResult.FAIL])
                                                            else: res.append([f"Response not found for Renegotiate", Enums.TestResult.FAIL])
                                                        else: res.append([f"Renegotiate not found", Enums.TestResult.FAIL])
                                                    else: res.append([f"{self.ECAP_pkt} not found", Enums.TestResult.FAIL])
                                                else: res.append([f"CAL_OP_RSP not found", Enums.TestResult.FAIL])
                                            else: res.append([f"CAL_OP(CMT) not found", Enums.TestResult.FAIL])



                                    else: res.append([f"{level}, {int(pwr['Power']*1000)}mW is not set",Enums.TestResult.FAIL])

                                if len(sts_chk) == 0:
                                    res.append(["Received CAL_CAPTURE_RSP responses with status:0 for all CAL_CAPTURE packets, expected:0", Enums.TestResult.PASS])

                                
                                if calbPoints is not None:
                                    if Check.get('skiplevel'):
                                        pointlmt = (4-len(Check["skiplevel"]))*20
                                    else: pointlmt = 80
                                    if CAL_CAPTURE_cnt >= pointlmt:
                                        res.append([f"Recived all the {CAL_CAPTURE_cnt} CAL_CAPTURE packets, Expected: >= {pointlmt}",Enums.TestResult.PASS])
                                    else: 
                                        #If all calib points not recvd, then check for the renego happened for 15W else it's Fail
                                        res.append([f"Mismatch in CAL_CAPTURE packet count, Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}, Expected: >= {pointlmt}",Enums.TestResult.FAIL])
                                else: res.append([f"CAL_ENTER_RSP packet not recevied, Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}",Enums.TestResult.FAIL])

                                
                                #6.Verify CAL_EXIT packet 
                                pkt_exit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",value="Clear: Retain CAL points",limit=newlmt)
                                if len(pkt_exit)>2:
                                    clear = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(pkt_exit[2],"clear")[0]['sRawData'])[0]
                                    res.append([f"CAL_EXIT(Clear: Retain CAL points) with clear: {clear} found at index@{pkt_exit[2]}", Enums.TestResult.PASS])
                                
                                    #6b, Ensure the CAlib duration which is mentioned on the CAL_ENTER_RSP packet , and calculate the interval btw CAL_ENTER to CAL_EXIT
                                    if CAL_ENTER_STOP and calduration:
                                        if (pkt_exit[0]-CAL_ENTER_STOP) > calduration:
                                            res.append([f"Calculated Calib duration is {round(pkt_exit[0]-CAL_ENTER_STOP,2)}Sec, which is not in limit of {calduration}Sec",Enums.TestResult.FAIL])
                                        else:res.append([f"Calculated Calib duration is {round(pkt_exit[0]-CAL_ENTER_STOP,2)}Sec, which is in limit of {calduration}Sec",Enums.TestResult.PASS])
                                    else:res.append([f"CAL_ENTER Packet or CAL duration not found",Enums.TestResult.PASS])
                                else: res.append([f"CAL_EXIT(Clear: Retain CAL points) not found", Enums.TestResult.FAIL])

                                #7.Check the Alpha and Beta values from the DPCAL_PARAM packet.
                                pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM",limit=newlmt,Type="Response")
                        
                                if len(pkt_DPM)>2:
                                    alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
                                    beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
                                    if any(r == 0 for r in [alpha,beta]):
                                        res.append([f"The DPCAL_PARAM packet wit Alpha: {alpha}, Beta: {beta} received at {round(pkt_DPM[0],2)}sec",Enums.TestResult.FAIL])
                                    else:res.append([f"The DPCAL_PARAM packet with Alpha: {alpha}, Beta: {beta} received at {round(pkt_DPM[0],2)}sec",Enums.TestResult.PASS])
                                else:res.append([f"DPCAL_PARAM packet not recevied",Enums.TestResult.FAIL])
                        

                            
                        elif CAL == 0:
                            res.append([f"Received CAL = 0(Calibration not supported) in ECAP packet at {round(ECAP[0],2)} sec, expected: 0", Enums.TestResult.PASS])
                        else: res.append([f"Received CAL = {CAL} in ECAP packet at {round(ECAP[0],2)} sec, expected: 0 or 1", Enums.TestResult.FAIL])
        return res








    def DPLOSS_PARAMETER_CLEAR(self,Flow_limit,Check):
        res = []
        ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
        if len(ECAP)>2:
            CAL = self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'cal')[0]['sRawData'])
            if CAL == 0:
                res.append([f"Received CAL = 0(Calibration not supported) in ECAP packet at {round(ECAP[0],2)} sec, expected: 0", Enums.TestResult.PASS])
            elif CAL == 1:
                tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                dplosschks = self.DPlossCalibration(Flow_limit,tempcheck)
                # print(chk for chk in dplosschks)
                for chk in dplosschks:
                    res.append(chk)
                calexit = self.PktMethod.GetPacketDetails(packet="CAL_EXIT",limit=[ECAP[2],Flow_limit[1]],Type="Packet")
            else:
                res.append([f"Received CAL = {CAL} in ECAP packet at {round(ECAP[0],2)} sec, expected: 0 or 1", Enums.TestResult.FAIL])

        

        return res



    def CAL_CAPCheck(self,Flow_limit,Check):
        res = []
        pkt_DPM = self.PktMethod.GetPacketDetails(packet="DPCAL_PARAM [0x54]",limit=Flow_limit,Type="Response")
        if len(pkt_DPM)>2:
            CAL_PKT = self.PktMethod.GetPacketDetails(packet="CAL_CAP [0x43]",limit=[pkt_DPM[2],Flow_limit[1]],Type="Response")
            # # print("pkt_CALCAP:",pkt_DPM)
            # # print("CAL_PKT:",CAL_PKT)
            # # print("hvjk",self.PktMethod.GetPayloadDetails(CAL_PKT[2],"CAL_M0: Calibration Mode 0 is supported"))
            if len(CAL_PKT) > 1:
                CAL_M0 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(CAL_PKT[2],"CAL_M0: Calibration Mode 0 is supported")[0]['sRawData'])[1]
                if CAL_M0 == 1:
                    res.append([f"CAL_M0: Found CAL_CAP [0x43] packet at @index {CAL_PKT[2]} and CAL_M0 is set to {CAL_M0}, Expected: CAL_M0 = 1", Enums.TestResult.PASS])
                else: res.append([f"CAL_M0: Found CAL_CAP [0x43] packet at @index {CAL_PKT[2]} and CAL_M0 is set to {CAL_M0}, Expected: CAL_M0 = 1", Enums.TestResult.FAIL])
            else: res.append(["CAL_CAP [0x43] packet is not found.", Enums.TestResult.FAIL])
        else: res.append(["DPCAL_PARAM [0x54] packet is not found.", Enums.TestResult.INCONCLUSIVE])
        # # print("CAL_CAPCheck:",res)
        return res

    def CalculateGainG(self,Flow_limit,Check):
        res = []
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        #1. Get mentiond load
        loadpkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Load']}",limit=Flow_limit,Type="TesterMsg")
        if len(loadpkt)>2:
            res.append([f"Found set load {Check['Load']}mA packet at {round(loadpkt[0],3)}Sec",Enums.TestResult.PASS])
            #find the Inv packet
            InvPkt = self.PktMethod.GetPacketDetails(packet=self.Inv_vol_pkt,limit=[loadpkt[2],Flow_limit[1]],Type="Response")
            if len(InvPkt)>2:
                res.append([f"The Inverter_Voltage packet found at {round(InvPkt[0],3)}sec",Enums.TestResult.PASS])
                #Calculate G 
                Vinv = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(InvPkt[2],"Vinv")[0]['sDescription'])[0]
                Vrect = self.PktMethod.CalculateVoltTwindow(InvPkt[2]-1,self.AllChannelData)
                ChkRes = CommonMethods.check_measure(Check['expected'],round(Vrect[0]/Vinv,2),Check['comp'])
                res.append([f"Calculated G is {round(Vrect[0]/Vinv,2)} limit {ChkRes[2]}, where Vinv={Vinv}V measured at {round(InvPkt[0],3)}sec and Vrect={Vrect[0]}V measured at {round(self.file_list[InvPkt[2]-1]['startTime'],3)}sec",ChkRes[1]])
            else:res.append([f"The Inverter_Voltage packet not found between",Enums.TestResult.FAIL])
        else:res.append([f"Set load {Check['Load']}mA packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
        return res

    def PrectWithLoads(self,Flow_limit,Check):
        res=[]
        #1. Get mentiond load
        TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load 1040",limit=Flow_limit,Type="TesterMsg")
        if len(TempPkt1)>2:
            #iterat with all prects
            cnt = 1
            res.append([f"Found set load 1040mA packet at {round(TempPkt1[0],3)}Sec",Enums.TestResult.PASS])
            TempLimit = [TempPkt1[2]+1,Flow_limit[1]]
            for prect in Check['expected']:
                TempPkt2 =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {prect['Load']}",limit=TempLimit,Type="TesterMsg")
                # print("TempPkt2:",TempPkt2)
                if len(TempPkt2)>2:
                    res.append([f"Prect_{cnt}:Found set load {prect['Load']}mW packet at {round(TempPkt2[0],3)}Sec",Enums.TestResult.PASS])
                    #find the stabilization
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[TempPkt2[2],Flow_limit[1]],Type="TesterMsg")
                    # print("TempPkt3:",TempPkt3)
                    if len(TempPkt3)>2:
                        res.append([f"Prect_{cnt}:Stabilization found at {round(TempPkt3[0],3)}sec",Enums.TestResult.PASS])
                        #Get Prect from PLA
                        TempPkt4 = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[TempPkt3[2],Flow_limit[1]])
                        # print("TempPkt4:",TempPkt4)
                        if len(TempPkt4)>2:
                            Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(TempPkt4[2],"PRECT")[0]['sDescription'])[0]
                            ChkRes = CommonMethods.check_measure(prect['exp'],Prect,prect['comp'])
                            res.append([f"Prect_{cnt}:Found PLA_2 packet at {round(TempPkt4[0],3)}sec with Prect {Prect}W, limit {ChkRes[2]}W",ChkRes[1]])
                        else:res.append([f"Prect_{cnt}:PLA packet not found between {round(TempPkt3[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                    else:res.append([f"Prect_{cnt}:Stabilization is not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                    TempLimit=[TempPkt2[2]+1,Flow_limit[1]]
                else:res.append([f"Prect_{cnt}:Set load {prect['Load']}mA packet not found between {round(TempPkt2[0],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
                cnt+=1
        else:res.append([f"Set_Load 1040mA packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}",Enums.TestResult.FAIL])
        # # print("PrectWithLoad:",res)
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
                                # if "t_gap" in chk:
                                #     CEx = self.PktMethod.GetPacketDetails(packet=f"Extended Control Error",limit=[TempPkt5[2],TempPkt2[2]],Type="Packet")
                                #     if len(CEx)>2:
                                #         res.append([f"Required time period is 51 ms ± 2 ms, i.e, (t_xceresponsetimeout = 20 ms + t_delay = 5 ms + t_active = 21 ms + 5 ms ± 2 ms)", Enums.TestResult.PASS])
                                #         t_req = (TempPkt5[0]-CEx[1])*1000
                                #         chk_resx = CommonMethods.check_measure(chk['t_gap'],t_req,0)
                                #         res.append([f"The time between Extended Control Error and Set_load {int(PotLoad/2)}mW is {chk_resx[3]} ms, Expected: {chk_resx[3]} ms",chk_resx[1]])
                                #     else: res.append([f"Extended Control Error packet not found before Set_load {int(PotLoad/2)}mW",""])

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
                res.append([f"ECAP values: {ECAP}", Enums.TestResult.PASS])
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
                res.append([f"EXCAP values: {EXCAP}", Enums.TestResult.PASS])
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

        res.append([f"Test results validation starts from here:", Enums.TestResult.PASS])


        if ECAP == {'LPM': 1, 'NPM': 0, 'HPM': 0, 'CPM': 0}:
            res.append([f"Power modes in MODECAP packet are {ECAP}", Enums.TestResult.PASS])
            if EXCAP["LPMVoltage_Ref0"] != 0:
                res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"LPMVoltage_Ref0 is {EXCAP["LPMVoltage_Ref0"]} V, Expected: != 0 V", Enums.TestResult.FAIL])

            if EXCAP["LPMVoltage_Ref1"] != 0:
                res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.PASS])
            else: res.append([f"LPMVoltage_Ref1 is {EXCAP["LPMVoltage_Ref1"]} V, Expected: != 0 V", Enums.TestResult.FAIL])
            
            if EXCAP["Low_Power_Mode"] != 0 and EXCAP["Low_Power_Mode"] <= 10:
                res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: != 0 W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", Enums.TestResult.PASS])
            else: res.append([f"LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: != 0 W and LPM Potential Load Power is {EXCAP["Low_Power_Mode"]} W, Expected: <= 10 W", Enums.TestResult.FAIL])

            if all(EXCAP[key] == 0 for key in EXCAP if key not in ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]):
                res.append([f'All values are equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]', Enums.TestResult.PASS])
            else: res.append([f'All values are not equal to zero in EXCAP except ["LPMVoltage_Ref0","LPMVoltage_Ref1","Low_Power_Mode"]', Enums.TestResult.FAIL])

            if all(GMP[key] == 0 for key in GMP):
                res.append([f'All values are equal to zero in GMP', Enums.TestResult.PASS])
            else: res.append([f'All values are not equal to zero in GMP', Enums.TestResult.FAIL])

        elif ECAP == {'LPM': 1, 'NPM': 1, 'HPM': 0, 'CPM': 0}:
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
        
    def PrectWithMODECAP(self,Flow_limit,Check):
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        res = []
        TypeSD = ""
        TyepDscr = ""
        # print(self.Header['TestcaseName'])
        if 'NPM' in self.Header['TestcaseName']:
            TypeSD = "NPM"
            TyepDscr = "Nominal_Power_Mode"
        elif 'LPM' in self.Header['TestcaseName']:
            TypeSD = "LPM"
            TyepDscr = "Low_Power_Mode"
        elif 'HPM' in self.Header['TestcaseName']:
            TypeSD = "HPM"
            TyepDscr = "High_Power_Mode"
        elif 'CPM' in self.Header['TestcaseName']:
            TypeSD = "CPM"
            TyepDscr = "Continuous_Power_Mode"


        #1. Find the MODEXCAP packet
        TempPkt1 = self.PktMethod.GetPacketDetails(packet="MODEXCAP",limit=Flow_limit,Type="Response")
        if len(TempPkt1)>2:
            # print(TypeSD,TyepDscr,TempPkt1)
            TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref0")[0]['sDescription']
            if ':' in TempVal:TempVal = TempVal.split(':')[1]
            ref0 = GeneralMethods.GetFloatFromStr(TempVal)[0]
            
            TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],f"{TypeSD}Voltage_Ref1")[0]['sDescription']
            if ':' in TempVal:TempVal = TempVal.split(':')[1]
            ref1 = GeneralMethods.GetFloatFromStr(TempVal)[0]
            
            TempVal = self.PktMethod.GetPayloadDetails(TempPkt1[2],TyepDscr)[0]['sDescription']
            if ':' in TempVal:TempVal = TempVal.split(':')[1]
            MaxW = GeneralMethods.GetFloatFromStr(TempVal)[0]

            # Check for the DPLOSS calibration
            if TypeSD != "LPM":
                ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=Flow_limit,Type="Response")
                if len(ECAP)>2:
                    Nego = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ECAP[2],"Negotiable_Load_Power")[0]['sDescription'])[0]
                    # print("Nego:",Nego)
                    if Nego >= 15:
                        res.append([f"Negotiable_Load_Power is {Nego} W in {self.ECAP_pkt}, so DPLOSS calibration will perform, Expected: >= 15 W", Enums.TestResult.PASS])
                        tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                        if TypeSD == "NPM":
                            tempcheck = {"expected": "DPlossCalibrationCheck","DPLC": "DPLC1","skiplevel": ["Level4"],"flow": 2,"Result_check": True,Enums.TestResult.INCONCLUSIVE: False,"CheckSEQ": 1}
                        dploss_res=self.DPlossCalibration(Flow_limit,tempcheck)
                        for tempres in dploss_res: res.append(tempres)
                    else: res.append([f"Negotiable_Load_Power is {Nego} W in {self.ECAP_pkt}, so DPLOSS calibration won't perform, Expected: >= 15 W", Enums.TestResult.PASS])
                else: res.append([f"{self.ECAP_pkt} response is not observed", Enums.TestResult.FAIL])

            res.append([f"Found MODEXCAP at {round(TempPkt1[0],3)}sec, with {TypeSD} : Voltage Ref0: {ref0} V, Voltage Ref1: {ref1} V and Potential Load Power: {MaxW} W",Enums.TestResult.PASS])

            #check for the PRECT1 & 2 with set load value of MAXW 
            #Prect 1###########################################################################
            Load1Pkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(MaxW*1000)}",limit=[TempPkt1[2],Flow_limit[1]],Type="TesterMsg")
            if len(Load1Pkt)>2:
                #Find Stabilization 
                Stable1Pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Load1Pkt[2],Flow_limit[1]],Type="TesterMsg")
                if len(Stable1Pkt)>2:
                    res.append([f"Prect1:Stabilization found at {round(Stable1Pkt[0],3)}sec",Enums.TestResult.PASS])
                    #Get the Prect from next PLA_2 packet and Vrect measure on before CE packet
                    PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[Stable1Pkt[2],Flow_limit[1]])
                    if len(PLAPkt)>2:
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"PRECT")[0]['sDescription'])[0]
                        # ChkRes = CommonMethods.check_measure([MaxW-0.1,MaxW+0.1],Prect)
                        ChkRes = CommonMethods.check_measure([MaxW-0.1],Prect,comp='GTEQL')
                        # print("ChkRes:",ChkRes)
                        res.append([f"Prect1: {Prect}W found in PLA_2 packet at {round(PLAPkt[0],3)}sec, limit:{ChkRes[2]} W (MODEXCAP[Potential Load Power]- 0.1 W)",ChkRes[1]])
                    else:res.append([f"Prect1: PLA_2 packet not found after the stabilization",Enums.TestResult.FAIL])
                    #Ensure the Vrect
                    CE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[Stable1Pkt[2],Load1Pkt[2]])
                    if len(CE)>2:
                        reslt = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                        ChkRes = CommonMethods.check_measure([ref0-((ref0/100)*5),ref0+((ref0/100)*5)],reslt[0])
                        res.append([f"Prect1: The Measured Vrect on the XCE packet at {round(CE[0],3)}sec is {reslt[0]}V, limit: {ChkRes[2]}V (MODEXCAP[Main Active Mode (Voltage Vref0)])",ChkRes[1]])
                    else:res.append("Prect1: XCE packet not found before the Stabilization",Enums.TestResult.FAIL)
                else:res.append([f"Prect1:Stablization not found between {round(Load1Pkt[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.FAIL])
            else:res.append([f"Prect1: The Set_Load {int(MaxW*1000)} packet not found between {round(TempPkt1[0],3)}sec to {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.FAIL])
            #prect2###################################################################################
            Load2Pkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(MaxW*1000)}",limit=[Flow_limit[1],TempPkt1[2]],Type="TesterMsg")
            if len(Load2Pkt)>2:
                #Find Stabilization 
                Stable2Pkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[Load2Pkt[2],Flow_limit[1]],Type="TesterMsg")
                if len(Stable2Pkt)>2:
                    res.append([f"Prect2:Stabilization found at {round(Stable2Pkt[0],3)}sec",Enums.TestResult.PASS])
                    #Get the Prect from next PLA_2 packet and Vrect measure on before CE packet
                    PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[Stable2Pkt[2],Flow_limit[1]])
                    if len(PLAPkt)>2:
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"PRECT")[0]['sDescription'])[0]
                        # ChkRes = CommonMethods.check_measure([MaxW-0.1,MaxW+0.1],Prect)
                        ChkRes = CommonMethods.check_measure([MaxW-0.1],Prect,comp='GTEQL')
                        res.append([f"Prect2: {Prect} W found in PLA_2 packet at {round(PLAPkt[0],3)}sec, limit:{ChkRes[2]} W (MODEXCAP[Potential Load Power]- 0.1 W)",ChkRes[1]])
                    else:res.append([f"Prect2: PLA_2 packet not found after the stabilization",Enums.TestResult.FAIL])
                    #Ensure the Vrect
                    CE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[Stable2Pkt[2],Load2Pkt[2]])
                    if len(CE)>2:
                        reslt = self.PktMethod.CalculateVoltTwindow(CE[2],self.AllChannelData)
                        ChkRes = CommonMethods.check_measure([ref1-((ref1/100)*5),ref1+((ref1/100)*5)],reslt[0])
                        res.append([f"Prect2: The Measured Vrect on the XCE packet at {round(CE[0],3)}sec is {reslt[0]}V, limit: {ChkRes[2]}V (MODEXCAP[Main Active Mode (Voltage Vref1)])",ChkRes[1]])
                    else:res.append("Prect2: XCE packet not found before the Stabilization",Enums.TestResult.FAIL)
                else:res.append([f"Prect2:Stablization not found between {round(Load1Pkt[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.FAIL])
            else:res.append([f"Prect2: The Set_Load {int(MaxW*1000)} packet not found between {round(TempPkt1[0],3)}sec to {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec",Enums.TestResult.FAIL])

        else:res.append([f"The MODEXCAP packet not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec",Enums.TestResult.FAIL])
        return res
    def PrectCompare(self,Flow_limit,Check):
        Prectlist = []
        res =[]
        cnt = 1
        for ld in Check['Loads']:
            #1.Get Loads
            LoadPkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(ld)}",limit=Flow_limit,Type="TesterMsg")
            if len(LoadPkt)>2:
                if cnt == 2:
                    PLA_middle = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[LoadPkt[2],Flow_limit[0]])
                    if len(PLA_middle) > 2:
                        res.append([f"PLA_2 packet found with start_time: {round(PLA_middle[0],3)} sec and stop_time: {round(PLA_middle[1],3)} sec", Enums.TestResult.PASS])
                        res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec",Enums.TestResult.PASS])
                        if PLA_middle[0]<LoadPkt[0]<PLA_middle[1]:
                            res.append([f"Set Load packet for load {ld} mA recived inmiddle of PLA_2 packet at {round(LoadPkt[0],3)}sec",Enums.TestResult.PASS])
                        else: res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec, not recived inmiddle of PLA_2 packet",Enums.TestResult.FAIL])
                    else: res.append([f"PLA_2 packet not found after stabilizing the previous load.",Enums.TestResult.FAIL])
                else: res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec",Enums.TestResult.PASS])

                nxt_setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load",limit=[LoadPkt[2]+1,Flow_limit[1]],Type="TesterMsg")
                if len(nxt_setload)>2:
                    search_lmt = [LoadPkt[2],nxt_setload[2]]
                else:
                    search_lmt = [LoadPkt[2],Flow_limit[1]]
                print("search_lmt:",search_lmt)
                #Get Stabilization
                StablePkt = self.PktMethod.GetExactPacketDetails(packet="MPP_XCEV_Ideal",limit=search_lmt,Type="TesterMsg")
                print("StablePkt:",StablePkt)
                if len(StablePkt)>2:
                    res.append([f"Stablization found for load {ld} mA at {round(StablePkt[0],3)} sec",Enums.TestResult.PASS])
                    #Get the PLA_2
                    PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[StablePkt[2],Flow_limit[1]])
                    if len(PLAPkt)>2:
                        Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"PRECT")[0]['sDescription'])[0]
                        Vrect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"VRECT")[0]['sDescription'])[0]
                        Irect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLAPkt[2],"IRECT")[0]['sDescription'])[0]
                        if cnt == 1:
                            ChkRes = CommonMethods.check_measure([11.88,12.12],Vrect,0)
                            res.append([f"Prect{cnt}: Found PLA_2 packet at {round(PLAPkt[0],3)}sec with Prect: {Prect} W, Vrect: {Vrect} V, Irect: {Irect} A, Expected: Vrect: {ChkRes[2]} V",ChkRes[1]])
                        else:
                            res.append([f"Prect{cnt}: Found PLA_2 packet at {round(PLAPkt[0],3)}sec with Prect: {Prect} W, Vrect: {Vrect} V, Irect: {Irect} A",Enums.TestResult.PASS])
                        Prectlist.append(Prect)

                        if cnt == 2:
                            # 50mA load dump
                            Loaddump = self.PktMethod.GetPacketDetails(packet=f"Set_Load {50}",limit=[StablePkt[2],Flow_limit[1]],Type="TesterMsg")
                            if len(Loaddump)>2:
                                loaddone = self.PktMethod.GetPacketDetails(packet=f"Load Set Done",limit=[Loaddump[2],Flow_limit[1]],Type="TesterMsg")
                                if len(loaddone)>2:
                                    Second_PLAPkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[Loaddump[2],Flow_limit[0]])
                                    if len(Second_PLAPkt)>2:
                                        res.append([f"PLA_2 packet found with start_time: {round(Second_PLAPkt[0],3)} sec and stop_time: {round(Second_PLAPkt[1],3)} sec", Enums.TestResult.PASS])
                                        res.append([f"Set_Load 50mA found at {round(Loaddump[0],3)} sec", Enums.TestResult.PASS])
                                        res.append([f"Load Set Done found at {round(loaddone[0],3)} sec", Enums.TestResult.PASS])
                                        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
                                        irect2 = self.PktMethod.CalculateVoltTwindow(loaddone[2]+1, AllChannelData3)[0]*1000
                                        ChkRes2 = CommonMethods.check_measure([49],irect2,"GTEQL")
                                        
                                        if Second_PLAPkt[0]<Loaddump[0]<Second_PLAPkt[1] and Second_PLAPkt[0]<loaddone[0]<Second_PLAPkt[1]:
                                            res.append([f"Set_Load 50mA and Load set done are found inmiddle of PLA_2 packet", Enums.TestResult.PASS])
                                        else: res.append([f"Set_Load 50mA and Load set done are not found inmiddle of PLA_2 packet", Enums.TestResult.FAIL])
                                        res.append([f"Measured Irect is {irect2} mA at {round(loaddone[0],3)} sec, Expected: 50mA", ChkRes2[1]])
                                    else: res.append([f"PLA_2 packet not found",Enums.TestResult.FAIL])
                                else: res.append([f"Load Set Done not found for 50mA",Enums.TestResult.FAIL])
                            else: res.append([f"Set_Load 50 mA not found",Enums.TestResult.INCONCLUSIVE])

                    else:res.append([f"Prect{cnt}:PLA_2 packet not found after the stabilization",Enums.TestResult.FAIL])
                else:res.append([f"Stablization not found for load {ld}",Enums.TestResult.INCONCLUSIVE])
            else:res.append([f"Set Load for {ld}mA not received",Enums.TestResult.INCONCLUSIVE])
            cnt+=1
        if len(Prectlist)==2:
            if Prectlist[0]<Prectlist[1]:
                res.append([f"Prect1 : {Prectlist[0]} W, Prect2: {Prectlist[1]} W, Expected Prect1<Prect2",Enums.TestResult.PASS])
            else:res.append([f"Prect1 : {Prectlist[0]} W, Prect2: {Prectlist[1]} W, Expected Prect1<Prect2",Enums.TestResult.FAIL])
        else:res.append([f"Not found 2 prect values for the comparison",Enums.TestResult.INCONCLUSIVE])
        return res
    
    def FODTempCheck(self,Flow_limit,Check):
        if "FromPKT" in Check:
            a = Flow_limit[0]
            while a < Flow_limit[1]:
                pkt1 = self.PktMethod.GetPacketDetails(packet=Check['FromPKT']['Packet'][0],limit=[a,Flow_limit[1]],Type=Check['FromPKT']['Packet'][1])
                if len(pkt1)>2:
                    a = pkt1[2]
                    if "Response" in Check['FromPKT']:
                        respid = self.PktMethod.GetPacketResponse2(pkt1[2], [pkt1[2]+1, Flow_limit[1]])
                        if respid is not None:
                            if Check['FromPKT']['Packet'][0] in self.file_list[respid]['pktType']:
                                id2 = respid
                                break
                            else: a = respid
                    else:
                        id2 = pkt1[2]
                        break
                a += 1
            else: id2 = 0
        else: id2 = 0


        self.test_halt = False
        res = []
        self.AllChannelData12= self.PlotMethod.GetAllChannelData('12',self.JapiData)
        full_data_length = len(self.AllChannelData12['RV']['displayDataChunk'])

        TS = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[0,len(self.file_list)],Type="TesterMsg")

        # CHECK 1: Test has run for 30 minutes
        if not self.test_halt:
            # print("TS:",TS)
            if len(TS)>2:
                # # print(self.PktMethod.Timeconvert(TS[0]))
                if TS[0] > 1800:
                    res.append([f"Test has run for 30 minutes: Test_Stop is observed at {self.PktMethod.Timeconvert(TS[0])}", Enums.TestResult.PASS])
            else: res.append([f"Test_Stop not observed", Enums.TestResult.FAIL])

        # CHECK 2: TFO exceeds the FO’s safe temperature limit.
        id = id2
        CP = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station",limit=[0,Flow_limit[1]],Type="TesterMsg")
        if len(CP)>2:
            t1 = CP[0]
        else: t1 = self.file_list[id]['startTime'] #sec
        t1 = self.file_list[id]['startTime'] #sec
        sindex = int((t1*1000)/self.AllChannelData12['Interval'])
        tempdata = self.AllChannelData12['RV']['displayDataChunk'][sindex:]
        
        Maxtemp = max(tempdata)
        T2 = ((self.AllChannelData12['RV']['displayDataChunk'].index(Maxtemp))*self.AllChannelData12['Interval'])/1000
        # print("Maxtemp:", max(tempdata), "time:",T2)
        if not self.test_halt:
            if Maxtemp > Check['FOtempLimit'][1]:
                res.append([f"TFO exceeds the FO’s safe temperature limit: TFO: {Maxtemp} °C at {T2} sec, Maximum temperature limit of {Check['FOtempLimit'][0]}: {Check['FOtempLimit'][1]} °C", Enums.TestResult.PASS])
                self.test_halt = True

        # CHECK 3: TFO stabilizes to ±1 °C within 5 minutes
        if not self.test_halt:
            id = id2
            t1 = self.file_list[id]['startTime'] #sec
            t2 = 300 #5min
            end = self.file_list[Flow_limit[1]]['startTime']
            
            while t2 <= end:
                sindex = int((t1*1000)/self.AllChannelData12['Interval'])
                eindex = int((t2*1000)/self.AllChannelData12['Interval'])
                temp1 = round(self.AllChannelData12['RV']['displayDataChunk'][sindex],3)
                if 0 <= eindex < full_data_length:
                    temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex], 3)
                # temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex],3)
                    if abs(temp2 - temp1) <= 1:
                        # print("t1:",self.PktMethod.Timeconvert(t1),"temp1:",temp1,"t2:",self.PktMethod.Timeconvert(t2),"temp2:",temp2)
                        res.append([f"TFO Stabilises to ±1 °C between {self.PktMethod.Timeconvert(t1)} with TFO: {temp1} °C and {self.PktMethod.Timeconvert(t2)} with TFO: {temp2} °C in 5 minutes period.", Enums.TestResult.PASS])
                        self.test_halt = True
                        break
                else: break

                t1 += 1
                t2 += 1

        # CHECK 4: TFO < 0.8*maximum temperature after 10 minutes
        if not self.test_halt:
            if len(TS)>2 and TS[0] > 600:
                id = id2
                t1 = self.file_list[id]['startTime'] #sec
                t2 = 600 #sec -->10min
                FOtemp = Check['FOtempLimit'][1]
                eindex = int((t2*1000)/self.AllChannelData12['Interval'])
                if 0 <= eindex < full_data_length:
                    temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex],3)
                    if temp2 < (0.8*FOtemp):
                        # print("TFO < 0.8*maximum temperature after 10 minutes:", temp2, "Expected:>=",0.8*FOtemp)
                        res.append([f"TFO < 0.8*maximum temperature after 10 minutes: TFO: {temp2} °C, Maximum temperature limit of {Check['FOtempLimit'][0]}: {FOtemp} °C", Enums.TestResult.PASS])
                        self.test_halt = True

        # Power removal
        if not self.test_halt:
            if len(TS)>2:
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown",limit=[Flow_limit[0],TS[2]+1],Type="TesterMsg")
                if len(sd)>2:
                    res.append([f"Test case terminated due to power signal removal at {self.PktMethod.Timeconvert(sd[0])}", Enums.TestResult.PASS])
            else: res.append([f"Test_Stop not observed", Enums.TestResult.FAIL])

        res.append([f"Measured maximum temperature of FO is: {Maxtemp} °C", Enums.TestResult.PASS])

        return res
    


    def VrectPeak(self,Flow_limit,Check):
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
      
        res =[]
        Maxlimit = Check['Count']
        # id = 1
        # Cloak after 3 CXE
        Templimt = Flow_limit
        clk1 = self.PktMethod.GetPacketDetails(packet="Cloak",limit=Templimt,Type="Packet")
        if len(clk1)>2:
            xce_cnt = 0
            x = Templimt[0]
            while x < clk1[2]:
                XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[x,clk1[2]],Type="Packet")
                if len(XCE)>2:
                    x = XCE[2]
                    xce_cnt += 1
                x += 1
            if xce_cnt >= 3:
                res.append([f"TPR requested Cloak after {xce_cnt} Extended Control Error packets, Expected: Atleast after 3 Extended Control Error packets",Enums.TestResult.PASS])
            else: res.append([f"TPR requested Cloak after {xce_cnt} Extended Control Error packets, Expected: Alteast after 3 Extended Control Error packets",Enums.TestResult.FAIL])

            # Load to 0mA
            AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
            sindex = int((clk1[0]*1000)/AllChannelData3['Interval'])-5
            eindex = int((self.file_list[len(self.file_list)-1]['startTime']*1000)/AllChannelData3['Interval'])
            id1 = sindex
            Irect = 0
            threshold = 0.020
            interval = AllChannelData3['Interval']
            required_samples = int(0.030 / interval)
            count = 0
            t_prev = 0
            t_curr = 0
            t_total = 0
            for id1 in range(id1, eindex + 1):
                Irect = round(AllChannelData3['RV']['displayDataChunk'][id1], 3)
                # # print("Irect:",Irect)
                if Irect < threshold:
                    count += 1
                    if count == 1: 
                        res.append([f"TPR set load to 0 mA from {round((id1*AllChannelData3['Interval'])/1000,3)} sec", Enums.TestResult.PASS])
                    else:
                        t_prev = (id1-1)*AllChannelData3['Interval']
                        t_curr = id1*AllChannelData3['Interval']
                        t_total += (t_curr-t_prev)
                        # # print(t_prev,t_curr,t_total)
                    if t_total > 30:
                        res.append([f"TPR stayed below 20 mA and 50 mA ballast load is not applied for at least 30 ms", Enums.TestResult.PASS])
                        # print("Stayed below 0.020 for 30 ms. Breaking loop.")
                        break      
                else:
                    count = 0
                    t_total = 0
            else:
                res.append([f"TPR not stayed below 20 mA for at least 30 ms", Enums.TestResult.FAIL])
                # print("Signal did NOT stay below 0.020 for 30 ms.")

            # Crx 174 nF
            crx = self.PktMethod.GetPacketDetails(packet="CRx_Status",value="_174nF",limit=[clk1[2],len(self.file_list)-1],Type="TesterMsg")
            if len(crx)>2:
                res.append([f"Crx=174 nF is found at {round(crx[0])} sec", Enums.TestResult.PASS])
            else: res.append([f"Crx=174 nF is not found after 1st cloak", Enums.TestResult.FAIL])

            # Vrect max before 10 cloak pings
            id = clk1[2]
            clk_cnt = 0
            end = len(self.file_list)-1
            vrect_max = [0]
            vrect_min = [0]
            while id < end:
                PD = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[id,end],Type="TesterMsg")
                if len(PD)>2:
                    # print("pd:",PD)
                    clk = self.PktMethod.GetPacketDetails(packet="Cloak",limit=[PD[2],end],Type="Packet")
                    if len(clk)>2:
                        peakvol =  self.PlotMethod.CalculateHighVoltageTimePeriod(self.AllChannelData,PD[0]*1000,clk[0]*1000)
                        if peakvol is None:
                            res.append([f"Peak voltage calculation not performed",Enums.TestResult.FAIL])
                        else:
                            ChkRes = CommonMethods.check_measure(Check['expected'],peakvol,Check['comp'])
                            res.append([f"The Calculated Vrect peak is {peakvol}V, measured before Cloak packet between {round(PD[0],3)}Sec- {round(clk[0],3)}Sec, limit {ChkRes[2]}V",ChkRes[1]])
                        clk_cnt += 1
                        if clk_cnt == 1:
                            vrect_min = vrect_max = [peakvol,round(PD[0],3),round(clk[0],3)]
                        else:
                            if peakvol < vrect_min[0]: vrect_min = [peakvol,round(PD[0],3),round(clk[0],3)]
                            if peakvol > vrect_max[0]: vrect_max = [peakvol,round(PD[0],3),round(clk[0],3)]
                        id = clk[2]
                id+=1
            
            if clk_cnt == 10:
                res.append([f"10 cloak pings observed, Expected: 10",Enums.TestResult.PASS])
            else: res.append([f"{clk_cnt} cloak pings observed, Expected: 10",Enums.TestResult.FAIL])
            res.append([f"Vrect_min is {vrect_min[0]}V, measured before Cloak packet between {vrect_min[1]}Sec- {vrect_min[2]}Sec", Enums.TestResult.PASS])
            res.append([f"Vrect_max is {vrect_max[0]}V, measured before Cloak packet between {vrect_max[1]}Sec- {vrect_max[2]}Sec", Enums.TestResult.PASS])

        return res
          
    def PrectAFLoads(self,Flow_limit,Check):
        try:
            res=[]
            # prect = []
            #1.Get the Loads
            for Prect in Check['expected']:
                #Get Prect value from the PLA packet
                LoadPkt =  self.PktMethod.GetPacketDetails(packet=f"Set_Load {Prect['Load']}",limit=Flow_limit,Type="TesterMsg")
                if len(LoadPkt)>2:
                    res.append([f"Set Load {Prect['Load']} packet found at {round(LoadPkt[0],3)}sec",Enums.TestResult.PASS])
                    if Check['MeasureType'] == "Packet":
                        #calculate Prec value
                        if Prect['Condition']['Type']=="PowerLimit":
                            #Get the power value from PLA packet once after reaching the powerlimit
                            id = LoadPkt[2]
                            while id < Flow_limit[1]:
                                PLApkt = self.PktMethod.GetPacketDetails(packet="PLA_2",limit=[id,Flow_limit[1]])
                                if len(PLApkt)>2:
                                    PLAprect =GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLApkt[2],"PRECT")[0]['sDescription'])[0]
                                    # prect.append(PLAprect)
                                    if Prect['Condition']['comp'] =="GTEQL":
                                        if PLAprect >= Prect['Condition']['value']:
                                            res.append([f"Found Prect {PLAprect}W at {round(PLApkt[0],3)}sec, which is above the Limit {Prect['Condition']['value']}W",Enums.TestResult.PASS])
                                            break
                                    id = PLApkt[2]+1
                                else:
                                    res.append([f"PLA_2 packet with Prect value above the limit {Prect['Condition']['value']} not found.",Enums.TestResult.FAIL])
                                    break  
                    elif Check['MeasureType']=="Plot":
                        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
                        self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
                        #Default get the measure af the stabilization
                        if Prect['Condition']['Type']=="Stabilization":
                            staPkt = self.PktMethod.GetPacketDetails(packet="MPP_XCEV_Ideal",limit=[LoadPkt[2],Flow_limit[1]],Type="TesterMsg")
                            if len(staPkt)>2:
                                #Get the CE packet
                                CEpkt = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[staPkt[2],Flow_limit[0]])
                                if len(CEpkt)>2:
                                    res.append([f"Stablization found at {round(CEpkt[0],3)}sec",Enums.TestResult.PASS])

                                    #Get the index of the allchannel data 
                                    ChIndex = int((CEpkt[0]*1000)-6/self.AllChannelData['Interval'])
                                    # print("ChIndex1:",int((CEpkt[0]*1000)-8/self.AllChannelData['Interval']))
                                    # print("ChIndex2:",int((CEpkt[0]*1000)-6/self.AllChannelData['Interval']))
                                    
                                    I = round(abs(self.AllChannelData3['RV']['displayDataChunk'][ChIndex]*1000),4)
                                    V = round(abs(self.AllChannelData['RV']['displayDataChunk'][ChIndex]*1000),4)
                                    p = round((I/1000)*(V/1000),3)
                                    PowerChkRes = CommonMethods.check_measure(Prect['exp'],p,Prect['comp'])
                                    res.append([f"Measured Prect is {p}W measured at {round(CEpkt[0]-0.006,3)}sec, limit {PowerChkRes[2]}W",PowerChkRes[1]])
                                    res.append([f"Measured Irect is {round(I/1000,3)}A measured at {round(CEpkt[0]-0.006,3)}sec",Enums.TestResult.PASS])
                                    if 'Vrect' in Prect:
                                        VrectChkRes = CommonMethods.check_measure(Prect['Vrect']['exp'],round(V/1000,3),Prect['Vrect']['comp'])
                                        res.append([f"Measured Vrect is {round(V/1000,3)}V measured at {round(CEpkt[0]-0.006,3)}sec, limit {VrectChkRes[2]}W",VrectChkRes[1]])
                                    # respkt = self.PktMethod.CalculateVoltTwindow(CEpkt[2],self.AllChannelData)
                                else:res.append([f"Stabilization not found for the load {Prect['Load']}mW",Enums.TestResult.FAIL])
                            else:res.append([f"Stabilization not found for the load {Prect['Load']}mW",Enums.TestResult.FAIL])
                else:res.append[f"Set Load {Prect['Load']} packet not found",Enums.TestResult.FAIL]
            return res
        except Exception as e:
            print(e)
    def t_modecomplete(self,Flow_limit,Check):
        try:
            res=[]
            pwrvalue = Check["PowerMode"]
            #1.find the packet MSR packet with powermode change
            Pkt1 = self.PktMethod.GetPacketDetails(packet="MSR",value=pwrvalue,limit=Flow_limit)
            if len(Pkt1)>2:
                res.append([f"Power Mode update packet MSR with value {pwrvalue} found at {round(Pkt1[0],3)}sec",Enums.TestResult.PASS])
                #get the reponse of the packet
                responseID = self.PktMethod.GetPacketResponse(Pkt1[2],[Pkt1[2]+1,Flow_limit[1]])
                if responseID is not None:

                    if "MSS" in self.file_list[responseID]['pktType'] and "PENDING" in self.file_list[responseID]['value']:
                        res.append([f"MSS[PENDING] received at {round(self.file_list[responseID]['startTime'],3)}sec",Enums.TestResult.PASS])

                        Pkt2 = self.PktMethod.GetPacketDetails(packet="EPTR",limit=[Pkt1[2],Flow_limit[1]],Type="Response")
                        if len(Pkt2)>2:
                            res.append([f"EPTR request received at {round(Pkt2[0],3)} sec",Enums.TestResult.PASS])
                            ChkRes = CommonMethods.check_measure(Check['expected'],round((Pkt2[0]-self.file_list[responseID]['stopTime'])*1000,3),Check['comp'])
                            res.append([f"The measured t_modecomplete is {ChkRes[3]}ms, Limit {ChkRes[2]}ms",ChkRes[1]])
                        else:res.append([f"Packet EPTR not found",Enums.TestResult.FAIL])
                    elif "MSS" in self.file_list[responseID]['pktType'] and ("SUCCESS" in self.file_list[responseID]['value'] or "BUSY" in self.file_list[responseID]['value'] or "FAIL" in self.file_list[responseID]['value']):
                        res.append([f"MSS[{self.file_list[responseID]['value']}] received at {round(self.file_list[responseID]['startTime'],3)}sec",Enums.TestResult.INCONCLUSIVE])
                    
                else:res.append([f"Response not found for the MSR packet",Enums.TestResult.FAIL])
            else:res.append([f"Power Mode update packet MSRwith {pwrvalue} not found",Enums.TestResult.FAIL])
            return res
        except Exception as e:
            print(e)
            
    def t_ept_modechange(self,Flow_limit,Check):
    
        res=[]
        pwrvalue = Check["PowerMode"]
         #1.find the packet MSR packet with powermode change
        Pkt1 = self.PktMethod.GetPacketDetails(packet="MSR",value=pwrvalue,limit=Flow_limit)
        if len(Pkt1)>2:
            # res.append([f"Power Mode update packet MSR with value {pwrvalue} found at {round(Pkt1[0],3)}sec",Enums.TestResult.PASS])
            #get the reponse of the packet
            responseID = self.PktMethod.GetPacketResponse(Pkt1[2],[Pkt1[2]+1,Flow_limit[1]])
            if responseID is not None:

                if "MSS" in self.file_list[responseID]['pktType'] and "PENDING" in self.file_list[responseID]['value']:
                    # res.append([f"MSS[PENDING] received at {round(self.file_list[responseID]['startTime'],3)}sec",Enums.TestResult.PASS])

    
                    EPTR = self.PktMethod.GetPacketDetails(packet="EPTR",value="Power Mode Change",limit=Flow_limit,Type="Response")
                    if len(EPTR)>2:
                        res.append([f"EPTR_Power Mode Change request received at {round(EPTR[0],3)} sec",Enums.TestResult.PASS])
                        EPT = self.PktMethod.GetPacketDetails(packet="End Power Transfer",value="EPT/pmc",limit=[EPTR[2],Flow_limit[1]],Type="Packet")
                        if len(EPT)>2:
                            res.append([f"End Power Transfer packet found at {round(EPT[0],3)} sec",Enums.TestResult.PASS])
                            PD = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=[EPT[2],len(self.file_list)-1],Type="TesterMsg")
                            if len(PD)>2:
                                ChkRes = CommonMethods.check_measure(Check['expected'],round((PD[0]-EPT[1])*1000,3),Check['comp'])
                                res.append([f"The measured t_ept_modechange is {ChkRes[3]}ms, Limit {ChkRes[2]}ms",ChkRes[1]])
                            else:res.append([f"PD not found after the 360Khz flow",Enums.TestResult.FAIL])
                        else: res.append([f"End Power Transfer(EPT/pmc) packet not found",Enums.TestResult.FAIL])
                    else: res.append([f"PTxDUT not sent EPTR",Enums.TestResult.PASS])
                    
                elif "MSS" in self.file_list[responseID]['pktType'] and ("SUCCESS" in self.file_list[responseID]['value'] or "BUSY" in self.file_list[responseID]['value'] or "FAIL" in self.file_list[responseID]['value']):
                    res.append([f"MSS[{self.file_list[responseID]['value']}] received at {round(self.file_list[responseID]['startTime'],3)}sec",Enums.TestResult.INCONCLUSIVE])
        
        return res
     
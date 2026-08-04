# from Resources.tkfilebrowser import recent_files
from Scripts import JsonSchema
import os,re
import sys
sys.path.append('Scripts')
import traceback
import zipfile
from MainModule import JsonOperations,APIOperations,GeneralMethods

from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from datetime import datetime,date

# from collections import deque
import traceback

class CommonCTSChecks():
    def __init__(self,Header,file_list,JapiData,BackupJson,ProjectJson,flows):
        #Define Global variables
        CTS = JsonOperations('json/CTSvalidation/MPPTPR.json')
        self.JCTSData =CTS.read_file()
        self.flows = flows

        self.JapiData = JapiData
        self.Header = Header
        self.Product = self.Header['Product']
        self.Mode = self.Header['Mode']
        self.TestCaseName = self.Header['TestcaseName']
        self.ProjectJson = ProjectJson
        self.file_list = file_list
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()

        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        #Define modules
        self.PktMethod = PacketMethods(file_list=self.file_list,Header=self.Header)
        self.PlotMethod = PlotMethods(Header=self.Header)
        # self.Certification=self.BKjsonData['testBkpAppModeString']
        self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
        self.GetInitailVoltage(2)

        # Certificate wise packet names
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        if self.Certification in ["2.0.1","2.1.0","2.2.1","2.3.0"]:
            self.ECAP_pkt = "Extended_Power_Transmitter_Extended_Capabilities"
            self.XID_pkt = "MPP_Extended_Identification"
            self.Inv_vol_pkt = "Inverter_Voltage"
            self.PLAP_pkt = "Power_Loss_Accounting_Parameters"
        else:
            self.ECAP_pkt = "Power Transmitter Extended Capabilities"
            self.XID_pkt = "Extended Identification"
            self.Inv_vol_pkt = "Inverter Voltage"
            self.PLAP_pkt = "Power Loss Accounting Parameters"

    def Timeout(self, Flow_limit, Check):
        res = []
        id = self.stability
        Tout = round(self.file_list[Flow_limit[1]].get('startTime') - self.file_list[id].get('stopTime'), 3)
        ChkRes = CommonMethods.check_measure(Check['expected'], Tout, Check['comp'])
        res.append([f"The Measured Ttimeout between Extended_Control_Error and Shutdown is: {ChkRes[3]} S, Limit: {ChkRes[2]}", ChkRes[1]])
        return res
    def Vrect_ping(self, Flow_limit, Check):
        res = []
        CP = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station", limit=[len(self.file_list) - 1, 0], Type="TesterMsg")
        print("CP:", CP)
        if len(CP) > 2:
            cnt = 1
            id = CP[2]
            end = len(self.file_list) - 1
            vrects = []
            while id <= end:
                pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[id, end], Type="TesterMsg")
                if len(pd) > 2:
                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], end], Type="TesterMsg")
                    if len(sd) > 2:
                        fop_pkt = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd[2], sd[2]], Type="TesterMsg")
                        if len(fop_pkt) > 2:
                            id = fop_pkt[2]
                            fop = float(self.file_list[fop_pkt[2]]['value'].split(":")[1].split(" ")[0])
                            ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[fop_pkt[2], end], Type="Packet")
                            if len(ss) > 2:
                                id = sd[2]
                                ChkRes = CommonMethods.check_measure([127.5, 128.5], fop, 0)
                                res.append([f"Measured FOP_{cnt} is {ChkRes[3]} kHz at {round(fop_pkt[0], 3)}sec, , Expected: {ChkRes[2]} kHz", ChkRes[1]])
                                res.append([f"Signal strength Packet found at {round(ss[0], 3)} sec", "Pass"])
                                vrect_max = self.PktMethod.CalculateVoltTwindow(ss[2], self.AllChannelData, winsize=[9, 11], max=True)[0]
                                vrects.append(vrect_max)
                                ChkRes3 = CommonMethods.check_measure([4, 8.5] if cnt == 1 else [4, 13], vrect_max, 0)
                                res.append([f"Measured Vrect_ping{cnt} is {ChkRes3[3]} V, Expected: {ChkRes3[2]} V", ChkRes3[1]])
                                
                                cnt += 1
                            elif cnt == 1:
                                res.append([f"Signal strength Packet not found", "Fail"])
                        # elif cnt == 1:
                        #     res.append([f"FOP: packet not found", "Fail"])
                    elif cnt == 1:
                        res.append([f"Shutdown packet not found", "Fail"])
                elif cnt == 1:
                    res.append([f"Ping Detected packet not found", "Fail"])
                id += 1
            if cnt == 2:
                ChkRes2 = CommonMethods.check_measure([4, 13], vrects[0], 0)
                res.append([f"Measured Vrect_pingx is equal to Vrect_ping1 i.e, {ChkRes2[3]} V, Expected: {ChkRes2[2]} V", ChkRes2[1]])
        return res
    def Vrect_ping360(self, Flow_limit, Check):
        res = []
        fop_pkt = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=Flow_limit, Type="TesterMsg")
        print("fop_pkt:", fop_pkt)
        if len(fop_pkt) > 2:
            fop = float(self.file_list[fop_pkt[2]]['value'].split(":")[1].split(" ")[0])
            ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[fop_pkt[2], Flow_limit[1]], Type="Packet")
            if len(ss) > 2:
                ChkRes = CommonMethods.check_measure([359.46, 360.54], fop, 0)
                res.append([f"Measured FOP is {ChkRes[3]} kHz at {round(fop_pkt[0], 3)}sec, , Expected: {ChkRes[2]} kHz", ChkRes[1]])
                res.append([f"Signal strength Packet found at {round(ss[0], 3)} sec", "Pass"])
                vrect_max = self.PktMethod.CalculateVoltTwindow(ss[2], self.AllChannelData, winsize=[9, 11], max=True)[0]
                ChkRes3 = CommonMethods.check_measure([7, 13], vrect_max, 0)
                res.append([f"Measured Vrect_ping is {ChkRes3[3]} V, Expected: {ChkRes3[2]} V", ChkRes3[1]])
            else:
                res.append([f"Signal strength Packet not found", "Fail"])
        else:
            res.append([f"FOP: packet not found", "Fail"])


        return res
    def Illegal(self, Flow_limit, Check):
        print("Illegal started")
        res = []
        first_xce = self.PktMethod.GetPacketDetails(packet="Extended Control Error", limit=Flow_limit, Type="Packet")
        if len(first_xce)>2:


            for pkt in Check['expected']:
                id = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0],value=pkt['refpkt'][2] if len(pkt['refpkt']) == 3 else None,limit=[Flow_limit[0], len(self.file_list) - 1],Type=pkt['refpkt'][1])[2]
                limit = Flow_limit
                if "PktLimit" in pkt:
                    limit = self.PktMethod.GetLimits(pkt['PktLimit'], pkt, Flow_limit)
                TempPkt1 = self.PktMethod.GetexactPacketDetails(packet=pkt['packet1'][0],value=pkt['packet1'][2] if len(pkt['packet1']) == 3 else None,limit=[id, limit[1]],Type=pkt['packet1'][1])
                
                if len(TempPkt1) > 2:
                    if "typ" in pkt:
                        print("pkt:", pkt['typ'])
                        res.append([f"{pkt['typ']} {pkt['packet1'][0]} packet found at {round(TempPkt1[0], 3)} sec", "Pass"])
                        tdiff = round(TempPkt1[0]-first_xce[0],3)
                        res.append([f"TPR sent {pkt['typ']} {pkt['packet1'][0]} packet in {tdiff} sec, Expected: 2 to 8 sec", "Pass" if 2<=tdiff<=8 else "Fail"])
                    TempPkt2 = self.PktMethod.GetPacketDetails(packet=pkt['packet2'][0],value=pkt['packet2'][2] if len(pkt['packet2']) == 3 else None,limit=[TempPkt1[2] + 1, limit[1] + 1],Type=pkt['packet2'][1])
                
                    if len(TempPkt2) > 2:
                        Tresult = round((TempPkt2[0] - TempPkt1[1]) * 1000, 3)
                        ChkRes = CommonMethods.check_measure(pkt['exp'], Tresult, pkt['comp'])
                        res.append([f"The Measured {pkt['chk']} between {pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ''} and {pkt['packet2'][0]} {pkt['packet2'][2] if len(pkt['packet2']) == 3 else ''}: {ChkRes[3]} ms, Limit: {ChkRes[2]} ms", ChkRes[1]])
                    else:
                        res.append([f"{pkt['packet2'][0]} {pkt['packet2'][2] if len(pkt['packet2']) == 3 else ''} not found", "Pass"])
                else:
                    res.append([f"{pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ''} not found", "Pass"])
        else:
            res.append([f"PT phase not found","Inconclusive"])
        return res
    def FOP(self, Flow_limit, Check):
        res = []
        for pkt in Check['expected']:
            limit = Flow_limit
            if 'CLOAK' in self.Header['TestcaseID']:
                end = len(self.file_list)
                limit = Flow_limit
            elif "PktLimit" in pkt:
                if pkt['PktLimit'] == "refCustom":
                    pass
                elif pkt['PktLimit'] == "refPrevious":
                    limit = [0, Flow_limit[0]]
                elif pkt['PktLimit'] == "refNextAll":
                    limit = [Flow_limit[1], len(self.file_list) - 1]
                elif pkt['PktLimit'] == "refAll":
                    limit = [0, len(self.file_list) - 1]
                elif pkt['PktLimit'] == "Flow":
                    limit = Flow_limit
                elif pkt['PktLimit'] == 'FromExncnt':
                    excnt = self.GetPacketDetails(packet="Execution_count_no", limit=[0, Flow_limit[0] - 1])
                    limit = [excnt[2], Flow_limit[1]] if len(excnt) > 2 else Flow_limit
                elif pkt['PktLimit'] == "FromCustomPacket":
                    CP = self.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0], value=pkt['CustomLimit']['Packet'][1], limit=Flow_limit)
                    limit = [CP[2], Flow_limit[1]] if len(CP) > 2 else Flow_limit
                end = limit[1]
            else:
                limit = Flow_limit
                end = Flow_limit[1]
            refpkt = self.PktMethod.GetPacketDetails(
                packet=pkt['refpkt'][0],
                value=pkt['refpkt'][2] if len(pkt['refpkt']) == 3 else None,
                limit=limit,
                Type=pkt['refpkt'][1])
            if len(refpkt) > 2:
                id = refpkt[2]
                TempPkt1 = self.PktMethod.GetPacketDetails(
                    packet=pkt['packet1'][0],
                    value=pkt['packet1'][2] if len(pkt['packet1']) == 3 else None,
                    limit=[id, end],
                    Type=pkt['packet1'][1])
                if len(TempPkt1) > 2:
                    fop = float(self.file_list[TempPkt1[2]]['value'].split(":")[1].split(" ")[0].strip())
                    ChkRes = CommonMethods.check_measure(pkt['exp'], fop, pkt['comp'])
                    res.append(
                        [f"{pkt['chkname'] if 'chkname' in pkt else ''} {self.file_list[TempPkt1[2]]['value']} assertion with FOP {ChkRes[3]} kHz is found at {round(TempPkt1[0], 3)} sec, Limit: {ChkRes[2]} kHz", ChkRes[1]])
                    if "PTphaseChk" in pkt:
                        x = TempPkt1[2]
                        while x < end:
                            if self.file_list[x]['description'] == "PT":
                                res.append(
                                    [f'PT Phase started at {round(self.file_list[x]["startTime"], 3)}sec after re-attach', "Pass"])
                                break
                            x += 1
                        else:
                            res.append([f'PT Phase not started after re-attach', "Fail"])
                    if "Vrect_max" in pkt:
                        ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[TempPkt1[2], end], Type="Packet")
                        if len(ss) > 2:
                            res.append([f"Signal strengt packet found at {round(ss[0], 3)} Sec", "Pass"])
                            self.AllChannelData = self.PlotMethod.GetAllChannelData2('2', self.JapiData)
                            vrect_max = self.PktMethod.CalculateVoltTwindow(ss[2], self.AllChannelData, winsize=[9, int((ss[0] - refpkt[1]) * 1000)], max=True)[0]
                            ChkRes = CommonMethods.check_measure(pkt['Vrect_max'][1], vrect_max, pkt['Vrect_max'][0])
                            res.append(
                                [f"Measured Vrect_max is {ChkRes[3]} V, measured between {round(refpkt[1], 3)} Sec to {round((ss[0] - 0.009), 3)} Sec, Expected : {ChkRes[2]} V", ChkRes[1]])
                        else:
                            res.append([f"Signal strengt packet not found", "Fail"])
                else:
                    res.append([f"{pkt['packet1'][0]} packet not found", "Fail"])
            else:
                res.append([f"{pkt['refpkt'][0]} packet not found", "Fail"])


        return res
    def Tnextping(self, Flow_limit, Check):
        res = []
        XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error", limit=Flow_limit, Type="Packet")
        if len(XCE) > 2:
            res.append([f'PT Phase started at {round(XCE[0], 3)} sec', "Pass"])
            limit1 = [Flow_limit[0], len(self.file_list) - 1]
            TempPkt1 = self.PktMethod.GetPacketDetails(packet=Check['expected'][0]['packet1'][0],value=Check['expected'][0]['packet1'][1],limit=[Flow_limit[1], XCE[2]],Type=Check['expected'][0]['packet1'][2])
            if len(TempPkt1) > 2:
                res.append([f'{Check["expected"][0]["packet1"][0]} {Check["expected"][0]["packet1"][1]} {Check["expected"][0]["packet1"][2]} found at {round(TempPkt1[0], 3)} sec', "Pass"])
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[TempPkt1[2], Flow_limit[1] + 1], Type="TesterMsg")
                if len(sd) > 2:
                    if sd[0] - TempPkt1[1] >= 60:
                        res.append([f'PTx does not stop power for {sd[0] - TempPkt1[1]}, Expected: within 1 minute', "Inconclusive"])
                else:
                    res.append([f'Shutdown not found', "Fail"])
                TempPkt2 = self.PktMethod.GetPacketDetails(packet=Check['expected'][0]['packet2'][0],value=Check['expected'][0]['packet2'][1],limit=[TempPkt1[2], limit1[1]],Type=Check['expected'][0]['packet2'][2])
                fop = self.PktMethod.GetPacketDetails(value='FOP:',limit=[TempPkt1[2], limit1[1]],Type="TesterMsg")
                if len(TempPkt2) > 2 and len(fop) > 2:
                    res.append([f'{Check["expected"][0]["packet2"][0]} {Check["expected"][0]["packet2"][2]} found at {round(TempPkt2[0], 3)} sec', "Pass"])
                    ChkRes = CommonMethods.check_measure(Check['expected'][0]['exp'], (TempPkt2[0] - TempPkt1[1]) * 1000, Check['expected'][0]['comp'])
                    res.append([f'Measured Tnextping is {round(ChkRes[3], 3)} ms, Expected: {ChkRes[2]} ms', ChkRes[1]])
                else:
                    res.append([f'PTx unable to reping after sending EPT data packet', "Inconclusive"])
            else:
                res.append([f'{Check["expected"][0]["packet1"][0]} {Check["expected"][0]["packet1"][1]} {Check["expected"][0]["packet1"][2]} not found', "Inconclusive"])
        else:
            res.append([f'PT Phase not started', "Inconclusive"])


        return res
    def Tresponse(self, Flow_limit, Check):
        res = []
        for pkt in Check['expected']:
            id = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0], limit=Flow_limit, Type=pkt['refpkt'][1])[2]
            end = Flow_limit[1]
            TempPkt1 = self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0], limit=[id, end], Type=pkt['packet1'][1])
            if len(TempPkt1) > 2:
                res.append([f"{pkt['packet1'][0]} packet found at {round(TempPkt1[0], 3)} sec", "Pass"])
                TempPkt2 = self.PktMethod.GetPacketDetails(packet=pkt['packet2'][0], limit=[TempPkt1[2] + 1, end + 1], Type=pkt['packet2'][1])
                if len(TempPkt2) > 2:
                    res.append([f"{pkt['packet2'][0]} packet found at {round(TempPkt2[0], 3)} sec", "Pass"])
                    if 'Response' in self.GetPacketType(TempPkt2[2] + 1) and self.file_list[TempPkt2[2] + 1]['pktType'] in ['ACK', 'NAK']:
                        Tresult = round((self.file_list[TempPkt2[2] + 1]['startTime'] - TempPkt1[1]) * 1000, 3)
                        ChkRes = CommonMethods.check_measure(pkt['exp'], Tresult, pkt['comp'])
                        res.append(
                            [f"{self.file_list[TempPkt2[2] + 1]['pktType']} response to {pkt['packet2'][0]} packet is received in: {ChkRes[3]} ms from 360kHz digital ping, Limit: {ChkRes[2]} ms", ChkRes[1]])
                    elif 'TesterMsg' in self.GetPacketType(TempPkt2[2] + 1) and 'Response' in self.GetPacketType(TempPkt2[2] + 2) and self.file_list[TempPkt2[2] + 2]['pktType'] in ['ACK', 'NAK']:
                        Tresult = round((self.file_list[TempPkt2[2] + 2]['startTime'] - TempPkt1[1]) * 1000, 3)
                        ChkRes = CommonMethods.check_measure(pkt['exp'], Tresult, pkt['comp'])
                        res.append(
                            [f"{self.file_list[TempPkt2[2] + 2]['pktType']} response to {pkt['packet2'][0]} packet is received in: {ChkRes[3]} ms from 360kHz digital ping, Limit: {ChkRes[2]} ms", ChkRes[1]])


        return res
    def PROP(self, Flow_limit, Check):
        res = []
        PT_start_index = 0

        xce = self.PktMethod.GetPacketDetails(packet="Extended Control Error", limit=Flow_limit)
        if len(xce) >2:
            PT_start_index = xce
        
        in_pt_cnt = 0
        Prev_pkt = []

        id = Flow_limit[0]
        end = Flow_limit[1]
        while id < Flow_limit[1]:
            TempPkt1 = self.PktMethod.GetPacketDetails(packet=Check['expected'][0]["packet"][0], limit=[id, end], Type=Check['expected'][0]["packet"][1])
            if len(TempPkt1) > 2:
                resp = self.PktMethod.GetPacketResponse2(TempPkt1[2], [TempPkt1[2] + 1, Flow_limit[1]])
                if "Nego" in self.file_list[TempPkt1[2]]['description']:
                    res.append([f"{Check['expected'][0]['packet'][0]} packet received in Neg phase at index@{TempPkt1[2]}", "Pass"])
                    if resp is not None:
                        if 'ND' in self.file_list[resp]['pktType']:
                            res.append([f"{self.file_list[resp]['pktType']} response received for {Check['expected'][0]['packet'][0]} packet in Neg phase", "Pass"])
                        else:
                            res.append([f"{self.file_list[resp]['pktType']} response received for {Check['expected'][0]['packet'][0]} packet in Neg phase", "Fail"])
                    else:
                        res.append([f"Response not received for {Check['expected'][0]['packet'][0]} in Neg phase", "Fail"])


                if "PT" in self.file_list[TempPkt1[2]]['description']:
                    tdiff = None

                    if in_pt_cnt == 0:
                        tdiff = round((TempPkt1[0] - PT_start_index[0]),3)
                    else: 
                        tdiff = round((TempPkt1[0] - Prev_pkt[0]),3)
                    
                    Prev_pkt = TempPkt1
                    res.append([f"{Check['expected'][0]['packet'][0]} packet received in PT phase at index@{TempPkt1[2]}", "Pass"])

                    if tdiff is not None:
                        if 2 <= tdiff <= 8:
                            # res.append([f"TPR sent {Check['expected'][0]['packet'][0]} packet in {tdiff} sec, from {"first XCE packet" if in_pt_cnt == 0 else "previous {Check['expected'][0]['packet'][0]} packet"}, Expected: 2 to 8 sec", "Pass"])
                            res.append([f"TPR sent {Check['expected'][0]['packet'][0]} packet in {tdiff} sec, "f"from {'first XCE packet' if in_pt_cnt == 0 else f'previous {Check['expected'][0]['packet'][0]} packet'}, "f"Expected: 2 to 8 sec","Pass"])
                        else:
                            # res.append([f"TPR sent {Check['expected'][0]['packet'][0]} packet in {tdiff} sec, Expected: 2 to 8 sec", "Fail"])
                            res.append([f"TPR sent {Check['expected'][0]['packet'][0]} packet in {tdiff} sec, "f"from {'first XCE packet' if in_pt_cnt == 0 else f'previous {Check['expected'][0]['packet'][0]} packet'}, "f"Expected: 2 to 8 sec","Fail"])
                    in_pt_cnt += 1
                    if resp is None:
                        res.append([f"Response not received for {Check['expected'][0]['packet'][0]} in PT phase", "Pass"])
                    else:
                        res.append([f"{self.file_list[resp]['pktType']} response received for {Check['expected'][0]['packet'][0]} in PT phase", "Fail"])
                id = TempPkt1[2]
            id += 1


        return res
    def Reping(self, Flow_limit, Check):
        res = []
        if "PktLimit" in Check['expected'][0]:
            templimit = self.PktMethod.GetLimits(Check['expected'][0]['PktLimit'], Check['expected'][0], Flow_limit)
        else:
            templimit = Flow_limit
        if "refpkt" in Check['expected'][0]:
            TempPkt1 = self.PktMethod.GetPacketDetails(
                packet=Check['expected'][0]['refpkt'][0], limit=templimit, Type=Check['expected'][0]['refpkt'][1])
            if len(TempPkt1) > 2:
                templimit2 = [TempPkt1[2], templimit[0]]
            else:
                res.append([f"{Check['expected'][0]['refpkt'][0]} not found", "Fail"])
                templimit2 = templimit
        else:
            templimit2 = templimit
        TempPkt2 = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=templimit2, Type="TesterMsg")
        if len(TempPkt2) > 2:
            TempPkt3 = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[TempPkt2[2], templimit[1]], Type="TesterMsg")
            if len(TempPkt3) > 2:
                res.append([f"Ping Detected TesterMsg found at {round(TempPkt3[0], 3)} sec", "Pass"])
                Tresult1 = round((TempPkt3[0] - TempPkt2[1]) * 1000, 3)
                ChkRes1 = CommonMethods.check_measure([500], Tresult1, "LTEQL")
                res.append(
                    [f"The Measured {Check['expected'][0]['chk']} between Shutdown and Ping detected is: {ChkRes1[3]} ms, Limit: {ChkRes1[2]} ms", ChkRes1[1]])
                TempPkt4 = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[TempPkt3[2] + 1, templimit[1]], Type="Packet")
                if len(TempPkt4) > 2:
                    res.append([f"Signal Strength packet found at {round(TempPkt4[0], 3)} sec", "Pass"])
                    fop = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[TempPkt3[2] + 1, TempPkt4[2]], Type="TesterMsg")
                    if len(fop) > 2:
                        fopval = float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0])
                        ChkRes2 = CommonMethods.check_measure([127.5, 128.5], fopval, "BTW")
                        res.append(
                            [f"Fop is {ChkRes2[3]} kHz found at {round(fop[0], 3)} sec, Limit: {ChkRes2[2]} kHz", ChkRes1[1]])
                        vrect = self.PktMethod.CalculateVoltTwindow(
                            TempPkt4[2], self.AllChannelData, winsize=[9, int((TempPkt4[0] - TempPkt2[1]) * 1000)], max=True)[0]
                        ChkRes3 = CommonMethods.check_measure([19], vrect, "LTEQL")
                        res.append(
                            [f"Measured Vrect_max is {ChkRes3[3]} V between {round(TempPkt2[1], 3)} sec to {round((TempPkt4[0]) - 0.009, 3)} Sec, Limit: {ChkRes3[2]} V", ChkRes3[1]])
                    else:
                        res.append([f"Fop TesterMsg not found", "Fail"])
                else:
                    res.append([f"Signal strength Packet not found", "Fail"])
            else:
                res.append([f"Ping Detected TesterMsg not found", "Fail"])
        else:
            res.append([f"Shutdown TesterMsg not found", "Fail"])


        return res
    def NegPhase(self, Flow_limit, Check):
        res = []
        id = Flow_limit[0]
        end = Flow_limit[1]
        while id < Flow_limit[1]:
            if "Nego" in self.file_list[id]['description']:
                res.append([f"Entered to Negotiation phase at {round(self.file_list[id]['startTime'], 3)} sec", "Pass"])
                break
            id += 1
        else:
            res.append([f"Negotiation phase not observed", "Fail"])
        
        if "EDS_pkts" in Check:
            EDS_TPR = self.PktMethod.GetPacketDetails(packet="Enabled Data Streams", limit=Flow_limit, Type="Packet")
            if len(EDS_TPR) > 2:
                res.append([f"Enabled Data Streams packet found at {round(EDS_TPR[0], 3)} sec with following data:", "Pass"])

                QI_desc = self.PktMethod.GetPayloadDetails(EDS_TPR[2], "Streams_Bitmask")[0]['sDescription'].strip()
                QI_value = self.PktMethod.GetPayloadDetails(EDS_TPR[2], "Streams_Bitmask")[0]['sRawData'].strip()

                if QI_desc == "QI Authentication" and QI_value == "0x02":
                    res.append([f"Streams_Bitmask: {QI_desc}-{QI_value}, Expected: QI Authentication-0x02", "Pass"])
                else:
                    res.append([f"Streams_Bitmask: {QI_desc}-{QI_value}, Expected: QI Authentication-0x02", "Fail"])

                if "resp_check" in Check['EDS_pkts']:
                    respid = self.PktMethod.GetPacketResponse2(EDS_TPR[2], [EDS_TPR[2]+1, Flow_limit[1]])
                    if respid is not None:
                        if "Enabled Data Streams" in self.file_list[respid]['pktType']:
                            res.append([f"PTx responded with Enabled Data Streams response at {round(self.file_list[respid]['startTime'],3)} sec", "Pass"])
                        else:
                            res.append([f"PTx responded with {self.file_list[respid]['pktType']} at {round(self.file_list[respid]['startTime'],3)} sec", "Fail"])
                    else:
                        res.append([f"PTx not responded", 'Fail'])
            else:
                res.append([f"TPR not sent Enabled Data Streams packet", 'Fail'])

        if Check['expected'][0].get('chk'):
            if "Illegal" in Check['expected'][0]['chk']:
                TempPkt1 = self.PktMethod.GetPacketDetails(
                    packet=Check['expected'][0]['packet1'][0], limit=[id, end], Type=Check['expected'][0]['packet1'][1])
                if len(TempPkt1) > 2:
                    res.append(
                        [f"Illegal {Check['expected'][0]['packet1'][0]} packet found at {round(TempPkt1[0], 3)} sec", "Pass"])
                    for nxt_pkt in Check['expected'][0]['packet2']:
                        TempPkt2 = self.PktMethod.GetPacketDetails(packet=nxt_pkt[0], limit=[TempPkt1[2] + 1, end + 1], Type=nxt_pkt[1])
                        if len(TempPkt2) > 2:
                            res.append([f"{nxt_pkt[0]} packet found at {round(TempPkt2[0], 3)} sec", "Pass"])
                            Tresult = round((TempPkt2[0] - TempPkt1[1]) * 1000, 3)
                            ChkRes = CommonMethods.check_measure(Check['expected'][0]['exp'], Tresult, Check['expected'][0]['comp'])
                            res.append(
                                [f"The Measured Tterminate between illegal {Check['expected'][0]['packet1'][0]} and {nxt_pkt[0]} is: {ChkRes[3]} ms, Limit: {ChkRes[2]} ms", ChkRes[1]])
                        else:
                            res.append([f"{nxt_pkt[0]} packet not found", "Fail"])
                else:
                    res.append([f"Illegal {Check['expected'][0]['packet1'][0]} packet not found", "Fail"])


            if "PWRmatch" in Check['expected'][0]['chk']:
                SDFppwr = self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['PotentialLoadPower']
                ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt, limit=[id, end], Type="Response")
                if len(ECAP) > 2:
                    ECAPppwr = float(self.PktMethod.GetPayloadDetails(ECAP[2], "Potential_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                    ECAPnpwr = float(self.PktMethod.GetPayloadDetails(ECAP[2], "Negotiable_Load_Power")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                    if SDFppwr == ECAPppwr:
                        res.append(
                            [f"PTx DUT potential load power is {ECAPppwr} W is matching with SDF poentail power:{SDFppwr} W", "Pass"])
                    else:
                        res.append(
                            [f"Mismatch in PTx DUT potential load power is {ECAPppwr} W with SDF poentail power:{SDFppwr} W", "Fail"])
                    srq = self.PktMethod.GetPacketDetails(packet="SRQ", value="Extended Power Level Selection:", limit=[ECAP[2], end])
                    if len(srq) > 2:
                        srenpwr = float(self.PktMethod.GetPayloadDetails(srq[2], "Load_Power_low")[0]['sDescription'].split(":")[1].split("W")[0].strip())
                        if ECAPnpwr == srenpwr:
                            res.append(
                                [f"PTx DUT negotiable load power is {ECAPnpwr} W is matching with SRQ_Extended Power Level Selection load power:{srenpwr} W", "Pass"])
                        else:
                            res.append(
                                [f"Mismatch in PTx DUT potential load power is {ECAPnpwr} W with SRQ_Extended Power Level Selection load power:{srenpwr} W", "Fail"])
                    else:
                        res.append([f"SRQ_Extended Power Level Selection: packet not found", "Fail"])
                else:
                    res.append([f"{self.ECAP_pkt} packet not found", "Fail"])
        return res

    def Entry_init(self,Flow_limit,Check):
        res = []
        end = len(self.file_list)
        response_cnt = 1
        seqcnt_val = []
        start = 0
        while start < end:
            print("start:",start)
            pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[start, end], Type="TesterMsg")
            print("pd:",pd)
            if len(pd) > 2:
                sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], end], Type="TesterMsg")
                print("sd:",sd)
                if len(sd) > 2:
                    fop = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd[2], sd[2]], Type="TesterMsg")
                    print("fop:",fop)
                    if len(fop) > 2:
                        fopval = float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0])
                        ChkRes = CommonMethods.check_measure([127.5, 128.5], fopval, 0)
                        
                        if 127.5 < fopval < 128.5:
                            id2 = pd[2]
                            while id2 < sd[2]:
                                if self.file_list[id2]['isTesterPkt'] == True and self.file_list[id2]['isFWTestermessage'] == False:
                                    # res.append([f"Ping detected at {round(pd[0],3)} sec", "Pass"])
                                    # res.append([f"Fop is {ChkRes[3]} kHz found at {round(fop[0], 3)} sec, Limit: {ChkRes[2]} kHz", ChkRes[1]])
                                    res.append([f"TPR responded with {self.file_list[id2]['pktType']} to the digital ping 128kHz at {round(self.file_list[id2]['startTime'], 3)}sec", "Pass"])

                                    # Neg phase
                                    x = id2
                                    y = sd[2]
                                    while x < y:
                                        if "Nego" in self.file_list[x]['description']:
                                            res.append([f"Entered to Negotiation phase at {round(self.file_list[x]['startTime'], 3)} sec", "Pass"])
                                            break
                                        x += 1
                                    else:
                                        res.append([f"Negotiation phase not observed", "Fail"])

                                    srqen = self.PktMethod.GetPacketDetails(packet="SRQ", value="End Negotiation", limit=[id2, sd[2]], Type="Packet")
                                    if len(srqen) > 2:
                                        srqvalue = int(self.file_list[srqen[2]]['value'].split(":")[1].split("}")[0])
                                        res.append([f"SRQ Count {response_cnt}: SRQ - End Negotiation packet with SRQ/en : {srqvalue} found at {round(srqen[0], 3)} sec", "Pass"])
                                        seqcnt_val.append(srqvalue)
                                        if response_cnt >= 2:
                                            break


                                        coilre = self.PktMethod.GetPacketDetails(packet="Coil_Remove_From_Base_Station", limit=[srqen[2], end], Type="TesterMsg")
                                        if len(coilre) > 2:
                                            useract1 = self.PktMethod.GetPacketDetails(packet="User Action status", limit=[coilre[2], end], Type="TesterMsg")
                                            if len(useract1) > 2:
                                                res.append([f"TPR removed from PTx surface at {round(useract1[0],3)} sec", "Pass"])
                                                t1 = self.file_list[useract1[2]]['stopTime']
                                                coilpl = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station", limit=[useract1[2], end], Type="TesterMsg")
                                                if len(coilpl) > 2:
                                                    useract2 = self.PktMethod.GetPacketDetails(packet="User Action status", limit=[coilpl[2], end], Type="TesterMsg")
                                                    if len(useract2) > 2:
                                                        res.append([f"TPR placed on PTx surface at {round(useract2[0],3)} sec", "Pass"])
                                                        t2 = self.file_list[useract2[2]]['startTime']
                                                        Trpchk = CommonMethods.check_measure([5, 10], round(t2 - t1, 3), 0)
                                                        res.append([f"Tremoveplace is: {Trpchk[3]} sec, limit: {Trpchk[2]} sec", Trpchk[1]])

                                    response_cnt += 1
                                    break
                                id2 += 1
                                if response_cnt > 2:
                                    break
                        if response_cnt > 2:
                            break
                    # else:
                    #     res.append([f"Fop TesterMsg not found", "Fail"])
                    start =sd[2]   
            #     else:
            #         res.append([f"Shutdown not found in the digital ping", "Fail"])
            # else:
            #     res.append([f"digital ping not found", "Fail"])

            start += 1
        if len(seqcnt_val) == 2:
            if seqcnt_val[0] == seqcnt_val[1]:
                res.append([f"SRQ count 1 is matching with SRQ count 2", "Pass"])
            else:
                res.append([f"Mismatch in SRQ/en count values, SRQ/en count1:{seqcnt_val[0]}, SRQ/en count2:{seqcnt_val[1]}", "Pass"])
        else:
            res.append([f"2 128khHz digital ping sequences not found", "Fail"])
        return res

    def DigitalPing_response(self,Flow_limit):
        res = []
        pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[Flow_limit[0], Flow_limit[1]], Type="TesterMsg")
        if len(pd) > 2:
            res.append([f"Digital ping found at {round(self.file_list[pd[2]]['startTime'], 3)}sec", "Pass"])
            sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], Flow_limit[1]+2], Type="TesterMsg")
            if len(sd) > 2:
                fop = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd[2], sd[2]], Type="TesterMsg")
                if len(fop) > 2:
                    ChkRes = CommonMethods.check_measure([127.5, 128.5], float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]), 0)
                    res.append([f"{self.file_list[fop[2]]['value']} is observed at {round(fop[0], 3)} sec, Expected: {ChkRes[2]} kHz", ChkRes[1]])
                id2 = pd[2]
                while id2 < sd[2]:
                    if self.file_list[id2]['isTesterPkt'] == True and self.file_list[id2]['isFWTestermessage'] == False:
                        res.append([f"TPR responded with {self.file_list[id2]['pktType']} at {round(self.file_list[id2]['startTime'], 3)}sec", "Pass"])
                        break
                    id2 += 1
                else:
                    res.append([f"TPR not responded to  digital ping 128 kHz from {round(pd[0], 3)} sec to {round(sd[0], 3)} sec", "Fail"])
            else:
                res.append([f"Shutdown not found in the digital ping", "Fail"])
        else:
            res.append([f"digital ping not found", "Fail"])

        return res


    def RMS_voltage(self,id,TempPkt,Flow_limit,pkt):
        RMS_flag = False
        vrect = None
        x = TempPkt[2]
        while not RMS_flag:
            end1 = Flow_limit[1]
            if pkt['t'][2] == "before":
                end1 = Flow_limit[0] #id
            elif pkt['t'][2] == "after":
                end1 = Flow_limit[1]
            print("x,end1:",x,end1)
            RMS_pkt = self.PktMethod.GetPacketDetails(packet="RMS_Data", limit=[x, end1], Type="TesterMsg")
            print("RMS_pkt:",RMS_pkt)
            if len(RMS_pkt) > 2:
                t1 = None
                if pkt['t'][1] == 'start':
                    t1 = abs((float(TempPkt[0]) - float(RMS_pkt[0])) * 1000)
                elif pkt['t'][1] == 'end':
                    t1 = abs((float(TempPkt[1]) - float(RMS_pkt[0])) * 1000)
                print("t1:",t1,pkt['t'][0][0],pkt['t'][0][1])
                if pkt['t'][0][0] != pkt['t'][0][1]:
                    if pkt['t'][0][0] <= t1 <= pkt['t'][0][1]:
                        RMS_flag = True
                        vrect = float(self.file_list[RMS_pkt[2]]['value'].split(":")[2].split()[0])
                        print("vrect:",vrect)
                        break
                else:
                    if (pkt['t'][0][0]-0.5) <= t1 <= (pkt['t'][0][1]+0.5):
                        RMS_flag = True
                        vrect = float(self.file_list[RMS_pkt[2]]['value'].split(":")[2].split()[0])
                        print("vrect:",vrect)
                        break
                if t1 > pkt['t'][0][1]:
                    break
                x = RMS_pkt[2]+1
            else:
                # res.append([f"RMS_Data packet not found", "Fail"])
                break
        return vrect

        
    def Uro(self, Flow_limit, Check):
        res = []
        if self.stability is not None:
            id = self.stability
            for pkt in Check['expected']:
                start = 0
                if pkt.get('packet1'):
                    while start <= pkt['cnt']:
                        # RMS_flag = False
                        if pkt.get('refpkt'):
                            refpkt1 = self.PktMethod.GetPacketDetails(packet=pkt ['refpkt'][0], value=pkt['refpkt'][1], limit=[id, Flow_limit[1]], Type=pkt['refpkt'][2])
                            if len(refpkt1) > 2:
                                id = refpkt1[2]
                        TempPkt1 = self.PktMethod.GetPacketDetails(packet=pkt['packet1']['packet'][0], value=pkt['packet1']['packet'][1], limit=[id, Flow_limit[1]], Type=pkt['packet1']['packet'][2])
                        if len(TempPkt1) > 2:

                            vrect1 = self.RMS_voltage(id,TempPkt1,Flow_limit,pkt['packet1'])
                            print("vrect1:",vrect1)
                            if vrect1 is not None:
                                res.append([f"Measured {pkt['packet1']['uro_type']} is {vrect1} mV", "Pass"])
                            else: 
                                res.append([f"RMS_Data packet not found", "Fail"])
                            
                            if pkt.get('pkt1_resp'):
                                respid = self.PktMethod.GetPacketResponse2(TempPkt1[2], [TempPkt1[2]+1, Flow_limit[1]])
                                if respid is not None:
                                    if self.file_list[respid]['pktType'] == pkt['pkt1_resp']:
                                        res.append([f"Received response for {pkt['packet1']['packet'][0]} is: {self.file_list[respid]['pktType']}", "Pass"])
                                    else:
                                        res.append([f"Received response for {pkt['packet1']['packet'][0]} is: {self.file_list[respid]['pktType']}, expected: {pkt['pkt1_resp']}", "Inconclusive"])
                                else:
                                    res.append([f"Response for {pkt['packet1']['packet'][0]} packet not found", "Fail"])

                            if pkt.get('t1b'):
                                vrect2 = self.RMS_voltage(id,TempPkt1,Flow_limit,pkt['t1b'])
                                print("vrect2:",vrect2)
                                if vrect2 is not None:
                                    res.append([f"Measured {pkt['t1b']['uro_type']} is {vrect2} mV", "Pass"])
                                    ChkRes = CommonMethods.check_measure(pkt['exp'], round(abs(vrect1 - vrect2), 3), pkt['comp'])
                                    res.append([f"The Measured |{pkt['packet1']['uro_type']}-{pkt['t1b']['uro_type']}| is: {ChkRes[3]} mV, Limit: {ChkRes[2]} mV", ChkRes[1]])
                                    id = TempPkt1[2] + 1
                                    start += 1
                                else: 
                                    res.append([f"RMS_Data packet not found", "Fail"])
                                        
                            if pkt.get('packet2'):
                                # TempPkt2 = self.PktMethod.GetPacketDetails(packet=pkt['packet2']['packet'][0], limit=[TempPkt1[2] + 1, Flow_limit[1]], Type=pkt['packet2']['packet'][2])
                                # if len(TempPkt2) > 2:
                                desired_pkt=self.PktMethod.NextOcuurance("Packet",[TempPkt1[2]+1,Flow_limit[1]])
                                if desired_pkt is not None:
                                    TempPkt2 = [self.file_list[desired_pkt]['startTime'],self.file_list[desired_pkt]['stopTime'],desired_pkt]
                                    print("TempPkt2:",TempPkt2)
                                    vrect2 = self.RMS_voltage(id,TempPkt2,Flow_limit,pkt['packet2'])
                                    print("vrect2:",vrect2)
                                    if vrect2 is not None:
                                        res.append([f"Measured {pkt['packet2']['uro_type']} is {vrect2} mV", "Pass"])
                                        # res.append([f"Measured Uro2 is {vrect2} V at {pkt['packet2']['packet'][0]} at {self.PktMethod.Timeconvert(TempPkt2[0])}", "Pass"])
                                        ChkRes = CommonMethods.check_measure(pkt['exp'], round(abs(vrect1 - vrect2), 3), pkt['comp'])
                                        res.append([f"The Measured |{pkt['packet1']['uro_type']}-{pkt['packet2']['uro_type']}| is: {ChkRes[3]} mV, Limit: {ChkRes[2]} mV", ChkRes[1]])
                                        if pkt.get('pkt2_resp'):
                                            resp_pkt = self.file_list[TempPkt2[2] + 1]['pktType']
                                            ChkRes = CommonMethods.check_measure(pkt['pkt2_resp'], resp_pkt, "EQL")
                                            res.append([f"Received responce for {pkt['packet2'][0]} is: {ChkRes[3]}, expected: {ChkRes[0]}", ChkRes[1]])
                                        id = TempPkt2[2] + 1
                                        start += 1
                                    else: 
                                        res.append([f"RMS_Data packet not found", "Fail"])
                        else: break
                        if start == pkt['cnt']:
                            break
                # break

        return res
        




















        # res = []
        # if self.stability is not None:
        #     id = self.stability
        #     for pkt in Check['expected']:
        #         start = 0
        #         if pkt.get('packet1'):
        #             while start <= pkt['cnt']:
        #                 if pkt.get('refpkt'):
        #                     refpkt1 = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0], value=pkt['refpkt'][1], limit=[id, Flow_limit[1]], Type=pkt['refpkt'][2])
        #                     if len(refpkt1) > 2:
        #                         id = refpkt1[2]
        #                 TempPkt1 = self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0], value=pkt['packet1'][1], limit=[id, Flow_limit[1]], Type=pkt['packet1'][2])
        #                 if len(TempPkt1) > 2:
        #                     vrect1 = self.CalculateVoltTwindow(TempPkt1[2], self.AllChannelData, at=pkt['t1a'][1], measure=pkt['t1a'][2], winsize=pkt['t1a'][0])
        #                     res.append([f"Measured Uro1 is {vrect1[0]} V at {pkt['packet1'][0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}", "Pass"])
        #                     if pkt.get('pkt1_resp'):
        #                         resp_pkt = self.file_list[TempPkt1[2] + 1]['pktType']
        #                         ChkRes = CommonMethods.check_measure(pkt['pkt1_resp'], resp_pkt, comp="EQL")
        #                         res.append([f"Received responce for {pkt['packet1'][0]} is: {ChkRes[3]}, expected: {ChkRes[0]}", ChkRes[1]])
        #                     if pkt.get('t1b'):
        #                         vrect2 = self.CalculateVoltTwindow(TempPkt1[2], self.AllChannelData, at=pkt['t1b'][1], measure=pkt['t1b'][2], winsize=pkt['t1b'][0])
        #                         ChkRes = CommonMethods.check_measure(pkt['exp'], round(abs((vrect1[0] - vrect2[0]) * 1000), 3), pkt['comp'])
        #                         res.append([f"Measured Uro2 is {vrect2[0]} V at {pkt['packet1'][0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}", "Pass"])
        #                         res.append([f"The Measured |Uro1-Uro2| is: {ChkRes[3]} mV, Limit: {ChkRes[2]} mV", ChkRes[1]])
        #                         id = TempPkt1[2] + 1
        #                         start += 1
        #                     if pkt.get('packet2'):
        #                         TempPkt2 = self.PktMethod.GetPacketDetails(packet=pkt['packet2'][0], limit=[TempPkt1[2] + 1, Flow_limit[1]], Type=pkt['packet2'][2])
        #                         if len(TempPkt2) > 2:
        #                             vrect2 = self.CalculateVoltTwindow(TempPkt2[2], self.AllChannelData, at=pkt['t2a'][1], measure=pkt['t2a'][2], winsize=pkt['t2a'][0])
        #                             res.append([f"Measured Uro2 is {vrect2[0]} V at {pkt['packet2'][0]} at {self.PktMethod.Timeconvert(TempPkt2[0])}", "Pass"])
        #                             ChkRes = CommonMethods.check_measure(pkt['exp'], round(abs((vrect1[0] - vrect2[0]) * 1000), 3), pkt['comp'])
        #                             res.append([f"The Measured |Uro1-Uro2| is: {ChkRes[3]} mV, Limit: {ChkRes[2]} mV", ChkRes[1]])
        #                             if pkt.get('pkt2_resp'):
        #                                 resp_pkt = self.file_list[TempPkt2[2] + 1]['pktType']
        #                                 ChkRes = CommonMethods.check_measure(pkt['pkt2_resp'], resp_pkt, "EQL")
        #                                 res.append([f"Received responce for {pkt['packet2'][0]} is: {ChkRes[3]}, expected: {ChkRes[0]}", ChkRes[1]])
        #                             id = TempPkt2[2] + 1
        #                             start += 1
        #                 if start == pkt['cnt']:
        #                     break


        # return res

    
    def Exempted_Packets(self, Flow_limit, Check):
        res = []
        for pkt in Check['expected']:
            if "PktLimit" in pkt:
                limit = self.PktMethod.GetLimits(pkt['PktLimit'], pkt, Flow_limit)
            else:
                limit = Flow_limit
            refpkt = self.PktMethod.GetPacketDetails(
                packet=pkt['refpkt'][0], value=pkt['refpkt'][1],
                limit=[Flow_limit[0], len(self.file_list) - 1], Type=pkt['refpkt'][2])
            Pktcount = 0
            if len(refpkt) > 2:
                id = refpkt[2]
                while id < limit[1]:
                    TempPkt = self.PktMethod.GetPacketDetails(packet=pkt['packet'][0], value=pkt['packet'][1], limit=[id, limit[1]], Type=pkt['packet'][2])
                    if len(TempPkt) > 2:
                        res.append([f"{pkt['packet'][0]} {pkt['packet'][1] if pkt['packet'][1] is not None else ''} {pkt['packet'][2]} found at {round(TempPkt[0], 3)} sec after {pkt['refpkt'][0]}", "Fail"])
                        id = TempPkt[2]
                        Pktcount += 1
                    id += 1
            else:
                res.append([f"{pkt['refpkt'][0]} {pkt['refpkt'][1] if pkt['refpkt'][1] is not None else ''} {pkt['refpkt'][2]} not found", 'Pass'])
            if Pktcount > 0:
                res.append([f"Received {Pktcount} {pkt['packet'][0]} {pkt['packet'][1] if pkt['packet'][1] is not None else ''} {pkt['packet'][2]} after {pkt['refpkt'][0]}", "Fail"])
            else:
                res.append([f"{pkt['packet'][0]} {pkt['packet'][1] if pkt['packet'][1] is not None else ''} {pkt['packet'][2]} not found after {pkt['refpkt'][0]} {pkt['refpkt'][1] if pkt['refpkt'][1] is not None else ''}", "Pass"])


        return res

    def InitialVoltage(self,Flow_limit,Check):
        res = []
        if self.initialVolt is not None:
            res.append([f"The Measured voltage is {self.initialVolt}V at {round(self.file_list[self.stability]['startTime'],2)}sec","Pass"])
        else:res.append(["Stabilization not found","Fail"])
        return res

    def FOPresent(self, Flow_limit, Check):
        res = []
        limit = Flow_limit
        id = limit[0]
        UA = self.PktMethod.GetPacketDetails(packet='User Action status', limit=[id, limit[1]], Type="TesterMsg")
        if len(UA) > 2:
            end = UA[2]
        else:
            end = limit[1]
        respid = 0
        nakcnt = 0
        while id < end:
            PLA = self.PktMethod.GetPacketDetails(packet='Power Loss Accounting', limit=[id, end])
            if len(PLA) > 2:
                respid = self.PktMethod.GetPacketResponse2(PLA[2], [PLA[2] + 1, limit[1]])
                if respid is not None:
                    if self.file_list[respid]['pktType'] == "NAK":
                        nakcnt += 1
                        res.append(
                            [f"NAK response received for Power Loss Accounting packet at {round(PLA[0], 3)} sec", 'Pass'])
                        res.append(
                            [f"NAK received for Power Loss Accounting packet before RFO inserting at {self.PktMethod.Timeconvert(self.file_list[respid]['startTime'])}", 'Fail'])
                        break
                id = PLA[2]
            id += 1
        if nakcnt == 0:
            res.append([f"NAK not received for Power Loss Accounting packet before RFO inserting", 'Pass'])

        # After inserting RFO
        if len(UA)> 2:
            res.append([f'RFO insertion started from {round(UA[0],3)} sec', 'Pass'])
            self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
            self.AllChannelData3= self.PlotMethod.GetAllChannelData('3',self.JapiData)
            id = UA[2]
            Consecutive_NAK_cnt = 0
            throttle_cnt = 0

            print("new limit:",id,limit[1])
            # Vrect_drop_data = []
            v1x = 0
            v2x = 0
            max_drop = 0
            max_drop_PLA = 0
            tx = 0
            last_NAK = 0
            t_start = 0
            while id < limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[id,limit[1]])
                # print("TempPkt2:",TempPkt2)
                if len(TempPkt2)>2:
                    Pktresp = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,limit[1]])
                    # if Pktresp is not None:
                    #     res.append([f"{self.file_list[Pktresp]['pktType']} response received to PLA_2 packet at {round(TempPkt2[0],3)} sec", "Pass"])
                        
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
                            throttle_cnt += 1
                            if throttle_cnt == 1:
                                t_start = TempPkt2[0]

                                
                            # last_NAK = x
                            res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                        else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])

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

                                print("TempPkt2[2]:",TempPkt2)
                                print("Vrect(end+19):",v1)
                                print("Vrect(end+40):",v2)
                                print("Vrect drop:",abs(v2-v1))
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
                    # res.append([f"Removed the applied POFFSET from {round(TempPkt2[0],3)} sec", "Pass"]) 
                    break
                id += 1

            # print("v1x:",v1x,"v2x:",v2x,"max_drop:",max_drop,"tx:",tx,"t1:",(tx+19)/1000,"t2:",(tx+40)/1000)
            # print("throttle_cnt:",throttle_cnt)
            if max_drop < 1:
                res.append([f"During PTx-DUT power throttling, Maximum Vrect drop: {round(max_drop,3)} V found at PLA @index {max_drop_PLA}, with the following measurements:, Limit: Vrect drop < 1V", "Pass"])
                
            else: 
                res.append([f"During PTx-DUT power throttling, Maximum Vrect drop: {round(max_drop,3)} V found at PLA @index {max_drop_PLA}, with the following measurements:, Limit: Vrect drop < 1V", "Fail"])
            res.append([f"Vrect_1 :{round(v1x,3)}V measured at {round((tx+19)/1000,3)}s , Vrect_2 :{round(v2x,3)}V measured at {round((tx+40)/1000,3)}s", "Pass"])
            res.append([f"Power Loss Accounting packets count where PTx throttled: {throttle_cnt}", "Pass"])

            #Check for execution time from Throttling # min 1 min
            t_diff = self.file_list[Flow_limit[1]]['startTime'] - t_start
            print("t_diff:",t_diff)
            if t_diff >= 60:
                res.append([f"Testing continued for more than 1 min from the point of stopping RFO movement.","Pass"])

            elif t_diff < 60:
                atn = self.PktMethod.GetPacketDetails(packet="ATN",limit=[last_NAK,limit[1]],Type="Response")
                if len(atn) > 2:
                    res.append([f"PTx sent ATN packet after power throttling at {round(atn[0],3)} sec", "Pass"])
                    reneg = self.PktMethod.GetPacketDetails(packet="Renegotiate",limit=[atn[2],limit[1]])
                    if len(reneg) > 2:
                        res.append([f"TPR sent Renegotiate packet after power throttling at {round(reneg[0],3)} sec", "Pass"])
                        respid = self.PktMethod.GetPacketResponse2(reneg[2],[reneg[2]+1,limit[1]])
                        if respid is not None:
                            if 'ACK' in self.file_list[respid]['pktType']:
                                res.append([f"PTx sent ACK response to Renegotiate packet after power throttling at {round(self.file_list[respid]['startTime'],3)} sec", "Pass"])
                            else:
                                res.append([f"PTx not sent ACK response to Renegotiate packet after power throttling at {round(self.file_list[respid]['startTime'],3)} sec", "Fail"])
                        else:
                            res.append([f"No response received for Renegotiate packet after power throttling", "Fail"])
                    else:
                        res.append([f"PTx not sent Renegotiate packet after power throttling", "Fail"])
                else:
                    res.append([f"PTx not initiated renegotiation with ATN after power throttling", "Fail"])
            else: 
                res.append([f"Testing continued for more than 1 min from the point of stopping RFO movement and PTx not initiated renegotiation with ATN after power throttling", "Fail"])

            if last_NAK != 0:
                id2 = last_NAK
                while id2 < limit[1]:
                    safe_pla = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[id2,limit[1]])
                    if len(safe_pla) > 2:
                        respid2 = self.PktMethod.GetPacketResponse2(safe_pla[2],[safe_pla[2]+1,limit[1]])
                        if respid2 is not None:
                            if "ACK" in self.file_list[respid2]['pktType']:
                                res.append([f"PTx-DUT sends NAKs to Power Loss Accounting until a new stable power level is reached, then sends an ACK at {round(safe_pla[0],3)} sec", "Pass"])
                                break
                        else:
                            res.append([f"No response received for Power Loss Accounting at {round(safe_pla[0],3)} sec", "Fail"])
                        id2 = safe_pla[2]
                    else:
                        res.append([f"Stable power is not reached.", "Fail"])
                    id2 += 1
                else: 
                    res.append([f"ACK is not received to Power Loss Accounting after renegotiation", "Fail"])
            else:
                res.append([f"No NAK Response received to Power Loss Accounting packets while inserting RFO", "Fail"])



        return res
    def EDSCheck(self, Flow_limit, Check):
        res = []
        allresp = []
        for chk in Check["expected"]:
            allresp.append(self.EDSFlow(chk))
        res = [sub for group in allresp for sub in group]


        return res
    def AuthCheck(self, Flow_limit, Check):
        res = []
        allresp = []
        for chk in Check["expected"]:
            allresp.append(self.AuthFlow(chk))
        res = [sub for group in allresp for sub in group]   
        return res

    def Certificate_chain_segment(self,Flow_limit,Check):
        res = []
        prev_len = 0
        auth_limit = [0, len(self.Auth_file_list)]
        # print("auth_limit:",auth_limit)
        id = 0
        while id < auth_limit[1]:
            get_cert = self.GetAuthPacketDetails(packet="GET_CERTIFICATE", limit=[id,auth_limit[1]], Type="Packet")
            # print("get_cert: ", get_cert)
            if len(get_cert) > 2:
                res.append([f"GET_CERTIFICATE packet found at {self.PktMethod.Timeconvert(get_cert[0])}", "Pass"])
                cert_resp = self.GetAuthPacketDetails(packet="CERTIFICATE", limit=[get_cert[2],auth_limit[1]], Type="Response")
                # print("cert_resp: ", cert_resp)
                if len(cert_resp) > 2:
                    res.append([f"CERTIFICATE response found at {self.PktMethod.Timeconvert(cert_resp[0])} with following details", "Pass"])
                    header_Payload = self.Auth_file_list[cert_resp[2]]['header_Payload']['sFieldType'].split(":")[-1].strip()
                    if "header_start" in Check:
                        header_start_val = header_Payload.split()[0]
                        if header_start_val == Check['header_start']:
                            res.append([f"Certificate response starts with header {header_start_val}, Expected:{Check['header_start']}", "Pass"])
                        else:
                            res.append([f"Certificate response starts with header {header_start_val}, Expected:{Check['header_start']}", "Fail"])

                    cert_length = len(header_Payload.split(" "))-1
                    Fianl_len = cert_length-prev_len
                    # update previous length
                    prev_len = cert_length
                    
                    # Certificate_Chain_Segment = self.GetAuthPayloadDetails(cert_resp[2], "Certificate_Chain_Segment", f"B1_B{upper_byte}", "[7:0")[0]['sRawData']
                    # res.append([f"Length of Certificate_Chain_Segment: {Fianl_len}", "Pass"])
                    # cert_chain_len = len(Certificate_Chain_Segment.split("-"))
                    if 1 <= Fianl_len <= Check['expected']:
                        res.append([f"Length of Certificate_Chain_Segment: {Fianl_len}, Expected: [1-{Check['expected']}]", "Pass"])
                    else:
                        res.append([f"Length of Certificate_Chain_Segment: {Fianl_len}, Expected: [1-{Check['expected']}]", "Fail"])
                    id = cert_resp[2]
                else:
                    res.append(["CERTIFICATE response not found", "Fail"])
          
            id += 1

        if "complete_certificate_chain" in Check:
            Final_certificate = self.GetAuthPacketDetails(packet="CERTIFICATE", limit=[len(self.Auth_file_list)-1, 0], Type="Response")
            if len(Final_certificate)>2:
                Full_certificate = self.Auth_file_list[Final_certificate[2]]['header_Payload']['sFieldType'].split(":")[-1].strip()
                modified_full_certificate = Full_certificate.replace("0x","").strip()
                res.append([f"Received complete certificate chain is: {Full_certificate}", "Pass"])

                # WPC_root = self.GetAuthPayloadDetails(Final_certificate[2], "Root_Certificate_Hash", "B3_B34", "[7:0")[0]['sRawData'].strip()
                WPC_root = self.PayloadDetails_Auth(Final_certificate[2], "Root_Certificate_Hash")[0]['sRawData'].strip()
                modified_WPC_root = WPC_root.replace("-"," ")
                res.append([f"WPC Root is: {WPC_root}", "Pass"])

                # Manufacturee_certificate = self.GetAuthPayloadDetails(Final_certificate[2], "Manufacturer_CA_Certificate", "B35_B331", "[7:0")[0]['sRawData'].strip()
                Manufacturee_certificate = self.PayloadDetails_Auth(Final_certificate[2], "Manufacturer_CA_Certificate")[0]['sRawData'].strip()
                modified_Manufacturee_certificate = Manufacturee_certificate.replace("-"," ")
                res.append([f"Manufacturer certificate is: {Manufacturee_certificate}", "Pass"])

                if modified_WPC_root in modified_full_certificate and modified_Manufacturee_certificate in modified_full_certificate:
                    res.append([f"Certificate chain is signed by WPC root certificate key", "Pass"])
                else:
                    res.append([f"Certificate chain is not signed by WPC root certificate key", "Fail"])
                
            else:
                res.append(["Complete certificate chain not found", "Fail"])

        return res
    
    def t_certReady(self,Flow_limit,Check):
        res = []

        id = 0
        while id < Flow_limit[1]:
            sadc_open = self.PktMethod.GetPacketDetails(packet="SADC",value="Open Stream", limit=[id,Flow_limit[1]], Type="Packet")
            if len(sadc_open)>2:
                sadt1 = self.PktMethod.GetPacketDetails(packet="SADT", limit=[sadc_open[2],Flow_limit[1]], Type="Packet")
                if len(sadt1) > 2:
                    cert1_data = self.PktMethod.GetPayloadDetails(sadt1[2], Check['Certificate1'])
                    if cert1_data:
                        cert1 = cert1_data[0]['sDescription'].strip()
                        if cert1 == Check['Certificate1']:
                            sadc1 = self.PktMethod.GetPacketDetails(packet="SADC",value="Close Stream", limit=[sadt1[2],Flow_limit[1]], Type="Packet")
                            if len(sadc1)>2:
                                res.append([f"{cert1}: SDAC Close Stream packet ending is observed at {round(sadc1[1],3)} sec", "Pass"])
                                t1 = sadc1[1]
                                
                                sadt2 = self.PktMethod.GetPacketDetails(packet="SADT", limit=[sadc1[2],Flow_limit[1]], Type="Response")
                                if len(sadt2)>2:
                                    cert2_data = self.PktMethod.GetPayloadDetails(sadt2[2], Check['Certificate2'])
                                    if cert2_data:
                                        cert2 = cert2_data[0]['sDescription'].strip()
                                        if cert2 == Check['Certificate2']:
                                            sadc2 = self.PktMethod.GetPacketDetails(packet="SADC",value="Open Stream", limit=[sadt2[2],sadc1[2]], Type="Response")
                                            if len(sadc2)>2:
                                                atn = self.PktMethod.GetPacketDetails(packet="ATN", limit=[sadc2[2],sadc1[2]], Type="Response")
                                                if len(atn)>2:
                                                    res.append([f"ATN response for {cert2} is observed at {round(atn[1],3)} sec", "Pass"])
                                                    t2 = atn[0]
                                                    t_diff = t2-t1
                                                    if t_diff <= 3:
                                                        res.append([f"Measured t_{Check['Certificate2']}Ready is {round(t_diff*1000,3)} mS, Expected: ≤ 3 Seconds", "Pass"])
                                                    else:
                                                        res.append([f"Measured t_{Check['Certificate2']}Ready is {round(t_diff*1000,3)} mS, Expected: ≤ 3 Seconds", "Fail"])
                                                    break
                                                else: res.append([f"ATN response for {cert2} not found", "Fail"])
                                            else: res.append([f"SADC Open Stream response for {cert2} not found", "Fail"])
                                else: res.append([f"SADT response for {cert2} not found", "Fail"])
                            else: res.append([f"SADC Close Stream packet for {cert1} not found", "Fail"])       
                    else: id = sadt1[2]
                                     
            id += 1














        # id = 0
        #     while id < Flow_limit[1]:
        #         sadt1 = self.PktMethod.GetPacketDetails(packet="SADT", limit=[id,Flow_limit[1]], Type="Packet")
        #         if len(sadt1) > 2:
        #             cert1 = self.PktMethod.GetPayloadDetails(sadt1[2], Check['Certificate1'])[0]['sDescription'].strip()
        #             if cert1 == Check['Certificate1']:
        #                 sadc1 = self.PktMethod.GetPacketDetails(packet="SADC",value="Close Stream", limit=[sadt1[2],Flow_limit[1]], Type="Packet")
        #                 if len(sadc1)>2:
        #                     res.append([f"{cert1}: SDAC Close Stream packet ending is observed at {round(sadc1[1],3)} sec", "Pass"])
        #                     t1 = sadc1[1]

        #                     sadt2 = self.PktMethod.GetPacketDetails(packet="SADT", limit=[sadc1[2],Flow_limit[1]], Type="Response")
        #                     if len(sadt2)>2:
        #                         cert2 = self.PktMethod.GetPayloadDetails(sadt2[2], Check['Certificate2'])[0]['sDescription'].strip()
        #                         if cert2 == Check['Certificate2']:
        #                             sadc2 = self.PktMethod.GetPacketDetails(packet="SADC",value="Open Stream", limit=[sadt2[2],sadc1[2]], Type="Response")
        #                             if len(sadc2)>2:
        #                                 atn = self.PktMethod.GetPacketDetails(packet="ATN", limit=[sadc2[2],sadc1[2]], Type="Response")
        #                                 if len(atn)>2:
        #                                     res.append([f"ATN response for {cert2} is observed at {round(atn[1],3)} sec", "Pass"])
        #                                     t2 = atn[0]
        #                                     t_diff = t2-t1
        #                                     if t_diff <= 3:
        #                                         res.append([f"Measured t_{Check['Certificate2']}Ready is {round(t_diff*1000,3)} mS, Expected: ≤ 3 Seconds", "Pass"])
        #                                     else:
        #                                         res.append([f"Measured t_{Check['Certificate2']}Ready is {round(t_diff*1000,3)} mS, Expected: ≤ 3 Seconds", "Fail"])
        #                                     break
                
                                     
        #     id += 1
        return res

        
    def AuthMessages(self, Flow_limit, Check):
        res = []
        id = 0
        BitsCompare = {}
        base_limit = [0, len(self.Auth_file_list)]
        for chk in Check["expected"]:
            if 'PktLimit' in chk:
                if chk['PktLimit'] == 'ReversefromNthpkt':
                    cnt = 0
                    exp_cnt = chk['CustomLimit']['nthpkt']
                    id = 0
                    while id <= base_limit[1]:
                        CP = self.GetAuthPacketDetails(packet=chk['CustomLimit']['Packet'][0], value=chk['CustomLimit']['Packet'][1],limit=[id, base_limit[1]], Type=chk['CustomLimit']['Packet'][2])
                        if len(CP) > 2:
                            cnt += 1
                            if cnt == exp_cnt:
                                auth_limit = [CP[2], base_limit[0]]
                                break
                            id = CP[2]
                        id += 1
                elif chk['PktLimit'] == 'BTWNpkts':
                    CP1 = self.GetAuthPacketDetails(packet=chk['CustomLimit']['Packet1'][0], value=chk['CustomLimit']['Packet1'][1],limit=auth_limit, Type=chk['CustomLimit']['Packet1'][2])
                    CP2 = self.GetAuthPacketDetails(packet=chk['CustomLimit']['Packet2'][0], value=chk['CustomLimit']['Packet2'][1],limit=chk, Type=chk['CustomLimit']['Packet1'][2])
                    if len(CP1) > 2 and len(CP2) > 2:
                        auth_limit = [CP1[2], CP2[2]]
                elif chk['PktLimit'] == "FromCustomPacket":
                    CP = self.GetAuthPacketDetails(packet=chk['CustomLimit']['Packet'][0], value=chk['CustomLimit']['Packet'][1],limit=chk, Type=chk['CustomLimit']['Packet1'][2])
                    auth_limit = [CP[2] + 1, auth_limit[1]] if len(CP) > 2 else auth_limit
                elif chk['PktLimit'] == "UptoCustomPacket":
                    CP = self.GetAuthPacketDetails(packet=chk['CustomLimit']['Packet'][0], value=chk['CustomLimit']['Packet'][1],limit=chk, Type=chk['CustomLimit']['Packet1'][2])
                    auth_limit = [auth_limit[0], CP[2]] if len(CP) > 2 else auth_limit
            else:
                auth_limit = [0, len(self.Auth_file_list) - 1]
            authpkt = self.GetAuthPacketDetails(packet=chk['Packet'][0], value=chk['Packet'][1], limit=auth_limit, Type=chk['Packet'][2])
            if len(authpkt) > 2:
                print("authpkt:",authpkt)
                res.append([f"In {chk['CertType']}, {chk['Packet'][0]}_{chk['Packet'][1] if chk['Packet'][1] is not None else ''} {chk['Packet'][2]} found at {self.PktMethod.Timeconvert(authpkt[0])}", "Pass"])
                for ck in chk['Checks']:
                    # authpayload = self.GetAuthPayloadDetails(authpkt[2], ck, chk['Checks'][ck]['Byte'], chk['Checks'][ck]['Bit'])
                    authpayload = self.PayloadDetails_Auth(authpkt[2], ck)
                    # if len(authpayload) > 0:
                    print("authpayload:",authpayload)
                    if authpayload is not None:
                        for pyload in [authpayload[-1]]:
                            if chk['Checks'][ck]['comp'] == "str":
                                if 'expected' in chk['Checks'][ck]:
                                    if chk['Checks'][ck]['expected'] in pyload[chk['Checks'][ck]['flag']]:
                                        res.append([f"In {chk['CertType']}, the Recevied {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']]}, Expected: {chk['Checks'][ck]['expected']}", "Pass"])
                                    else:
                                        res.append([f"In {chk['CertType']}, the Recevied {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']]}, Expected: {chk['Checks'][ck]['expected']}", "Fail"])
                                if 'startswith' in chk['Checks'][ck]:
                                    if pyload[chk['Checks'][ck]['flag']][:5] == chk['Checks'][ck]['startswith']:
                                        res.append([f"In {chk['CertType']}, the Recevied {chk['Checks'][ck].get('CheckName', ck)} starts with {chk['Checks'][ck]['startswith']}", "Pass"])
                                    else:
                                        res.append([f"In {chk['CertType']}, the Recevied {chk['Checks'][ck].get('CheckName', ck)} starts with {pyload[chk['Checks'][ck]['flag']][:5]}, Expected: {chk['Checks'][ck]['startswith']}", "Fail"])
                                if 'compare' in chk['Checks'][ck]:
                                    if 'comp1' == chk['Checks'][ck]['compare'] or 'comp2' == chk['Checks'][ck]['compare']:
                                        BitsCompare[chk['Checks'][ck]['compare']] = [chk['CertType'], chk['Checks'][ck].get('CheckName', ck),pyload[chk['Checks'][ck]['flag']], chk['Checks'][ck].get('comparetype')]
                                        res.append([f"In {chk['CertType']}, the Recevied value for {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']]}", "Pass"])
                                if 'customexp' in chk['Checks'][ck]:
                                    # PTMC = self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['ManufacturerCode'].split("x")[1]
                                    PTMC = self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['MemberCode'].split("x")[1]
                                    SDF_QIID = int(self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['QIID'])
                                    comparedata = {"PTMC": PTMC, "Qi_ID": SDF_QIID}
                                    if chk['Checks'][ck]['customexp'] == "PTMC":
                                        data = pyload[chk['Checks'][ck]['flag']].split("-")[0]
                                    else:
                                        data = int(pyload[chk['Checks'][ck]['flag']])
                                    if comparedata[chk['Checks'][ck]['customexp']] == data:
                                        res.append([f"PTx {chk['Checks'][ck]['customexp']}: {data} is matching with SDF {chk['Checks'][ck]['customexp']}: {comparedata[chk['Checks'][ck]['customexp']]}", "Pass"])
                                    else:
                                        res.append([f"PTx {chk['Checks'][ck]['customexp']}: {data} is not matching with SDF {chk['Checks'][ck]['customexp']}: {comparedata[chk['Checks'][ck]['customexp']]}", "Fail"])
                                if 'expectedfromNth' in chk['Checks'][ck]:
                                    if chk['Checks'][ck]['expectedfromNth'] == pyload[chk['Checks'][ck]['flag']][chk['Checks'][ck]['comparefromNth']:]:
                                        res.append([f"In {chk['CertType']}, {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']][chk['Checks'][ck]['comparefromNth']:]}, matches expected", "Pass"])
                                    else:
                                        res.append([f"In {chk['CertType']}, {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']][chk['Checks'][ck]['comparefromNth']:]}, Expected: {chk['Checks'][ck]['expectedfromNth']}", "Fail"])
                            elif chk['Checks'][ck]['comp'] == "btw":
                                if chk['Checks'][ck]['flag'] == "sRawData":
                                    originaldata = int(pyload[chk['Checks'][ck]['flag']].replace("-", ""), 16)
                                    comparedata = [int(chk['Checks'][ck]['expected'][0], 16), int(chk['Checks'][ck]['expected'][1], 16)]
                                else:
                                    originaldata = int(pyload[chk['Checks'][ck]['flag']])
                                    comparedata = chk['Checks'][ck]['expected']
                                if originaldata >= comparedata[0] and originaldata <= comparedata[1]:
                                    res.append([f"In {chk['CertType']}, the Recevied {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']]}, within range {comparedata}", "Pass"])
                                else:
                                    res.append([f"In {chk['CertType']}, the Recevied {chk['Checks'][ck].get('CheckName', ck)} is {pyload[chk['Checks'][ck]['flag']]}, out of range {comparedata}", "Fail"])
                                if 'compare' in chk['Checks'][ck]:
                                    if 'comp1' == chk['Checks'][ck]['compare'] or 'comp2' == chk['Checks'][ck]['compare']:
                                        BitsCompare[chk['Checks'][ck]['compare']] = [chk['CertType'], chk['Checks'][ck].get('CheckName', ck),pyload[chk['Checks'][ck]['flag']], chk['Checks'][ck].get('comparetype')]
                    else:
                        res.append([f"In {chk['CertType']}, {chk['Checks'][ck].get('CheckName', ck)} not found", 'Fail'])
            else:
                res.append([f"{chk['Packet'][0]}_{chk['Packet'][1] if chk['Packet'][1] is not None else ''} {chk['Packet'][2]} not found", 'Fail'])
        print("BitsCompare:",BitsCompare)
        if len(BitsCompare) > 0:
            if BitsCompare['comp1'][3] == "EQL":
                if BitsCompare['comp1'][2] == BitsCompare['comp2'][2]:
                    res.append([f"{BitsCompare['comp1'][0]}'s, {BitsCompare['comp1'][1]}: {BitsCompare['comp1'][2]} is equal to {BitsCompare['comp2'][0]}'s, {BitsCompare['comp2'][1]}: {BitsCompare['comp2'][2]}, Expected: Both should be equal", "Pass"])
                else:
                    res.append([f"{BitsCompare['comp1'][0]}'s, {BitsCompare['comp1'][1]}: {BitsCompare['comp1'][2]} is not equal to {BitsCompare['comp2'][0]}'s, {BitsCompare['comp2'][1]}: {BitsCompare['comp2'][2]}, Expected: Both should be equal", "Fail"])
            elif BitsCompare['comp1'][3] == "NEQL":
                if BitsCompare['comp1'][2] != BitsCompare['comp2'][2]:
                    res.append([f"{BitsCompare['comp1'][0]}'s, {BitsCompare['comp1'][1]}: {BitsCompare['comp1'][2]} is not equal to {BitsCompare['comp2'][0]}'s, {BitsCompare['comp2'][1]}: {BitsCompare['comp2'][2]}, Expected: Both should not be equal", "Pass"])
                else:
                    res.append([f"{BitsCompare['comp1'][0]}'s, {BitsCompare['comp1'][1]}: {BitsCompare['comp1'][2]} is equal to {BitsCompare['comp2'][0]}'s, {BitsCompare['comp2'][1]}: {BitsCompare['comp2'][2]}, Expected: Both should not be equal", "Fail"])


        return res

    # def Compare_Certificate_Data(self,Flow_limit,Check):
    #     res = []
    #     auth_limit = [0, len(self.Auth_file_list) - 1]
    #     authpkt1 = self.GetAuthPacketDetails(packet=Check['Packet'][0], value=Check['Packet'][1], limit=auth_limit, Type=Check['Packet'][2])
    #     if len(authpkt1) > 0:
    #         authpayload = self.GetAuthPayloadDetails(authpkt1[2], "Authentication_Protocol_Version", "B0", "[7:4")[0]['sDescription'].split(":")[-1].strip()





    #     return res
            
        

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
    def Frequency_Parameters(self, Flow_limit, Check):
        res = []
        measures = self.TestResults()
        if measures is not None:
            for chk in Check['expected']:
                finalval = self.Measurements(measures, chk['MeasurementName'])
                ChkRes1 = CommonMethods.check_measure(chk['expected_val'][0], round(finalval[0],7), chk['comp'])
                ChkRes2 = CommonMethods.check_measure(chk['expected_val'][1], finalval[1], "EQL")
                res.append(
                    [f"Measured {chk['MeasurementName']} is {format(ChkRes1[3],'f')} {ChkRes2[3]}, Expected: {ChkRes1[2]} {chk['expected_val'][1][0]} ", ChkRes1[1]])
                if ChkRes2[1] != "Pass":
                    res.append([f"Mismatch in Units: {ChkRes2[3]}, Expected: {ChkRes2[2]}", ChkRes2[1]])
        return res
    def Test_Results(self, Flow_limit, Check):
        res = []
        data = APIOperations(url=self.JapiData[self.Product][self.Mode]['GetWaveformTestResult'], retype='json').GetRequest()

        if data is not None:
            for level1 in data:
                if level1.get("children"):
                    for level2 in level1["children"]:
                        if level2.get("children"):
                            for level3 in level2["children"]:

                                if level3.get("displayString") and level3.get("result"):

                                    display = level3["displayString"]

                                    # Remove testcase numbering like:
                                    # 13.6.2
                                    # 13.6.2:
                                    # 13.6.2Verify
                                    display = re.sub(r'^\d+(\.\d+)*\s*:?\s*', '', display)

                                    res.append([display, level3["result"]])

                                if level3.get("children"):
                                    for level4 in level3["children"]:

                                        if level4.get("displayString") and level4.get("result"):

                                            if "\n" in level4["displayString"]:
                                                for line in level4["displayString"].split("\n"):
                                                    res.append([line, level4["result"]])

                                            else:
                                                res.append([level4["displayString"], level4["result"]])





        
        # if data is not None:
        #     for level1 in data:
        #         if level1.get("children"):
        #             for level2 in level1["children"]:
        #                 if level2.get("children"):
        #                     for level3 in level2["children"]:
        #                         if level3.get("displayString") and level3.get("result"):
        #                             display = level3["displayString"]
        #                             if ": " in display:
        #                                 display = display.split(": ", 1)[1]
        #                             res.append([display, level3["result"]])

        #                         if level3.get("children"):
        #                             for level4 in level3["children"]:
        #                                 if level4.get("displayString") and level4.get("result"):
        #                                     if "\n" in level4["displayString"]:
        #                                         for line in level4["displayString"].split("\n"):
        #                                             res.append([line, level4["result"]])
        #                                     else:
        #                                         res.append([level4["displayString"], level4["result"]])

        # if data is not None:
        #     for level1 in data:
        #         if level1.get("children"):
        #             for level2 in level1["children"]:
        #                 if level2.get("children"):
        #                     for level3 in level2["children"]:
        #                         if level3.get("displayString") and level3.get("result"):
        #                             res.append([f"{level3['displayString'].split(': ')[1]}", level3["result"]])
        #                         if level3.get("children"):
        #                             for level4 in level3["children"]:
        #                                 if level4.get("displayString") and level4.get("result"):
        #                                     if "\n" in level4["displayString"]:
        #                                         for line in level4["displayString"].split("\n"):
        #                                             res.append([line, level4["result"]])
        #                                     else:
        #                                         res.append([f"{level4['displayString']}", level4["result"]])


        return res
    def First_Ping(self, Flow_limit, Check):
        res = []
        if "PktLimit" in Check:
            tempUlmt = Flow_limit[1]
        else:
            tempUlmt = Flow_limit[0]
        cp = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station", limit=[0, tempUlmt], Type="TesterMsg")
        if len(cp) > 2:
            ua = self.PktMethod.GetPacketDetails(packet="User Action status", limit=[cp[2], tempUlmt], Type="TesterMsg")
            if len(ua) > 2:
                pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[ua[2], tempUlmt], Type="TesterMsg")
                if len(pd) > 2:
                    res.append([f"First ping found at {round(self.file_list[pd[2]]['startTime'], 3)}sec", "Pass"])
                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], tempUlmt], Type="TesterMsg")
                    if len(sd) > 2:
                        fop = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd[2], sd[2]], Type="TesterMsg")
                        if len(fop) > 2:
                            ChkRes = CommonMethods.check_measure([127.5, 128.5], float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]), 0)
                            res.append([f"{self.file_list[fop[2]]['value']} is observed at {round(fop[0], 3)} sec, Expected: {ChkRes[2]} kHz", ChkRes[1]])
                        id = pd[2]
                        while id < sd[2]:
                            if self.file_list[id]['isTesterPkt'] == True and self.file_list[id]['isFWTestermessage'] == False:
                                res.append([f"TPR responded with {self.file_list[id]['pktType']} at {round(self.file_list[id]['startTime'], 3)}sec", "Fail"])
                                break
                            id += 1
                        else:
                            res.append([f"TPR not responded to first digital ping 128 kHz from {round(pd[0], 3)} sec to {round(sd[0], 3)} sec", "Pass"])


                        # second ping
                        if "second_ping" in Check:
                            pd2 = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[sd[2], Flow_limit[1]], Type="TesterMsg")
                            if len(pd2) > 2:
                                res.append([f"Second ping found at {round(self.file_list[pd2[2]]['startTime'], 3)}sec", "Pass"])
                                sd2 = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd2[2], Flow_limit[1]+2], Type="TesterMsg")
                                if len(sd2) > 2:
                                    fop2 = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd2[2], sd2[2]], Type="TesterMsg")
                                    if len(fop2) > 2:
                                        ChkRes = CommonMethods.check_measure([127.5, 128.5], float(self.file_list[fop2[2]]['value'].split(":")[1].split(" ")[0]), 0)
                                        res.append([f"{self.file_list[fop2[2]]['value']} is observed at {round(fop2[0], 3)} sec, Expected: {ChkRes[2]} kHz", ChkRes[1]])
                                    id2 = pd2[2]
                                    while id2 < sd2[2]:
                                        if self.file_list[id2]['isTesterPkt'] == True and self.file_list[id2]['isFWTestermessage'] == False:
                                            res.append([f"TPR responded with {self.file_list[id2]['pktType']} at {round(self.file_list[id2]['startTime'], 3)}sec", "Pass"])

                                            if "ChecksList" in Check:
                                                data = self.PacketCheck_New(Flow_limit, Check)
                                                for ele in data:
                                                    res.append(ele)

                                            break
                                        id2 += 1
                                    else:
                                        res.append([f"TPR not responded to second digital ping 128 kHz from {round(pd2[0], 3)} sec to {round(sd2[0], 3)} sec", "Fail"])
                                else:
                                    res.append([f"Shutdown not found in the second ping", "Fail"])
                            else:
                                res.append([f"Second ping not found", "Fail"])



                    else:
                        res.append([f"Shutdown not found in the first ping", "Fail"])
                else:
                    res.append([f"First ping not found", "Fail"])
            else:
                res.append([f"User action not found", "Fail"])


        return res
    def Vrect_Irect(self, Flow_limit, Check):
        res = []
        self.AllChannelData3 = self.PlotMethod.GetAllChannelData('3', self.JapiData)
        id = Flow_limit[0]
        for prect in Check['expected']:
            if self.stability is not None:
                load = 0
                if prect.get("LoadPercent"):
                    if prect["LoadPercent"] != "NA":
                        negload_pkt = self.PktMethod.GetPacketDetails(
                            packet=self.ECAP_pkt, limit=Flow_limit, Type="Response")
                        if len(negload_pkt) > 2:
                            negload = float(self.PktMethod.GetPayloadDetails(negload_pkt[2], "Negotiable_Load_Power")[0]['sDescription'].split("Negotiable Load Power value:")[1].split("W")[0].strip())
                            res.append([f"Negotiable_Load_Power: {negload}W is observed in {self.ECAP_pkt} packet at index @{negload_pkt[2]}", "pass"])
                            load = int(prect["LoadPercent"] * 0.01 * negload * 1000)
                    else:
                        load = 600
                
                elif prect.get("ECAP"):
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
                
                else:
                    load = int(prect[prect['setting']]['set'])
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {load}", limit=[id, Flow_limit[1]], Type="TesterMsg")
                if len(TempPkt1) > 2:
                    self.GetInitailVoltage(2, start=TempPkt1[2])
                    if prect.get("LoadPercent"):
                        if prect["LoadPercent"] != "NA":
                            res.append([f"{prect['LoadPercent']}% of Negotiable load: {load} mW is applied in {self.file_list[TempPkt1[2]].get('pktType')} packet at index @{TempPkt1[2]}", "Pass"])
                        else:
                            res.append([f"Minimum load: {load} mW is applied in {self.file_list[TempPkt1[2]].get('pktType')} packet at index @{TempPkt1[2]}", "Pass"])
                    else:
                        res.append([f"{self.file_list[TempPkt1[2]].get('pktType')} packet is found at index @{TempPkt1[2]}", "pass"])
                    if self.XCEV_Ideal is not None:
                        res.append([f"Power transfer stabilized at {self.PktMethod.Timeconvert(self.file_list[self.XCEV_Ideal]['startTime'])}", "Pass"])
                    else:
                        res.append([f"Power transfer not stabilized", "Fail"])


                    if not prect.get("LoadPercent"):
                        irect = self.PktMethod.CalculateVoltTwindow(self.stability, self.AllChannelData3)
                        vrect = self.PktMethod.CalculateVoltTwindow(self.stability, self.AllChannelData)
                        power = round(vrect[0] * irect[0], 3)
                        if prect.get("ECAP"):
                            ChkRes5 = CommonMethods.check_measure(prect['exp'] if prect.get("exp") else [(load-100)/1000],power,"GTEQL")
                            res.append([f"Measured Prect is {power} W, Vrect is: {vrect[0]} V, Irect: {irect[0]} A, Limit: Prect: {ChkRes5[2]} W,", ChkRes5[1]])
                        else:
                            if prect.get('irect'):
                                # if prect['irect'].get('comp'):
                                if 'comp' in prect['irect']:
                                    if prect['irect']['comp'] != 'NA':
                                        ChkRes1 = CommonMethods.check_measure(prect['irect']['exp'], irect[0], prect['irect']['comp'])
                                    else:
                                        ChkRes1 = ['NA', 'Pass', 'NA', irect[0]]
                                    res.append([f"Measured Irect is {ChkRes1[3]} A at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}{f", Expectd: {ChkRes1[2]} A" if ChkRes1[2] != "NA" else ""}", ChkRes1[1]])
                                else: res.append([f"Measured Irect is {irect[0]} A at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}", "Pass"])
                            else:
                                res.append([f"Measured Irect is {irect[0]} A at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}", "Pass"])
                            
                            if prect.get('vrect'):
                                if 'comp' in prect['vrect']:
                                    if prect['vrect']['comp'] != 'NA':
                                        ChkRes2 = CommonMethods.check_measure(prect['vrect']['exp'], vrect[0], prect['vrect']['comp'])
                                    else:
                                        ChkRes2 = ['NA', 'Pass', 'NA', vrect[0]]
                                    res.append([f"Measured Vrect is {ChkRes2[3]} V at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}{f", Expectd: {ChkRes2[2]} V" if ChkRes2[2] != "NA" else ""}", ChkRes2[1]])
                                else: res.append([f"Measured Vrect is {vrect[0]} A at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}", "Pass"])
                            else:
                                res.append([f"Measured Vrect is {vrect[0]} A at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}", "Pass"])
                            
                            if prect.get('Prect'):
                                if 'comp' in prect['Prect']:
                                    if prect['Prect']['comp'] != 'NA':
                                        ChkRes3 = CommonMethods.check_measure(prect['Prect']['exp'], power, prect['Prect']['comp'])
                                    else:
                                        ChkRes3 = ['NA', 'Pass', 'NA', power]
                                    res.append([f"Measured Prect is {power} W at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}{f", Expectd: {ChkRes3[2]} W" if ChkRes3[2] != "NA" else ""}", ChkRes3[1]])
                                else:
                                    res.append([f"Measured Prect is {power} W at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}", "Pass"])
                            else:
                                res.append([f"Measured Prect is {power} W at {self.PktMethod.Timeconvert(self.file_list[self.stability]['startTime'])}", "Pass"])
                    else:
                        irect = self.PktMethod.CalculateVoltTwindow(self.stability, self.AllChannelData3)[0]
                        vrect = self.PktMethod.CalculateVoltTwindow(self.stability, self.AllChannelData)[0]
                        power = round(vrect * irect, 3)
                        ChkRes4 = CommonMethods.check_measure([(load - 100) / 1000], power, "GTEQL")
                        res.append([f"Measured Prect is {power} W, Limit: {ChkRes4[2]} W, Vrect is: {vrect} V, Irect: {irect} A", ChkRes4[1]])

                    id = self.stability
                    if prect.get('Monitor'):
                        self.Monitor_load([id,Flow_limit[1]],prect['Monitor'])

                else:
                    if prect.get("LoadPercent") and prect["LoadPercent"] != "NA":
                        res.append([f"{prect['LoadPercent']}% of Negotiable load is not applied", "Fail"])
                    else:
                        res.append([f"Set_Load {load}mW packet not found", "Inconclusive"])


        return res

    def Monitor_load(self,limit,Monitor_check):
        res = []
        id = limit[0]
        t0 = self.file_list[id]['startTime']
        end_pkt = self.PktMethod.GetPacketDetails(packet=Monitor_check['until'], limit=[id, limit[1]], Type="TesterMsg")
        if len(end_pkt)>2:
            t_end = end_pkt[0]
            
            while id < end_pkt[2]:
                XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error", limit=[id, end_pkt[2]], Type="Packet")
                if len(XCE) > 2:
                    irect = self.PktMethod.CalculateVoltTwindow(XCE[2], self.AllChannelData3)[0]
                    vrect = self.PktMethod.CalculateVoltTwindow(XCE[2], self.AllChannelData)[0]
                    power = round(vrect[0] * irect[0], 3)

                    ChkRes = CommonMethods.check_measure(Monitor_check['comp'][0], power, Monitor_check['comp'][1])
                    if "Pass" in ChkRes[1]:
                        pass
                    elif "Fail" in ChkRes[1]:
                        break
                        pass

                    id = XCE[2]

                id += 1
            else:
                if (t_end - t0) > Monitor_check['time']:
                    res.append([f""])
                else:
                    res.append([f""])
        return res






    
    def t_cloak(self, Flow_limit, Check):
        res = []
        SRQ1 = self.PktMethod.GetPacketDetails(packet="SRQ", value="Cloak Ping Delay Low", limit=Flow_limit, Type="Packet")
        if len(SRQ1) > 2:
            t1 = float(self.PktMethod.GetPayloadDetails(SRQ1[2], 'Cloak_Ping_Delay_Value_Low')[0]["sRawData"].split("x")[-1])
            SRQ2 = self.PktMethod.GetPacketDetails(packet="SRQ", value="Cloak Ping Delay High", limit=Flow_limit, Type="Packet")
            if len(SRQ2) > 2:
                t2 = float(self.PktMethod.GetPayloadDetails(SRQ2[2], 'Cloak_Ping_Delay_Value_High')[0]["sRawData"].split("x")[-1])
                ChkRes = CommonMethods.check_measure([Check['expected'][0]], t1 + t2, Check['expected'][1])
                res.append(
                    [f"Measured Negotiate t_cloak: {ChkRes[3]} Sec at index@{SRQ1[2]} and index@{SRQ2[2]}, Expected: {ChkRes[2]} Sec", ChkRes[1]])
            else:
                res.append([f"SRQ Cloak_Ping_Delay_Value_High packet not observed", "Fail"])
        else:
            res.append([f"SRQ Cloak_Ping_Delay_Value_Low packet not observed", "Fail"])
        return res

    def Set_Load(self, Flow_limit, Check):
        res = []
        id = 0
        if "PktLimit" in Check:
            limit2 = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
            end = limit2[1]
        else: end = len(self.file_list)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3', self.JapiData)
        cnt = 0
        while id < end:
            if not Check.get("Nopings"):
                TempPkt1 = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[id, end], Type="TesterMsg")
                if len(TempPkt1) > 2:
                    setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Set_load']}mA", limit=[TempPkt1[2], id], Type="TesterMsg")
                    if len(setload) > 2:
                        res.append([f"Set_Load: {Check['Set_load']} mA found at index@{setload[2]}, Expected: {Check['Set_load']} mA", "Pass"])
                        sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[TempPkt1[2] + 1, end], Type="TesterMsg")
                        ts = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Test_Stop", limit=[TempPkt1[2] + 1, end], Type="TesterMsg")
                        if len(sd) > 2 or len(ts) > 2:
                            # sindex2 = int(((TempPkt1[1] * 1000)) / AllChannelData3['Interval'])
                            sindex2 = int(((self.file_list[TempPkt1[2]+1]["stopTime"]) * 1000) / AllChannelData3['Interval'])
                            eindex2 = int(((sd[0] if len(sd) > 2 else ts[0]) * 1000) / AllChannelData3['Interval'])
                            cnt += 1
                            x = sindex2
                            while x <= eindex2:
                                # if (Check['Set_load'] + 1) >= AllChannelData3['RV']['displayDataChunk'][x] * 1000 >= (Check['Set_load'] - 0.2):
                                value = AllChannelData3['RV']['displayDataChunk'][x] * 1000 
                                if (Check['Set_load'] - 0.2) <= value <= (Check['Set_load'] + 2):
                                    res.append([f"In ping_{cnt}, Irect: {round(value, 2)} mA found", "Pass"])
                                    break
                                if value > (Check['Set_load'] + 2):
                                    res.append([f"In ping_{cnt}, Irect: {round(value, 2)} mA found, Expected: {Check['Set_load']} mA", "Fail"])
                                    break
                                x += 1
                            else:
                                print(f"Not reached to {Check['Set_load']}mA in {cnt}th ping from {TempPkt1[2]} to {sd[2] if len(sd) > 2 else ts[2]}")
                                res.append([f"In {cnt}th ping, Irect is not reached to {Check['Set_load']} mA", "Fail"])
                            id = sd[2] if len(sd) > 2 else ts[2]
            else:
                setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Set_load']}mA", limit=[id, end], Type="TesterMsg")
                if len(setload) > 2:
                    res.append([f"Set_Load: {Check['Set_load']} mA found at index@{setload[2]}, Expected: {Check['Set_load']} mA", "Pass"])
                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[setload[2] + 1, end], Type="TesterMsg")
                    ts = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Test_Stop", limit=[setload[2] + 1, end], Type="TesterMsg")
                    if len(sd) > 2 or len(ts) > 2:
                        sindex2 = int(((setload[1] * 1000)) / AllChannelData3['Interval'])
                        eindex2 = int(((sd[0] if len(sd) > 2 else ts[0]) * 1000) / AllChannelData3['Interval'])
                        cnt += 1
                        x = sindex2
                        while x <= eindex2:
                            if (Check['Set_load'] + 0.2) >= AllChannelData3['RV']['displayDataChunk'][x] * 1000 >= (Check['Set_load'] - 0.2):
                                res.append([f"Irect: {round(AllChannelData3['RV']['displayDataChunk'][x] * 1000, 2)} mA is found, Expected: {Check['Set_load']} mA", "Pass"])
                                break
                            x += 1
                        else:
                            res.append([f"In {cnt}th cloak ping, Irect is not reached to {Check['Set_load']} mA", "Fail"])
                        id = sd[2] if len(sd) > 2 else ts[2]
                else:
                    res.append([f"Set_Load: {Check['Set_load']} mA not found", "Fail"])
            id += 1
        return res

    def Set_Load_128kHz(self, Flow_limit, Check):
        res = []
        CP = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station", limit=[len(self.file_list) - 1, 0], Type="TesterMsg")
        print("CP:", CP)
        if len(CP) > 2:
            cnt = 1
            id = CP[2]
            end = len(self.file_list) - 1
            vrects = []
            AllChannelData3 = self.PlotMethod.GetAllChannelData2('3', self.JapiData)
            while id <= end:
                pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[id, end], Type="TesterMsg")
                print("pd",pd)
                if len(pd) > 2:
                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], end+1], Type="TesterMsg")
                    ts = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Test_Stop", limit=[pd[2], end+1], Type="TesterMsg")
                    if len(sd) > 2 or len(ts) > 2:
                        fop_pkt = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[pd[2], sd[2] if len(sd) > 2 else ts[2]], Type="TesterMsg")
                        print("fop_pkt",fop_pkt)
                        if len(fop_pkt) > 2:
                            fop = float(self.file_list[fop_pkt[2]]['value'].split(":")[1].split(" ")[0])
                            if 127.5 < fop < 128.5:
                                # res.append([f"FOP: {fop} kHz found at {round(fop_pkt[0],3)} sec, Expected: 127.5 kHz < fop <128.5 kHz", "Pass"])
                                ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[fop_pkt[2], end], Type="Packet")
                                print("ss",ss)
                                if len(ss) > 2:
                                    id = ss[2]
                                    id_pkt = self.PktMethod.GetPacketDetails(packet="Identification", limit=[ss[2], end], Type="Packet")
                                    if len(id_pkt) > 2:
                                        id = id_pkt[2]
                                        xid = self.PktMethod.GetPacketDetails(packet=self.XID_pkt, limit=[id_pkt[2], end], Type="Packet")
                                        if len(xid) > 2:
                                            id = xid[2]
 
                                            sindex2 = int(((self.file_list[ss[2]]["startTime"]) * 1000) / AllChannelData3['Interval'])
                                            eindex2 = int(((self.file_list[sd[2] if len(sd) > 2 else ts[2]]["startTime"]) * 1000) / AllChannelData3['Interval'])
                                            x = sindex2
                                            while x <= eindex2:
                                                value = AllChannelData3['RV']['displayDataChunk'][x] * 1000 
                                                # print("value:",value)
                                                if (Check['Set_load'] - 1.3) <= value <= (Check['Set_load'] + 2):
                                                    res.append([f"In ping_{cnt}, Irect: {round(value, 2)} mA found, Expected: {Check['Set_load']} mA", "Pass"])
                                                    break
                                                if value > (Check['Set_load'] + 2):
                                                    res.append([f"In ping_{cnt}, Irect: {round(value, 2)} mA found, Expected: {Check['Set_load']} mA", "Fail"])
                                                    break
                                                x += 1
                                            else:
                                                print(f"Not reached to {Check['Set_load']}mA in {cnt}th ping from {ss[2]} to {sd[2] if len(sd) > 2 else ts[2]}")
                                                res.append([f"In {cnt}th ping, Irect is not reached to {Check['Set_load']} mA", "Fail"])
                                            cnt += 1
                                            id = xid[2]
                                        
                            # else: res.append([f"FOP: {fop} kHz found at {round(fop_pkt[0],3)} sec, Expected: 127.5 kHz < fop <128.5 kHz", "Fail"])
                id += 1               
        return res


    def Set_Load_New(self, Flow_limit, Check):
        res = []
        if Check['flow'] == 1:
            id = 0
        else: id = self.flows[1]['Limit'][1]
        if "PktLimit" in Check:
            limit2 = self.PktMethod.GetLimits(Check['PktLimit'],Check,Flow_limit)
            end = limit2[1]
        else: end = len(self.file_list)-1
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3', self.JapiData)
        cnt = 0
        print("id:",id,"end:",end)
        while id < end:
            TempPkt1 = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[id, end], Type="TesterMsg")
            if len(TempPkt1) > 2:
                setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Set_load']}mA", limit=[TempPkt1[2], id], Type="TesterMsg")
                if len(setload) > 2:
                    res.append([f"Set_Load: {Check['Set_load']} mA found at index@{setload[2]}, Expected: {Check['Set_load']} mA", "Pass"])
                    sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[TempPkt1[2] + 1, end+1], Type="TesterMsg")
                    ts = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Test_Stop", limit=[TempPkt1[2] + 1, end+1], Type="TesterMsg")
                    print("sd:",sd)
                    print("ts:",ts)
                    if len(sd) > 2 or len(ts) > 2:
                        # sindex2 = int(((TempPkt1[1] * 1000)) / AllChannelData3['Interval'])
                        sindex2 = int(((self.file_list[TempPkt1[2]+1]["stopTime"]) * 1000) / AllChannelData3['Interval'])
                        eindex2 = int(((sd[0] if len(sd) > 2 else ts[0]) * 1000) / AllChannelData3['Interval'])
                        cnt += 1
                        x = sindex2
                        while x <= eindex2:
                            value = AllChannelData3['RV']['displayDataChunk'][x] * 1000 
                            # print("value:",value)
                            if (Check['Set_load'] - 1.3) <= value <= (Check['Set_load'] + 2):
                                res.append([f"In ping_{cnt}, Irect: {round(value, 2)} mA found", "Pass"])
                                break
                            if value > (Check['Set_load'] + 2):
                                res.append([f"In ping_{cnt}, Irect: {round(value, 2)} mA found, Expected: {Check['Set_load']} mA", "Fail"])
                                break
                            x += 1
                        else:
                            print(f"Not reached to {Check['Set_load']}mA in {cnt}th ping from {TempPkt1[2]} to {sd[2] if len(sd) > 2 else ts[2]}")
                            res.append([f"In {cnt}th ping, Irect is not reached to {Check['Set_load']} mA", "Fail"])
                        id = sd[2] if len(sd) > 2 else ts[2]

            id += 1



            
        return res

    
   
                
    


    def Cloak(self, Flow_limit, Check):
        res = []
        end = len(self.file_list)
        ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=Flow_limit, Type="Packet")
        if len(ss) > 2:
            if "DPL" in Check["expected"][0]["chks"]:
                dpl = round(self.PktMethod.CalculateVoltTwindow(ss[2], self.AllChannelData, winsize=[9, 11])[0], 3)
                dpl_lmt = [round((dpl - (dpl / 20)), 3), round((dpl + (dpl / 20)), 3)]
                res.append([f"Measured DPL voltage is: {dpl} V", "Pass"])
            clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak", limit=[ss[2], Flow_limit[1]], Type="Packet")
            if len(clk_ping) > 2:
                initial_cloak = clk_ping[2]
                reason = self.PktMethod.GetPayloadDetails(clk_ping[2], 'Reason')[0]["sDescription"].split(":")[-1]
                rsn_chk = CommonMethods.check_measure(Check["expected"][0]["clk_reason"], reason, "EQL")
                clk_resp = self.file_list[clk_ping[2] + 1].get('pktType')
                res.append([f"Cloak enter found with reason:{reason} at {round(clk_ping[0], 3)} sec and received {self.file_list[clk_ping[2] + 1].get('pktType')}", rsn_chk[1]])
                id = clk_start = clk_ping[2] + 1
                cnt = 1
                pings = 0
                while id < end:
                    if "Timing" in Check["expected"][0]["chks"]:
                        sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[clk_ping[2], end], Type="TesterMsg")
                        if len(sd) > 2:
                            Tterm = round((sd[0] - self.file_list[clk_ping[2] + 1].get('stopTime')) * 1000, 3)
                            ChkRes1 = CommonMethods.check_measure([28], Tterm, "LTEQL")
                            res.append([f"Measured Tterminate_{cnt} is {ChkRes1[3]} ms from the end of index@{clk_ping[2] + 1} to the start of index@{sd[2]}, Limit: [{ChkRes1[2]}] ms", ChkRes1[1]])
                        pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[sd[2], end], Type="TesterMsg")
                        if len(pd) > 2:
                            Tcloak = round((self.file_list[pd[2]].get('startTime') - self.file_list[clk_ping[2] + 1].get('stopTime')) * 1000, 3)
                            ChkRes2 = CommonMethods.check_measure([475, 525], Tcloak, "GTEQL")
                            res.append([f"Measured Tcloak_{cnt} is {ChkRes2[3]} ms from the end of index@{clk_ping[2] + 1} to the start of index@{pd[2]}, Limit: [{ChkRes2[2]}] ms", ChkRes2[1]])

                    if "pings" in Check["expected"][0]:
                        if len(clk_ping)>2:
                            sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[clk_ping[2], end], Type="TesterMsg")
                            if len(sd) > 2:
                                pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[sd[2], end], Type="TesterMsg")
                                if len(pd) > 2:
                                    pings += 1
                    
                    clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak", limit=[id, end], Type="Packet")
                    print("clk_ping",clk_ping)
                    if len(clk_ping) > 2:
                        reason = self.GetPayloadDetails(clk_ping[2], 'Reason')[0]["sDescription"].split(":")[-1]
                        rsn_chk = CommonMethods.check_measure(Check["expected"][0]["clk_reason"], reason, "EQL")

                        respid = self.PktMethod.GetPacketResponse2(clk_ping[2], [clk_ping[2]+1, end])
                        print("respid",respid)
                        if respid is not None:

                            clk_resp = self.file_list[respid]['pktType']
                            if "ACK" in clk_resp:
                                res.append([f"Cloak Ping {cnt} found with reason:{reason} at {round(clk_ping[0], 3)} sec and received {clk_resp}", rsn_chk[1]])
                                cpl = round(self.PktMethod.CalculateVoltTwindow(clk_ping[2], self.AllChannelData, winsize=[9, 11])[0], 3)
                                if "Timing" in Check["expected"][0]["chks"]:
                                    ChkRes3 = CommonMethods.check_measure(dpl_lmt, cpl, 0)
                                    res.append([f"Measured CPL voltage in Cloak sequence {cnt} is: {ChkRes3[3]} V, Limit: [{ChkRes3[2]}] V (DPL ± 5%)", ChkRes3[1]])
                                if cnt == 5:
                                    break
                                
                                # id = clk_ping[2]
                                # cnt += 1
                            elif "ATN" in clk_resp:
                                res.append([f"Cloak Ping {cnt} found with reason:{reason} at {round(clk_ping[0], 3)} sec and received {clk_resp}", rsn_chk[1]])
                                res.append([f"PTx initiated cloak exit by sending ATN response to cloak ping {cnt}", "Pass"])
                            id = clk_ping[2]
                            cnt += 1

                    id += 1
                clk_exit = self.PktMethod.GetPacketDetails(packet="MPP_Cloak_Exit", limit=[clk_start, end], Type="TesterMsg")
                if len(clk_exit) > 2:
                    exitid = clk_exit[2]
                else:
                    exitid = id
                while clk_start < exitid:
                    if "Packet" in self.PktMethod.GetPacketType(clk_start):
                        Cloakdict = {"Report": "", "Get Request": "PTx Extended Identification", "Cloak": ""}
                        if any(k in self.file_list[clk_start]['pktType'] and v in self.file_list[clk_start]['value'] for k, v in Cloakdict.items()):
                            if "Cloak" not in self.file_list[clk_start]['pktType']:
                                respid2 = self.PktMethod.GetPacketResponse2(clk_start, [clk_start+1, exitid])
                                print("respid2",respid2)
                                if respid2 is not None:
                                    res.append([f"{self.file_list[clk_start]['pktType']} {self.file_list[clk_start]['value']} packet and {self.file_list[respid2]['pktType']} response found", "Pass"])
                        else:
                            if Check["expected"][0].get("illegal_chk"):
                                ill_chk = CommonMethods.check_measure(Check["expected"][0]["illegal_chk"], self.file_list[clk_start]['pktType'], "EQL")
                                res.append([f"Illegal packet {ill_chk[3]} found at {round(self.file_list[clk_start]['startTime'], 3)} sec", ill_chk[1]])
                            else:
                                res.append([f"Illegal packet found at {round(self.file_list[clk_start]['startTime'], 3)} sec", "Fail"])
                            sd = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[clk_start, end], Type="TesterMsg")
                            if len(sd) > 2:
                                Tterm = round((sd[0] - self.file_list[clk_start].get('stopTime')) * 1000, 3)
                                ChkRes1 = CommonMethods.check_measure([28], Tterm, "LTEQL")
                                res.append([f"Measured Tterminate at {round(self.file_list[clk_start].get('stopTime'), 3)} Sec is: {ChkRes1[3]} ms, Limit: [{ChkRes1[2]}] ms", ChkRes1[1]])
                    clk_start += 1

                if "Diable_ASK" in Check["expected"][0]["chks"]:
                    id = initial_cloak+1
                    while id <= Flow_limit[1]:
                        if self.PktMethod.GetPacketType(id)=="Packet":
                            #calculate interval
                            # results = CommonMethods.check_measure(Check['expected_value'],round((self.file_list[Flow_limit[1]]['stopTime']-self.file_list[id]['startTime'])*1000,3),Check['comp'])
                            # res.append([f"Measured last ASK to shutdown interval is {results[3]}ms, expected value:{results[2]}ms",results[1]])     
                            # break
                            if (clk_ping[0] - self.file_list[id]['startTime']) < 1:
                                res.append([f"Once in the Cloak state, within 1 second TPR sent {self.file_list[id]['pktType']} ASK packet at {round(self.file_list[id]['startTime'], 3)} sec","Fail"])
                                break
                            # else:
                            #     res.append([f"Once in the Cloak state, TPR sent {self.file_list[id]['pktType']} ASK packet at {round(self.file_list[id]['startTime'], 3)} sec","Pass"])
                            #     break
                        id += 1
                    else: 
                        res.append([f"Once in the Cloak state, TPR did not sent ASK packet for 1 sec","Pass"])

                if "ENTER" not in self.Header['TestcaseID']:
                    if len(clk_exit) > 2:
                        res.append([f"Cloak exit found at {round(clk_exit[0], 3)} sec", "Pass"])
                    else:
                        res.append([f"Cloak exit was not found", "Fail"])
                if "pings" in Check["expected"][0]:
                    pings_chk_resp = CommonMethods.check_measure([Check["expected"][0]['pings'][0]], pings, Check["expected"][0]['pings'][1])
                    res.append([f"System stayed for {pings} Cloak Pings, tcloak, cycle, Expected: {pings_chk_resp[2]}", pings_chk_resp[1]])

                if "2ndseq" in Check["expected"][0]["chks"]:
                    fop = self.PktMethod.GetPacketDetails(packet="", value="FOP:", limit=[exitid, end], Type="TesterMsg")
                    if len(fop) > 2:
                        ChkRes = CommonMethods.check_measure([127.5, 128.5], float(self.file_list[fop[2]]['value'].split(":")[1].split(" ")[0]), 0)
                        res.append([f"{self.file_list[fop[2]]['value']} is observed at {round(fop[0], 3)} sec, Expected: {ChkRes[2]} kHz", ChkRes[1]])
                        ss2 = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[exitid, end], Type="Packet")
                        if len(ss2) > 2:
                            res.append([f"Ping phase is observed at {round(ss2[0], 3)} sec", "Pass"])
                        else:
                            res.append([f"Ping phase is not observed", "Fail"])
                    else:
                        res.append([f"FOP is not observed", "Fail"])
                if "PT" in Check["expected"][0]["chks"]:
                    CE = self.PktMethod.GetPacketDetails(packet="Extended Control Error", limit=[exitid, end], Type="Packet")
                    if len(CE) > 2:
                        res.append([f"Entered to PT Phase at {round(self.file_list[CE[2]]['startTime'], 3)} sec after cloak exit", "Pass"])

                        if "t_atn" in Check["expected"][0]["chks"]:
                            eptid = self.PktMethod.GetPacketDetails(packet="Extended Power Transmitter Identification", limit=[exitid, initial_cloak], Type="Response")
                            if len(eptid)>2:
                                dsr = self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[exitid, end], Type="Packet")
                                if len(dsr) > 2:
                                    res.append([f"DSR/POLL packet found at {round(dsr[0], 3)} sec in PT Phase", "Pass"])
                                    t_atn = round((dsr[0] - eptid[1]) * 1000, 3)
                                    res.append([f"Measured t_atn is {t_atn} ms from Extended Power Transmitter Identification to DSR/POLL packet", "Pass"])
                                else:
                                    res.append([f"DSR/POLL packet not found in PT Phase", "Fail"])
                            else:
                                res.append([f"Extended Power Transmitter Identification packet not found", "Fail"])

                        res.append([f"TPR sent Extended Control Error at {round(CE[0], 3)} sec", "Pass"])
                        SD = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[CE[2], end], Type="TesterMsg")
                        if len(SD) < 2:
                            res.append([f"PTx kept Power signal ON", "Pass"])
                        else:
                            res.append([f"PTx removed Power signal", "Fail"])
                    else:
                        res.append([f"PT Phase not found after cloak exit", "Fail"])
        else:
            res.append([f"Signal strength packet not found", "Fail"])


        return res
    def MPP_FSK_Pattern(self, Flow_limit, Check):
        res = []
        MPP_status = None
        id = Flow_limit[0]
        while id < Flow_limit[1]:
            pkt = self.PktMethod.GetPacketDetails(packet=Check['expected'][0]['refpkt'][0], limit=Flow_limit, Type=Check['expected'][0]['refpkt'][1])
            if len(pkt) > 2:
                pktrespid = self.PktMethod.GetPacketResponse2(pkt[2], [pkt[2] + 1, Flow_limit[1]])
                if pktrespid is not None:
                    if Check['expected'][0]['MPP_Pattern']:
                        if "MPP" not in self.file_list[pktrespid]['pktType']:
                            MPP_status = False
                            res.append([f"{self.file_list[pktrespid]['pktType']} pattern observed at {round(self.file_list[pktrespid]['startTime'], 3)} sec CE Packet, Expected: MPP pattern", "Fail"])
                            break
                        else: 
                            MPP_status = True
                    elif not Check['expected'][0]['MPP_Pattern']:
                        if "MPP" in self.file_list[pktrespid]['pktType']:
                            MPP_status = True
                            res.append([f"MPP FSK Pattern observed at {round(self.file_list[pktrespid]['startTime'], 3)} sec after CE Packet, Expected: No MPP pattern", "Fail"])
                            break
                        else:
                            MPP_status = False
                else:
                    if not Check['expected'][0]['MPP_Pattern']:
                        MPP_status = False
            id += 1

        if Check['expected'][0]['MPP_Pattern']:
            if MPP_status is not None:
                if MPP_status:
                    res.append([f"PTx sent MPP pattern after CE Packets", "Pass"])
                # else:
                #     res.append([f"PTx not sent MPP pattern after CE Packets", "Fail"])

        elif not Check['expected'][0]['MPP_Pattern']:
            if MPP_status is not None:
                if not MPP_status:
                    res.append([f"PTx not sent MPP pattern after CE Packets", "Pass"])



        return res
    def CloakDetect(self, Flow_limit, Check):
        res = []
        end = len(self.file_list)
        ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=Flow_limit, Type="Packet")
        if len(ss) > 2:
            dlypkt = self.PktMethod.GetPacketDetails(packet="SRQ ", value="Cloak Ping Delay Low", limit=Flow_limit, Type="Packet")
            if len(dlypkt) > 2:
                cdelay = (GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(dlypkt[2], 'Cloak_Ping_Delay_Value_Low')[0]['sDescription'])[0]) * 1000
                res.append([f"SRQ/Cloak packet with {cdelay} ms delay configuration was found at {round(dlypkt[0], 3)} sec", "Pass"])
            else:
                res.append([f"SRQ/Cloak packet was not found", "Fail"])
            dtctpkt = self.PktMethod.GetPacketDetails(packet="SRQ ", value="Cloak Detect Ping Interval", limit=Flow_limit, Type="Packet")
            if len(dtctpkt) > 2:
                cdetect = (GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(dtctpkt[2], 'Cloak_Detect_Ping_Value')[0]['sDescription'])[0]) * 1000
                res.append([f"SRQ/detect packet with {cdetect} ms delay value was found at {round(dtctpkt[0], 3)} sec", "Pass"])
            else:
                res.append([f"SRQ/detect packet was not found", "Fail"])
            clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak", limit=[ss[2], Flow_limit[1]], Type="Packet")
            if len(clk_ping) > 2:
                reason = self.GetPayloadDetails(clk_ping[2], 'Reason')[0]["sDescription"].split(":")[-1]
                rsn_chk = CommonMethods.check_measure(Check["expected"][0]["clk_reason"], reason, "EQL")
                clk_resp = self.file_list[clk_ping[2] + 1].get('pktType')
                clk_resp_stop = self.file_list[clk_ping[2] + 1].get('stopTime')
                res.append([f"Cloak enter found with reason:{reason} at {round(clk_ping[0], 3)} sec and received {self.file_list[clk_ping[2] + 1].get('pktType')}", rsn_chk[1]])
                id = clk_ping[2] + 1
                clk_start = clk_ping[2] + 1
                cnt = 1
                pings = 0
                while id < end:
                    pd = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[clk_ping[2], end], Type="TesterMsg")
                    if len(pd) > 2:
                        sd1 = self.PktMethod.GetPacketDetails(packet="Shutdown", limit=[pd[2], end], Type="TesterMsg")
                        if len(sd1) > 2:
                            Tdactive = round((sd1[0] - pd[1]) * 1000, 3)
                            ChkRes = CommonMethods.check_measure([2, 5], Tdactive, 0)
                            res.append([f"Measured Tdactive {cnt} is: {ChkRes[3]} ms, at {round(pd[0], 3)} sec, Limit: [{ChkRes[2]}] ms", ChkRes[1]])
                        pd1 = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[pd[2] + 1, end], Type="TesterMsg")
                        if len(pd1) > 2:
                            Tcloakdetect = round((pd1[0] - pd[1]) * 1000, 3)
                            ChkRes2 = CommonMethods.check_measure([190, 210], Tcloakdetect, 0)
                            res.append([f"Measured Tcloakdetect {cnt} is: {ChkRes2[3]} ms, at {round(pd[0], 3)} sec, Limit: [{ChkRes2[2]}] ms", ChkRes2[1]])
                    clk_ping = self.PktMethod.GetPacketDetails(packet="Cloak", limit=[id, end], Type="Packet")
                    if len(clk_ping) > 2:
                        pd2 = self.PktMethod.GetPacketDetails(packet="Ping Detected", limit=[clk_ping[2], clk_start], Type="TesterMsg")
                        if len(pd2) > 2:
                            pings += 1
                            Tcloak = round((pd2[0] - clk_resp_stop) * 1000, 3)
                            ChkRes3 = CommonMethods.check_measure([8265, 9135], Tcloak, 0)
                            res.append([f"Measured Tcloak {cnt} is: {ChkRes3[3]} ms, at {round(clk_resp_stop, 3)} sec, Limit: [{ChkRes3[2]}] ms", ChkRes3[1]])
                        reason = self.GetPayloadDetails(clk_ping[2], 'Reason')[0]["sDescription"].split(":")[-1]
                        rsn_chk = CommonMethods.check_measure(Check["expected"][0]["clk_reason"], reason, "EQL")
                        clk_resp = self.file_list[clk_ping[2] + 1].get('pktType')
                        clk_resp_stop = self.file_list[clk_ping[2] + 1].get('stopTime')
                        if "ACK" in clk_resp:
                            res.append([f"Cloak Ping {cnt} found with reason:{reason} at {round(clk_ping[0], 3)} sec and received {self.file_list[clk_ping[2] + 1].get('pktType')}", rsn_chk[1]])
                            if cnt == 5:
                                break
                            id = clk_ping[2]
                            cnt += 1
                    id += 1

                pings_chk_resp = CommonMethods.check_measure([5], pings, "EQL")
                res.append([f"System stayed in Cloak Phase for {pings} Cloak Ping cycles (tcloak), Expected: {pings_chk_resp[2]}", pings_chk_resp[1]])


        return res

    def Detach_Reattach(self,Flow_limit,Check):
        res=[]
        end = len(self.file_list)-1
        clk = self.PktMethod.GetPacketDetails(packet="Cloak", limit=Flow_limit, Type="Packet")
        if len(clk) > 2:
            coil_remove = self.PktMethod.GetPacketDetails(packet="Coil_Remove_From_Base_Station", limit=[clk[2],end], Type="TesterMsg")
            if len(coil_remove)>2:
                UA1 = self.PktMethod.GetPacketDetails(packet="User Action status", limit=[coil_remove[2],end], Type="TesterMsg")
                if len(UA1)>2:
                    t1 = round(UA1[0]-clk[0],3)
                    res.append([f"Detach happened in {t1} sec from the start of cloak, Expected: 5 to 10 sec", "Pass" if 5<=t1<=10 else "Fail"])

                    coil_place = self.PktMethod.GetPacketDetails(packet="Coil_Place_On_Base_Station", limit=[UA1[2],end], Type="TesterMsg")
                    if len(coil_place)>2:
                        UA2 = self.PktMethod.GetPacketDetails(packet="User Action status", limit=[coil_place[2],end], Type="TesterMsg")
                        if len(UA2)>2:
                            t2 = round(UA2[0]-UA1[0],3)
                            res.append([f"Reattach happened in {t2} sec from detach, Expected: 5 to 10 sec", "Pass" if 5<=t2<=10 else "Fail"])
                        else: res.append([f"User action not found to reattach", 'Fail'])
                    else: res.append([f"Coil_Place_On_Base_Station not found to reattach", 'Fail'])
                else: res.append([f"User action not found to detach", 'Fail'])
            else: res.append([f"Coil_Remove_From_Base_Station not found to detach", 'Fail'])
        else: res.append([f"System didn't went to cloak", 'Fail'])

            
        

        return res
    def Random_load(self, Flow_limit, Check):
        res = []
        if self.stability is not None:
            id = Flow_limit[0]
            voltages = []
            nak_flag = False
            finalload = None
            while id < Flow_limit[1]:
                if "Set_Load" in self.file_list[id].get('pktType'):
                    res.append([f"{self.file_list[id].get('pktType')} packet found at index @{id}", "Pass"])
                    id2 = id + 1
                    while id2 < Flow_limit[1]:
                        if any(rs in self.file_list[id2].get('pktType') for rs in ['Extended Control Error', 'Power Loss Accounting']):
                            if "NAK" in self.file_list[id2 + 1].get('pktType'):
                                res.append(
                                    [f"NAK response observed for {self.file_list[id2].get('pktType')} at index@{id2}", "Pass"])
                                nak_flag = True
                        if "Set_Load 80mA" in self.file_list[id2].get('pktType'):
                            id = id2 - 1
                            finalload = id2
                            break
                        elif "Set_Load" in self.file_list[id2].get('pktType'):
                            id = id2 - 1
                            break
                        if "MPP_XCEV_Ideal" in self.file_list[id2].get('pktType'):
                            self.GetInitailVoltage(2, start=id2)
                            res.append([f"Measured Vrect is {self.initialVolt} V, Irect is {self.initialCurrent} A", "Pass"])
                        id2 += 1
                id += 1
            if not nak_flag:
                res.append([f"NAK is not observed for any of the above applied loads", "Pass"])


        return res

    

        
    def CE_Count(self, Flow_limit, Check):
        res = []
        id = Flow_limit[0]
        CE_count = 0
        while id < Flow_limit[1]:
            if any(rs in self.file_list[id].get('pktType') for rs in ['Load Set Done']):
                id2 = id
                while id2 <= self.stability:
                    if 'Control Error' in self.file_list[id2].get('pktType') and any(
                            rs in self.file_list[id2]['header_Payload']['childelement'][0]['childelement'][0]['sDescription']
                            for rs in ['Control Error Value : 1','Control Error Value : 0', 'Control Error Value : -1']):
                        CE_count += 1
                    if 'MPP_XCEV_Ideal' in self.file_list[id2].get('pktType'):
                        break
                    id2 += 1
            id += 1
        ChkRes = CommonMethods.check_measure(Check['expected'], CE_count, Check['comp'])
        res.append([f"Measured CE count is: {CE_count}, limit: {ChkRes[2]}", ChkRes[1]])
        return res
    
    def PacketSeq(self, Flow_limit, Check):
        res = []
        excnt = self.GetPacketDetails(packet="Execution_count_no", limit=[0, Flow_limit[0] - 1])
        limit = [excnt[2], len(self.file_list) - 1] if len(excnt) > 2 else Flow_limit
        TempPkt1 = self.PktMethod.GetPacketDetails(packet="Configuration", limit=limit, Type="Packet")
        if len(TempPkt1) > 2:
            res.append([f"Configuration packet found at {round(TempPkt1[0], 3)} sec", "Pass"])
            respid = self.PktMethod.GetPacketResponse2(TempPkt1[2], [TempPkt1[2] + 1, limit[1]])
            if respid is not None:
                if self.file_list[respid]['pktType'] in ["MPP", "MPP:ACK", "MPP ACK"]:
                    res.append([f"ACK response received for Configuration packet at {round(self.file_list[respid]['startTime'], 3)} sec, Expected: {['MPP', 'ACK', 'NAK']}", "Pass"])
                elif self.file_list[respid]['pktType'] == "NAK":
                    res.append([f"NAK response received for Configuration packet at {round(self.file_list[respid]['startTime'], 3)} sec, Expected: {['MPP', 'ACK', 'NAK']}", "Pass"])
                    if Check['expected'].get("Errbit"):
                        Reqerror = self.PktMethod.GetPacketDetails(packet="Get Request", value="PTx error status", limit=[TempPkt1[2] + 1, limit[1]], Type="Packet")
                        if len(Reqerror) > 2:
                            res.append([f"Get Request(PTx error status) found at {round(Reqerror[0], 3)}sec", "Pass"])
                            ptxerror = self.PktMethod.GetPacketDetails(packet="PTx Error status", limit=limit, Type="Response")
                            if len(ptxerror) > 2:
                                error = self.PktMethod.GetPayloadDetails(ptxerror[2], "Error")[0]['sRawData']
                                res.append([f"PTx Error status received found at {round(ptxerror[0], 3)}sec, with Error : {error}, Expected: Error ≠ 0", "Pass" if error != "0x00" else "Fail"])
                            else:
                                res.append([f"PTx Error status not received", "Fail"])
                        else:
                            res.append([f"Get Request(PTx error status) not found", "Fail"])

                    data = self.PacketCheck_New(limit, Check)
                    for ele in data:
                        res.append(ele)
                    if Check['expected'].get("Tterminate"):
                        data2 = self.T_measures(Flow_limit, Check['expected']["Tterminate"][0])
                        for ele in data2:
                            res.append(ele)
            else:
                res.append([f"NO response received for Configuration packet", "Fail"])
        else:
            res.append([f"Configuration packet not found", "Fail"])
        return res
    
    def Encoded(self, Flow_limit, Check):
        res = []
        data = self.PacketCheck_New(Flow_limit,Check)
        for ele in data:
            if "Found" in ele[0]:
                res.append(
                    [ele[0].replace("response", f"{Check['expected'][0]['mergingdata']}"), ele[1]])
            else:
                res.append(ele)
        return res
    
    def PARAMcheck(self, Flow_limit, Check):
        res = []
        self.AllChannelData3 = self.PlotMethod.GetAllChannelData('3', self.JapiData)
        id = 0
        end = len(self.file_list)
        conditions = {"condition_A": [], "condition_B": [], "condition_C": []}
        for cond in conditions:
            Tstart = self.PktMethod.GetPacketDetails(packet='Test_Status', value="Test_Started", limit=[id, end], Type="TesterMsg")
            if len(Tstart) > 2:
                Tstop = self.PktMethod.GetPacketDetails(packet='Test_Status', value="Test_Stop", limit=[Tstart[2], end], Type="TesterMsg")
                if len(Tstop) > 2:
                    conditions[cond] = [Tstart[2], Tstop[2]]
                    id = Tstop[2]
        cnt = 1
        self.default_values = []
        NAK_offset = {"condition_A": 0, "condition_B": 0, "condition_C": 0}
        for cond in conditions:
            if conditions[cond]:
                start = conditions[cond][0]
                stop = conditions[cond][1]
                res.append([f"{cond} validating from {self.PktMethod.Timeconvert(self.file_list[start]['startTime'])} to {self.PktMethod.Timeconvert(self.file_list[stop]['startTime'])}", "Pass"])
                PLAP78 = self.PktMethod.GetPacketDetails(packet=self.PLAP_pkt, limit=conditions[cond], Type="Packet")
                if len(PLAP78) > 2:
                    Alpha_FM = int(self.PktMethod.GetPayloadDetails(PLAP78[2], "Alpha_FM")[0]['sDescription'].split(":")[1].split(" ")[1].strip())
                    Alpha_FM_raw = float(self.PktMethod.GetPayloadDetails(PLAP78[2], "Alpha_FM")[0]['sDescription'].split(":")[1].split(" ")[2].strip("()"))
                    Alpha_FM_DC = int(self.PktMethod.GetPayloadDetails(PLAP78[2], "Alpha_FM_DC")[0]['sDescription'].split(":")[1].split(" ")[1].strip())
                    Alpha_FM_DC_raw = float(self.PktMethod.GetPayloadDetails(PLAP78[2], "Alpha_FM_DC")[0]['sDescription'].split(":")[1].split(" ")[2].strip("()"))
                    g_coil_TX = int(self.PktMethod.GetPayloadDetails(PLAP78[2], Check['PTx_coil_key'])[0]['sDescription'].split(":")[1].split(" ")[1].strip())
                    g_coil_TX_raw = float(self.PktMethod.GetPayloadDetails(PLAP78[2], Check['PTx_coil_key'])[0]['sDescription'].split(":")[1].split(" ")[2].strip("()"))
                    if cnt == 1:
                        self.default_values = [Alpha_FM, Alpha_FM_raw, Alpha_FM_DC, Alpha_FM_DC_raw, g_coil_TX, g_coil_TX_raw]
                        res.append([f"Alpha_FM: {Alpha_FM}, Alpha_FM_raw: {Alpha_FM_raw} in  PLAP (0x78) packet at {self.PktMethod.Timeconvert(PLAP78[0])}", "Pass"])
                        res.append([f"Alpha_FM_DC: {Alpha_FM_DC}, Alpha_FM_DC_raw: {Alpha_FM_DC_raw} in  PLAP (0x78) packet at {self.PktMethod.Timeconvert(PLAP78[0])}", "Pass"])
                        res.append([f"{Check['PTx_coil_key']}: {g_coil_TX}, {Check['PTx_coil_key']}_raw: {g_coil_TX_raw} in  PLAP (0x78) packet at {self.PktMethod.Timeconvert(PLAP78[0])}", "Pass"])
                    else:
                        exp_alpha = int(self.default_values[0] if cnt == 2 else 0.8 * self.default_values[0])
                        exp_alpha_raw = self.default_values[1] if cnt == 2 else 0.8 * self.default_values[1]
                        # res_str = "Pass" if (Alpha_FM == exp_alpha and Alpha_FM_raw == exp_alpha_raw) else "Fail"
                        # res.append([f"Alpha_FM: {Alpha_FM}, Alpha_FM_raw: {Alpha_FM_raw} in PLAP (0x78), Expected: Alpha_FM: {exp_alpha} {f'(default value)' if cnt == 2 else '(0.8 * default value)'}, Alpha_FM_raw: {exp_alpha_raw} {f'(default value)' if cnt == 2 else '(0.8 * default value)'}. Default values: Alpha_FM: {self.default_values[0]}, Alpha_FM_raw: {self.default_values[1]}", res_str])
                        res_str = "Pass" if Alpha_FM == exp_alpha else "Fail"
                        res.append([f"Alpha_FM: {Alpha_FM}, Alpha_FM_raw: {Alpha_FM_raw} in PLAP (0x78), Expected: Alpha_FM: {exp_alpha} {f'(default value)' if cnt == 2 else '(0.8 * default value)'}. Default values: Alpha_FM: {self.default_values[0]}, Alpha_FM_raw: {self.default_values[1]}", res_str])
                        
                        exp_dc = int(self.default_values[2] if cnt == 2 else 0.8 * self.default_values[2])
                        exp_dc_raw = self.default_values[3] if cnt == 2 else 0.8 * self.default_values[3]
                        # res_str2 = "Pass" if (Alpha_FM_DC == exp_dc and Alpha_FM_DC_raw == exp_dc_raw) else "Fail"
                        # res.append([f"Alpha_FM_DC: {Alpha_FM_DC}, Alpha_FM_DC_raw: {Alpha_FM_DC_raw} in PLAP (0x78), Expected: Alpha_FM_DC: {exp_dc} {f'(default value)' if cnt == 2 else '(0.8 * default value)'}, Alpha_FM_DC_raw: {exp_dc_raw} {f'(default value)' if cnt == 2 else '(0.8 * default value)'}. Default values: Alpha_FM_DC: {self.default_values[2]}, Alpha_FM_DC_raw: {self.default_values[3]}", res_str2])
                        res_str2 = "Pass" if Alpha_FM_DC == exp_dc else "Fail"
                        res.append([f"Alpha_FM_DC: {Alpha_FM_DC}, Alpha_FM_DC_raw: {Alpha_FM_DC_raw} in PLAP (0x78), Expected: Alpha_FM_DC: {exp_dc} {f'(default value)' if cnt == 2 else '(0.8 * default value)'}. Default values: Alpha_FM_DC: {self.default_values[2]}, Alpha_FM_DC_raw: {self.default_values[3]}", res_str2])

                        exp_tx = int(0.8 * self.default_values[4] if cnt == 2 else self.default_values[4])
                        exp_tx_raw = 0.8 * self.default_values[5] if cnt == 2 else self.default_values[5]
                        # res_str3 = "Pass" if (g_coil_TX == exp_tx and g_coil_TX_raw == exp_tx_raw) else "Fail"
                        # res.append([f"{Check['PTx_coil_key']}: {g_coil_TX}, {Check['PTx_coil_key']}_raw: {g_coil_TX_raw} in PLAP (0x78), Expected: {Check['PTx_coil_key']}: {exp_tx} {f'(0.8 * default value)' if cnt == 2 else '(default value)'}, {Check['PTx_coil_key']}_raw: {exp_tx_raw} {f'(0.8 * default value)' if cnt == 2 else '(default value)'}. Default values: {Check['PTx_coil_key']}: {self.default_values[4]}, {Check['PTx_coil_key']}_raw: {self.default_values[5]}", res_str3])
                        res_str3 = "Pass" if g_coil_TX == exp_tx else "Fail"
                        res.append([f"{Check['PTx_coil_key']}: {g_coil_TX}, {Check['PTx_coil_key']}_raw: {g_coil_TX_raw} in PLAP (0x78), Expected: {Check['PTx_coil_key']}: {exp_tx} {f'(0.8 * default value)' if cnt == 2 else '(default value)'}. Default values: {Check['PTx_coil_key']}: {self.default_values[4]}, {Check['PTx_coil_key']}_raw: {self.default_values[5]}", res_str3])
                else:
                    res.append([f"PLAP (0x78) packet not found", "Fail"])
                PLAP5F = self.PktMethod.GetPacketDetails(packet=self.PLAP_pkt, limit=conditions[cond], Type="Response")
                if len(PLAP5F) > 2:
                    g_coil_RX = float(self.PktMethod.GetPayloadDetails(PLAP5F[2], Check['PRx_coil_key'])[0]['sDescription'].split(":")[1].split(" ")[1].strip())
                    g_coil_RX_raw = float(self.PktMethod.GetPayloadDetails(PLAP5F[2], Check['PRx_coil_key'])[0]['sDescription'].split(":")[1].split(" ")[2].strip("()"))
                    if g_coil_RX == 10000 and g_coil_RX_raw == 1:
                        res.append([f"{Check['PRx_coil_key']}: {g_coil_RX}, {Check['PRx_coil_key']}_raw: {g_coil_RX_raw} in PLAP (0x5F), Expected: 10000, 1", "Pass"])
                    else:
                        res.append([f"{Check['PRx_coil_key']}: {g_coil_RX}, {Check['PRx_coil_key']}_raw: {g_coil_RX_raw} in PLAP (0x5F), Expected: 10000, 1", "Fail"])
                else:
                    res.append([f"PLAP (0x5F) packet not found", "Fail"])
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load 15000mW", limit=conditions[cond], Type="TesterMsg")
                print("TempPkt1:",TempPkt1)
                if len(TempPkt1) > 2:
                    self.GetInitailVoltage(2, start=TempPkt1[2],end=conditions[cond][1])
                    res.append([f"{self.file_list[TempPkt1[2]]['pktType']} found at {self.PktMethod.Timeconvert(TempPkt1[0])}", "Pass"])
                    if self.XCEV_Ideal is not None:
                        res.append([f"Power transfer stabilized at {self.PktMethod.Timeconvert(self.file_list[self.XCEV_Ideal]['startTime'])}", "Pass"])
                        irect = self.PktMethod.CalculateVoltTwindow(self.stability, self.AllChannelData3)
                        # ChkRes1 = CommonMethods.check_measure([1.080, 1.090], irect[0], 0)
                        res.append([f"Measured Irect is {irect[0]} A", "Pass"])
                        vrect = self.PktMethod.CalculateVoltTwindow(self.stability, self.AllChannelData)
                        ChkRes2 = CommonMethods.check_measure([13.86, 14.14], vrect[0], 0)
                        res.append([f"Measured Vrect is {ChkRes2[3]} V, Limit: {ChkRes2[2]} V", ChkRes2[1]])
                        power = round(vrect[0] * irect[0], 3)
                        ChkRes3 = CommonMethods.check_measure([15], power, "GTEQL")
                        res.append([f"Measured Prect is {power} W, Limit: {ChkRes3[2]} W", ChkRes3[1]])
                    else:
                        res.append([f"Power transfer not stabilized", "Fail"])
                else:
                    res.append([f"Set_Load 1500mW assertion not found", "Fail"])
                nak_chk = False
                AllChannelData = self.PlotMethod.GetAllChannelData2('2', self.JapiData)
                AllChannelData3 = self.PlotMethod.GetAllChannelData2('3', self.JapiData)
                Flow_limit = conditions[cond]
                TempPkt = ["MPP_XCEV_Ideal", "TesterMsg"]
                TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0], limit=Flow_limit, Type=TempPkt[1])
                if len(TempPkt1) > 2:
                    packetCount = 0
                    id = TempPkt1[2]
                    ReceivedPower_offset = 0.0
                    while id < Flow_limit[1]:
                        TempPkt2 = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting", limit=[id, Flow_limit[1]])
                        if len(TempPkt2) > 2:
                            TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset", limit=[TempPkt2[2], TempPkt2[2] - 5], Type="TesterMsg")
                            TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified", limit=[TempPkt2[2], TempPkt2[2] - 5], Type="TesterMsg")
                            if len(TempPkt3) > 2 and len(TempPkt4) > 2:
                                packetCount += 1
                                Received_Power = float(self.file_list[TempPkt4[2]]['value'].split("Received:")[1].split("mW")[0].strip())
                                RP_offset = float(self.file_list[TempPkt3[2]]['value'].split("RP offset:")[1].split("W")[0].strip()) * 1000
                                PLA_ReceivedPower = round(float(self.PktMethod.GetPayloadDetails(TempPkt2[2], "Received_Power_Value")[0]['sDescription'].split("Estimated Received Power value:")[1].split("W")[0].strip()) * 1000, 1)
                                if abs(ReceivedPower_offset) == RP_offset:
                                    pass
                                else:
                                    res.append(
                                        [f"Mismatch in offset applied: {RP_offset} mW, Expected offset: {abs(ReceivedPower_offset)} mW", "Fail"])
                                if PLA_ReceivedPower == (Received_Power + ReceivedPower_offset):
                                    res.append(
                                        [f"Received power in PLA packet: {PLA_ReceivedPower} mW is matching to calculated power: {(Received_Power + ReceivedPower_offset)} mW after applying {ReceivedPower_offset} mW offset", "Pass"])
                                else:
                                    res.append(
                                        [f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {(Received_Power + ReceivedPower_offset)} mW after applying {ReceivedPower_offset} mW offset", "Fail"])
                                x = TempPkt2[2] + 1
                                if 'TesterMsg' in self.GetPacketType(x):
                                    x += 1
                                res.append([f"{self.file_list[x]['pktType']} response received for PLA packet", "Pass"])
                                if 'NAK' in self.file_list[x]['pktType']:
                                    nak_chk = True
                                    NAK_offset[cond] = ReceivedPower_offset
                                    res.append([f"NAK response received after applying {ReceivedPower_offset} mW offset for PLA packet", "Pass"])
                                    vrect1 = self.CalculateVoltTwindow(TempPkt2[2], AllChannelData, at="end", measure="after", winsize=[15, 19])[0]
                                    irect1 = self.CalculateVoltTwindow(TempPkt2[2], AllChannelData3, at="end", measure="after", winsize=[15, 19])[0]
                                    Prect1 = vrect1 * irect1
                                    vrect2 = self.CalculateVoltTwindow(TempPkt2[2], AllChannelData, at="end", measure="after", winsize=[40, 44])[0]
                                    irect2 = self.CalculateVoltTwindow(TempPkt2[2], AllChannelData3, at="end", measure="after", winsize=[40, 44])[0]
                                    Prect2 = vrect2 * irect2
                                    if (Prect2 - Prect1) * 1000 <= 50:
                                        res.append([f"PTx throttled while sending NAK to PLA packet at {self.PktMethod.Timeconvert(TempPkt2[0])}", "Pass"])
                                    else:
                                        res.append([f"PTx not throttled while sending NAK to PLA packet at {self.PktMethod.Timeconvert(TempPkt2[0])}", "Fail"])
                            id = TempPkt2[2] + 1
                            ReceivedPower_offset -= 10.0
                        else:
                            break
                    sd = self.PktMethod.GetPacketDetails(packet='Test_Status', value="Test_Stop", limit=[Flow_limit[1], Flow_limit[0]], Type="TesterMsg")
                    if len(sd) > 2:
                        res.append([f"PTx removed power at {self.PktMethod.Timeconvert(sd[0])}", "Pass"])
                    else:
                        res.append([f"PTx does not removed power", "Fail"])
                    if packetCount == 0:
                        res.append(
                            [f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'], 3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}Sec", "Fail"])
                    elif not nak_chk:
                        res.append(
                            [f"Received {packetCount} PLA Packets with all ACK responses, without Throttling", "Fail"])
                    else:
                        res.append(
                            [f"Received {packetCount} PLA Packets with offset value between {round(TempPkt1[0], 3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}sec", "Pass"])
                else:
                    res.append(
                        [f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'], 3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}Sec", "Fail"])
                cnt += 1
            else:
                res.append([f"{cond} sequence not found.", "Fail"])
        if abs(NAK_offset['condition_B']) < abs(NAK_offset['condition_A']):
            res.append(
                [f"PPR_offset_B: {abs(NAK_offset['condition_B'])} < PPR_offset_A: {abs(NAK_offset['condition_A'])}, Expected: PPR_offset_B < PPR_offset_A", "Pass"])
        else:
            res.append(
                [f"PPR_offset_B: {abs(NAK_offset['condition_B'])}, PPR_offset_A: {abs(NAK_offset['condition_A'])}, Expected: PPR_offset_B < PPR_offset_A", "Fail"])
        if abs(NAK_offset['condition_C']) < abs(NAK_offset['condition_A']):
            res.append(
                [f"PPR_offset_C: {abs(NAK_offset['condition_C'])} < PPR_offset_A: {abs(NAK_offset['condition_A'])}, Expected: PPR_offset_C < PPR_offset_A", "Pass"])
        else:
            res.append(
                [f"PPR_offset_C: {abs(NAK_offset['condition_C'])}, PPR_offset_A: {abs(NAK_offset['condition_A'])}, Expected: PPR_offset_C < PPR_offset_A", "Fail"])


        return res
    def TxceStable(self, Flow_limit, Check):
        res = []
        setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['set_load']}mA", limit=Flow_limit, Type="TesterMsg")
        if len(setload) > 2:
            ideal = self.GetPacketDetails(packet='MPP_XCEV_Ideal', limit=[setload[2], Flow_limit[1]])
            if len(ideal) > 1:
                XCE = self.GetPacketDetails(packet='Extended Control Error', limit=[ideal[2], setload[2]])
                if len(XCE) > 1:
                    chk_res = CommonMethods.check_measure(Check['expected'], (round(XCE[1] - setload[1], 3)), "LTEQL")
                    res.append(
                        [f"Measured Txce_stable is {chk_res[3]} sec, Expected: {chk_res[2]}", chk_res[1]])
                else:
                    res.append([f"Extended Control Error packet not found.", "Fail"])
            else:
                res.append([f"MPP_XCEV_Ideal packet not found.", "Fail"])
        else:
            res.append([f"Set_Load {Check['set_load']}mA packet not found.", "Inconclusive"])


        return res
    def Vrect_Ref(self, Flow_limit, Check):
        id = 0
        end = len(self.file_list) - 1
        res = []
        ssvrect = {"z_0mm": "", "z_1mm": "", "z_2mm": ""}
        EXcntpkt = self.PktMethod.GetPacketDetails(packet="Execution_count_no", limit=[end, id], Type="TesterMsg")
        if len(EXcntpkt) > 2:
            ssvrect['z_0mm'] = EXcntpkt[2]
            IncZ1 = self.PktMethod.GetPacketDetails(packet="Increase_z_By_1mm", limit=[EXcntpkt[2], end], Type="TesterMsg")
            if len(IncZ1) > 2:
                ssvrect['z_1mm'] = IncZ1[2]
                IncZ2 = self.PktMethod.GetPacketDetails(packet="Increase_z_By_1mm", limit=[IncZ1[2] + 1, end], Type="TesterMsg")
                if len(IncZ2) > 2:
                    ssvrect['z_2mm'] = IncZ2[2]
                else:
                    res.append([f"Increase_z_By_1mm assertion_2 not found", "Fail"])
            else:
                res.append([f"Increase_z_By_1mm assertion_1 not found", "Fail"])
        else:
            res.append([f"Execution_count_no not found", "Fail"])
        vrectmax = {"z_0mm": 0, "z_1mm": 0, "z_2mm": 0}
        for key, value in ssvrect.items():
            if value:
                res.append([f"{self.file_list[value]['pktType']} found at {round(self.file_list[value]['startTime'], 3)} sec", "Pass"])
                cnt = 1
                start = value
                vmax = 0
                while cnt <= 5:
                    ss = self.PktMethod.GetPacketDetails(packet="Signal strength", limit=[start, end])
                    if len(ss) > 2:
                        vrect = float(round(self.PktMethod.CalculateVoltTwindow(ss[2], self.AllChannelData, winsize=[9, 11])[0], 3))
                        res.append([f"At {key}, Vrect at Signal strength_{cnt} is {vrect} V, found at {round(ss[0], 3)} sec", "Pass"])
                        if vrect > vmax:
                            vmax = vrect
                        start = ss[2] + 1
                    else:
                        res.append([f"Signal strength not found", "Fail"])
                    cnt += 1
                vrectmax[key] = vmax
                res.append([f"Vrect_{list(ssvrect.keys()).index(key)}_max at {key} is {vmax} V", "Pass"])
        maxkey = max(vrectmax, key=vrectmax.get)
        res.append([f"Final Maximum voltage is {max(vrectmax.values())} V at {maxkey}", "Pass"])
        res = res


        return res
    def Vrect_max(self, Flow_limit, Check):
        res = []
        setload = self.PktMethod.GetPacketDetails(packet=f'Set_Load 80mA', limit=Flow_limit, Type="TesterMsg")
        if len(setload) > 2:
            res.append([f"Load current switched to 80 mA at {round(setload[0],3)} sec", "Pass"])
            sindex = int((((self.file_list[setload[2]].get('startTime') - 1) * 1000)) / self.AllChannelData['Interval'])
            eindex = int((((self.file_list[setload[2]].get('startTime') + 1) * 1000)) / self.AllChannelData['Interval'])
            id = sindex
            vrects = list(self.AllChannelData['RV']['displayDataChunk'][sindex:eindex + 1])
            vrect_max = max(vrects)
            vrect_max_index = sindex + vrects.index(vrect_max) + 1
            t1 = self.AllChannelData['Interval'] * vrect_max_index
            if vrect_max <= 20.4:
                res.append([f"Vrect_max: {round(vrect_max, 3)} V found at {self.PktMethod.ms_to_time(t1)}, Expected: <= 20.4 V", "Pass"])
            else:
                res.append([f"Vrect_max: {round(vrect_max, 3)} V found at {self.PktMethod.ms_to_time(t1)}, Expected: <= 20.4 V", "Fail"])
        else:
            res.append([f"Set_Load 80mA packet not found.", "Fail"])
        return res
    
    # def InitialVoltage_Vrectfinal0(self, Flow_limit, Check):
    #     res = []
    #     if self.initialVoltage is not None:
    #         AllMeasures[CTSCheck] = self.initialVoltage
    #         res.append(
    #             [f"The Measured voltage is {self.initialVoltage}V at {round(self.file_list[self.stability]['startTime'], 2)}sec", "Pass"])
    #     else:
    #         res.append(["Stabilization not found", "Fail"])


    #     return res
    # def Vrectfinal1(self, Flow_limit, Check):
    #     res = []
    #     if self.stability is not None:
    #         ideal = self.GetPacketDetails(packet='MPP_XCEV_Ideal', limit=[self.stability + 8, len(self.file_list) - 1])
    #         if len(ideal) > 1:
    #             XCE = self.GetPacketDetails(packet='Extended Control Error', limit=[ideal[2], self.stability + 8])
    #             self.XCEref = XCE
    #             if len(XCE) > 1:
    #                 res = self.CalculateVoltTwindow(XCE[2], self.AllChannelData)
    #                 AllMeasures[CTSCheck] = res[0]


    #     return res
    # def Vrectfinal2(self, Flow_limit, Check):
    #     res = []
    #     if self.XCEref:
    #         ideal = self.GetPacketDetails(packet='MPP_XCEV_Ideal', limit=[self.XCEref[2] + 8, len(self.file_list) - 1])
    #         if len(ideal) > 1:
    #             XCE = self.GetPacketDetails(packet='Extended Control Error', limit=[ideal[2], self.XCEref[2] + 8])
    #             if len(XCE) > 1:
    #                 res = self.CalculateVoltTwindow(XCE[2], self.AllChannelData)
    #                 AllMeasures['Vrectfinal2'] = res[0]


    #     return res
    def VrecrfinalComp(self, Flow_limit, Check):
        res = []
        # AllMeasures[CTSCheck] = str(AllMeasures['Vrectfinal0']) + ':' + str(AllMeasures['Vrectfinal1']) + ':' + str(AllMeasures['Vrectfinal2'])
        self.AllChannelData3 = self.PlotMethod.GetAllChannelData('3', self.JapiData)

        cnt = 0
        Vrect_values = []
        id = Flow_limit[0]
        while id < Flow_limit[1]:
            Setload = self.PktMethod.GetPacketDetails(packet=f'Set_Load 50mA', limit=[id,Flow_limit[1]], Type="TesterMsg")
            if len(Setload) > 2:
                res.append([f"Set_Load 50mA packet found at {round(Setload[0], 3)} Sec, Expected: Set_Load 50mA", "Pass"])
                Ideal = self.PktMethod.GetPacketDetails(packet='MPP_XCEV_Ideal', limit=[Setload[2], Flow_limit[1]], Type="TesterMsg")
                if len(Ideal) > 2:
                    res.append([f"MPP_XCEV_Ideal packet found at {round(Ideal[0], 3)} Sec", "Pass"])
                    xce = self.PktMethod.GetPacketDetails(packet='Extended Control Error', limit=[Ideal[2],Setload[2]], Type="Packet")
                    if len(xce)>2:
                        Vrect = self.CalculateVoltTwindow(xce[2], self.AllChannelData)[0]
                        Irect = self.CalculateVoltTwindow(xce[2], self.AllChannelData3)[0]
                        chk_res = CommonMethods.check_measure([(Check['vrect_val'][cnt]-0.25),(Check['vrect_val'][cnt]+0.25)], Vrect, 0)
                        res.append([f"Measured Vrectfinal_{cnt} = {Vrect} V at {round(xce[0],3)} sec, Expected: {chk_res[2]}", chk_res[1]])
                        Vrect_values.append(Vrect)

                        cnt += 1
                        id = xce[2]
            
            id += 1
        
        if len(Vrect_values) == 3:
            if Check['chk'] == "Vrectfinal0<Vrectfinal1<Vrectfinal2":
                if Vrect_values[0]<Vrect_values[1]<Vrect_values[2]:
                    res.append([f"Vrectfinal0 = {Vrect_values[0]} V, Vrectfinal1 = {Vrect_values[1]} V, Vrectfinal2 = {Vrect_values[2]} V, Expected: {Check['chk']}", 'Pass'])
                else: res.append([f"Vrectfinal0 = {Vrect_values[0]} V, Vrectfinal1 = {Vrect_values[1]} V, Vrectfinal2 = {Vrect_values[2]} V, Expected: {Check['chk']}", 'Fail'])
            elif Check['chk'] == "Vrectfinal0>Vrectfinal1>Vrectfinal2":
                if Vrect_values[0]>Vrect_values[1]>Vrect_values[2]:
                    res.append([f"Vrectfinal0 = {Vrect_values[0]} V, Vrectfinal1 = {Vrect_values[1]} V, Vrectfinal2 = {Vrect_values[2]} V, Expected: {Check['chk']}", 'Pass'])
                else: res.append([f"Vrectfinal0 = {Vrect_values[0]} V, Vrectfinal1 = {Vrect_values[1]} V, Vrectfinal2 = {Vrect_values[2]} V, Expected: {Check['chk']}", 'Fail'])
        else: res.append([f"Control stabilized for only {len(Vrect_values)} loads, Expected: 3 loads", "Fail"])





        return res
    def PR_MAX(self, Flow_limit, Check):
        res = []
        loads = [50, 400]
        cnt = 1
        vinv_list = []
        for load in loads:
            Setload = self.PktMethod.GetPacketDetails(packet=f'Set_Load {load}mA', limit=Flow_limit, Type="TesterMsg")
            if len(Setload) > 2:
                res.append([f"Set_Load {load}mA packet found at {round(Setload[0], 3)} Sec, Expected: Set_Load {load}mA", "Pass"])
                Ideal = self.PktMethod.GetPacketDetails(packet='MPP_XCEV_Ideal', limit=[Setload[2], Flow_limit[1]], Type="TesterMsg")
                if len(Ideal) > 2:
                    res.append([f"MPP_XCEV_Ideal packet found at {round(Ideal[0], 3)} Sec", "Pass"])
                    Get_inv = self.PktMethod.GetPacketDetails(packet="Get Request", value="PTx Inverter Voltage", limit=[Ideal[2], Flow_limit[1]], Type="Packet")
                    if len(Get_inv) > 2:
                        if cnt == 2:
                            t_waited = round(Get_inv[0] - Setload[1], 3)
                            if t_waited > 5:
                                res.append([f"Waited for {t_waited}sec after Set_Load {load}mA, Expected: > 5 sec", "Pass"])
                            else:
                                res.append([f"Waited for {t_waited}sec after Set_Load {load}mA, Expected: > 5 sec", "Fail"])
                        res.append([f"Get Request (PTx Inverter Voltage) packet found at {round(Get_inv[0], 3)} Sec", "Pass"])
                        inv_resp = self.PktMethod.GetPacketDetails(packet=self.Inv_vol_pkt, limit=[Get_inv[2], Flow_limit[1]], Type="Response")
                        if len(inv_resp) > 2:
                            res.append([f"{self.Inv_vol_pkt} response found at {round(inv_resp[0], 3)} Sec", "Pass"])
                            Vinv = float(self.PktMethod.GetPayloadDetails(inv_resp[2], "Vinv")[0]['sDescription'].split(":")[-1].split("V")[0].strip())
                            Vrect = self.PktMethod.CalculateVoltTwindow(inv_resp[2], self.AllChannelData, winsize=[1, 3])[0]
                            G = round(Vrect / Vinv, 3)
                            chk_res = CommonMethods.check_measure(Check['G1_exp' if cnt == 1 else 'G2_exp'], G, 0)
                            res.append([f"Measured G{cnt}: {G}, Vrect{cnt}: {Vrect} V, Vinv{cnt}: {Vinv} V at {round(inv_resp[0], 3)} Sec, Expected G{cnt}: {chk_res[2]}", chk_res[1]])
                            vinv_list.append(Vinv)
                            if cnt == 1:
                                x = inv_resp[2]
                                while x < Flow_limit[1]:
                                    if 'Extended Control Error' in self.file_list[x].get('pktType'):
                                        if self.file_list[x].get('value') not in ['0']:
                                            res.append([f"Extended Control Error {self.file_list[x]['value']} found at {round(self.file_list[x]['startTime'], 3)} Sec, Expected: Extended Control Error 0 only", "Fail"])
                                            break
                                    x += 1
                                else:
                                    res.append([f"Extended Control Error 0 is observed from {round(inv_resp[0], 3)} Sec to {round(self.file_list[Flow_limit[1]]['startTime'], 3)} Sec(end of test)", "Pass"])
                            cnt += 1
                        else:
                            res.append([f"{self.Inv_vol_pkt} not found", "Fail"])
                    else:
                        res.append([f"Get Request (PTx Inverter Voltage) not found", "Fail"])
                else:
                    res.append([f"MPP_XCEV_Ideal not found", "Fail"])
            else:
                res.append([f"Set_Load 50mA not found", "Fail"])
        if len(vinv_list) == 2:
            vinv_delta = round(abs(vinv_list[1] - vinv_list[0]), 3)
            if vinv_delta <= 0.2:
                res.append(
                    [f"The Measured Vinverter_Delta is {vinv_delta * 1000} mV, Expected: <= 200 mV", "Pass"])
            else:
                res.append(
                    [f"The Measured Vinverter_Delta is {vinv_delta * 1000} mV, Expected: <= 200 mV", "Fail"])
        else:
            res.append([f"Vinverter_Delta not found", "Fail"])
        return res
    
    def PeakCurrent(self, Flow_limit, Check):
        res = []
        PC = self.GetPacketDetails(packet='Short_Fixture_Status', value="PeakCurrent", limit=[Flow_limit[0], len(self.file_list)])
        if len(PC) > 2:
            resp = GeneralMethods.GetFloatFromStr(self.file_list[PC[2]]['value'])
            chk = CommonMethods.check_measure([6.7], resp[0], 'LTEQL')
            res.append([f'The Measured PeakCurrent is {chk[3]} A at {self.PktMethod.Timeconvert(PC[0])}, Expected: {chk[2]} A', chk[1]])
        else:
            res.append([f'Short_Fixture_Status not found', 'Fail'])
        return res
    
    # def BitsCheck(self, Flow_limit, Check):
    #     res = []
    #     self.BitsCheck_New(Flow_limit, flwID, Check, AllMeasures)
    #     return res
    
    def AUTHBitsCheck(self, Flow_limit, Check):
        res = []
        tempresp = self.AUTHBitsCheck_New(Flow_limit, Check)
        for new_res in tempresp:
            res.append(new_res)
        return res
    
    def Preceived(self, Flow_limit, Check):
        res = []
        Setload = self.PktMethod.GetPacketDetails(packet=f'Set_Load', limit=Flow_limit, Type="TesterMsg")
        if len(Setload) > 2:
            LoadLimit = [self.stability, Flow_limit[1]]
            MinRP = self.GetPacketDetails(packet="Received Power", limit=LoadLimit)
            if len(MinRP) > 2:
                id = MinRP[2]
                RPlist = []
                while id <= Flow_limit[1]:
                    if "Shutdown" in self.file_list[id]['pktType']:
                        res.append(
                            [f"Power signal was removed within 2mins from the load ramp. at {round(self.file_list[id]['startTime'], 3)} sec", "Fail"])
                        break
                    if (self.file_list[id]['startTime'] - MinRP[0]) >= 120:
                        res.append([f"Power signal was not removed for 2mins after the load ramp.", "Pass"])
                        break
                    if 'Received Power' in self.file_list[id]['pktType']:
                        result = GeneralMethods.GetFloatFromStr(self.file_list[id]['value'])
                        RPlist.append(result[0])
                    id += 1
                prect_min = min(RPlist)
                prect_max = max(RPlist)
                res.append([f"The measured Prect_min is {prect_min} W, Expected: >=5 W", "Pass" if max(RPlist) >= 5 else "Fail"])
                res.append([f"The measured Prect_max is {prect_max} W, Expected: <=7.5 W", "Pass" if max(RPlist) <= 7.5 else "Fail"])
        return res
    
    def RP_avgPower(self, Flow_limit, Check):
        res = []
        maxtime = self.GetPacketDetails(packet="MPP_XCEV_Ideal", limit=[self.stability, Flow_limit[1]])[1] + 2
        id = self.stability
        power = 0
        cnt = 0
        while id < Flow_limit[1]:
            if float(self.file_list[id].get('startTime')) > maxtime:
                break
            if 'Received Power' in self.file_list[id].get('pktType'):
                cnt += 1
                power = power + float(self.file_list[id]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'].split('w')[0].replace('{', ''))
                print("RP8:",float(self.file_list[id]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'].split('w')[0].replace('{', '')))
            id += 1
        # AllMeasures[CTSCheck] = power / cnt if 0 not in [cnt, power] else None
        if 0 not in [cnt, power]:
            avg_pwr = power / cnt
            print("avg_pwr:",avg_pwr)
            chk_resp = CommonMethods.check_measure([4.5], avg_pwr, 'GT')
            print("chk_resp:",chk_resp)
            res.append([f"Measured RP8 avaerage value is {chk_resp[3]} W, Expected: {chk_resp[2]} W", chk_resp[1]])
        return res
    
    # def PacketCheck(self, Flow_limit, Check):
    #     res = []
    #     self.PacketCheck_New(Flow_limit, flwID, Check, AllMeasures)


    #     return res
    # def PLA_Throttle(self, Flow_limit, Check):
    #     res = []
    #     if self.stability is not None:
    #         values = []
    #         id = self.stability
    #         while id < Flow_limit[1]:
    #             PLA = self.GetPacketDetails(packet="PLA_2", limit=[id, Flow_limit[1]])
    #             if len(PLA) > 2:
    #                 v1 = self.CalculateVoltageOnTime(self.AllChannelData, (PLA[1] * 1000) + Check['V1'])
    #                 v2 = self.CalculateVoltageOnTime(self.AllChannelData, (PLA[1] * 1000) + Check['V2'])
    #                 v2 = v2 + Check['V2_round']
    #                 values.append([v1, v2, f"PLA@{PLA[2]}:V1={round(v1 / 1000, 3)}V@{(PLA[1] * 1000) + Check['V1']}ms:V2={round(v2 / 1000, 3)}@{(PLA[1] * 1000) + Check['V2']}ms"])
    #                 id = PLA[2] + 1
    #             else:
    #                 break
    #         if len(values) > 0:
    #             AllMeasures[CTSCheck] = values


    #     return res
    def PTPhase(self, Flow_limit, Check):
        res = []
        if 'PktLimit' in Check:
            limit = self.PktMethod.GetLimits(Check['PktLimit'], Check, Flow_limit)
        else:
            limit = Flow_limit
        id = limit[0]
        while id < limit[1]:
            if self.file_list[id]['pktType'] in ["Extended Control Error","Control Error"]:
                # AllMeasures[CTSCheck] = round(self.file_list[id]['startTime'], 2)
                res.append([f'PT Phase started from {round(self.file_list[id]['startTime'],3)} sec', "Pass"])
                break
            id += 1
        if len(res) == 0:
            res.append([f'PT Phase not found.', "Fail"])

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
                    res.append([f"Set_Load {load} mW is observed at index @{TempPkt1[2]}", "pass"])
                else:
                    res.append([f"Set_Load {load} mW is not observed.", "Fail"])
            else:
                res.append([f"{self.ECAP_pkt} not recevied", "Fail"])

        if "Load_upto" in Check:
            x = Flow_limit[0]
            end = Flow_limit[1]
            ECAP_cnt = 0
            res.append([f"We have to set load upto the Negotiable load power value in the ECAP packet reported by the PTxDUT", "pass"])
            while x < end:
                # limit2 = [x,end]
                ECAP = self.PktMethod.GetPacketDetails(packet=self.ECAP_pkt,limit=[x,end],Type="Response")
                if len(ECAP) > 2:
                    ECAP_cnt += 1
                    x = ECAP[2]
                    Load_pwr = float(self.PktMethod.GetPayloadDetails(ECAP[2],Check['Load_upto']["ECAP"])[0]['sDescription'].split(":")[1].split("W")[0].strip())
                    res.append([f"{Check['Load_upto']['ECAP']}: {Load_pwr}W is observed in {self.ECAP_pkt} packet at index @{ECAP[2]}", "pass"])
                    load = int(Load_pwr*1000) #mW

                    TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load ", limit=[ECAP[2], end], Type="TesterMsg")
                    if len(TempPkt1) > 2:
                        x = TempPkt1[2]
                        applied_load = int(self.file_list[x]['pktType'].split()[1].split("mW")[0])
                        if applied_load <= load:
                            res.append([f"Set_Load {applied_load} mW is observed at index @{TempPkt1[2]}, Expected: Upto the Negotiable load power value in the ECAP packet ", "pass"])
                        else:
                            res.append([f"Set_Load {applied_load} mW is observed at index @{TempPkt1[2]}, Expected: Upto the Negotiable load power value in the ECAP packet", "Fail"])
                    else:
                        res.append([f"Set_Load {load} mW is not observed.", "Fail"])

                    # TempPkt1 = self.PktMethod.GetPacketDetails(packet=f"Set_Load {load}mW", limit=[ECAP[2], end], Type="TesterMsg")
                    # if len(TempPkt1) > 2:
                    #     x = TempPkt1[2]
                    #     res.append([f"Set_Load {load} mW is observed at index @{TempPkt1[2]}", "pass"])
                    # else:
                    #     res.append([f"Set_Load {load} mW is not observed.", "Fail"])
                else:
                    if ECAP_cnt < 1:
                        res.append([f"{self.ECAP_pkt} not recevied", "Fail"])

                    break
                x += 1




        return res

    
    def DPlossCalibration(self, Flow_limit, Check):
        res = []
        calbPoints = None
        Pkt = self.GetPacketDetails(packet="CAL_ENTER", limit=Flow_limit)
        if len(Pkt) > 2:
            CAL_ENTER_STOP = Pkt[1]
            res.append([f"Received CAL_ENTER packet at {round(Pkt[0], 2)} sec", "Pass"])
        else:
            res.append([f"CAL_ENTER packet not recevied", "Fail"])
        Pkt_res = self.GetPacketDetails(packet="CAL_ENTER_RSP", limit=Flow_limit)
        if len(Pkt_res) > 2:
            calduration = int(GeneralMethods.GetFloatFromStr(self.file_list[Pkt_res[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0])
            if self.Mode == "TPT":
                calduration = calduration * 60
            calbPoints = int(GeneralMethods.GetFloatFromStr(self.file_list[Pkt_res[2]]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])[0])
            res.append([f"Received CAL_ENTER_RSP packet at {round(Pkt_res[0], 2)} sec, with Calib points of {calbPoints}", "Pass"])
        else:
            res.append([f"CAL_ENTER_RSP packet not recevied", "Fail"])
        id = Pkt[2] if len(Pkt) > 0 else Flow_limit[0]
        CAL_CAPTURE_cnt = 0
        CalStart = 0
        CalEnd = 0
        CalLevels = []
        prevIndex = 0
        pkt_cmt = self.GetPacketDetails(packet="CAL_OP", value="CMT ", limit=Flow_limit)
        TempLimit = [id, pkt_cmt[2]] if len(pkt_cmt) > 2 else [id, Flow_limit[1]]
        while id < TempLimit[1]:
            if 'CAL_CAPTURE' in self.file_list[id]['pktType']:
                if self.GetPacketType(id) == "Packet" if self.Mode == "TPT" else self.GetPacketType(id) == "Response":
                    if CAL_CAPTURE_cnt == 1:
                        CalStart = round(self.file_list[id]['startTime'], 2)
                    CalEnd = round(self.file_list[id]['stopTime'], 2)
                    if CAL_CAPTURE_cnt > 0:
                        if abs(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(id, "PRECT")[0]['sDescription'])[0] - GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(prevIndex, "PRECT")[0]['sDescription'])[0]) >= 1.5:
                            if len(CalLevels) == 0:
                                CalLevels.append([TempLimit[0], prevIndex])
                            else:
                                CalLevels.append([CalLevels[len(CalLevels) - 1][1] + 1, prevIndex])
                    CAL_CAPTURE_cnt += 1
                    prevIndex = id
            id += 1
        CalLevels.append([CalLevels[len(CalLevels) - 1][1] + 1, prevIndex])
        if calbPoints is not None:
            if CAL_CAPTURE_cnt == calbPoints:
                res.append([f"Recived all the {calbPoints} CAL_CAPTURE packets between {CalStart}sec to {CalEnd}sec", "Pass"])
            else:
                res.append([f"Mismatch in CAL_CAPTURE packet count, No,of Calib points={calbPoints} and Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}", "Fail"])
        else:
            res.append([f"CAL_ENTER_RSP packet not recevied, Recevied CAL_CAPTURE count={CAL_CAPTURE_cnt}", "Fail"])
        if len(pkt_cmt) > 2:
            res.append([f"Received CAL_OP packet at {round(pkt_cmt[0], 2)} sec", "Pass"])
        else:
            res.append([f"CAL_OP packet not recevied", "Fail"])
        Renego = self.GetPacketDetails(packet="SRQ", value="Extended Power Level Selection", limit=Flow_limit)
        if len(Renego) > 2:
            Renegoval = GeneralMethods.GetFloatFromStr(self.file_list[Renego[2]]['value'])[0]
            if Check['Renego_LoadPower'] == Renegoval:
                res.append([f"The applied Load power value in ECAP is {Renegoval}W @index {Renego[2]} and CTS is {Check['Renego_LoadPower']}W", "Pass"])
            else:
                res.append([f"The applied Load power value in ECAP is {Renegoval}W @index {Renego[2]} and CTS is {Check['Renego_LoadPower']}W", "Fail"])
        else:
            res.append([f"The ECAP packet not received to apply {Check['Renego_LoadPower']}W", "Fail"])
        pkt_exit = self.GetPacketDetails(packet="CAL_EXIT", limit=Flow_limit)
        if len(pkt_exit) > 2:
            res.append([f"Received CAL_EXIT packet at {round(pkt_exit[0], 2)} sec", "Pass"])
            if CAL_ENTER_STOP and calduration:
                if (pkt_exit[0] - CAL_ENTER_STOP) > calduration:
                    res.append([f"Calculated Calib duration is {round(pkt_exit[0] - CAL_ENTER_STOP, 2)}S, which is not in limit of {calduration}", "Fail"])
                else:
                    res.append([f"Calculated Calib duration is {round(pkt_exit[0] - CAL_ENTER_STOP, 2)}S, which is in limit of {calduration}", "Pass"])
            else:
                res.append([f"CAL_ENTER Packet or CAL duration not found", "Pass"])
        else:
            res.append([f"CAL_EXIT packet not recevied", "Fail"])
        pkt_DPM = self.GetPacketDetails(packet="DPCAL_PARAM", limit=Flow_limit)
        if len(pkt_DPM) > 2:
            alpha = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0]
            beta = GeneralMethods.GetFloatFromStr(self.file_list[pkt_DPM[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0]
            if any(r == 0 for r in [alpha, beta]):
                res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0], 2)}sec,Alpha:{alpha},Beta:{beta}", "Fail"])
            else:
                res.append([f"The DPCAL_PARAM packet received at {round(pkt_DPM[0], 2)}sec,Alpha:{alpha},Beta:{beta}", "Pass"])
        else:
            res.append([f"DPCAL_PARAM packet not recevied", "Fail"])
        if 'AddChecks' in Check:
            for addcheck in Check['AddChecks']:
                if addcheck == 'CAL_CAP_Level_counts':
                    Level = 0
                    for CALLVL in CalLevels:
                        Level += 1
                        CalLvlCnt = 0
                        id = CALLVL[0]
                        while id <= CALLVL[1]:
                            TempPkt = self.GetPacketDetails(packet="CAL_CAPTURE", limit=[id, CALLVL[1]])
                            if len(TempPkt) > 2:
                                if self.GetPacketType(id) == "Packet" if self.Mode == "TPT" else self.GetPacketType(id) == "Response":
                                    CalLvlCnt += 1
                                id = TempPkt[2] + 1
                            else:
                                break
                        reslt = self.check_measure(Check['AddChecks'][addcheck][f'Level{Level}']['expected'], CalLvlCnt, Check['AddChecks'][addcheck][f'Level{Level}']['comp'])
                        res.append([f"Received {CalLvlCnt} packets in Level{Level} in {round(self.file_list[CALLVL[0]]['startTime'], 3)}Sec-{round(self.file_list[CALLVL[1]]['stopTime'], 3)}sec, limit {reslt[2]}", reslt[1]])
                elif addcheck == 'CAL_CAP_Level_Prect':
                    Level = 0
                    for CALLVL in CalLevels:
                        Level += 1
                        CalLvlPrect = []
                        id = CALLVL[0]
                        while id <= CALLVL[1]:
                            TempPkt = self.GetPacketDetails(packet="CAL_CAPTURE", limit=[id, CALLVL[1]])
                            if len(TempPkt) > 2:
                                if self.GetPacketType(id) == "Packet" if self.Mode == "TPT" else self.GetPacketType(id) == "Response":
                                    CalLvlPrect.append(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt[2], 'PRECT')[0]['sDescription'])[0])
                                    reslt = self.check_measure(Check['AddChecks'][addcheck][f'Level{Level}']['expected'], CalLvlPrect[len(CalLvlPrect) - 1])
                                    res.append([f"Level{Level}: Received PRECT is {CalLvlPrect[len(CalLvlPrect) - 1]}W on {TempPkt[0]}sec, Limit:{reslt[2]}", reslt[1]])
                                id = TempPkt[2] + 1
                            else:
                                break
                elif addcheck == 'DiffMaxMinPRECT':
                    TempLimit = [CalLevels[0][0], CalLevels[len(CalLevels) - 1][1]]
                    id = TempLimit[0]
                    TempValList = []
                    while id <= TempLimit[1]:
                        TempPkt = self.GetPacketDetails(packet="CAL_CAPTURE", limit=[id, TempLimit[1]])
                        if len(TempPkt) > 2:
                            if self.GetPacketType(TempPkt[2]) == "Packet" if self.Mode == "TPT" else self.GetPacketType(TempPkt[2]) == "Response":
                                TempValList.append(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt[2], 'PRECT')[0]['sDescription'])[0])
                            id = TempPkt[2] + 1
                        else:
                            break
                    if len(TempValList) > 0:
                        reslt = self.check_measure(Check['AddChecks'][addcheck]['expected'], max(TempValList) - min(TempValList), Check['AddChecks'][addcheck]['comp'])
                        res.append([f"Max PRECT={max(TempValList)}W and Min PRECT={min(TempValList)}W and the Difference is {round(max(TempValList) - min(TempValList), 3)}W, Limit {reslt[2]}", reslt[1]])
                    else:
                        res.append([f"Level{Level} :No PRECT values oberved for the calculations", "FAIL"])
        # AllMeasures[CTSCheck] = res


        return res
    # def PacketCustomTimeOut(self, Flow_limit, Check):
    #     res = []
    #     Spkt = self.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=Flow_limit)
    #     if len(Spkt) > 2:
    #         Epkt = self.GetPacketDetails(packet=Check['EndPacket'][0], value=Check['EndPacket'][1], limit=[Flow_limit[0], Flow_limit[1] + 1])
    #         if len(Epkt) > 2:
    #             AllMeasures[CTSCheck] = round(Epkt[0] - Spkt[1], 2)
    #             AllMeasures[f"{CTSCheck}_remarks"] = f"The Measured timeout between {Check['StartPacket'][0]} and {Check['EndPacket'][0]} is {AllMeasures[CTSCheck]} sec."
    #         else:
    #             AllMeasures[f"{CTSCheck}_remarks"] = f"{Check['EndPacket'][0]} not found for the calculation"
    #     else:
    #         AllMeasures[f"{CTSCheck}_remarks"] = f"{Check['StartPacket'][0]} not found for the calculation"


    #     return res
    def Throttle(self, Flow_limit, Check):
        res = []
        if self.stability is not None:
            Finalres = []
            id = self.stability
            x = id
            load_reduced = False
            PLA_wo_offset = False
            res.append([f"After stabilization at {round(self.file_list[self.stability]['startTime'],2)}sec", "Pass"])
            while id < Flow_limit[1]:
                PLA = self.GetPacketDetails(packet="Power Loss Accounting", limit=[id, Flow_limit[1]])
                if len(PLA) > 2:
                    PLAOffset = self.GetPacketDetails(packet="Power Offset", limit=[PLA[2], PLA[2] - 5])
                    PLARect = self.GetPacketDetails(packet="Rectified", limit=[PLA[2], PLA[2] - 5])
                    if len(PLAOffset) > 2 and len(PLARect) > 2:
                        if not load_reduced:
                            res.append([f"TPR reported Ppr,est = Ppr - 669 mW and Prect,est =Prect – 669 mW at {round(PLAOffset[0],3)} sec", "Pass"])
                            res.append([f"Power Loss Accounting packet found at {round(PLA[0],3)} sec", "Pass"])

                            Prect = round(round(GeneralMethods.GetFloatFromStr(self.file_list[PLARect[2]]['pktType'])[1] - (Check['expected'][0]['PrectOffsetValue'] / 1000), 3) * 1000)
                            PLA_Prect = round(float(self.file_list[PLA[2]].get("value").strip("{}W")) * 1000)
                            if PLA_Prect == Prect:
                                res.append([f"The calculated Prect {Prect}mW and Received prect {PLA_Prect}mW are same for the PLA@index{PLA[2]}", "Pass"])
                            else:
                                res.append([f"The calculated Prect {Prect}mW and Received prect {PLA_Prect}mW are not same for the PLA@index{PLA[2]}", "Fail"])

                            respid = self.PktMethod.GetPacketResponse2(PLA[2], [PLA[2]+1, Flow_limit[1]])
                            if respid is not None:
                                pla_resp = self.file_list[respid].get("pktType")
                                if Check['expected'][0]["exp_resp1"] in pla_resp:
                                    res.append([f"Received {pla_resp} response for PLA packet, expected: {Check['expected'][0]['exp_resp1']}", "Pass"])
                                else:
                                    res.append([f"Received {pla_resp} response for PLA packet, expected: {Check['expected'][0]['exp_resp1']}", "Fail"])


                                # Throttle check
                                if 'NAK' in pla_resp:
                                    # print("NAK:",x)
                                    # last_NAK = x
                                    # Consecutive_NAK_cnt += 1
                                    # nak_chk = True
                                    vrect1 = self.PktMethod.CalculateVoltTwindow(PLA[2],self.AllChannelData,at="end",measure="after",winsize=[15,19])[0]
                                    irect1 = self.PktMethod.CalculateVoltTwindow(PLA[2],self.AllChannelData3,at="end",measure="after",winsize=[15,19])[0]
                                    Prect1 = vrect1*irect1

                                    vrect2 = self.PktMethod.CalculateVoltTwindow(PLA[2],self.AllChannelData,at="end",measure="after",winsize=[40,44])[0]
                                    irect2 = self.PktMethod.CalculateVoltTwindow(PLA[2],self.AllChannelData3,at="end",measure="after",winsize=[40,44])[0]
                                    Prect2 = vrect2*irect2

                                    pwr_diff = round((Prect2-Prect1)*1000,3)
                                    
                                    
                                    if pwr_diff <= 50:    #P2-P1 <= 50mW --> Throttle
                                        # last_NAK = x
                                        # throttle_cnt += 1
                                        # if throttle_cnt == 1:
                                        #     t_start = PLA[0]
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA_2 packet at {round(PLA[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA_2 packet at {round(PLA[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])



                            if Check['expected'][0].get('Prect_reduced'):
                                pred = round(GeneralMethods.GetFloatFromStr(self.file_list[PLA[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0], 3)
                                if pred < Check['expected'][0]['Prect_reduced']:
                                    res.append([f"TPR dialed down the target load to {pred} W, expected: <5w", "Pass"])
                                    load_reduced = True
                                    x = PLA[2]
                        else:
                            res.append([f"Offsets applied even after Prect is reduced below 5W", "Fail"])
                            PLA_wo_offset = False
                            break

                    else:
                        if load_reduced:
                            PLA_wo_offset = True

                    id = PLA[2] + 1
                else:
                    break
            if PLA_wo_offset:
                res.append([f"TPR continued sending PLA without the 669mW offset", "Pass"])


            if Check['expected'][0].get("removeoffset"):
                if Check['expected'][0]["removeoffset"]:
                    atn_status = False
                    while x < Flow_limit[1]:
                        PLA2 = self.GetPacketDetails(packet="Power Loss Accounting", limit=[x, Flow_limit[1]])
                        if len(PLA2) > 2:

                            respid2 = self.PktMethod.GetPacketResponse2(PLA2[2], [PLA2[2]+1, Flow_limit[1]])
                            if respid2 is not None:

                                pla_resp2 = self.file_list[respid2].get("pktType")
                                

                                if pla_resp2 == "ATN":
                                    atn_status = True
                                    res.append([f"Safe power level is reached and {pla_resp2} response received to PLA packet at {round(PLA2[0],3)}sec", "Pass"])

                                    desired_pkt=self.PktMethod.NextOcuurance("Packet",[respid2,Flow_limit[1]])
                                    if desired_pkt is not None:
                                        if "DSR" in self.file_list[desired_pkt].get("pktType") and "POLL" in self.file_list[desired_pkt].get("value"):
                                            res.append([f"Received DSR POLL for ATN packet at {round(self.file_list[desired_pkt].get('startTime'),3)}sec", "Pass"])

                                            cap_upda = self.PktMethod.GetPacketDetails(packet=Check['expected'][0]["Tcapupdate"]['packet'][0], limit=[desired_pkt, Flow_limit[1]],Type=Check['expected'][0]["Tcapupdate"]['packet'][1])
                                            if len(cap_upda) > 2:
                                                res.append([f"{Check['expected'][0]["Tcapupdate"]['packet'][0]} response found at {round(cap_upda[0],3)}sec", "Pass"])
                                                Tcapupdate = round((cap_upda[0] - self.file_list[respid2]['stopTime'])*1000,3)
                                                TcapChk = CommonMethods.check_measure(Check['expected'][0]["Tcapupdate"]['exp'], Tcapupdate, Check['expected'][0]["Tcapupdate"]['comp'])
                                                res.append([f"Measured Tcapupdate: {TcapChk[3]} ms, Expected: {TcapChk[2]} ms", TcapChk[1]])
                                            else: 
                                                res.append([f"{Check['expected'][0]["Tcapupdate"]['packet'][0]} response not found", "Fail"])
  
                                        else:
                                            res.append([f"DSR POLL not received for ATN packet at {round(self.file_list[desired_pkt].get('startTime'),3)}sec", "Fail"])

                                    break
                                else:
                                    res.append([f"{pla_resp2} response received to PLA packet at {round(PLA2[0],3)}sec", "Pass"])
                                
                        x += 1

                    if not atn_status:
                        res.append(["ATN is not received after completing the power throttling and reaching safe power level.","Fail"])

                    
                    




        return res
    def PLAOffsetCheck(self, Flow_limit, Check):
        if self.stability is not None:
            Finalres = []
            id = self.stability
            while id < Flow_limit[1]:
                PLA = self.GetPacketDetails(packet="Power Loss Accounting", limit=[id, Flow_limit[1]])
                if len(PLA) > 2:
                    PLAOffset = self.GetPacketDetails(packet="Power Offset", limit=[PLA[2], PLA[2] - 5])
                    PLARect = self.GetPacketDetails(packet="Rectified", limit=[PLA[2], PLA[2] - 5])
                    if len(PLAOffset) > 2 and len(PLARect) > 2:
                        res = []
                        Prect = round(GeneralMethods.GetFloatFromStr(self.file_list[PLARect[2]]['pktType'])[0] + (Check['PrectOffsetValue'] / 1000), 3) * 1000
                        PLA_Prect = round(GeneralMethods.GetFloatFromStr(self.file_list[PLA[2]]['header_Payload']['childelement'][2]['childelement'][0]['sDescription'])[0], 3) * 1000
                        if PLA_Prect == Prect:
                            res.append([f"The calculated Prect {Prect}mW and Received prect {PLA_Prect}mW are same for the PLA@index{PLA[2]}", "Pass"])
                        else:
                            res.append([f"The calculated Prect {Prect}mW and Received prect {PLA_Prect}mW are not same for the PLA@index{PLA[2]}", "Fail"])
                        offsetval = (round(GeneralMethods.GetFloatFromStr(self.file_list[PLAOffset[2]]['value'])[1], 3) * 1000)
                        if type(Check['RPOffsetValue']) == str:
                            if Check['RPOffsetValue'] == "PrectOffset+/-50":
                                TempLimit = [Check['PrectOffsetValue'] - 50, Check['PrectOffsetValue'] + 50] if Check['PrectOffsetValue'] < 0 else [Check['PrectOffsetValue'] + 50, Check['PrectOffsetValue'] - 50]
                                if offsetval >= TempLimit[0] and offsetval <= TempLimit[1]:
                                    res.append([f"The received offset value {offsetval}mW is in the limit of {TempLimit[0]}mW to {TempLimit[1]}mW", "Pass"])
                                else:
                                    res.append([f"The received offset value {offsetval}mW is not in the limit of {TempLimit[0]}mW to {TempLimit[1]}mW", "Fail"])
                        PLA_RP = round((GeneralMethods.GetFloatFromStr(self.file_list[PLA[2]]['header_Payload']['childelement'][1]['childelement'][0]['sDescription'])[0] * 1000), 3)
                        Rect_RP = round(GeneralMethods.GetFloatFromStr(self.file_list[PLARect[2]]['pktType'])[1], 3) * 1000
                        if PLA_RP == Rect_RP + offsetval:
                            res.append([f"The RP value:{PLA_RP}mW is same as adding offset of {offsetval}mW to the Rectified RP value {Rect_RP}mW", "Pass"])
                        else:
                            res.append([f"The RP value:{PLA_RP}mW is not same as adding offset of {offsetval}mW to the Rectified RP value {Rect_RP}mW", "Fail"])
                        if 'Fail' in [item[1] for item in res]:
                            Finalres.append([','.join([item[0] for item in res]), "Fail"])
                        else:
                            Finalres.append([','.join([item[0] for item in res]), "Pass"])
                    id = PLA[2] + 1
                else:
                    break
            # AllMeasures[CTSCheck] = Finalres


        return res
  

    def RenegoCheck1(self, Flow_limit, Check):
        res = []
        CustomLimit = self.GetLimits(Check['LimitType'], Check['LimitDetails'], Flow_limit)
        if CustomLimit is not None:
            res.append([f"Found {Check['LimitDetails']['Packet'][0]} with response {Check['LimitDetails']['Response']} @{CustomLimit[0]}", "Pass"])
            id = CustomLimit[0]
            if Check.get("pkts_chk"):
                for pkts in Check["pkts_chk"]["packet_res"]:
                    pkt = self.GetPacketDetails(packet=pkts[0], value=pkts[1], limit=[id, CustomLimit[1]])
                    if len(pkt) > 2:
                        # resp = self.file_list[pkt[2] + 1]['pktType']
                        respid = self.PktMethod.GetPacketResponse2(pkt[2], [pkt[2]+1, CustomLimit[1]])
                        if respid is not None:
                            resp = self.file_list[respid]['pktType']
                            ChkRes = CommonMethods.check_measure(pkts[2], resp, "EQL")
                            res.append([f"{pkts[0]} {f'({pkts[1]})' if pkts[1] else ''} packet is found at index@{pkt[2]} and received response is {ChkRes[3]}, Expected: {ChkRes[0]}", ChkRes[1]])
                        id = pkt[2] + 2
            if Check.get("rms_pkt"):
                rms = self.GetPacketDetails(packet=Check["rms_pkt"], limit=[id, CustomLimit[1]])
                if len(rms) > 2:
                    rms_volt = round(float(self.file_list[rms[2]]['value'].split(":")[2].split(" ")[1]) / 1000, 3)
                    ChkRes = CommonMethods.check_measure([7], rms_volt, "GTEQL")
                    res.append([f"Measured Uro is {ChkRes[3]} V, Expected: {ChkRes[2]} V", ChkRes[1]])
        return res
    def RenegoCheck(self, Flow_limit, Check):
        res = []
        CustomLimit = self.GetLimits(Check['LimitType'], Check['LimitDetails'], Flow_limit)
        if CustomLimit is not None:
            res.append([f"Found {Check['LimitDetails']['Packet'][0]} with response {Check['LimitDetails']['Response']} @{CustomLimit[0]}", "Pass"])
            Renego = self.GetPacketDetails(packet="SRQ", value="Extended Power Level Selection", limit=CustomLimit)
            if len(Renego) > 2:
                Renegoval = GeneralMethods.GetFloatFromStr(self.file_list[Renego[2]]['value'])[0]
                if Check['Power'] == Renegoval:
                    res.append([f"The applied Load power value in ECAP is {Renegoval}W @{Renego[2]} and CTS is {Check['Power']}W", "Pass"])
                    XCEIdel = self.GetPacketDetails(packet="MPP_XCEV_Ideal", limit=[Renego[2], CustomLimit[1]])
                    if len(XCEIdel) > 2:
                        CE = self.GetPacketDetails(packet="Extended Control Error", limit=[XCEIdel[2], CustomLimit[0]])
                        if len(CE) > 2:
                            reslt = self.CalculateVoltTwindow(CE[2], self.AllChannelData)
                            if reslt[0] >= Check['Power'] - (Check['Power'] * 5) / 100 and reslt[0] <= Check['Power'] + (Check['Power'] * 5) / 100:
                                res.append([f"The Mesure voltage {reslt[0]}V @{reslt[1]} is in the limit of {Check['Power'] - (Check['Power'] * 5) / 100} to {Check['Power'] + (Check['Power'] * 5) / 100}", "Pass"])
                            else:
                                res.append([f"The Mesure voltage {reslt[0]}V @{reslt[1]} is not in the limit of {Check['Power'] - (Check['Power'] * 5) / 100} to {Check['Power'] + (Check['Power'] * 5) / 100}", "Fail"])
                        else:
                            res.append("Control Error pacekt not found above the MPP_XCEV_Ideal packet", "Fail")
                    else:
                        res.append(["MPP_XCEV_Ideal packet not found after the Renego", "Fail"])
                else:
                    res.append([f"The applied Load power value in ECAP is {Renegoval}W @{Renego[2]} and CTS is {Check['Power']}W", "Fail"])
            else:
                res.append([f"The ECAP packet not received to applied {Check['Power']}W", "Fail"])
        else:
            res.append([f"Coudn't find the {Check['LimitDetails']['Packet'][0]} with response {Check['LimitDetails']['Response']} from the flow {'-'.join(map(str, Flow_limit))}", "Fail"])
        # AllMeasures[CTSCheck] = res


        return res
    # def LoadForNegoPower(self, Flow_limit, Check):
    #     res = []
    #     negoval = None
    #     TmpPkt = self.GetPacketDetails(packet=self.ECAP_pkt, limit=Flow_limit)
    #     if len(TmpPkt) > 2:
    #         res.append([f"The {self.ECAP_pkt} pacekt found at {round(TmpPkt[0], 3)}sec ", "Pass"])
    #         EcapPayload = self.GetPayloadDetails(TmpPkt[2], "Negotiable_Load_Power")
    #         if len(EcapPayload) > 0:
    #             negoval = int(GeneralMethods.GetFloatFromStr(EcapPayload[0]['sDescription'])[0])
    #             res.append([f"The Negotiable_Load_Power is {negoval}", "Pass"])
    #         else:
    #             res.append([f"Negotiable_Load_Power payload not found the for packet", "Fail"])
    #     else:
    #         res.append([f"The {self.ECAP_pkt} pacekt not found between {round(self.file_list[Flow_limit[0]]['startTime'], 3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}sec", "Fail"])
    #     if negoval is not None:
    #         TmpPkt = self.GetPacketDetails(packet="Set_Load", limit=[Flow_limit[1], Flow_limit[0]])
    #         if len(TmpPkt) > 2:
    #             load = int(GeneralMethods.GetFloatFromStr(self.file_list[TmpPkt[2]]['pktType'])[0])
    #             if Check['Type'] == 'value':
    #                 if load == Check['value']:
    #                     res.append([f"The applied load {load}mW is same as expected value of {Check['value']}", "Pass"])
    #                 else:
    #                     res.append([f"The applied load {load}mW is not same as expected value of {Check['value']}", "Fail"])
    #             elif Check['Type'] == 'Percentage':
    #                 if load == int(((negoval * 1000) * Check['value']) / 100):
    #                     res.append([f"The applied load {load}mW is same as expected value of {Check['value']}% of {negoval} i.e. {int((negoval * Check['value']) / 100)}", "Pass"])
    #                 else:
    #                     res.append([f"The applied load {load}mW is not same as expected value of {Check['value']}% of {negoval} i.e. {int((negoval * Check['value']) / 100)}", "Fail"])
    #         else:
    #             res.append([f"The Set_Load pacekt not found between {round(self.file_list[Flow_limit[0]]['startTime'], 3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}sec", "Fail"])
    #     else:
    #         res.append([f"Since the Negotiable_Load_Power not found load check not performed", "Fail"])
    #     AllMeasures[CTSCheck] = res


    #     return res
    # def RenegoPRECTInterval(self, Flow_limit, Check):
    #     res = []
    #     TempPkt1 = self.GetPacketDetails(packet=self.ECAP_pkt, limit=[Flow_limit[1], Flow_limit[0]])
    #     if len(TempPkt1) > 2:
    #         Value = round(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt1[2], 'Negotiable_Load_Power')[0]['sRawData'])[0], 3)
    #         res.append([f"ECAP packet found at {round(TempPkt1[0], 3)}sec with Negotiable_Load_Power:{Value}W", 'Pass'])
    #         id = TempPkt1[2]
    #         TempPktStatus = False
    #         while id < Flow_limit[1]:
    #             TempPkt2 = self.GetPacketDetails(packet="PLA_2", limit=[id, Flow_limit[1]])
    #             if len(TempPkt2) > 2:
    #                 if round(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt2[2], 'PRECT')[0]['sDescription'])[0], 3) >= (Value * Check['PRECTPercentage']) / 100:
    #                     TempPktStatus = True
    #                     res.append([f"The PLA packet recevied at {round(TempPkt2[0], 3)}, with PRECT value of {round(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt2[2], 'PRECT')[0]['sDescription'])[0], 3)}", "Pass"])
    #                     PTstart = self.GetPacketDetails(packet="Extended Control Error", limit=[TempPkt1[2], Flow_limit[1]])
    #                     if len(PTstart) > 2:
    #                         result = self.check_measure(Check['expected_value'], round(TempPkt2[0] - PTstart[0], 3), Check['comp'])
    #                         res.append([f"PT phase started after ECAP on {round(PTstart[0], 3)}sec and Found the PLA packet on {TempPkt2[0]}, The calculated intervel is {round(TempPkt2[0] - PTstart[0], 3)}sec, Limit:{result[2]}sec", result[1]])
    #                     break
    #                 id = TempPkt2[2] + 1
    #             else:
    #                 break
    #         if TempPktStatus == False:
    #             res.append([f"PLA packet with expected PRECT value not found", "Fail"])
    #     else:
    #         res.append([f"ECAP packet not found", 'Fail'])
    #     AllMeasures[CTSCheck] = res


    #     return res
    # def ChargeStatus(self, Flow_limit, Check):
    #     res = []
    #     InitialVal = None
    #     Value = None
    #     TempPkt1 = self.GetPacketDetails(packet="Charge Status", limit=Flow_limit)
    #     if len(TempPkt1) > 2:
    #         InitialVal = round(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt1[2], "Charger_Status_Value")[0]['sRawData'])[0], 3)
    #         res.append([f"Charge Status packet found at {round(TempPkt1[0], 3)}Sec, With Initial charge value {InitialVal}", "Pass"])
    #         id = TempPkt1[2] + 1
    #         while id < Flow_limit[1]:
    #             TempPkt2 = self.GetPacketDetails(packet="Charge Status", limit=[id, Flow_limit[1]])
    #             if len(TempPkt2) > 2:
    #                 Value = round(GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt2[2], "Charger_Status_Value")[0]['sRawData'])[0], 3)
    #                 if Value >= InitialVal + Check['ExpectedValue']:
    #                     res.append([f"Charge Status packet found at {round(TempPkt2[0], 3)}sec with charge value {Value} and reached the charge value of initial charge value + {Check['ExpectedValue']}", "Pass"])
    #                     tid = TempPkt2[2] + 1
    #                     while tid < Flow_limit[1]:
    #                         if self.GetPacketType(tid) == "Packet":
    #                             res.append([f"Found packets after reaching the charge status limit", 'Fail'])
    #                             break
    #                         tid += 1
    #                     if tid == Flow_limit[1]:
    #                         res.append([f"Test terminated after reaching the charge limit", 'Pass'])
    #                     break
    #                 id = TempPkt2[2] + 1
    #             else:
    #                 res.append([f"Last Received Charge Status packet value {Value}", 'Pass'])
    #                 break
    #         if Value is None:
    #             res.append([f"No further chanrge status packets Received after the first packet", "Fail"])
    #     else:
    #         res.append([f"Charge Status packet not found between {round(self.file_list[Flow_limit[0]]['startTime'], 3)} to {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}", "Fail"])
    #     AllMeasures[CTSCheck] = res


    #     return res
    # def Linearization(self, Flow_limit, Check):
    #     res = []
    #     TempPkt1 = self.GetPacketDetails(packet="SRQ", value="Load Power", limit=Flow_limit)
    #     if len(TempPkt1) > 2:
    #         Value = round(GeneralMethods.GetFloatFromStr((self.GetPayloadDetails(TempPkt1[2], 'Load_Power_low')[0]['sDescription']))[0], 2)
    #         res.append([f"SRQ Load Power packet found at {round(TempPkt1[0], 3)}sec with load power value {Value}W", "Pass"])
    #         TempPkt2 = self.GetPacketDetails(packet="SRQ", value="Control Error Calculation Method", limit=[TempPkt1[2] + 1, Flow_limit[1]])
    #         if len(TempPkt2) > 2:
    #             Value1 = self.GetPayloadDetails(TempPkt2[2], 'Request')[0]['sRawData']
    #             Value2 = self.GetPayloadDetails(TempPkt2[2], 'CE_Calculation_Method')[0]['sRawData']
    #             if Value1 == "0xA1" and Value2 == "0x02":
    #                 res.append([f"SRQ_Control Error Calculation Method packet found at {round(TempPkt2[2], 3)}sec, with payload value Request:{Value1} and CE_Calculation_Method:{Value2} ", "Pass"])
    #             else:
    #                 res.append([f"SRQ_Control Error Calculation Method packet found at {round(TempPkt2[2], 3)}sec, with payload value Request:{Value1} and CE_Calculation_Method:{Value2} ", "Fail"])
    #             TempPkt3 = self.GetPacketDetails(packet="SRQ", value="Control Gain", limit=[TempPkt2[2] + 1, Flow_limit[1]])
    #             if len(TempPkt3) > 2:
    #                 resp = self.GetPacketResponse(TempPkt3, [TempPkt3[2] + 1, Flow_limit[1]])
    #                 if resp is not None:
    #                     if self.file_list[resp]['pktType'] == "ACK":
    #                         res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(TempPkt3[0], 3)}sec", "Pass"])
    #                     else:
    #                         res.append([f"Received {self.file_list[resp]['pktType']} response for SRQ_Control Gain packet at {round(TempPkt3[0], 3)}sec", "Fail"])
    #                 else:
    #                     res.append([f"Response not found for SRQ_Control Gain packet at {round(TempPkt3[0], 3)}sec", "Fail"])
    #                 Value1 = GeneralMethods.GetFloatFromStr(self.GetPayloadDetails(TempPkt3[2], 'G_TARGET')[0]['sDescription'])[0]
    #                 if Value1 >= 0.1 and Value1 <= 0.9:
    #                     res.append([f"The Received G_TARGET is {Value1}, which is in limit of 0.1-0.9", "Pass"])
    #                 else:
    #                     res.append([f"The Received G_TARGET is {Value1}, which is not in limit of 0.1-0.9", "Fail"])
    #             else:
    #                 res.append([f"SRQ_Control Gain packet not found between {round(self.file_list[TempPkt2[2] + 1]['startTime'], 3)} to {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}", "Fail"])
    #         else:
    #             res.append([f"SRQ_Control Error Calculation Method packet not found between {round(self.file_list[TempPkt1[2] + 1]['startTime'], 3)} to {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}", "Fail"])
    #     else:
    #         res.append([f"SRQ Load Power packet not found between {round(self.file_list[Flow_limit[0]]['startTime'], 3)}sec to {round(self.file_list[Flow_limit[1]]['stopTime'], 3)}sec", "Fail"])
    #     AllMeasures[CTSCheck] = res


        return res
    # def KestCheck(self, Flow_limit, Check):
    #     res = []
    #     TempPkt1 = self.GetPacketDetails(packet="KEST_COEFF", limit=Flow_limit)
    #     if len(TempPkt1) > 2:
    #         P1 = self.GetPayloadDetails(TempPkt1[2], 'Parameter_1')[0]['sDescription']
    #         P2 = self.GetPayloadDetails(TempPkt1[2], 'Parameter_2')[0]['sDescription']
    #         sel = self.GetPayloadDetails(TempPkt1[2], 'Selector')[0]['sRawData']
    #         if sel == "0x00":
    #             res.append([f"The KEST_COEFF packet found at {round(TempPkt1[0], 3)}sec with Parameter1:{P1},paramter2:{P2} and Selector:{sel}", "Pass"])
    #         else:
    #             res.append([f"The KEST_COEFF packet found at {round(TempPkt1[0], 3)}sec with Parameter1:{P1},paramter2:{P2} and Selector:{sel}", "Fail"])
    #         TempPkt2 = self.GetPacketDetails(packet="Kest_First_Set_Value", limit=Flow_limit)
    #         if len(TempPkt2) > 2:
    #             Vctx = round(GeneralMethods.GetFloatFromStr(self.file_list[TempPkt2[2]]['pktType'])[0], 3)
    #             Vin = round(GeneralMethods.GetFloatFromStr(self.file_list[TempPkt2[2]]['pktType'])[1], 3)
    #             res.append([f"The Kest_First_Set_Value packet found at {round(TempPkt2[2], 3)}sec, with Vctx:{Vctx} and Vin:{Vin}", "Pass"])
    #         else:
    #             res.append([f"The KEST_COEFF packet not found", "Fail"])
    #         TempPkt3 = self.GetPacketDetails(packet="K_est Value", limit=Flow_limit)
    #         if len(TempPkt3) > 2:
    #             Kest = GeneralMethods.GetFloatFromStr(self.file_list[TempPkt3[2]]['pktType'])[0]
    #             if '.P1' in self.TestID:
    #                 Kiactual = self.BKjsonData['testBkpQiconfig']['Kest_P1_MPTPT']
    #             elif '.P2' in self.TestID:
    #                 Kiactual = self.BKjsonData['testBkpQiconfig']['Kest_P2_MPTPT']
    #             else:
    #                 Kiactual = self.BKjsonData['testBkpQiconfig']['Kest_P3_MPTPT']
    #             res.append([f"The K_est Value packet found at {round(TempPkt3[0], 3)},with Kest value :{Kest} Ki_actual from SDF :{Kiactual}", "Pass"])
    #             if (Kiactual - Kest) / Kiactual < 0.06:
    #                 res.append([f"The value of (Kiactual-Kest)/Kiactual is {round((Kiactual - Kest) / Kiactual, 3)} is < 0.06", "Pass"])
    #             else:
    #                 res.append([f"The value of (Kiactual-Kest)/Kiactual is {round((Kiactual - Kest) / Kiactual, 3)} is not < 0.06", "Fail"])
    #         else:
    #             res.append([f"The K_est Value pacekt not found", "Fail"])
    #     else:
    #         res.append([f"The Kest_First_Set_Value packet not found", "Fail"])
    #     AllMeasures[CTSCheck] = res
    

    
 
    def PLAOffsetCheck2(self, Flow_limit, Check,flow_limit=None):
        res = []
        duration_flag = False
        removepwr = False
        duration = None
        nak_chk =False
        NAK_Monitor_resp = False
        AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        if flow_limit is None:
            Flow_limit = Flow_limit
        else: Flow_limit = flow_limit
        # print("Flow_limit:",Flow_limit)

        if "after" in Check:
            TempPkt = Check['after']
        else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]

        # if TempPkt is None:
        #     if "FOD" in self.TestID:
        #         TempPkt = ["Extended Control Error","Packet"]
        #     else: TempPkt = ["MPP_XCEV_Ideal","TesterMsg"]
        # else:
        #     TempPkt = TempPkt
        #1.check for stabilizaton
        TempPkt1 = self.PktMethod.GetPacketDetails(packet=TempPkt[0],limit=Flow_limit,Type=TempPkt[1])
        if len(TempPkt1)>2:
            # if "FOD" not in self.TestID:
            #     res.append([f"Stabilization found at {round(TempPkt1[0],3)}sec","Pass"])
            res.append([f"{Check['ReceivedPower_offset']} offset applied from {TempPkt[0]} at {self.PktMethod.Timeconvert(TempPkt1[0])}","Pass"])
            packetCount = 0
            #2.Find PLA packts has power offset
            id = TempPkt1[2]
            while id < Flow_limit[1]:
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    TempPkt3 = self.PktMethod.GetPacketDetails(packet="Power Offset",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    TempPkt4 = self.PktMethod.GetPacketDetails(packet="Rectified",limit=[TempPkt2[2],TempPkt2[2]-5],Type="TesterMsg")
                    if len(TempPkt3)>2 and len(TempPkt4)>2:
                        packetCount+=1
                        Received_Power = float(self.file_list[TempPkt4[2]]['value'].split("Received:")[1].split("mW")[0].strip())
                        RP_offset = float(self.file_list[TempPkt3[2]]['value'].split("RP offset:")[1].split("W")[0].strip())*1000

                        PLA_ReceivedPower = round(float(self.PktMethod.GetPayloadDetails(TempPkt2[2],"Received_Power_Value")[0]['sDescription'].split("Estimated Received Power value:")[1].split("W")[0].strip())*1000,1)
                        # print("PLA_ReceivedPower:",PLA_ReceivedPower)

                        # print("Received_Power:",Received_Power,"RP_offset:",RP_offset)
                        if abs(Check['ReceivedPower_offset']) == RP_offset:
                            # print("same offset applied")
                            pass
                        else: res.append([f"Mismatch in offset applied: {RP_offset} mW, Expected offset: {abs(Check['ReceivedPower_offset'])}", "Fail"])

                        calculated_pwr = (Received_Power + Check['ReceivedPower_offset'])
                        if calculated_pwr > 0:
                            if PLA_ReceivedPower == calculated_pwr:
                                res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW is matching to calculated power: {calculated_pwr} mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", "Pass"])
                            else: res.append([f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {calculated_pwr} mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", "Fail"])
                        else:
                            if PLA_ReceivedPower == 0:
                                res.append([f"Received power in PLA packet: {PLA_ReceivedPower} mW and calculated power {calculated_pwr} mW is considered as 0 mW as it is < 0 mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", "Pass"])
                            else: res.append([f"Mismatch in received power in PLA packet: {PLA_ReceivedPower} mW with calculated power: {calculated_pwr} mW after applying {Check['ReceivedPower_offset']} mW offset at {round(TempPkt2[0],3)} sec", "Fail"])
                        
                        # PLA response
                        x = TempPkt2[2]+1
                        if 'TesterMsg'in self.GetPacketType(x):
                            x += 1

                        if 'Response' in self.GetPacketType(x):
                            if 'After1min_resp' in Check:
                                if (TempPkt2[0] - TempPkt1[0]) < 60:
                                    if 'exp_resp' in Check:
                                        if self.file_list[x]['pktType'] in Check["exp_resp"]:
                                            res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Pass"])
                                        else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Fail"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet at index@{x}", "Pass"])
                            else:
                                if 'exp_resp' in Check:
                                    if self.file_list[x]['pktType'] in Check["exp_resp"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Pass"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet, Expected: {Check["exp_resp"]}", "Inconclusive"])
                                else: res.append([f"{self.file_list[x]['pktType']} response received for PLA packet at index@{x}", "Pass"])

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
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                else:
                                    if pwr_diff <= 50:
                                        res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                    else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to PLA packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                            elif 'ACK' in self.file_list[x]['pktType']:
                                res.append([f"PTx not throttled while sending ACK to PLA packet at {round(TempPkt2[0],3)} sec", "Pass"])
                        
                        # if 'After1min_resp' in Check:
                        #     if (TempPkt2[0] - TempPkt1[0]) >= 60:
                        #         if Check["After1min_resp"]["resp_comp"] == "EQL":
                        #             if self.file_list[x]['pktType'] in Check["After1min_resp"]["resp_value"]:
                        #                 res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["After1min_resp"]["resp_value"]}", "Pass"])
                        #             else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: {Check["After1min_resp"]["resp_value"]}", "Fail"])
                        #         elif Check["After1min_resp"]["resp_comp"] == "NEQL":
                        #             if self.file_list[x]['pktType'] not in Check["After1min_resp"]["resp_value"]:
                        #                 res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["After1min_resp"]["resp_value"]}", "Pass"])
                        #             else: res.append([f"{self.file_list[x]['pktType']} response received for PLA_2 packet at index@{x}, Expected: not in {Check["After1min_resp"]["resp_value"]}", "Fail"])
                        
                        if 'NAK_Monitor1min' in Check:
                            if (TempPkt2[0] - TempPkt1[0]) >= 60:
                                if not nak_chk:
                                    NAK_Monitor_resp = True

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
                        res.append([f"PTx removed power at {round(sd[0],3)} sec", "Pass"])
                    else: res.append([f"PTx does not removed power", "Fail"])
                else:
                    if len(sd)> 2:
                        removepwr = True
                        res.append([f"PTx removed power at {round(sd[0],3)} sec", "Fail"])
                    else: res.append([f"PTx does not removed power", "Pass"])

            if 'NAK_Monitor1min' in Check:
                if NAK_Monitor_resp:
                    res.append([f"NAK not observed to PLA packets for 1 min after applying offset", "Fail"])

            if 'CheckDuration' in Check:
                if not removepwr:
                    if duration_flag:
                        res.append([f"TPR monitored PLA packets for at least 1 minute after stabilizing.", "Pass"])
                    else: res.append([f"TPR monitored PLA packets for only {round(duration,3)} sec after stabilizing.", "Fail"])

            if packetCount == 0: 
                res.append([f"No PLA packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
            elif not nak_chk:
                res.append([f"Received {packetCount} PLA Packets with offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
            else:res.append([f"Received {packetCount} PLA Packets with offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
        else:res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
        return res
    
    def PrectCompare(self, Flow_limit, Check):
        # Flow_limit = self.flows[flwID]['Limit']
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        self.AllChannelData3 = self.PlotMethod.GetAllChannelData('3',self.JapiData)
        Prectlist = []
        res =[]
        cnt = 1
        for ld in Check['Loads']:
            #1.Get Loads
            LoadPkt = self.PktMethod.GetPacketDetails(packet=f"Set_Load {int(ld)}",limit=Flow_limit,Type="TesterMsg")
            if len(LoadPkt)>2:
                # res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec","Pass"])
                if cnt == 2:
                    PLA_middle = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[LoadPkt[2],Flow_limit[0]])
                    if len(PLA_middle) > 2:
                        res.append([f"Power Loss Accounting packet found with start_time: {round(PLA_middle[0],3)} sec and stop_time: {round(PLA_middle[1],3)} sec", "Pass"])
                        res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec","Pass"])
                        if PLA_middle[0]<LoadPkt[0]<PLA_middle[1]:
                            res.append([f"Set Load packet for load {ld} mA recived inmiddle of Power Loss Accounting packet at {round(LoadPkt[0],3)}sec","Pass"])
                        else: res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec, not recived inmiddle of Power Loss Accounting packet","Fail"])
                    else: res.append([f"Power Loss Accounting packet not found after stabilizing the previous load.","Fail"])
                else: res.append([f"Set Load packet for load {ld} mA recived at {round(LoadPkt[0],3)}sec","Pass"])

                nxt_setload = self.PktMethod.GetPacketDetails(packet=f"Set_Load",limit=[LoadPkt[2]+1,Flow_limit[1]],Type="TesterMsg")
                if len(nxt_setload)>2:
                    search_lmt = [LoadPkt[2],nxt_setload[2]]
                else:
                    search_lmt = [LoadPkt[2],Flow_limit[1]]
                print("search_lmt:",search_lmt)

                #Get Stabilization
                StablePkt = self.PktMethod.GetexactPacketDetails(packet="MPP_XCEV_Ideal",limit=search_lmt,Type="TesterMsg")
                if len(StablePkt)>2:
                    res.append([f"Stablization found for load {ld} mA at {round(StablePkt[0],3)} sec","Pass"])
                    #Get the PLA_2
                    XCE = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[StablePkt[2],LoadPkt[2]])
                    if len(XCE)>2:
                        
                        irect = self.PktMethod.CalculateVoltTwindow(XCE[2],self.AllChannelData3)[0]
                        vrect = self.PktMethod.CalculateVoltTwindow(XCE[2],self.AllChannelData)[0]

                        Prect = round((irect*vrect),3)
                        Prectlist.append(Prect)
                        if cnt == 1:
                            ChkRes = CommonMethods.check_measure([11.88,12.12],vrect,0)
                            res.append([f"Prect{cnt} found at {round(XCE[0],3)}sec with Prect: {Prect} W, Vrect: {vrect} V, Irect: {irect} A, Expected: Vrect: {ChkRes[2]} V",ChkRes[1]])
                        else:
                            res.append([f"Prect{cnt} found at {round(XCE[0],3)}sec with Prect: {Prect} W, Vrect: {vrect} V, Irect: {irect} A","Pass"])

                        if cnt == 2:
                            # 50mA load dump
                            Loaddump = self.PktMethod.GetPacketDetails(packet=f"Set_Load {50}",limit=[StablePkt[2],Flow_limit[1]],Type="TesterMsg")
                            if len(Loaddump)>2:
                                loaddone = self.PktMethod.GetPacketDetails(packet=f"Load Set Done",limit=[Loaddump[2],Flow_limit[1]],Type="TesterMsg")
                                if len(loaddone)>2:
                                    pla = self.PktMethod.GetPacketDetails(packet=f"Power Loss Accounting",limit=[Loaddump[2],Flow_limit[0]])
                                    if len(pla)>2:
                                        res.append([f"Power Loss Accounting packet found with start_time: {round(pla[0],3)} sec and stop_time: {round(pla[1],3)} sec", "Pass"])
                                        res.append([f"Set_Load 50mA found at {round(Loaddump[0],3)} sec", "Pass"])
                                        res.append([f"Load Set Done found at {round(loaddone[0],3)} sec", "Pass"])
                                        # AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
                                        irect2 = round(self.PktMethod.CalculateVoltTwindow(loaddone[2]+1, self.AllChannelData3)[0]*1000,3)
                                        ChkRes2 = CommonMethods.check_measure([49],irect2,"GTEQL")
                                        if pla[0]<Loaddump[0]<pla[1] and pla[0]<loaddone[0]<pla[1]:
                                            res.append([f"Set_Load 50mA and Load set done are found inmiddle of Power Loss Accounting packet", "Pass"])
                                        else: res.append([f"Set_Load 50mA and Load set done are not found inmiddle of Power Loss Accounting packet", "Fail"])
                                        res.append([f"Measured Irect is {irect2} mA at {round(loaddone[0],3)} sec, Expected: 50mA", ChkRes2[1]])
                                    else: res.append([f"Power Loss Accounting not found","Fail"])
                                else: res.append([f"Load Set Done not found for 50mA","Fail"])
                            else: res.append([f"Set_Load {50} mA not found","Inconclusive"])

                    else:res.append([f"Prect{cnt}:PLA_2 packet not found after the stabilization","Fail"])
                else:res.append([f"Stablization not found for load {ld}","Fail"])
            else:res.append([f"Set Load for {ld}mA not received","Inconclusive"])
            cnt+=1

        if len(Prectlist)==2:
            if Prectlist[0]<Prectlist[1]:
                res.append([f"Prect1 : {Prectlist[0]} W, Prect2:{Prectlist[1]} W, Expected: Prect1<Prect2","Pass"])
            else:res.append([f"Prect1 : {Prectlist[0]} W, Prect2:{Prectlist[1]} W, Expected: Prect1<Prect2","Fail"])
        else:res.append([f"Not found 2 prect values for the comparison","Inconclusive"])
        return res
 
    def PLA_Throttle2(self, Flow_limit, Check):
        res = []
        duration_flag = False
        removepwr = False
        duration = None
        nak_chk =False
        AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        
        # Flow_limit = self.flows[flwID]['Limit']
        
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
                TempPkt2 = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[id,Flow_limit[1]])
                if len(TempPkt2)>2:
                    packetCount+=1
                    # PLA response
                    x = self.PktMethod.GetPacketResponse2(TempPkt2[2],[TempPkt2[2]+1,Flow_limit[1]])
                    if x is not None:
                        if 'exp_resp' in Check:
                            if 'Response' in self.PktMethod.GetPacketType(x):
                                if Check["exp_resp"]["resp_comp"] == "EQL":
                                    if self.file_list[x]['pktType'] in Check["exp_resp"]["resp_value"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for Power Loss Accounting packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", "Pass"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for Power Loss Accounting packet at index@{x}, Expected: {Check["exp_resp"]["resp_value"]}", "Fail"])
                                elif Check["exp_resp"]["resp_comp"] == "NEQL":
                                    if self.file_list[x]['pktType'] not in Check["exp_resp"]["resp_value"]:
                                        res.append([f"{self.file_list[x]['pktType']} response received for Power Loss Accounting packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", "Pass"])
                                    else: res.append([f"{self.file_list[x]['pktType']} response received for Power Loss Accounting packet at index@{x}, Expected: not in {Check["exp_resp"]["resp_value"]}", "Fail"])
                        else: res.append([f"{self.file_list[x]['pktType']} response received for Power Loss Accounting packet at index@{x}", "Pass"])

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
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                            else:
                                if pwr_diff <= 50:
                                    res.append([f"PTx throttled with power difference: {pwr_diff} mW, while sending NAK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Fail"])
                                else: res.append([f"PTx not throttled with power difference: {pwr_diff} mW, while sending NAK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec. Throttle condition: P2-P1 <= 50mW", "Pass"])
                        elif 'ACK' in self.file_list[x]['pktType']:
                            res.append([f"PTx not throttled while sending ACK to Power Loss Accounting packet at {round(TempPkt2[0],3)} sec", "Pass"])

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
                        res.append([f"PTx removed power at {round(sd[0],3)} sec", "Pass"])
                    else: res.append([f"PTx does not removed power", "Fail"])
                else:
                    if len(sd)> 2:
                        removepwr = True
                        res.append([f"PTx removed power at {round(sd[0],3)} sec", "Fail"])
                    else: res.append([f"PTx does not removed power", "Pass"])

            if 'CheckDuration' in Check:
                if not removepwr:
                    if duration_flag:
                        res.append([f"TPR monitored Power Loss Accounting packets for at least 1 minute after stabilizing.", "Pass"])
                    else: res.append([f"TPR monitored Power Loss Accounting packets for only {round(duration,3)} sec after stabilizing.", "Fail"])

            if packetCount == 0: 
                res.append([f"No Power Loss Accounting packets found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
            elif not nak_chk:
                res.append([f"Received {packetCount} Power Loss Accounting Packets with all ACK responses, without Throttling and offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
            else:res.append([f"Received {packetCount} Power Loss Accounting Packets with offset value between {round(TempPkt1[0],3)}sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}sec","Pass"])
        else: res.append([f"Stablization not found between {round(self.file_list[Flow_limit[0]]['startTime'],3)}Sec - {round(self.file_list[Flow_limit[1]]['stopTime'],3)}Sec","Fail"])
        return res


    def FSK_Tresponse(self, Flow_limit, Check):
        res = []
        id = Flow_limit[0]
        while id <= Flow_limit[1]:
            if "Get Request" in self.file_list[id]['pktType']:
                res.append([f"{self.file_list[id]['pktType']} {self.file_list[id]['value']} packet found at {round(self.file_list[id]['startTime'],3)} sec", "Pass"])
                respid = self.PktMethod.GetPacketResponse2(id, [id+1, Flow_limit[1]])
                if respid is not None:
                    res.append([f"{self.file_list[respid]['pktType']} {self.file_list[respid]['value']} response received at {round(self.file_list[respid]['startTime'],3)} sec", "Pass"])
                    tdiff = round((self.file_list[respid]['startTime'] - self.file_list[id]['stopTime'])*1000,3)
                    if 3 <= tdiff <= 10:
                        res.append([f"Measured Tresponse between {self.file_list[id]['pktType']} {self.file_list[id]['value']} and {self.file_list[respid]['pktType']} {self.file_list[respid]['value']} is {tdiff} ms, Expected: 3 to 10 ms", "Pass"])
                    else:
                        res.append([f"Measured Tresponse between {self.file_list[id]['pktType']} {self.file_list[id]['value']} and {self.file_list[respid]['pktType']} {self.file_list[respid]['value']} is {tdiff} ms, Expected: 3 to 10 ms", "Fail"])
                    id  =  respid
                else: res.append([f"No Response received for {self.file_list[id]['pktType']} {self.file_list[id]['value']} packet", "Fail"])
            id += 1 
        return res


    def T_measures(self, Flow_limit, Check):
        # Flow_limit = self.flows[flwID]['Limit']
        res = []
        for pkt in Check['expected']:
            if "PktLimit0" in pkt:
                xlimit = [0,len(self.file_list)-1]
            else: xlimit = [Flow_limit[0],len(self.file_list)-1]
            
            id = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0],value=pkt['refpkt'][2] if len(pkt['refpkt']) == 3 else None,limit=xlimit,Type=pkt['refpkt'][1])[2]

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
                    excnt = self.PktMethod.GetPacketDetails(packet="Execution_count_no",limit=[0,Flow_limit[0]-1],Type="TesterMsg")
                    limit=[excnt[2],Flow_limit[1]] if len(excnt)>2 else Flow_limit
                    print("T_measures:",limit)
                elif pkt['PktLimit'] == 'ExncntToEnd':
                    excnt = self.PktMethod.GetPacketDetails(packet="Execution_count_no",limit=[Flow_limit[1],0],Type="TesterMsg")
                    limit=[excnt[2],len(self.file_list)-2] if len(excnt)>2 else Flow_limit
                    # print("limit:",limit)
                elif pkt['PktLimit'] == "FromCustomPacket":
                    CP = self.PktMethod.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0],value=pkt['CustomLimit']['Packet'][1],limit=Flow_limit)
                    limit=[CP[2],Flow_limit[1]] if len(CP)>2 else Flow_limit
                end = limit[1]
            else: end = Flow_limit[1]
            # # print("Flow_limit:",Flow_limit)
            print("id:",id,"end:",end)
            start = 0
            # res = []
            cnt_end = pkt['cnt']
            while id < end:
                TempPkt1 =  self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0],value=pkt['packet1'][2] if len(pkt['packet1']) == 3 else None,limit=[id,end],Type=pkt['packet1'][1])
                # print("TempPkt1:",TempPkt1)
                if len(TempPkt1) > 2:
                    if TempPkt1[2]>=end: break

                    if "pkt1_resp" in pkt['packet2'][0]:
                        if pkt['packet2'][0][1] == "Response":
                            respid = self.PktMethod.GetPacketResponse2(TempPkt1[2],[TempPkt1[2]+1,end+1])
                            # print("respid:",respid)
                            if respid is not None:
                                resp = self.file_list[respid]['pktType']
                                if resp in pkt['packet2'][0][0]:
                                    TempPkt2 = [self.file_list[respid]['startTime'],self.file_list[respid]['stopTime'],respid]
                                else: TempPkt2 = []
                    else: TempPkt2 =  self.PktMethod.GetPacketDetails(packet=pkt['packet2'][0][0],value=pkt['packet2'][0][2] if len(pkt['packet2'][0]) == 3 else None,limit=[TempPkt1[2]+1,end+1],Type=pkt['packet2'][0][1])
                    # print("TempPkt2:",TempPkt2)
                    if len(TempPkt2) > 2:
                        if "skippkt" in pkt:
                            skippkt = self.PktMethod.GetPacketDetails(packet=pkt['skippkt'][0],value=pkt['skippkt'][2] if len(pkt['skippkt']) == 3 else None,limit=[TempPkt1[2],TempPkt2[2]],Type=pkt['skippkt'][1])
                            if len(skippkt)>2:
                                id = skippkt[2]+1
                                continue
                        # # print(f"{pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ""} packet found at {round(TempPkt1[0],3)} sec", "Pass")
                        # # print(f"{self.file_list[TempPkt2[2]]['pktType']} {pkt['packet2'][2] if len(pkt['packet1']) == 3 else ""} packet found at {round(TempPkt2[0],3)} sec", "Pass")
                        if "pkt1_resp" in pkt['packet2'][0]:
                            res.append([f"{pkt['packet1'][0]} packet found at {round(TempPkt1[0],3)} sec", "Pass"])
                        else: res.append([f"{pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ""} packet found at {round(TempPkt1[0],3)} sec", "Pass"])
                        res.append([f"{self.file_list[TempPkt2[2]]['pktType']} {pkt['packet2'][0][2] if len(pkt['packet2'][0]) == 3 else ""} packet found at {round(TempPkt2[0],3)} sec", "Pass"])

                        Tresult = round((TempPkt2[0]-TempPkt1[1])*1000,3)
                        # print(f"{pkt['chk']}:", round((TempPkt2[0]-TempPkt1[1])*1000,3))
                        ChkRes = CommonMethods.check_measure(pkt['exp'],Tresult,pkt['comp'])
                        # print("ChkRes:",ChkRes)

                        if 'Fail' in ChkRes[1]: res.append(ChkRes)
                        res.append([f"The Measured {pkt['chk']} between {pkt['packet1'][0]} {pkt['packet1'][2] if len(pkt['packet1']) == 3 else ""} and {pkt['packet2'][0][0]} {pkt['packet2'][0][2] if len(pkt['packet2'][0]) == 3 else ""} is: {ChkRes[3]} ms, Limit: {ChkRes[2]} ms", ChkRes[1]])

                        start += 1
                        id = TempPkt2[2]
                    elif "skippkt" not in pkt and cnt_end != "ALL":  
                        if start>=cnt_end: break
                        res.append([f"{pkt['packet2'][0][0]} packet not found", "Fail"])


                elif "skippkt" not in pkt and cnt_end != "ALL": 
                    if start>=cnt_end: break
                    res.append([f"{pkt['packet1'][0]} packet not found", "Fail"])
                id += 1
                # print("start:",start)
                if cnt_end != "ALL":
                    if start==cnt_end: break
                if id>=end: break

            if cnt_end != "ALL" and cnt_end > 1:
                if start==cnt_end:
                    res.append([f"Measured total {start} {pkt['chk']} between {pkt['packet1']} and {pkt['packet2'][0]}, Expected: {cnt_end}", "Pass"])
                else: res.append([f"Measured total {start} {pkt['chk']} between {pkt['packet1']} and {pkt['packet2'][0]}, Expected: {cnt_end}", "Fail"])
            
            # print('failures:',res)
        return res
    def T_Timeout(self, Flow_limit, Check):
        res = []
        for pkt in Check['expected']:
            header_time = 11.5#12 #ms
            ref_pkt = self.PktMethod.GetPacketDetails(packet=pkt['refpkt'][0],value=pkt['refpkt'][2] if len(pkt['refpkt']) == 3 else None,limit=Flow_limit,Type=pkt['refpkt'][1])
            if len(ref_pkt)>2:
                res.append([f"{pkt['refpkt'][0]} {pkt['refpkt'][1]} packet found at {round(ref_pkt[0],3)} sec", "Pass"])
                limit = [ref_pkt[2]+1,Flow_limit[1]+1]
                print("limit:",limit)
                TempPkt1 =  self.PktMethod.GetPacketDetails(packet=pkt['packet1'][0],value=pkt['packet1'][2] if len(pkt['packet1']) == 3 else None,limit=limit,Type=pkt['packet1'][1])
                print("TempPkt1:",TempPkt1)
                if len(TempPkt1)>2:
                    res.append([f"{pkt['packet1'][0]} {pkt['packet1'][1]} packet found at {round(TempPkt1[0],3)} sec", "Pass"])
                    TempPkt2 =  self.PktMethod.GetPacketDetails(packet=pkt['packet2'][0],value=pkt['packet2'][2] if len(pkt['packet2']) == 3 else None,limit=[TempPkt1[2]+1,limit[1]+1],Type=pkt['packet2'][1])
                    print("TempPkt2:",TempPkt2)
                    if len(TempPkt2)>2:
                        res.append([f"{pkt['packet2'][0]} {pkt['packet2'][1]} packet found at {round(TempPkt2[0],3)} sec", "Pass"])
                        Tresult = round(((TempPkt2[0]-TempPkt1[0])*1000)-header_time,3)
                        ChkRes = CommonMethods.check_measure(pkt['exp'],Tresult,pkt['comp'])
                        # if 'Fail' in ChkRes[1]: res.append(ChkRes)
                        res.append([f"The Measured {pkt['chk']} between {pkt['packet1'][0]} {pkt['packet1'][1]} and {pkt['packet2'][0]} {pkt['packet2'][1]} is: {ChkRes[3]} ms, Limit: {ChkRes[2]} ms", ChkRes[1]])
                    else: res.append([f"{pkt['packet2'][0]} packet not found", "Fail"])
                else: res.append([f"{pkt['packet1'][0]} packet not found", "Fail"])
            else: res.append([f"{pkt['refpkt'][0]} packet not found", "Fail"])
        return res         
            


    def FODTempCheck(self, Flow_limit, Check):
        # try:

        res = []
        templist = []
        # Flow_limit = self.flows[flwID]['Limit']
        self.AllChannelData12= self.PlotMethod.GetAllChannelData('12',self.JapiData)
        full_data_length = len(self.AllChannelData12['RV']['displayDataChunk'])

        self.test_halt = False

        # CHECK 1: Test has run for 30 minutes
        if not self.test_halt:
            TS = self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",limit=[0,len(self.file_list)+1],Type="TesterMsg")
            # print("TS:",TS)
            if len(TS)>2:
                # print(self.PktMethod.Timeconvert(TS[0]))
                if TS[0] > 1800:
                    res.append([f"Test has run for 30 minutes: Test_Stop is observed at {self.PktMethod.Timeconvert(TS[0])}", "Pass"])
            else: res.append([f"Test_Stop not observed", "Fail"])

        # CHECK 2: TFO exceeds the FO’s safe temperature limit.
        id = 0
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
                res.append([f"TFO exceeds the FO’s safe temperature limit: TFO: {Maxtemp} °C at {T2} sec, Maximum temperature limit of {Check['FOtempLimit'][0]}: {Check['FOtempLimit'][1]} °C", "Pass"])
                self.test_halt = True

        # CHECK 3: TFO stabilizes to ±1 °C within 5 minutes
        if not self.test_halt:
            id = 0
            t1 = self.file_list[id]['startTime'] #sec
            t2 = 300 #sec -->5min
            end = self.file_list[Flow_limit[1]]['startTime']
            
            # # print("deque:",self.check_temperature_stability_deque(t1,end,))
            while t2 <= end:
                sindex = int((t1*1000)/self.AllChannelData12['Interval'])
                eindex = int((t2*1000)/self.AllChannelData12['Interval'])
                temp1 = round(self.AllChannelData12['RV']['displayDataChunk'][sindex],3)
                # temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex],3)
                if 0 <= eindex < full_data_length:
                    temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex], 3)
                    if abs(temp2 - temp1) <= 1:
                        # print("t1:",self.PktMethod.Timeconvert(t1),"temp1:",temp1,"t2:",self.PktMethod.Timeconvert(t2),"temp2:",temp2)
                        res.append([f"TFO Stabilises to ±1 °C between {self.PktMethod.Timeconvert(t1)} with TFO: {temp1} °C and {self.PktMethod.Timeconvert(t2)} with TFO: {temp2} °C in 5 minutes period.", "Pass"])
                        self.test_halt = True
                        break
                else: break
                t1 += 1  # increase 1 sec
                t2 += 1  # increase 1 sec

        # CHECK 4: TFO < 0.8*maximum temperature after 10 minutes
        if not self.test_halt:
            id = 0
            t1 = self.file_list[id]['startTime'] #sec
            t2 = 600 #sec -->10min
            FOtemp = Check['FOtempLimit'][1]
            eindex = int((t2*1000)/self.AllChannelData12['Interval'])
            if 0 <= eindex < full_data_length:
                temp2 = round(self.AllChannelData12['RV']['displayDataChunk'][eindex],3)
                if temp2 < (0.8*FOtemp):
                    # print("TFO < 0.8*maximum temperature after 10 minutes:", temp2, "Expected:>=",0.8*FOtemp)
                    res.append([f"TFO < 0.8*maximum temperature after 10 minutes: TFO: {temp2} °C, Maximum temperature limit of {Check['FOtempLimit'][0]}: {FOtemp} °C", "Pass"])
                    self.test_halt = True

        res.append([f"Measured maximum temperature of FO is: {Maxtemp} °C, Maximum temperature limit of {Check['FOtempLimit'][0]}: {Check['FOtempLimit'][1]} °C", "Pass"])

        # print("result_res:", res)

        return res
        # except Exception as e:
        #     print(e)
    
    def EDSFlow(self,chk):
        res = []
        
        if 'PktLimit' in  chk['seq1']:
            limit = self.PktMethod.GetLimits(chk['seq1']['PktLimit'],chk['seq1'],self.flows[2]['Limit'])
        else: limit = self.flows[2]['Limit']
        # print("serieslimit:",limit)

        if 'seq_start' in chk['seq1']:
            start = self.PktMethod.GetPacketDetails(packet=chk['seq1']['seq_start'][0],value=chk['seq1']['seq_start'][1],limit=limit,Type="TesterMsg")
            if len(start) > 2:
                # print("start:",start)
                id = start[2]
            else:
                id = limit[0]
        else: id = limit[0]

        chain = self.PktMethod.GetPacketDetails(packet=chk['seq2']['endassertion'][0],value=chk['seq2']['endassertion'][1],limit=[id, limit[1]+1],Type=chk['seq2']['endassertion'][2])
        if len(chain) > 2:
            end = chain[2]
        else:
            end = limit[1]
        
        rec_size = 0
        self.nakflag = False
        self.sdsrerrflag = False
        rece_data_type = None
        sadc_close2data = []
        # main loop
        while id <= end:
            # print("LOOP START id:", id, "end:", end)
            # SEQ1 (request)
            # print("REQUESTING", chk['seq1']['action'])
            sadc_open1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[id, end],Type=chk['seq1']['packettype'][0])
            if not (len(sadc_open1) > 2):
                # no open found in [id, end] -> advance by 1 and retry
                # print("No SADC open for seq1 in range", [id, end])
                id += 1
                continue

            chkpoint = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open1[2], end],Type=chk['seq1']['packettype'][0])
            if len(chkpoint) > 2:
                if self.PktMethod.GetPayloadDetails(sadc_open1[2],chk['seq1']['action']) is None:
                    break
            else: break

            open1_idx = sadc_open1[2]
            # print("sadc_open1:", sadc_open1)
            size1 = int(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(sadc_open1[2],"parameter")[0]['sRawData'])) #bytes
            res.append([f"{chk['seq1']['action']} SADC_Open Stream with {size1} bytes is found @ {sadc_open1[2]} at {round(sadc_open1[0],3)} sec", 'Pass'])

            sadc_close1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[open1_idx, end],Type=chk['seq1']['packettype'][0])
            if not (len(sadc_close1) > 2):
                # couldn't find close for the open; move id to just after open index
                # print("No SADC close for seq1 after index", open1_idx)
                res.append([f"SADC close NOT FOUND for {chk['seq1']['action']}", 'Fail'])
                id = open1_idx + 1
                continue

            close1_idx = sadc_close1[2]
            # print("sadc_close1:", sadc_close1)

            self.respid = close1_idx
            # process certificate data between open1_idx and close1_idx
            k = open1_idx
            while k < close1_idx:
                sdsr = self.PktMethod.GetPacketDetails(packet='SDSR',limit=[k, close1_idx],Type=chk['seq1']['packettype'][1])
                if len(sdsr) > 2:
                    sadt = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sdsr[2], close1_idx],Type=chk['seq1']['packettype'][0])
                    if len(sadt) > 2:
                        # print("sadt (seq1):", sadt)
                        k = sadt[2]
                        # continue from sadt index (do not skip it unintentionally)
                k += 1
            res.append([f"{chk['seq1']['action']} SADC_Close Stream found @ {sadc_close1[2]} at {round(sadc_close1[0],3)} sec", 'Pass'])

            # ATN and DSR/POLL
            atn1 = self.PktMethod.GetPacketDetails(packet='ATN',limit=[sadc_close1[2], end],Type="Response")
            if len(atn1)>2:
                res.append([f"PTx sent ATN after {chk['seq1']['action']} at {round(atn1[0],3)} sec", 'Pass'])
                dsr = self.PktMethod.GetPacketDetails(packet='DSR',value="POLL",limit=[atn1[2], end],Type="Packet")
                if len(dsr)>2:
                    res.append([f"PRx sent DSR/POLL after {chk['seq1']['action']} at {round(dsr[0],3)} sec", 'Pass'])
                else: res.append([f"PRx not sent DSR/POLL after {chk['seq1']['action']}", 'Fail'])
            else: res.append([f"PTx not sent ATN after {chk['seq1']['action']}", 'Fail'])
            

            # ----- SEQ2 (response) -----
      
            # print("RESPONSE", chk['seq2']['action'])
            # start searching for seq2 from just after the first close
            search_start = close1_idx
            sadc_open2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[search_start, end],Type=chk['seq2']['packettype'][0])
            if not (len(sadc_open2) > 2):
                # print("No SADC open for seq2 in range", [search_start, end])
                # set id to just after close1 to avoid reprocessing same area
                id = close1_idx + 1
                continue

            open2_idx = sadc_open2[2]
            # print("sadc_open2:", sadc_open2)
            size2 = int(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(sadc_open2[2],"parameter")[0]['sRawData'])) #bytes
            res.append([f"{chk['seq2']['action']} SADC_Open Stream with {size2} bytes is found @ {sadc_open2[2]} at {round(sadc_open2[0],3)} sec", 'Pass'])

            if 'Tdts' in chk:
                if len(sadc_close2data)>2:
                    t4 = (sadc_open2[0]-sadc_close2data[0])*1000
                    chk4 = CommonMethods.check_measure([5000],t4,"LTEQL")
                    res.append([f"Tdts between PTx SADC close at {round(sadc_close2data[0],3)} sec and PTx SADC open at {round(sadc_open2[0],3)} sec is {round(chk4[3],3)} ms, Expected: {chk4[2]} ms", chk4[1]])
                sadc_close2data = []

            sadc_close2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[open2_idx, end],Type=chk['seq2']['packettype'][0])
            if not (len(sadc_close2) > 2):
                # print("No SADC close for seq2 after index", open2_idx)
                if 'errorchk' not in chk['seq2']:
                    res.append([f"SADC close NOT FOUND for {chk['seq2']['action']}", 'Fail'])
                    # move id forward to avoid endless loop
                    id = open2_idx + 1
                    continue
            
            if 'errorchk' not in chk['seq2']:
                close2_idx = sadc_close2[2]
            else: close2_idx = end
            sadc_close2data = sadc_close2
            # print("sadc_close2:", sadc_close2)

            # process certificate data between open2_idx and close2_idx
            sadt_even = []
            sadt_data = []
            sadt_retry = []
            k = open2_idx
            x = 1
            while k < close2_idx:
                self.sdsrerrflag = False
                sdsr = self.PktMethod.GetPacketDetails(packet='SDSR',limit=[k, close2_idx],Type=chk['seq2']['packettype'][1])
                # print("sdsr:",sdsr)
                if 'NAKchk' in chk['seq2']:
                    sdsrnak = self.PktMethod.GetPacketDetails(packet='SDSR',value='Type: NAK',limit=[k, close2_idx],Type=chk['seq2']['packettype'][1])
                    # print("sdsrnak:",sdsrnak)
                    if len(sdsrnak) > 2:
                        res.append([f"In {chk['seq2']['action']}, SDSR NAK is observed at {round(sdsrnak[0],3)} sec", 'Fail'])
                        self.nakflag = True
                        sdsr = sdsrnak

                if 'errorchk' in chk['seq2']:
                    sdsrerr = self.PktMethod.GetPacketDetails(packet=chk['seq2']['errorchk'][0],value=chk['seq2']['errorchk'][1],limit=[k, close2_idx],Type=chk['seq2']['errorchk'][2])
                    # print("sdsrerr:",sdsrerr)
                    if len(sdsrerr) > 2:
                        if sdsr[2] >= sdsrerr[2]:
                            res.append([f"{chk['seq2']['action']}, {chk['seq2']['errorchk'][0]}_{chk['seq2']['errorchk'][1]} is observed at {round(sdsrerr[0],3)} sec", 'Pass'])
                            self.sdsrerrflag = True
                            sdsr = sdsrerr
                    
                if len(sdsr) > 2:
                    sadt = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sdsr[2], close2_idx],Type=chk['seq2']['packettype'][0])
                    if len(sadt) > 2:
                        # print("sadt (seq2):", sadt)
                        sadt_data = sadt
                        sadt_retry.append(self.file_list[sadt[2]]['pktType'])
                        rece_data = self.file_list[sadt[2]]['pktType'].split("/")
                        rec_size = rec_size + int(rece_data[1][0])

                        if 'errorchk' in chk['seq2']:
                            if self.sdsrerrflag:
                                if sadt_retry[-2] == self.file_list[sadt[2]]['pktType']:
                                    res.append([f"PTx retried for {self.file_list[sadt[2]]['pktType']} is observed at {round(sadt[0],3)} sec", 'Pass'])
                                else: res.append([f"Observed {self.file_list[sadt[2]]['pktType']}, PTx not retried for previous SADT", 'Fail'])
                            else: res.append([f"{chk['seq2']['action']}, {self.file_list[sadt[2]]['pktType']} is observed at {round(sadt[0],3)} sec", 'Pass'])

                        rece_data_type = rece_data[1][1]
                        if 'Tdts' in chk:
                            if chk['seq2']['packettype'][0] == "Response":
                                if x == 1:
                                    if rece_data_type == 'e':
                                        sadt_even = sadt
                                        t1 = (sadt[0]-sadc_open2[0])*1000
                                        chk1 = CommonMethods.check_measure([5000],t1,"LTEQL")
                                        res.append([f"Tdts between PTx SADC open at {round(sadc_open2[0],3)} sec and PTx SADT_even at {round(sadt[0],3)} sec is {round(chk1[3],3)} ms, Expected: {chk1[2]} ms", chk1[1]])
                                        x += 1
                                if x == 2:
                                    if rece_data_type == 'o':
                                        t2 = (sadt[0]-sadt_even[0])*1000
                                        chk2 = CommonMethods.check_measure([5000],t2,"LTEQL")
                                        res.append([f"Tdts between PTx SADT_even at {round(sadt_even[0],3)} sec and PTx SADT_odd at {round(sadt[0],3)} sec is {round(chk2[3],3)} ms, Expected: {chk2[2]} ms", chk2[1]])
                                        x += 1
                        k = sadt[2]        
                k += 1

            if 'Tdts' in chk:
                if chk['seq2']['packettype'][0] == "Response":
                    if rece_data_type is not None:
                        t3 = (sadc_close2[0]-sadt_data[0])*1000
                        chk3 = CommonMethods.check_measure([5000],t3,"LTEQL")
                        res.append([f"Tdts between PTx SADT_{'even' if rece_data_type == 'e' else 'odd'} at {round(sadt_data[0],3)} and PTx SADC close at {round(sadc_close2[0],3)} sec is {round(chk3[3],3)} ms, Expected: {chk3[2]} ms", chk3[1]])
                    else: res.append([f"In {chk['seq2']['action']}, SADT data not observed", 'Fail'])

            if 'NAKchk' in chk['seq2']:
                if not self.nakflag: res.append([f"In {chk['seq2']['action']}, completely SDSR ACK is observed ", 'Pass'])

            if 'errorchk' not in chk['seq2']: 
                res.append([f"{chk['seq2']['action']} SADC_Close Stream found @ {sadc_close2[2]} at {round(sadc_close2[0],3)} sec", 'Pass'])
                # if chk['seq2'].get("Endtest") and chk['seq2']['Endtest']: 
                #     # print("Ending test")
                    # break
                    
            # After successful processing of both seq1 and seq2 streams, advance id to after seq2 close
            id = close2_idx + 1
            # print("ADVANCING id to", id, "end:", end)

        if len(chain)>2:
            res.append([f"{chk['seq2']['endassertion'][0]} {chk['seq2']['endassertion'][1]} found  @ {chain[2]} at {round(chain[0],3)} sec", 'Pass'])
        else: res.append([f"{chk['seq2']['endassertion'][0]} {chk['seq2']['endassertion'][1]} not found", 'Fail'])
        
        # print("AUTH_res:",res)
        return res

    def AuthFlow(self,chk):
        res = []

        if 'PktLimit' in  chk['seq1']:
            limit = self.PktMethod.GetLimits(chk['seq1']['PktLimit'],chk,self.flows[2]['Limit'])
        else: limit = self.flows[2]['Limit']
        # print("serieslimit:",limit)

        if 'seq_start' in chk['seq1']:
            start = self.PktMethod.GetPacketDetails(packet=chk['seq1']['seq_start'][0],value=chk['seq1']['seq_start'][1],limit=limit,Type="TesterMsg")
            if len(start) > 2:
                # print("start:",start)
                id = start[2]
            else:
                id = limit[0]
        else: id = limit[0]

        chain = self.PktMethod.GetPacketDetails(packet=chk['seq2']['endassertion'][0],value=chk['seq2']['endassertion'][1],limit=[id, limit[1]+1],Type=chk['seq2']['endassertion'][2])
        if len(chain) > 2:
            end = chain[2]
        else:
            end = limit[1]
        
        rec_size = 0
        # main loop
        while id <= end:
            # print("LOOP START id:", id, "end:", end)
            # ----- SEQ1 (request) -----
            # print("REQUESTING", chk['seq1']['action'])
            sadc_open1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[id, end],Type=chk['seq1']['packettype'][0])
            if not (len(sadc_open1) > 2):
                # no open found in [id, end] -> advance by 1 and retry
                # print("No SADC open for seq1 in range", [id, end])
                id += 1
                continue

            chkpoint = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sadc_open1[2], end],Type=chk['seq1']['packettype'][0])
            if len(chkpoint) > 2:
                if self.PktMethod.GetPayloadDetails(sadc_open1[2],chk['seq1']['action']) is None:
                    break
            else: break

            open1_idx = sadc_open1[2]
            # print("sadc_open1:", sadc_open1)
            size1 = int(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(sadc_open1[2],"parameter")[0]['sRawData'])) #bytes
            res.append([f"{chk['seq1']['action']} SADC_Open Stream with {size1} bytes is found @ {sadc_open1[2]} at {round(sadc_open1[0],3)} sec", 'Pass'])

            sadc_close1 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[open1_idx, end],Type=chk['seq1']['packettype'][0])
            if not (len(sadc_close1) > 2):
                # couldn't find close for the open; move id to just after open index
                # print("No SADC close for seq1 after index", open1_idx)
                res.append([f"SADC close NOT FOUND for {chk['seq1']['action']}", 'Fail'])
                id = open1_idx + 1
                continue

            close1_idx = sadc_close1[2]
            # print("sadc_close1:", sadc_close1)

            self.respid = close1_idx
            # process certificate data between open1_idx and close1_idx
            k = open1_idx
            while k < close1_idx:
                sdsr = self.PktMethod.GetPacketDetails(packet='SDSR',limit=[k, close1_idx],Type=chk['seq1']['packettype'][1])
                if len(sdsr) > 2:
                    sadt = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sdsr[2], close1_idx],Type=chk['seq1']['packettype'][0])
                    if len(sadt) > 2:
                        # print("sadt (seq1):", sadt)
                        k = sadt[2]
                        # continue from sadt index (do not skip it unintentionally)
                k += 1
            res.append([f"{chk['seq1']['action']} SADC_Close Stream found @ {sadc_close1[2]} at {round(sadc_close1[0],3)} sec", 'Pass'])

            # ----- SEQ2 (response) -----
            # print("RESPONSE", chk['seq2']['action'])
            # start searching for seq2 from just after the first close
            search_start = close1_idx
            sadc_open2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Open Stream:",limit=[search_start, end],Type=chk['seq2']['packettype'][0])
            if not (len(sadc_open2) > 2):
                # print("No SADC open for seq2 in range", [search_start, end])
                # set id to just after close1 to avoid reprocessing same area
                id = close1_idx + 1
                continue

            open2_idx = sadc_open2[2]
            # print("sadc_open2:", sadc_open2)
            size2 = int(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(sadc_open2[2],"parameter")[0]['sRawData'])) #bytes
            res.append([f"{chk['seq2']['action']} SADC_Open Stream with {size2} bytes is found @ {sadc_open2[2]} at {round(sadc_open2[0],3)} sec", 'Pass'])

            sadc_close2 = self.PktMethod.GetPacketDetails(packet='SADC',value="Close Stream:",limit=[open2_idx, end],Type=chk['seq2']['packettype'][0])
            if not (len(sadc_close2) > 2):
                # print("No SADC close for seq2 after index", open2_idx)
                # move id forward to avoid endless loop
                id = open2_idx + 1
                continue

            close2_idx = sadc_close2[2]
            # print("sadc_close2:", sadc_close2)

            # process certificate data between open2_idx and close2_idx
            k = open2_idx
            while k < close2_idx:
                sdsr = self.PktMethod.GetPacketDetails(packet='SDSR',limit=[k, close2_idx],Type=chk['seq2']['packettype'][1])
                if len(sdsr) > 2:
                    sadt = self.PktMethod.GetPacketDetails(packet='SADT',limit=[sdsr[2], close2_idx],Type=chk['seq2']['packettype'][0])
                    if len(sadt) > 2:
                        # print("sadt (seq2):", sadt)
                        rece_data = self.file_list[sadt[2]]['pktType'].split("/")
                        rec_size = rec_size + int(rece_data[1][0])
                        k = sadt[2]
                k += 1
            res.append([f"{chk['seq2']['action']} SADC_Close Stream found @ {sadc_close2[2]} at {round(sadc_close2[0],3)} sec", 'Pass'])

            
            # After successful processing of both seq1 and seq2 streams, advance id to after seq2 close
            id = close2_idx + 1
            # print("ADVANCING id to", id, "end:", end)

            # Response time chk
            if 'resptime' in chk['seq1']:
                atn = self.PktMethod.GetPacketDetails(packet='ATN',limit=[sadc_close1[2], sadc_open2[2]],Type="Response")
                if len(atn)>2:
                    t = round((atn[0] - sadc_close1[1])*1000,3) #sec
                    if t <= 3000:
                        res.append([f"Measured {chk['seq1']['resptime']} is {t} ms, Expected: <= 3000 ms", "Pass"])
                    else: res.append([f"Measured {chk['seq1']['resptime']} is {t} ms, Expected: <= 3000 ms", "Fail"])
                else: res.append([f"PTx didn't sent ATN response", "Fail"])
               

        if 'expBytes' in chk['seq2']:
            if 'certbytes' in chk['seq2']['expBytes'][0]:
                ChkRes = CommonMethods.check_measure(chk['seq2']['expBytes'][1],rec_size,chk['seq2']['expBytes'][2])
                # if chk['seq2']['expBytes'][1] == rec_size:
                res.append([f"Total {rec_size} bytes of data received for {chk['seq2']['action']} in SADT packets, Expected: {ChkRes[2]} bytes", ChkRes[1]])
                # else: res.append([f"Total {rec_size} bytes of data received for {chk['seq2']['action']} in SADT packets, Expected: {chk['seq2']['expBytes'][1]} bytes", 'Fail'])
            
            elif 'Slots_Returned_Mask' in chk['seq2']['expBytes'][0]:
                sadt1 = self.PktMethod.GetPacketDetails(packet='SADT',limit=[open2_idx, close2_idx],Type=chk['seq2']['packettype'][0])
                if len(sadt1)>2:
                    val = float(self.PktMethod.GetPayloadDetails(sadt1[2],"Slots_Returned_Mask")[0]['sDescription'].split(":")[1].strip())
                    res.append([f"Slot Returned Mask value is {val} in {chk['seq2']['action']}","Pass"])
                    exp = (val*32)+2
                    if exp == rec_size:
                        res.append([f"Number of bytes in Digests response is {rec_size} matching with (Slot Returned Mask*32)+2: {exp}", "Pass"])
                    else: res.append([f"Number of bytes in Digests response is {rec_size} not matching with (Slot Returned Mask*32)+2: {exp}", "Fail"])
                else: res.append([f"Digests response is not found","Fail"])
        else:
            res.append([f"Total {rec_size} bytes of data received for {chk['seq2']['action']} in SADT packets", 'Pass'])
        if len(chain)>2:
            res.append([f"{chk['seq2']['endassertion'][0]} {chk['seq2']['endassertion'][1]} found  @ {chain[2]} at {round(chain[0],3)} sec", 'Pass'])
        else: res.append([f"{chk['seq2']['endassertion'][0]} {chk['seq2']['endassertion'][1]} not found", 'Fail'])
        

        # print("AUTH_res:",res)
        return res


    def AuthSeq(self,index,Authvalue1='Challenge',Payload1=[],Authvalue2='Challenge Auth',Payload2=[]):
        id=index
        seq=False
        results=[]
        ADC_Auth=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth" ,limit=[id,self.Flow_limit[1]])
        if len(ADC_Auth)>2:
            # find Get Certificate
            ADT=self.PktMethod.GetPacketDetails(packet="ADT",value=Authvalue1, limit=[ADC_Auth[2]+1,self.Flow_limit[1]])
            if len(ADT)>2:
                res=self.Payload_Details(PacketName=Authvalue1,Index=ADT[2],PayLoads=Payload1)
                if len(res)>0:results.extend(res)
                ADC_End=self.PktMethod.GetPacketDetails(packet="ADC",value="End" ,limit=[id,self.Flow_limit[1]])
                if len(ADC_End)>2:
                    # Authentication response
                    ADCAuth_TPT=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth" ,Type="Response",limit=[ADC_End[2]+1,self.Flow_limit[1]])
                    if len(ADCAuth_TPT)>2:
                        # find Get Certificate
                        ADT_TPT=self.PktMethod.GetPacketDetails(packet="ADT",value=Authvalue2, Type="Response",limit=[ADCAuth_TPT[2]+1,self.Flow_limit[1]])
                        res=self.Payload_Details(PacketName=Authvalue2,Index=ADT_TPT[2],PayLoads=Payload2,Receiver=False)
                        if len(res)>0:results.extend(res)
                        ADC_End_TPT=self.PktMethod.GetPacketDetails(packet="ADC",value="End",Type="Response",limit=[ADCAuth_TPT[2]+1,self.Flow_limit[1]])
                        if len(ADC_End_TPT)>2:
                            id=ADC_End_TPT[2]+1
                            seq=True
                            results.append([f'PRx & PTx Sucessfully completed Authentication- {Authvalue1} Chain Sequence from id:{ADC_Auth[2]} to id :{ADC_End_TPT[2]}', 'Pass'])
                        else:results.append([f'PTx did not Closed {Authvalue2} Authentication Sequence', 'Inconclusive'])                                                        
                    else:results.append([f'PTx did not Initiated {Authvalue2} Authentication Sequence', 'Inconclusive'])
                else:results.append([f'Prx did not Closed Authentication Sequence', 'Inconclusive'])
            else:results.append([f'Prx did not sent {Authvalue1}', 'Inconclusive'])
        else:results.append([f'Prx did not Initiated Authentication:{Authvalue1} Sequence', 'Inconclusive'])
        return results,id,seq

###API Functions #########################################################################################################################
    def GetAllChannelData(self,index='2'):
        try:
            ACD={}
            TestTime = self.GetRunTime()
            if TestTime[1]/60 >15:
                # # print(TestTime[1]/60)
                plottime = int(((TestTime[1]*1000)/2.5)-80)
            else:
                plottime = int(((TestTime[1]*1000)/1.0510)-80)
            # # print(plottime)
            SignalAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['GetAllChannelData'],retype='json',param1=TestTime[1],param2=plottime)
            data = SignalAPI.GetRequest()
            if index in data:
                ACD['RV']=data[index]
                ACD['starttime'] = data[index]['absoluteStartTime']
                ACD['endtime'] = data[index]['absoluteEndTime']
                ACD['records'] = len(data[index]['displayDataChunk'])
                ACD['Diff'] =  ((ACD['endtime']-ACD['starttime'])/100000)
                ACD['Interval'] = (ACD['Diff']/ACD['records'])
            return ACD
        except Exception as e:
            print(e)
###Support Functions ####################################################################################################################
    #-Get Run time of the testcase, returns start time and end in nanoseconds,
    def GetRunTime(self):
        TcStartAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['GetWaveformStartTime'],retype='json')
        TCstartTime = TcStartAPI.GetRequest()
        TcStopAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['GetWaveformStopTime'],retype='json')
        TCstopTime = TcStopAPI.GetRequest()
        return[TCstartTime,TCstopTime/100000000]
    #-Create log releated to a testcase validation steps. update same into debug logfile
    def update_TClogs(self,logtype,log):
        # print(log)
        dt_object = datetime.fromtimestamp(datetime.now().timestamp())
        self.TClogs.append([str(dt_object),logtype,log])
    #- To search a given packet in the given limit, if packet found return the packet details  [starttime,endtime,index]
    def GetPacketDetails(self,packet='',value=None,limit=[],timelimit=None):
        # # print(limit,packet)
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                # # print(id,self.file_list[id].get('pktType'))
                if packet in self.file_list[id].get('pktType') and value in self.file_list[id].get('value') if value is not None else packet in self.file_list[id].get('pktType'):
                    if timelimit is None:
                        return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                    else:
                        if self.file_list[id].get('startTime') >= timelimit:
                            return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        else:
            while id != limit[1]:
                if all(rs in self.file_list[id].get('pktType') for rs in packet) and value in self.file_list[id].get('value') if value is not None else packet in self.file_list[id].get('pktType'):
                    return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        return[0]
    # AUTH messages payload details
    def GetAuthPayloadDetails(self,index,name,Byte,Bit):
        result = []
        for bits in self.Auth_file_list[index]['header_Payload']['childelement']:
            for payload in bits['childelement']:
                if payload['sDecodedValue'] == name or payload['sDescription'] == name:
                    result.append(payload)
                    return result
                for Authpayloads in payload['childelement']:
                    if Authpayloads.get('sFieldType')==Byte:
                        for payloads in Authpayloads['childelement']:
                            if payloads.get('sBitIndex') == Bit and payloads['sDecodedValue'] == name or payloads['sDescription'] == name:
                                result.append(payloads)
        return result
    def PayloadDetails_Auth(self,index,name):
        try:
            result = []
            for bits in self.Auth_file_list[index]['header_Payload']['childelement']:
                for payload in bits['childelement']:
                    if payload['sDecodedValue'] ==name or payload['sDescription'] ==name:
                        result.append(payload)
                        return result
                    for Authpayloads in payload['childelement']:
                        for payloads in Authpayloads['childelement']:
                            if  payloads['sDecodedValue'] == name   or  payloads['sDescription'] ==name:
                                result.append(payloads)
                                
            return result if len(result)>0 else None
        except Exception as e: return None
    def GetAuthPacketDetails(self,packet='',value=None,limit=[],timelimit=None,Type="Packet"):
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                # # print(id,self.file_list[id].get('pktType'))
                if packet == self.Auth_file_list[id].get('pktType') and value in self.Auth_file_list[id].get('value') if value is not None else packet == self.Auth_file_list[id].get('pktType'):
                    # print(id,self.Auth_file_list[id].get('pktType'))
                    if self.GetAuthPacketType(id)==Type:
                        if timelimit is None:
                            return[self.Auth_file_list[id].get('startTime'),self.Auth_file_list[id].get('stopTime'),id]
                        else:
                            if self.Auth_file_list[id].get('startTime') >= timelimit:
                                return[self.Auth_file_list[id].get('startTime'),self.Auth_file_list[id].get('stopTime'),id]
                            
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        else:
            while id != limit[1]:
                if all(rs in self.Auth_file_list[id].get('pktType') for rs in packet) and value in self.Auth_file_list[id].get('value') if value is not None else packet in self.Auth_file_list[id].get('pktType'):
                    return[self.Auth_file_list[id].get('startTime'),self.Auth_file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        return[0]
    def GetAuthPacketType(self,id):
        if self.Product == "C3":
            if self.Mode == 'TPT':
                if self.Auth_file_list[id]['isTesterPkt']==False and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
            elif self.Mode =="TPR":
                if self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.Auth_file_list[id]['isTesterPkt']==False and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
        elif self.Product == "MPP":
            if self.Mode=="TPR":
                if self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.Auth_file_list[id]['isTesterPkt']==False and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
            elif self.Mode=="TPT":
                if self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.Auth_file_list[id]['isTesterPkt']==False and self.Auth_file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.Auth_file_list[id]['isTesterPkt']==True and self.Auth_file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
        return None
    
    def TestResults(self):
        # print("TestResults",self.TestCaseName)
        jsondata = JsonOperations(self.ProjectJson)
        self.jsonValues = jsondata.read_file()
        data = self.jsonValues['TestingScope']

        for item in data:
            if item["TestName"] == self.TestCaseName.split(" ")[1]:
                return item["Measurements"]                      
        return None
   
    def Measurements(self,measurements,M_name):
        if measurements is not None:
            for measure in measurements:
                # if measure['MeasurementName'] == M_name:
                if measure['MeasurementName'] in M_name:
                    if measure['Prefix'] == "None" and measure['BaseUnit'] == "None":
                        return [measure['Value'],""]
                    else: return [measure['Value'],"".join([measure['Prefix'] if measure['Prefix'] is not None else "",measure['BaseUnit'] if measure['BaseUnit'] is not None else ""])]
       
        return None
    
    def AUTHBitsCheck_New(self,Flow_limit,Check):
        SubChecks=[]
        expvalues=[]
        BitsCompare = {}
        
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
            # print('bitsLimit',limit)
            tmpID = limit[0]
            while tmpID <= limit[1]:
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
                        SubChecks.append([f"The expected packet {self.file_list[pktres[2]]['pktType']}_{self.file_list[pktres[2]]['value']} found at {round(pktres[0],3)}sec","Pass"]) # SubChecks.append([f"The expected packet {'_'.join(ExpPacket)} found at {round(pktres[0],3)}sec","Pass"])
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
                                            SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as expected value of {BITSck['Checks'][ck]['expected']}","Pass"])
                                        elif 'random' in BITSck['Checks'][ck]['expected']:
                                            if BITSck['Checks'][ck].get('except'):
                                                if pyload[BITSck['Checks'][ck]['flag']] not in BITSck['Checks'][ck]['except']:
                                                    SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}","Pass"])
                                                else: SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}","Fail"])
                                            else: SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random value","Pass"])
                                        else:SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} is not expected value of {BITSck['Checks'][ck]['expected']}","Fail"])
                                    elif BITSck['Checks'][ck]['comp']=="str_Reverse":
                                        if BITSck['Checks'][ck]['expected'] in pyload[BITSck['Checks'][ck]['flag']]:
                                            SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as expected value of {BITSck['Checks'][ck]['expected']}","Fail"])
                                        else:SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} is not expected value of {BITSck['Checks'][ck]['expected']}","Pass"])
                                    elif BITSck['Checks'][ck]['comp']=="btw":
                                        # # print(int(pyload[BITSck['Checks'][ck]['flag']]),BITSck['Checks'][ck]['expected'])
                                        if int(pyload[BITSck['Checks'][ck]['flag']]) >= BITSck['Checks'][ck]['expected'][0] and int(pyload[BITSck['Checks'][ck]['flag']]) <= BITSck['Checks'][ck]['expected'][1]:
                                            SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as expected value in limit of  {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}","Pass"])
                                        else:SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]} as not expected value in limit of  {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}","Fail"])
                                    elif BITSck['Checks'][ck]['comp']=="Present":
                                        SubChecks.append([f"The Recevied {ck} is {pyload[BITSck['Checks'][ck]['flag']]}","Pass"])
                                    else:
                                        if ':' in pyload[BITSck['Checks'][ck]['flag']]:
                                            pyaloadli = pyload[BITSck['Checks'][ck]['flag']].split(':')
                                            # print("pyaloadli:",pyaloadli)
                                            payloadActual = '_'.join(pyaloadli[1:])
                                        else:payloadActual=pyload[BITSck['Checks'][ck]['flag']]
                                        revdval = GeneralMethods.GetFloatFromStr(payloadActual)
                                        # print("revdval:",revdval)
                                        if BITSck['Checks'][ck]['comp'] == 'GTEQL':
                                            if  revdval[0] >= BITSck['Checks'][ck]['expected']:
                                                SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}, which is >= {BITSck['Checks'][ck]['expected']}","Pass"])
                                            else:SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}, which is not >= {BITSck['Checks'][ck]['expected']}","Fail"])
                                        elif BITSck['Checks'][ck]['comp'] == 'LTEQL':
                                            if  revdval[0] <= BITSck['Checks'][ck]['expected']:
                                                SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}, which is <= {BITSck['Checks'][ck]['expected']}","Pass"])
                                            else:SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}, which is not <= {BITSck['Checks'][ck]['expected']}","Fail"])
                                        elif BITSck['Checks'][ck]['comp'] == 'EQL':
                                            if 'comp1' == BITSck['Checks'][ck]['expected'] or 'comp2' == BITSck['Checks'][ck]['expected']:
                                                BitsCompare[BITSck['Checks'][ck]['expected']] = [ck,revdval[0]]
                                                SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}","Pass"])
                                            else:
                                                if  revdval[0] == float(BITSck['Checks'][ck]['expected']):
                                                    SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}, which is == {BITSck['Checks'][ck]['expected']}","Pass"])
                                                else:SubChecks.append([f"The Recevied value of {ck} is {revdval[0]}, which is not == {BITSck['Checks'][ck]['expected']}","Fail"])
                            else:SubChecks.append([f"The payload {ck} for packet {'_'.join(ExpPacket)} not found for the packet {'_'.join(ExpPacket)}","Fail"])
                    if 'PacketCount' not in BITSck:
                        break
                    if 'PacketCount' in BITSck:
                        if BITSck['PacketCount'] == "ALL":
                            pass
                        else:
                            if BITSck['PacketCount']==PktCount:
                                break
                    tmpID = pktres[2]+1
                else:
                    if 'PacketCount' in BITSck:
                        if BITSck['PacketCount'] == "ALL":
                            SubChecks.append([f"Received {PktCount} {'_'.join(ExpPacket)} packets","Pass"])
                        else:
                            if PktCount < BITSck['PacketCount']:
                                SubChecks.append([f"Out of {BITSck['PacketCount']} Received only {PktCount} {'_'.join(ExpPacket)} packets","Fail"])
                    else:
                        if PktCount==0:
                            SubChecks.append([f"The expected packet {'_'.join(ExpPacket)} not found between {round(self.file_list[limit[0]]['startTime'],3)}sec to {round(self.file_list[limit[1]]['stopTime'],3)}sec ","Fail"])
                    break
            expvalues.append(expvalue)

            if len(BitsCompare)>0:
                if BitsCompare['comp1'][1] == BitsCompare['comp2'][1]:
                    SubChecks.append([f"{BitsCompare['comp1'][0]}: {BitsCompare['comp1'][1]} is equal to {BitsCompare['comp2'][0]}: {BitsCompare['comp2'][1]}","Pass"])
                else: SubChecks.append([f"{BitsCompare['comp1'][0]}: {BitsCompare['comp1'][1]} is not equal to {BitsCompare['comp2'][0]}: {BitsCompare['comp2'][1]}","Fail"])

        # AllMeasures['BitsCheck_exp'] = ';'.join(expvalues)
        # AllMeasures['BitsCheck'] = 'Found Issues' if any(res[1]=="Fail" for res in SubChecks) else 'No Issues'
        # AllMeasures['BitsCheck_res'] = 'Fail' if any(res[1]=="Fail" for res in SubChecks) else 'Pass'
        # AllMeasures['BitsCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
        # AllMeasures['BitsCheck_Details']=SubChecks
        # print("SubChecks:",SubChecks)
        return SubChecks

    # - Get packet Type, testermsg/packet/response
    def GetPacketType(self,id):
        if self.Product == "C3":
            if self.Mode == 'TPT':
                if self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
            elif self.Mode =="TPR":
                if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
        elif self.Product == "MPP":
            if self.Mode=="TPR":
                if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
            elif self.Mode=="TPT":
                if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
        return None
    
    #-fetch c3testcase checks results
    def GetC3TCchecks(self):
        try:
            TCpath = self.TracePath
            #clear temp
            temppath = os.listdir('temp')
            for file in temppath: os.remove(os.path.join('temp',file))
            with zipfile.ZipFile(TCpath, 'r') as zip_ref:
                for files in zip_ref.infolist():
                    if not files.is_dir():
                        if 'TD_' in files.filename:
                            zip_ref.extract(files.filename,"temp")
                            dataobj = JsonOperations(os.path.join("temp",files.filename))
                            data = dataobj.read_file()
                            return data[0]['m_TestResults']['TestList']
            return {}
        except Exception as e:
            traceback.print_exc()
    #- Get software side high level results
    def GetJSONTCData(self,TestID,BackupJson,retunData):
        try:
            BKjson = JsonOperations(BackupJson)
            BKjsonData = BKjson.read_file()
            for TCdata in BKjsonData['testBkpTestResultsandPath']:
                if TCdata is not None:
                    if TCdata['testcaseDetails']['m_TestId'] == TestID:
                        if retunData == "TCresult":
                            return TCdata['testinformation']['TestResult']
                        elif retunData == "TCcoil":
                            return TCdata['testinformation']['TesterConfiguration']['CoilUsed']
            return 'NA'
        except Exception as e:
            print(e)
    #- Run time of the testcase 
    def UpdateTestRunTimings(self,TCname,JSONvalues):
        try:
            for TCdata in JSONvalues['TestingScope']:
                if TCdata is not None:
                    if TCdata['TestName'] == TCname:
                        self.Header['TestedTime_start']= TCdata['TestStartTime']
                        self.Header['TestedTime_end']= TCdata['TestEndTime']
                        stime = [int(num) for num in self.Header['TestedTime_start'].split('T')[1].split('+')[0].replace('.',':').split(':')]
                        etime = [int(num) for num in self.Header['TestedTime_end'].split('T')[1].split('+')[0].replace('.',':').split(':')]
                        st = (((stime[0]*1000)*60)*60)+((stime[1]*1000)*60)+(stime[2]*1000)+stime[3]
                        et = (((etime[0]*1000)*60)*60)+((etime[1]*1000)*60)+(etime[2]*1000)+etime[3]
                        self.Header['TestedTime'] =abs(st-et)
                        break
        except Exception as e:
            traceback.print_exc()
    #- General method to retun values from backupjson file for a testcase.
    def GetTCValuesfromBackUpJSON(self,KeyToFind="_testID"):
        BKjson = JsonOperations(self.BackupJson)
        self.BKjsonData = BKjson.read_file()
        for TCdata in self.BKjsonData['testBkpTestResultsandPath']:
            if TCdata['testcaseDetails']['m_DisplayName'] == self.TestCaseName:
                res = self.GetValuefromKey(TCdata,KeyToFind)
                return res
    #Get value from matching key of dict
    def GetValuefromKey(self,TCdata,KeyToFind):
        for key, value in TCdata.items():
            if key == KeyToFind:
                return value
            elif isinstance(value, dict):
                # Recursively search in nested dictionaries
                result = self.GetValuefromKey(value, KeyToFind)
                if result is not None:
                    return result
        return None  
    # #- Idetify flow for MPP
    # def Findflow(self,limit):
    #     id = limit[0]
    #     index = 1
    #     while id<limit[1]:
    #         if 'Identification' in self.file_list[id].get('pktType'):
    #             index=1
    #         if 'Specific Request' in self.file_list[id].get('pktType') and 'Frequency Selection: 360 Khz' in self.file_list[id].get('value'):
    #             index = 1
    #             break
    #         if 'Extended_Power_Receiver_Capabilities' in self.file_list[id].get('pktType'):
    #             index = 2
    #             break
    #         elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' in self.file_list[id].get('value'):
    #             index = 1
    #             break
    #         elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' not in self.file_list[id].get('value'):
    #             index = 2
    #             break
    #         elif 'FOP:' in  self.file_list[id].get('value'):
    #             if float(self.file_list[id].get('value').split(':')[1].split(' ')[0]) >300:
    #                 index =2
    #                 break
    #             else:
    #                 index=1
    #                 break
    #         elif '128' in self.file_list[id].get('value'):
    #             index = 1
    #             break
    #         elif '360' in self.file_list[id].get('value'):
    #             index = 2
    #             break
    #         id+=1
    #     return index
    #- Find the Testcase index in group TC mode
    def GetTCindexfromGroupRun(self):
        JBkup = JsonOperations(self.BackupJson)
        JBkupData =JBkup.read_file()
        TClist = []
        for TCdata in JBkupData["testBkpTestResultsandPath"]:
            if self.TestID == TCdata['testcaseDetails']['m_TestId']:
                #Get same tracepath tc's 
                for TmpTcdata in JBkupData["testBkpTestResultsandPath"]:
                    if TCdata['actualTracePath'] == TmpTcdata['actualTracePath']:
                        TClist.append(TmpTcdata['testcaseDetails']['m_TestId'])
        # # print(TClist)
        if len(TClist)>0:
            # # print(TClist.index(self.TestID))
            return TClist.index(self.TestID)
        return 0
    #Functions related to the CTS checks
    #1. Get Stabilizied index and value
    def GetInitailVoltage(self,index,start=None,end=None):
        self.AllChannelData3 = self.PlotMethod.GetAllChannelData('3',self.JapiData)
        # if str(index) in self.Json_TC['other_checks_details']:
            # if 'CEStability' in self.Json_TC['other_checks_details'][str(index)]:
        try:
            # limit=[self.timing_map[index]['General']['PD'][0][0][0],self.timing_map[index]['General']['SD'][0][0][0]]
            # print("GetInitailVoltage:")
            if self.flows[index] is not None:
                limit = self.flows[index]['Limit']
                self.stability = None
                # print("limit:",limit)
                

                start1 = limit[0]
                end1 = limit[1]
                if start != None:
                    start1 = start
                if end != None:
                    end1 = end

                # print("start:",start1)
                # print("end:",end1)
                
                # if start == None:
                #     id = limit[0]
                # else: id = start

                id = start1
                end = end1

                print("id:",id)
                print("end:",end)

                while id < end:
                    if 'MPP_XCEV_Ideal' in self.file_list[id].get('pktType'):
                        loadsetdone = False
                        # print(id)
                        self.XCEV_Ideal = id
                        revid = id
                        while revid > start1:
                            if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                                self.stability=revid
                                # GetIntital Voltage
                                
                                # res = self.CalculateVoltTwindow(revid,self.AllChannelData)
                                voltage = self.PktMethod.CalculateVoltTwindow(revid,self.AllChannelData)
                                current = self.PktMethod.CalculateVoltTwindow(revid,self.AllChannelData3)
                                self.initialVolt =  voltage[0]
                                self.initialCurrent = current[0]

                                # # print('stability',self.stability,self.initialVolt)
                                break
                            revid-=1
                        break
                    id+=1
        except Exception as e:
            traceback.print_exc()
    #2. calculate vrect min /max for all XCE twin time
    def CalculateVoltTwindow(self,indx,AllChannelData,winsize=[5,8],at='start',measure='before',max = False): #[8,11]
        if at == "start":
            xceEtime = self.file_list[indx].get('startTime')*1000
        elif at == 'end':
            xceEtime = self.file_list[indx].get('stopTime')*1000
        if measure == 'before':
            xceSindex = int((xceEtime-(winsize[1]))/AllChannelData['Interval'])
            xceEindex = int((xceEtime-winsize[0])/AllChannelData['Interval'])
            # # print("xceStime:",xceEtime-winsize[1],"xceEtime:",xceEtime-winsize[0])
        elif measure == 'after':
            xceSindex = int((xceEtime+(winsize[0]))/AllChannelData['Interval'])
            xceEindex = int((xceEtime+winsize[1])/AllChannelData['Interval'])
            # # print("xceStime:",xceEtime+winsize[0],"xceEtime:",xceEtime+winsize[1])
        
        id = xceSindex
        VRlist=[]
        Vrectmax = 0
        max = max
        while id <= xceEindex:
            VRlist.append(abs(AllChannelData['RV']['displayDataChunk'][id]))
            # # print("voltages:",abs(AllChannelData['RV']['displayDataChunk'][id]))
            if max:
                if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) > Vrectmax or Vrectmax==0: 
                    Vrectmax = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
                    # print("Vrectmax:",Vrectmax)
            id+=1
        # # print("Vrectmax:",Vrectmax)
        # # print(VRlist)
        return [Vrectmax] if max else [round((sum(VRlist)/len(VRlist)),5), id-1]
    

    #3. Find that the measured CTS checks are in limit or not
    def check_measure(self,exp_val,obsr_val,comp=0):
        res = None
        compval=0
        exp_vals=[]
        if obsr_val != None:
            if len(exp_val)==1:
                exp_vals.append(exp_val[0])
                if comp =='GTEQL':
                    if  obsr_val >= exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'>={exp_val[0]}'
                elif comp =='LTEQL':
                    if  obsr_val <= exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'<={exp_val[0]}'
                elif comp =='EQL':
                    if  obsr_val == exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'=={exp_val[0]}'
                #add for rql,lseql
            else:
                exp_vals=exp_val
                compval=','.join(map(str,exp_vals))
                if obsr_val >= exp_vals[0] and obsr_val <= exp_vals[1]:
                    res =  'Pass'
                else:  
                    res = 'Fail'
        else:
            res = 'Fail'
        return [exp_vals,res,compval]
    #4. Find the XCE stable between the limits
    def GetStableBtwLimits(self,limit):
        id = limit[0]
        XCEcount = 0
        while id < limit[1]:
            if any(rs in self.file_list[id].get('pktType') for rs in ['Extended Control Error','Control Error']): XCEcount +=1
            if 'MPP_XCEV_Ideal' in self.file_list[id].get('pktType'):
                revid = id
                while revid > limit[0]:
                    
                    if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                        # res = self.CalculateVoltTwindow(revid,self.AllChannelData)
                        return [revid,XCEcount]
                    revid-=1
            id+=1
        return None
  
    # #6. BitsCheck
    # def BitsCheck(self,Flow_limit,flwID,Check,AllMeasures):
    #     try:
    #         reslt = []
    #         resvalue =[]
    #         expvalue = []
    #         for BITSck in Check['ChecksList']:
    #             # # print(BITSck)
    #             if BITSck['refPrevious']  == True:
    #                 limit = [0,Flow_limit[0]-1]
    #             else:
    #                 limit = Flow_limit
    #             #find the packet to check bits
    #             id = limit[0]
    #             pktindex = 0
    #             while id < limit[1]:
    #                 # if self.file_list[id]['isFWTestermessage'] != True and self.file_list[id]['isTesterPkt'] != True:
    #                 if BITSck['packet'][1] is None:
    #                     if BITSck['packet'][0] in self.file_list[id].get('pktType'):
    #                         pktindex = id
    #                         break
    #                 else:
    #                     if BITSck['packet'][0] in self.file_list[id].get('pktType') and BITSck['packet'][1] in self.file_list[id].get('value'):
    #                         pktindex = id
    #                         break
    #                 id+=1
    #             #once get pkt index performe bits checks
    #             if pktindex != 0:
    #                 for ck in BITSck['Checks']:
    #                     # # print(ck)
    #                     if ck =='NEG':
    #                         if  BITSck['Checks'][ck]['expected']=='SDF':
    #                             exp ='0x01' if self.jsonValues['DutInfo']['PRx']['IsNegotiationSupport']==True else '0x00'
    #                         else:exp = BITSck['Checks'][ck]['expected']

    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NEG='+str(exp))
    #                         # # print('neg',self.file_list[pktindex]['header_Payload']['childelement'][4]['childelement'][0]['sRawData'],BITSck['Checks'][ck]['expected'])
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][4]['childelement'][0]['sRawData'] != exp:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NEG='+str(self.file_list[pktindex]['header_Payload']['childelement'][4]['childelement'][0]['sRawData']))
                                
    #                     if ck == 'Mjrver':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mjrver='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mjrver='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']))
    #                     if ck == 'Mnrver':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mnrver='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Mnrver='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sRawData']))
    #                     if ck=='XIDvalue':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':XIDvalue='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sDescription'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':XIDvalue='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sDescription']))
    #                     if ck=='Restricted':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Restricted='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Restricted='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData']))
    #                     if ck=='Ext':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Ext='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Ext='+str(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][0]['sRawData']))
    #                     if ck=='PCHtime':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PCHtime='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PCHtime='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][0]['sRawData']))
    #                     if ck=='CLkpingValue':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkpingValue='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkpingValue='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData']))
    #                     if ck=='CLkdelay':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdelay='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdelay='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData']))
    #                     if ck=='CLkdetctPing':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdetctPing='+str(BITSck['Checks'][ck]['expected']))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData'] != BITSck['Checks'][ck]['expected']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkdetctPing='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sRawData']))
    #                     if ck=='CLkReason':
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkReason='+str(BITSck['Checks'][ck]['expected']))
    #                         if BITSck['Checks'][ck]['expected'] not in self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sDescription']:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CLkReason='+str(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sDescription']))
    #                     if ck=='NegoPwr':
    #                         exp = '-'.join(map(str,BITSck['Checks'][ck]['expected']))
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NegoPwr='+str(exp))
    #                         negolist = GeneralMethods.GetFloatFromStr(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][1]['sDescription'])
    #                         res = self.check_measure(BITSck['Checks'][ck]['expected'],negolist[0],BITSck['Checks'][ck]['comp'])
    #                         if res[1] == 'Fail':
    #                             reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':NegoPwr='+str(negolist[0]))
    #                     if ck=='PotentialPow':
    #                         exp = '-'.join(map(str,BITSck['Checks'][ck]['expected']))
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PotentialPow='+str(exp))
    #                         potnlist = GeneralMethods.GetFloatFromStr(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][1]['sDescription'])
    #                         res = self.check_measure(BITSck['Checks'][ck]['expected'],potnlist[0],BITSck['Checks'][ck]['comp'])
    #                         if res[1] == 'Fail':
    #                             reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':PotentialPow='+str(potnlist[0]))
    #                     if ck=='ReferencePower':
    #                         exp = BITSck['Checks'][ck]['expected'][0]
    #                         res = GeneralMethods.GetFloatFromStr(self.file_list[pktindex]['header_Payload']['childelement'][0]['childelement'][1]['sDescription'])
    #                         reslt1 = self.check_measure(BITSck['Checks'][ck]['expected'],res[0],BITSck['Checks'][ck]['comp'])
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':ReferencePower'+str(reslt1[2])+str(exp))
    #                         if reslt1[1] == 'Fail':reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':ReferencePower='+str(res[0]))
    #                     if ck=='ReservedBit':
    #                         exp = BITSck['Checks'][ck]['expected']
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':ReservedBit='+str(exp))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData'] != exp:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':ReservedBit='+str(self.file_list[pktindex]['header_Payload']['childelement'][1]['childelement'][0]['sRawData']))
    #                     if ck=='CNFB2B3':
    #                         exp = BITSck['Checks'][ck]['expected']
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CNFB2B3='+str(exp))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][3]['sRawData'] != exp:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CNFB2B3='+str(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][3]['sRawData']))
    #                     if ck=='CNFB2B7':
    #                         exp = BITSck['Checks'][ck]['expected']
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CNFB2B7='+str(exp))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][0]['sRawData'] != exp:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':CNFB2B7='+str(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][0]['sRawData']))
    #                     if ck=='Count':
    #                         exp = BITSck['Checks'][ck]['expected']
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Count='+str(exp))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][5]['sRawData'] != exp:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':Count='+str(self.file_list[pktindex]['header_Payload']['childelement'][2]['childelement'][5]['sRawData']))
    #                     if ck=='WindowSize':
    #                         exp = BITSck['Checks'][ck]['expected']
    #                         expvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':WindowSize='+str(exp))
    #                         if self.file_list[pktindex]['header_Payload']['childelement'][3]['childelement'][0]['sRawData'] != exp:
    #                                 reslt.append('Fail')
    #                         resvalue.append(str(BITSck['packet'][0])+'_'+str(BITSck['packet'][1])+':WindowSize='+str(self.file_list[pktindex]['header_Payload']['childelement'][3]['childelement'][0]['sRawData']))
    #             # # print(reslt)
    #             AllMeasures['BitsCheck'] =  ','.join(resvalue) if len(resvalue)>0 else 'NA'
    #             AllMeasures['BitsCheck_exp'] = ','.join(expvalue) if len(expvalue)>0 else 'NA'
    #             # AllMeasures['BitsCheck_res'] ='Fail' if len(reslt)>0 else 'Pass'
    #             AllMeasures['BitsCheck_res'] = 'Fail' if any(res[1]=="Fail" for res in resvalue) else 'Pass'
    #             AllMeasures['BitsCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
    #     except Exception as e:
    #         traceback.print_exc()
    # #7. PACKET CHECK
    # def PacketCheck(self,Flow_limit,flwID,Check,AllMeasures):
    #     Details = []
    #     reslt = []
    #     resvalue =[]
    #     expvalue = []
    #     for pkt in Check['ChecksList']:
    #         # # print(pkt)
    #         AllMeasures['PacketCheck_res']='Fail'
    #         # # print('pkt',pkt)
    #         evalue = str(pkt['packet'][0])+'_'+str(pkt['packet'][1])+';Phase: '+str(pkt['phase']) if pkt['packet'][1]!= None else str(pkt['packet'][0])+';Phase: '+str(pkt['phase'])
    #         pres = 'None'
    #         #Limits 1.refCustom , 2.refPrevious, 3.refNextAll, 4.refAll, 5.Flow
    #         if pkt['PktLimit'] == "refCustom":
    #             pass
    #         elif pkt['PktLimit'] == "refPrevious":
    #             limit = [0,Flow_limit[0]]
    #         elif pkt['PktLimit'] == "refNextAll":
    #             limit = [Flow_limit[1],len(self.file_list)-1]
    #         elif pkt['PktLimit'] == "refAll":
    #             limit=[0,len(self.file_list)-1]
    #         elif pkt['PktLimit'] == "Flow":
    #             limit = Flow_limit
    #         elif pkt['PktLimit'] == "FromCustomPacket":
    #             CP = self.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0],value=pkt['CustomLimit']['Packet'][1],limit=Flow_limit)
    #             limit=[CP[2],Flow_limit[1]] if len(CP)>2 else Flow_limit
    #         # # print('limit',limit)
    #         if limit != None:
    #             id = limit[0]
    #             pkcount = 0
    #             pkvcount = 0
    #             pkTresp = []
    #             Pkttimes = []
    #             PktInter = []
    #             PkRes =[]
    #             expPkt = [pkt['packet'][0],pkt['packet'][1]]
    #             preEndTime = 0
    #             while id < limit[1]:
    #                 #check if its packet
    #                 if self.GetPacketType(id) =="Packet":
    #                     if expPkt[0] in self.file_list[id].get('pktType') and expPkt[1] in self.file_list[id].get('value') if expPkt[1] is not None else expPkt[0] in self.file_list[id].get('pktType'):
    #                         # # print(pkt['phase'],id,'-',self.file_list[id].get('description'))
    #                         if pkt['phase'] != None:
    #                             if pkt['phase'] == self.file_list[id].get('description'):
    #                                 Details.append([f"Packet {expPkt[0]}_{expPkt[1]} found at {round(self.file_list[id]['startTime'],2)} sec","Pass"])
    #                                 pres = self.file_list[id].get('pktType')+'_'+self.file_list[id].get('value') if expPkt[1] is not None else self.file_list[id].get('pktType')
    #                                 pres=pres+'@'+str(id)+';Phase: '+str(pkt['phase'])
    #                                 if 'Pkt_count' in pkt: pkcount +=1
    #                                 if preEndTime!=0 : PktInter.append([round((self.file_list[id].get('startTime')*1000)-preEndTime,2),id])
    #                                 preEndTime=self.file_list[id].get('stopTime')*1000
    #                                 #to check proper resp for pkt
    #                                 rid = id+1
    #                                 resstatus = False
    #                                 #    # print('resps',rid)
    #                                 while rid < limit[1]:
    #                                     # # print(file_list[rid].get('pktType'))
    #                                     if self.GetPacketType(rid)=="Response":
    #                                     # if self.file_list[rid].get('isTesterPkt') == False and self.file_list[rid].get('isFWTestermessage')== False:
    #                                         PkRes.append([self.file_list[rid].get('pktType'),rid])
    #                                         pkTresp.append([round((self.file_list[rid]['startTime']-self.file_list[id]['stopTime'])*1000,2),id])
    #                                         resstatus=True
    #                                         break
    #                                     elif self.GetPacketType(rid)=="Packet":
    #                                     # elif self.file_list[rid].get('isTesterPkt') == True and self.file_list[rid].get('isFWTestermessage')== False:
    #                                         break
    #                                     rid+=1
    #                                 if resstatus==False: 
    #                                     PkRes.append(['NoResponse',rid-1])
    #                                 id=rid
    #                             else:id+=1
    #                     else:id+=1
    #                 else: 
    #                     id+=1
    #             if 'Pkt_response' in pkt:
    #                 evalue = evalue+';Response:'+'|'.join(pkt['Pkt_response'])
    #                 if len(PkRes)>0:
    #                     TPkRes=[]
    #                     for rs in PkRes:
    #                         if rs[0] not in pkt['Pkt_response']:
    #                             TPkRes.append('@'.join(map(str,rs)))
    #                     if len(TPkRes)>0:
    #                         reslt.append('Fail')
    #                         pres=pres+';Response:'+','.join(TPkRes)
    #                     else:pres=pres+';Response:'+'No mismatch'
    #                     # if any(rs not in pkt['Pkt_response'] for rs in PkRes): reslt.append('Fail')
    #                 else:
    #                     if 'NOResp' not in pkt['Pkt_response']:
    #                         reslt.append('Fail')
    #                     pres=pres+';Response:None'
    #             if 'Pkt_count' in pkt:
    #                 evalue = evalue+';Count:'+str(pkt['Pkt_count'])
    #                 pres=pres+';Count:'+str(pkcount)
    #                 if pkcount < pkt['Pkt_count']:reslt.append('Fail')
    #             if 'Pkt_Tresponse' in pkt:
    #                 evalue = evalue+';Tresponse:'+'-'.join(str(a) for a in pkt['Pkt_Tresponse'])+'ms'
    #                 if len(pkTresp)>0:
    #                     TpkTresp=[]
    #                     for rs in pkTresp:
    #                         if rs[0] < pkt['Pkt_Tresponse'][0] or rs[0] > pkt['Pkt_Tresponse'][1]:
    #                             TpkTresp.append(str(rs[0])+'@'+str(rs[1]))
    #                     if len(TpkTresp)>0:
    #                         reslt.append('Fail')
    #                         pres=pres+';Tresponse:'+','.join(TpkTresp)
    #                     else:pres=pres+';Tresponse:'+'No mismatch'
    #                     # pres=pres+';Tresponse:'+'|'.join(str(a) for a in pkTresp)
    #                     # if any(rs < pkt['Pkt_Tresponse'][0] or rs > pkt['Pkt_Tresponse'][1] for rs in pkTresp): reslt.append('Fail')
    #                 else:
    #                     pres=pres+';Tresponse:None'
    #                     reslt.append('Fail')
    #             if 'Pkt_Interval' in pkt:
    #                 TPktInter=[]
    #                 evalue = evalue+';Interval:'+'-'.join(str(a) for a in pkt['Pkt_Interval'])+'ms'
    #                 if len(PktInter)>0:
    #                     for rs in PktInter:
    #                         if rs[0] < pkt['Pkt_Interval'][0] or rs[0] > pkt['Pkt_Interval'][1]:
    #                             TPktInter.append(str(rs[0])+'@'+str(rs[1]))
    #                     if len(TPktInter)>0:
    #                         reslt.append('Fail')
    #                         pres=pres+';Interval:'+','.join(TPktInter)
    #                     else:pres=pres+';Interval:'+'No mismatch'
    #                     # pres=pres+';Interval:'+'|'.join(str(a) for a in PktInter)
    #                     # if any(rs != pkt['Pkt_Interval'] for rs in PktInter): reslt.append('Fail')
    #                 else:
    #                     pres=pres+';Interval:None'
    #                     reslt.append('Fail')
    #             expvalue.append(evalue)
    #             resvalue.append(pres)
    #         AllMeasures['PacketCheck_exp'] = ','.join(expvalue)
    #         AllMeasures['PacketCheck'] = ','.join(resvalue)
    #         AllMeasures['PacketCheck_res'] = 'Pass' if len(reslt) == 0 else 'Fail'
    #         AllMeasures['PacketCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
    #8. Get voltage for given time
    def CalculateVoltageOnTime(self,AllChannelData,time):
        index = int(time/AllChannelData['Interval'])
        #retrun in milliVolt
        return round(abs(AllChannelData['RV']['displayDataChunk'][index]*1000),4)
    #9.Find the Limits
    def GetLimits(self,Limittype,details,FlowLimit):
        # # print(details['Packet'][0])
        id = FlowLimit[0]
        if Limittype == "PacketWithResponse":
            while id < FlowLimit[1]:
                Pkt = self.GetPacketDetails(packet=details['Packet'][0],value=details['Packet'][1],limit=[id,FlowLimit[1]])
                if len(Pkt)>2:
                    #Get the response
                    tmpid = Pkt[2]+1
                    while tmpid < FlowLimit[1]:
                        if self.GetPacketType(tmpid)=="Response":
                            if self.file_list[tmpid]['pktType'] == details['Response']:
                                return [Pkt[2],FlowLimit[1]]
                        elif self.GetPacketType(tmpid)=="Packet":break
                        tmpid+=1
                    id=Pkt[2]+1
                else:break
        return None
    #11 Paylod check for a pacekt
    def BitsCheck_New(self, Flow_limit, Check):
        print("BitsCheck_New started")
        SubChecks=[]
        expvalues=[]
        BitsCompare = {}
        
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
            while tmpID <= limit[1]:
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
                        # SubChecks.append([f"The expected packet {self.file_list[pktres[2]]['pktType']}_{self.file_list[pktres[2]]['value']} found at {round(pktres[0],3)}sec","Pass"]) # SubChecks.append([f"The expected packet {'_'.join(ExpPacket)} found at {round(pktres[0],3)}sec","Pass"])
                        SubChecks.append([f"{BITSck['CheckName'] if 'CheckName' in BITSck else ""}The Expected {self.file_list[pktres[2]]['pktType']}_{self.file_list[pktres[2]]['value']} {PktType} found at {round(pktres[0],3)}sec","Pass"])
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
                                            SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}","Pass"])
                                            
                                        elif 'random' in BITSck['Checks'][ck]['expected']:
                                            if BITSck['Checks'][ck].get('except'):
                                                if pyload[BITSck['Checks'][ck]['flag']] not in BITSck['Checks'][ck]['except']:
                                                    SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}","Pass"])

                                                else: SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random and should not be in {BITSck['Checks'][ck]['except']}","Fail"])
                                            else: SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Random value","Pass"])
                                        elif "NEQL" in BITSck['Checks'][ck]['expected']:
                                            if BITSck['Checks'][ck]['val'] != pyload[BITSck['Checks'][ck]['flag']]:
                                                SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Not equal to {BITSck['Checks'][ck]['val']}","Pass"])
                                            else:
                                                SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: Not equal to {BITSck['Checks'][ck]['val']}","Fail"])
                                        else:SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}","Fail"])
                                        break
                                    elif BITSck['Checks'][ck]['comp']=="str_Reverse":
                                        if BITSck['Checks'][ck]['expected'] in pyload[BITSck['Checks'][ck]['flag']]:
                                            SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}","Fail"])
                                        else:SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}","Pass"])
                                    elif BITSck['Checks'][ck]['comp']=="btw":
                                        # # print(int(pyload[BITSck['Checks'][ck]['flag']]),BITSck['Checks'][ck]['expected'])
                                        if int(pyload[BITSck['Checks'][ck]['flag']]) >= BITSck['Checks'][ck]['expected'][0] and int(pyload[BITSck['Checks'][ck]['flag']]) <= BITSck['Checks'][ck]['expected'][1]:
                                            SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}","Pass"])
                                        else:SubChecks.append([f"Recevied {ck} valueis {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected'][0]}-{BITSck['Checks'][ck]['expected'][1]}","Fail"])
                                    elif BITSck['Checks'][ck]['comp']=="Present":
                                        SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}","Pass"])
                                    else:
                                        if ':' in pyload[BITSck['Checks'][ck]['flag']]:
                                            pyaloadli = pyload[BITSck['Checks'][ck]['flag']].split(':')
                                            # print("pyaloadli:",pyaloadli)
                                            payloadActual = '_'.join(pyaloadli[1:])
                                        else:payloadActual=pyload[BITSck['Checks'][ck]['flag']]
                                        # print("payloadActual:",payloadActual)
                                        revdval = GeneralMethods.GetFloatFromStr(payloadActual)
                                        # print("revdval1:",revdval)
                                        if BITSck['Checks'][ck].get("units"):
                                            revdval = [int(str(int(revdval[-1])),16)]
                                        # print("revdval2:",revdval)
                                        if BITSck['Checks'][ck]['comp'] == 'GTEQL':
                                            if  revdval[0] >= BITSck['Checks'][ck]['expected']:
                                                SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is >= {BITSck['Checks'][ck]['expected']}","Pass"])
                                            else:SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is not >= {BITSck['Checks'][ck]['expected']}","Fail"])
                                        elif BITSck['Checks'][ck]['comp'] == 'LTEQL':
                                            if  revdval[0] <= BITSck['Checks'][ck]['expected']:
                                                SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is <= {BITSck['Checks'][ck]['expected']}","Pass"])
                                            else:SubChecks.append([f"Recevied value of {ck} is {revdval[0]}, which is not <= {BITSck['Checks'][ck]['expected']}","Fail"])
                                        elif BITSck['Checks'][ck]['comp'] == 'EQL':
                                            if 'comp1' == BITSck['Checks'][ck]['expected'] or 'comp2' == BITSck['Checks'][ck]['expected']:
                                                BitsCompare[BITSck['Checks'][ck]['expected']] = [ck,revdval[0]]
                                                SubChecks.append([f"Recevied value of {ck} is {revdval[0]}","Pass"])
                                            else:
                                                if revdval[0] == float(BITSck['Checks'][ck]['expected']):
                                                    SubChecks.append([f"Recevied value of {ck} is {revdval[0]} {BITSck['Checks'][ck].get("units","")}, Expected: {BITSck['Checks'][ck]['expected']} {BITSck['Checks'][ck].get("units","")}","Pass"])
                                                else:SubChecks.append([f"Recevied value of {ck} is {revdval[0]} {BITSck['Checks'][ck].get("units","")}, Expected: {BITSck['Checks'][ck]['expected']} {BITSck['Checks'][ck].get("units","")}","Fail"])
                                        elif BITSck['Checks'][ck]['comp'] == 'no':
                                            SubChecks.append([f"Recevied {ck} value is {pyload[BITSck['Checks'][ck]['flag']]}, Expected: {BITSck['Checks'][ck]['expected']}","Pass"])


                            else: SubChecks.append([f"The payload {ck} for packet {'_'.join(ExpPacket)} not found for the packet {'_'.join(ExpPacket)}","Fail"])
                    if 'PacketCount' not in BITSck:
                        break
                    if 'PacketCount' in BITSck:
                        if BITSck['PacketCount'] == "ALL":
                            pass
                        else:
                            if BITSck['PacketCount']==PktCount:
                                break
                    tmpID = pktres[2]+1
                else:
                    if 'PacketCount' in BITSck:
                        if BITSck['PacketCount'] == "ALL":
                            SubChecks.append([f"Received {PktCount} {'_'.join(ExpPacket)} packets","Pass"])
                        else:
                            if PktCount < BITSck['PacketCount']:
                                SubChecks.append([f"Out of {BITSck['PacketCount']} Received only {PktCount} {'_'.join(ExpPacket)} packets","Fail"])
                    else:
                        if PktCount==0:
                            SubChecks.append([f"The expected packet {'_'.join(ExpPacket)} not found between {round(self.file_list[limit[0]]['startTime'],3)}sec to {round(self.file_list[limit[1]]['stopTime'],3)}sec ","Fail"])
                    break
            expvalues.append(expvalue)

            if len(BitsCompare)>0:
                if BitsCompare['comp1'][1] == BitsCompare['comp2'][1]:
                    SubChecks.append([f"{BitsCompare['comp1'][0]}: {BitsCompare['comp1'][1]} is equal to {BitsCompare['comp2'][0]}: {BitsCompare['comp2'][1]}","Pass"])
                else: SubChecks.append([f"{BitsCompare['comp1'][0]}: {BitsCompare['comp1'][1]} is not equal to {BitsCompare['comp2'][0]}: {BitsCompare['comp2'][1]}","Fail"])

        # AllMeasures['BitsCheck_exp'] = ';'.join(expvalues)
        # AllMeasures['BitsCheck'] = 'Found Issues' if any(res[1]=="Fail" for res in SubChecks) else 'No Issues'
        # AllMeasures['BitsCheck_res'] = 'Fail' if any(res[1]=="Fail" for res in SubChecks) else 'Pass'
        # AllMeasures['BitsCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
        # AllMeasures['BitsCheck_Details']=SubChecks
        return SubChecks
     

    #10. packet check with sub checks
    def PacketCheck_New(self,Flow_limit,Check):
        SubChecks = []
        expvalues=[]
        for pkt in Check['ChecksList']:
            expval = ""
            Pktcount = 0
            #Set the limit for the pacekt check mentioned in the setup
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
            elif pkt['PktLimit'] == "FromFlow":
                limit = [Flow_limit[0],len(self.file_list)-1]
            elif pkt['PktLimit'] == 'FromExncnt':
                excnt = self.PktMethod.GetPacketDetails(packet="Execution_count_no",limit=[0,Flow_limit[0]-1],Type="TesterMsg")
                limit=[excnt[2],Flow_limit[1]] if len(excnt)>2 else Flow_limit
            elif pkt['PktLimit'] == "FromCustomPacket":
                CP = self.PktMethod.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0],value=pkt['CustomLimit']['Packet'][1],limit=Flow_limit)
                limit=[CP[2]+1,Flow_limit[1]] if len(CP)>2 else Flow_limit
            elif pkt['PktLimit'] == "FromCustomPacketWhole":
                CP = self.PktMethod.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0],value=pkt['CustomLimit']['Packet'][1],limit=[0,len(self.file_list)-1])
                limit=[CP[2]+1,len(self.file_list)-1] if len(CP)>2 else Flow_limit
                # print("FromCustomPacket:",limit)
            elif pkt['PktLimit'] == 'BTWNpkts':
                CP1 = self.PktMethod.GetPacketDetails(packet=pkt['CustomLimit']['Packet1'][0],value=pkt['CustomLimit']['Packet1'][1],limit=Flow_limit,Type=pkt['CustomLimit']['Packet1'][2])
                CP2 = self.PktMethod.GetPacketDetails(packet=pkt['CustomLimit']['Packet2'][0],value=pkt['CustomLimit']['Packet2'][1],limit=Flow_limit,Type=pkt['CustomLimit']['Packet2'][2])
                if len(CP1)>2 and len(CP2)>2: limit=[CP1[2],CP2[2]]
            elif pkt['PktLimit'] == "UptoCustomPacket":
                CP = self.PktMethod.GetPacketDetails(packet=pkt['CustomLimit']['Packet'][0],value=pkt['CustomLimit']['Packet'][1],limit=Flow_limit,Type=pkt['CustomLimit']['Type'])
                limit=[Flow_limit[0],CP[2]-1] if len(CP)>2 else Flow_limit


            print('limit:',limit)
            ExpPacket = pkt['packet'] if pkt['packet'][1] is not None else [pkt['packet'][0]]
            expval=expval+f"{'_'.join(ExpPacket)}:"
            if 'Pkt_response' in pkt : expval=expval+f"Response in {','.join(pkt['Pkt_response'])}"
            if 'Pkt_count' in pkt : expval=expval+f"Pacekt Count= {pkt['Pkt_count']}"
            if limit != None:
                # SubChecks.append([f"Packet check for {'_'.join(ExpPacket)} initiated on limit {round(self.file_list[limit[0]]['startTime'],2)}Sec to {round(self.file_list[limit[1]]['startTime'],2)}Sec","Pass"])
                #Iterate on limit and get the matching packets
                id = limit[0]

                while id<=limit[1]:
                    # if self.GetPacketType(id) =="Packet":
                    #check for the phase 
                    if pkt['phase'] in self.file_list[id]['description']:
                        if ExpPacket[0] in self.file_list[id]['pktType'] and ExpPacket[1] in self.file_list[id]['value'] if len(ExpPacket)==2 else ExpPacket[0] in self.file_list[id]['pktType']:
                            if self.GetPacketType(id) == pkt['PktType'] if 'PktType' in pkt else "Packet":
                                # print("GetPacketType:",self.GetPacketType(id))
                                Pktcount+=1
                                SubChecks.append([f"{pkt['chkname'] if "chkname" in pkt else ""}{self.file_list[id]['pktType']} {self.file_list[id]['value']} Packet found at {round(self.file_list[id]['startTime'],3)} sec","Pass"])
                                # print("pktfound:",f"{'_'.join(ExpPacket)} Packet found at {round(self.file_list[id]['startTime'],3)} sec")
                                #Apply additional checks for the packet
                                #############################################################
                                # if 'Pkt_response' in pkt:
                                if pkt.get('Pkt_response'):
                                    tmpid = id+1
                                    RespFlag = False
                                    while tmpid < limit[1]:
                                        if self.GetPacketType(tmpid) =="Response":
                                            if any(res in self.file_list[tmpid]['pktType'] for res in pkt['Pkt_response']):
                                                # print("response:",self.file_list[tmpid]['pktType'])
                                                RespFlag=True
                                                SubChecks.append([f"Found {self.file_list[tmpid]['pktType']}_{self.file_list[tmpid]['value']} response for {'_'.join(ExpPacket)} packet at {round(self.file_list[tmpid]['startTime'],2)}sec, Which is expected amoung: [{','.join(pkt['Pkt_response'])}]","Pass"])
                                            else: SubChecks.append([f"Found response {self.file_list[tmpid]['pktType']} at {round(self.file_list[tmpid]['startTime'],2)}sec, Which is not expected amoung: [{','.join(pkt['Pkt_response'])}]","Fail"])
                                        elif self.GetPacketType(tmpid) =="Packet":break
                                        tmpid+=1
                                    if RespFlag == False:
                                        if "No" in pkt['Pkt_response']:
                                            SubChecks.append([f"Response not found for received for the packet.","Pass"])
                                        else:
                                            SubChecks.append([f"Response not found for received for the packet.","Fail"])
                                    if not pkt.get('Pkt_count'):
                                        break
                                elif not pkt.get('Pkt_count'):break
                                ############################################################
                    id+=1
                else:
                    # Packet not found
                    if (not pkt.get('Pkt_count')) or (pkt.get('Pkt_count') and Pktcount==0):
                        SubChecks.append([f"{ExpPacket[0]} {f'({ExpPacket[1]})' if len(ExpPacket)==2 else ""} not found","Inconclusive"])
            else:SubChecks.append([f"Packet check for {'_'.join(ExpPacket)} not initiated, limit not found","Fail"])
            # # print("SubChecks:",SubChecks)
            #check for pacekt count
            if 'Pkt_count' in pkt:
                if "ALL" in str(pkt['Pkt_count']):
                    SubChecks.append([f"The received pacekt count is {Pktcount}","Pass"])
                else:
                    if Pktcount >= int(pkt['Pkt_count']):
                        SubChecks.append([f"The received pacekt count is {Pktcount},Which is expected count of {pkt['Pkt_count']}","Pass"])
                    else:SubChecks.append([f"The received pacekt count is {Pktcount},Which is not expected count of {pkt['Pkt_count']}","Fail"])
            expvalues.append(expval)
        # if not returndata:
        #     AllMeasures['PacketCheck_exp'] = ';'.join(expvalues)
        #     AllMeasures['PacketCheck'] = 'Found Issues' if any(res[1]=="Fail" for res in SubChecks) else 'No Issues'
        #     AllMeasures['PacketCheck_res'] = 'Fail' if any(res[1]=="Fail" for res in SubChecks) else 'Pass'
        #     AllMeasures['PacketCheck_SEQ'] = Check['CheckSEQ'] if 'CheckSEQ' in Check else 0
        #     AllMeasures['PacketCheck_Details']=SubChecks
        # else: return SubChecks
        return SubChecks
    
    #Get the payload details by name
    def GetPayloadDetails(self,index,name):
        result = []
        for bits in self.file_list[index]['header_Payload']['childelement']:
            for payloads in bits['childelement']:
                if payloads['sDecodedValue'] == name or payloads['sDescription'] == name:
                    result.append(payloads)
        return result
    #Get the packet Response
    def GetPacketResponse(self,index,limit):
        id = limit[0]
        while id < limit[1]:
            if self.GetPacketType(id)=="Response":
                return id
            elif self.GetPacketType(id)=="Packet":
                break
            id+=1
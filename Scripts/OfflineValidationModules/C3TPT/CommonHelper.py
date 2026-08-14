import pandas as pd
import csv
import json
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods




class CommonCTSChecks:
    def __init__(self,file_list,Header,JapiData,BackupJson,Product,Mode):
        self.file_list=file_list
        self.Product=Product
        self.Mode=Mode
        self.Header=Header
        self.JapiData = JapiData
        self.PktMethod = PacketMethods(file_list,Header)
        self.PlotMethod = PlotMethods(Header)
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']

        

    
    def PktNumCheck(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        count=0
        id=0
        while id < self.Flow_limit[1]:
            TypeCheck=self.PktMethod.GetPacketType(id)
            if TypeCheck=='Packet':
                count+=1
                if Check['PktCount']== count:
                    if self.file_list[id]['pktType'] in Check['ExpPkt']:res.append([f'Prx sent the  {self.file_list[id]['pktType']} pkt as {Check['desc']} datapacket.', "Pass"])
                    else: res.append([f'Prx sent the  {self.file_list[id]['pktType']} pkt as {Check['desc']} datapacket.', "Fail"])
                    break
            id+=1
        return res

    def TimingPktCheck(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        DataPacket= str(f'{Check['ExpPkt'][0]}{'_' + Check['ExpPkt'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpPkt'][1] is not None else ''}')
        PingTime= self.PktMethod.GetPacketDetails(packet="Ping Initiated", limit=self.Flow_limit)
        pkt=self.PktMethod.GetPacketDetails(packet=Check['ExpPkt'][0], value=Check['ExpPkt'][1], limit=self.Flow_limit)
        if len(pkt)>2:
            Timing=round((pkt[0]-PingTime[0])*1000,2)
            res.append([f'Prx sent {DataPacket} data packet within {Timing} mS from Ping','Fail' if Timing > Check['Time'] else 'Pass'])
        else: res.append([f'Prx did not sent {DataPacket} data packet','Inconclusive'])
        return res
    
    def Major_Minor(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Exp = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=self.Flow_limit)
        if len(Exp)>2:
            MajorVersion=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Exp[2],'Major_Version')[0]['sRawData'])[1]
            MinorVersion=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Exp[2],'Minor_Version')[0]['sRawData'])[1]
            Msfg_code=self.PktMethod.GetPayloadDetails(Exp[2],'Manufacturer_Code')[0]['sRawData']
            ManufacturerCode_Esdf = self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['MemberCode']
            Comb=False
            for exp in Check['comb']:
                if MajorVersion in exp['Major']:
                    res.append([f'Prx sent the Major Version as {MajorVersion}  for the Identification datapacket ,Expected :{','.join(str(i) for i in exp['Major'])}', "Pass"])
                    if MinorVersion in exp['Minor']:
                        res.append([f'Prx sent the Minor Version as {MinorVersion}  for the Identification datapacket, Expected :should be in {','.join(str(i) for i in exp['Minor'])}', "Pass"])
                        Comb=True
                        Pkt_val1=self.PktMethod.hex_to_decimal(self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['MemberCode'])
                        Pkt_val2=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Exp[2],'Manufacturer_Code')[0]['sRawData'])
                        res.append([f'Prx sent Identification data packet With Manufacturer code :{Pkt_val1} and in SDF it was set to {Pkt_val2}','Pass' if Pkt_val1==Pkt_val2 else 'Fail'])
                        break 
            if not Comb :res.append([f'Prx sent Major Version as {MajorVersion} Expcted :{','.join(str(i) for i in exp['Major'])} & Minor Version as {MinorVersion} for the Identification data packet Expcted :should be in {','.join(str(i) for i in exp['Minor'])}','Fail'])
            if Check['Manufacturer_Code']: res.append([f'Prx sent ManufacturerCode as {Msfg_code} for the Identification data packet. In SDF it was set to {ManufacturerCode_Esdf}', 'Pass' if ManufacturerCode_Esdf==Msfg_code else 'Fail'])                   
        else: res.append([f'Prx did not sent Identification data packet','Fail'])
        return res

    def XIDCheck(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ID=self.PktMethod.GetPacketDetails(packet="Identification", limit=self.Flow_limit)
        if len(ID)>2:
            ID_bit=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ID[2],'Ext')[0]['sRawData'])[1]
            if ID_bit==1:
                id=ID[2]+1
                while id < self.Flow_limit[1]:
                    TypeCheck=self.PktMethod.GetPacketType(id)
                    if TypeCheck=='Packet' :
                        if self.file_list[id]['pktType']=="Extended Identification":
                            FE_Check=self.PktMethod.GetPayloadDetails(id,'Extended_Device_Identifier')[0]['sRawData']
                            res.append([f'Prx sent the Extended Identification data packet with {FE_Check} (Expected:!= 0xFE)','Fail' if FE_Check =="0xFE" else 'Pass'])
                        else:  res.append([f'Prx sent the {self.file_list[id]['pktType']} data packet.','Fail'])
                        break     
                    id+=1
            else: res.append([f'Prx did not set the Ext-Bit in the Identification data packet to ONE','Inconclusive' if Check['XID'] else 'Pass']) 
        else: res.append([f'Prx did not sent Identification data packet','Inconclusive'])
        return res

    def Neg_Compare(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration",limit=self.Flow_limit)
        if len(CFG)>2:
            if 'false' in self.file_list[CFG[2]]['value']:
                res.append([f'Prx sent Configuration data packet with Neg Bit :false','Pass'])
                # Compare Bits
                for Bit in Check['Bits']:
                    Val=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(CFG[2],Bit)[0]['sRawData'])
                    print(Val)
                    if Val >0 :res.append([f'Prx sent the Filed :{Bit} with value:{Val} in the  Configuration data packet','Fail'])
            else:  res.append([f'Prx sent Configuration data packet with Neg Bit :True','Pass'])     
        else:res.append([f'Prx did not sent Configuration data packet','Inconclusive'])
        return res

    def SDF_Checks(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        for pkt in Check['Pkts']:
            pkt_Details=self.PktMethod.GetPacketDetails(packet=pkt[0],value=pkt[1], limit=self.Flow_limit)
            if len(pkt_Details)>2:
                res.append([f'Prx sent {pkt[0]} data packet','Pass'])
                for sdfitems in pkt[2]:
                    SDF_item=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields'][sdfitems['SDFName']]
                    Pkt_val=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(pkt_Details[2],sdfitems['Name'])[0]['sRawData'])[1]
                    if sdfitems['comp']=="EQL":  res.append([f'Prx sent {sdfitems['Name']} as {Pkt_val} for the {pkt[0]} data packet. In SDF it was set to {SDF_item}', 'Pass'  if (SDF_item and Pkt_val==1 )or (not SDF_item and Pkt_val==0) else 'Fail'])   
            else: res.append([f'Prx did not sent {pkt} data packet','Fail'])
        return res

    def Compare_PCH_Count(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PCHcount,PCHValues=self.Pch()
        if not Check['PchLimit']:
            pkt_Details=self.PktMethod.GetPacketDetails(packet="Configuration", limit=self.Flow_limit)
            if len(pkt_Details)>2:
                Pkt_val=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(pkt_Details[2],"Count")[0]['sRawData'])[1]
                res.append([f'Prx sent {PCHcount} PCH data packets and count is set to {Pkt_val} in CFG Packet','Pass' if Pkt_val == PCHcount else'Fail'])  
        else:
            if PCHcount >0:
                for i in range(len(PCHValues)): res.append([f'Prx sent PCH data packet with val {PCHValues[i]}','Pass' if PCHValues[i] >=5 and PCHValues[i]<=100 else 'Fail'])
            else:res.append([f'Prx did not sent PCH data packet','Fail'])
        return res

    def OptionalDatapkts(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Count=0
        ID=self.PktMethod.GetPacketDetails(packet="Identification", limit=self.Flow_limit)
        if len(ID)>2:
            ID_bit=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(ID[2],'Ext')[0]['sRawData'])[1]
            CFG=self.PktMethod.GetPacketDetails(packet="Configuration", limit=[ID[2],self.Flow_limit[1]])
            if len(CFG)>2:
                id=ID[2]+1
                while id < CFG[2]:
                    TypeCheck=self.PktMethod.GetPacketType(id)
                    if TypeCheck=='Packet' :Count+=1
                    id+=1
                if ID_bit==1:Count-=1
                res.append([f'Prx sent {Count} OPtional data packets from ID/x to  CFG Packets','Pass' if Count==0 or Count<=7 else 'Fail'])  
                if Count>0:
                    PCHcount,PCHValues=self.Pch()
                    if PCHcount==0: res.append([f'Prx did not sent atleast one PCH Packets', 'Fail'])  
        return res

    def TimingCheck(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        for TC in Check['TimingCheck']:
            id=self.Flow_limit[0]
            match  TC :
                case "Twake":
                    ping = self.PktMethod.GetPacketDetails(packet="Ping Initiated",limit=[id,self.Flow_limit[1]],Type="TesterMsg")
                    if len(ping)>2:
                        #Find the First Packet
                        while id < self.Flow_limit[1]:
                            TypeCheck=self.PktMethod.GetPacketType(id)
                            Twake=round((self.file_list[id]['startTime']-ping[1])*1000,3)+5.50
                            Limit=Check['ExpTime'][0][TC]
                            if TypeCheck=='Packet' and self.file_list[id]['pktType'] == "Signal strength": 
                                res.append([f'Measured {TC} from {round(ping[1]*1000,3)} mS to {round((self.file_list[id]['startTime'])*1000+5.5,3)} mS  is {Twake} mS ,Limit :{Limit[0]} mS ~ {Limit[1]} mS ', 'Fail' if Twake <Limit[0] or Twake > Limit[1] else 'Pass'])
                                break
                            else:
                                if 'Shutdown' in self.file_list[id]['pktType']:
                                    res.append([f'could not able to find the Ping Packet', 'Fail'])
                                id+=1

                    else: res.append([f'could not able to find the Ping', 'Fail'])
                
                case "Tstart" |"Tsilent":
                    #Measure All Timing for all received Packets
                    id=self.Flow_limit[0]
                    while id < self.Flow_limit[1]:
                        TypeCheck=self.PktMethod.GetPacketType(id)
                        if TypeCheck=='Packet':
                            firstPktTime=self.file_list[id]['stopTime']
                            firstPKt=self.file_list[id]['pktType']
                            id+=1
                            #find the next packet
                            while id < self.Flow_limit[1]:
                                TypeCheck=self.PktMethod.GetPacketType(id)
                                if TypeCheck=='Packet':
                                    Limit=Check['ExpTime'][0][TC]
                                    Timing=round(((self.file_list[id]['startTime']-firstPktTime)*1000) +(5.50 if TC== "Tstart" else 0),3)
                                    if TC=='Tstart':res.append([f'Measured {TC} from {firstPKt}-{round(firstPktTime,3)} Sec to {self.file_list[id]['pktType']}-{round(self.file_list[id]['startTime'],3)} Sec  is {Timing} mS ,Limit :{Limit[0]} mS ~ {Limit[1]} mS ', 'Fail' if Timing <Limit[0] or Timing > Limit[1] else 'Pass'])
                                    else:res.append([f'Measured {TC} from {firstPKt}-{round(firstPktTime,3)} Sec to {self.file_list[id]['pktType']}-{round(self.file_list[id]['startTime'],3)} Sec  is {Timing} mS ,Limit : > {Limit[0]} mS ', 'Fail' if Timing <Limit[0] else 'Pass'])
                                    break
                                else:id+=1
                        else: id+=1
        return res

    def CFG_EPX(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration", value="Neg:true",limit=self.Flow_limit)
        if len(CFG)>2:
            Response=self.PktResponse(CFG[2]+1,self.Flow_limit[1])
            if Response is not None:
                Timing=round((self.file_list[Response[1]]['startTime']-self.file_list[CFG[2]]['stopTime'])*1000,3)
                if Check['TimingCheck']:
                    res.append([f'TPT sent {Response[0]} response for the CFG Packet, Expected:ACK', 'Inconclusive' if "ACK" not in Response[0] else 'Pass'])
                    res.append([f'Measured Tresponse from Configuartion at {{{ CFG[2]}}} to {Response[0]} is {Timing} mS, Limit :(14.7±0.3) ms.', 'Inconclusive' if Timing <14.4 or Timing > 15.0 else 'Pass'])
                # Log first Packet
                id=CFG[2]+1
                PktFound=False
                while id < self.Flow_limit[1]:
                    TypeCheck=self.PktMethod.GetPacketType(id)
                    if TypeCheck=='Packet':
                        PktFound=True
                        # Validate Pkt
                        pktPresent,PktsList=self.CheckPkt(id,Check['Pkts'])
                        if pktPresent : res.append([f'Prx sent {self.file_list[id]['pktType']} after the CFG Packet, which is within the List:[{PktsList}]', 'Pass'])
                        else:res.append([f'Prx sent {self.file_list[id]['pktType']} after the CFG Packet, which is not within the List:[{PktsList}]', 'Fail'])
                        break
                    id+=1
                if not PktFound:res.append([f'PRx did not sent any Packets after the CFG Packet', 'Inconclusive'])
            else:res.append([f'TPT did not sent Response for the CFG Packet', 'Inconclusive'])  
        else:res.append([f'Prx did not sent CFG Packet', 'Inconclusive'])
        return res

                                
    def PFO(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration", limit=self.Flow_limit)
        if len(CFG)>2:
            id=CFG[2]+1
            while id < self.Flow_limit[1]:
                pkt=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0], limit=[id,self.Flow_limit[1]])
                #find Estimated Assertion
                if len(pkt)>2:
                    Rxval=float(self.file_list[pkt[2]]['value'].replace('{','').replace('w','').replace('}','')) if  Check['BPP'] else float(self.file_list[pkt[2]]['value'].split(',')[1].replace('{','').replace('w','').replace('}',''))
                    Tx=self.PktMethod.GetPacketDetails(packet="Estimated_Transmitted_Power_Value",Type="TesterMsg" ,limit=[pkt[2],self.Flow_limit[1]])
                    Txval=float(self.file_list[Tx[2]]['value'].split(',')[0].replace('W','')) 
                    offset= 0.350
                    if Rxval > 5.00 and Rxval <=10.00 : offset=0.500
                    elif Rxval > 10.00:offset=0.750
                    if Check['BPP']:offset=0.350
                    result= 'Pass' if Rxval <= ( Txval +offset) and Txval <= Rxval else 'Fail'
                    res.append([f'Estimated Received Power is {Rxval}, Transmitter Power is {Txval} W at @{pkt[2]}, Limit :Pt ≤ Pr ≤ Pt +{offset}',result])
                    id=Tx[2]+1
                else:id+=1
            Timing=round((self.file_list[id]['startTime']-CFG[1])*1000,2)
            res.append([f'Prx did stayed in the PT Phase for {Timing} mS', 'Inconclusive' if Timing< Check['Timing'] else 'Pass'])
        else:res.append([f'Prx did not entered the PT Phase', 'Inconclusive'])
        return res
                                    
    def DSRCheck(self, CTSCheck, Check, flows, flwID):
          # log the PTx packet and look for DSR pkt
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        Pktscount=0
        while id < self.Flow_limit[1]:
            if Pktscount > Check['Pkt_count']:break
            PTxpkt=self.PktMethod.GetPacketDetails(packet=Check['PTx'][0], Type='Response',limit=[id,self.Flow_limit[1]])
            if len(PTxpkt)>2: 
                Pktscount+=1
                # find ATN response
                ATN=self.PktMethod.GetPacketDetails(packet="ATN",Type='Response', limit=[PTxpkt[2]+1,self.Flow_limit[1]])
                if len(ATN)>2:# check dsr pkt
                    DSR=self.PktMethod.GetPacketDetails(packet="DSR", limit=[PTxpkt[2]+1,ATN[2]])
                    if len(DSR)>2:
                        if "ND" in self.file_list[DSR[2]]['value']:
                            res.append([f'Prx sent  DSR/nd at @Id {DSR[2]} for PTx {Check['PTx'][0]} at @Id{PTxpkt[2]}', 'Pass'])
                        else: res.append([f'Prx sent DSR/{self.file_list[DSR[2]]['value']} at @Id {DSR[2]} for PTx {Check['PTx'][0]} at @Id{PTxpkt[2]}, Exp: DSR/ND', 'Fail'])
                    id=ATN[2]+1 
                else:
                    DSR=self.PktMethod.GetPacketDetails(packet="DSR", limit=[PTxpkt[2]+1,self.Flow_limit[1]])
                    if len(DSR)>2:
                        if "ND" in self.file_list[DSR[2]]['value']:
                            res.append([f'Prx sent  DSR/nd at @Id {DSR[2]} for PTx {Check['PTx'][0]} at @Id{PTxpkt[2]}', 'Pass'])
                        else: res.append([f'Prx sent DSR/{self.file_list[DSR[2]]['value']} at @Id {DSR[2]} for PTx {Check['PTx'][0]} at @Id{PTxpkt[2]},Exp: DSR/ND', 'Fail'])
                    id=DSR[2]+1 if len(DSR)>2 else id+1
            else:break
        return res

    def DSRATN(self, CTSCheck, Check, flows, flwID):
        # check the ATN response for 2nd rp Packet
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP2=0
        id =self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            # find RP
            RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=[id,self.Flow_limit[1]])
            if len(RP0)>2:
                RP2+=1
                if RP2%2==0:
                    # Check ATN Response
                    resp= self.PktMethod.GetPacketResponse(RP0,[RP0[2]+1,self.Flow_limit[1]])
                    if resp is not None:
                        if  self.file_list[resp]['pktType'] =="ATN":res.append([f'PTx sent Response- ATN for the 2nd RP data packet at @ID {RP0[2]}', 'Pass'])
                        else:res.append([f'PTx sent Response for the 2nd RP data packet at @ID {RP0[2]} is {  self.file_list[resp]['pktType']},Exp: ATN', 'Inconclusive'])
                    else:
                        PKT=self.findTypeid(limit=[RP0[2]+1,self.Flow_limit[1]],Type='Packet')
                        if PKT is not None:
                            res.append([f'PTx did not sent Response for the 2nd RP data packet at @ID {RP0[2]}.', 'Inconclusive'])
                id=RP0[2]+1
            else:break
        if RP2 <1:res.append([f'Prx sent only {RP2} RP/0 data packets.', 'Inconclusive'])
        return res

    def DSRPOLL(self, CTSCheck, Check, flows, flwID):
        # CHECK response for DSR/poll pckets
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PTxresponse=0
        id =self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            if PTxresponse >=Check['Pkt_count']:break
            # find DSR/Poll
            DSR=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[id,self.Flow_limit[1]])
            if len(DSR)>2:
                # Check  Response
                resp= self.PktMethod.GetPacketResponse(DSR,[DSR[2]+1,self.Flow_limit[1]])
                if resp is not None:
                    if Check['PTx'][0] in self.file_list[resp]['pktType'] and ( Check['PTx'][1] is None or Check['PTx'][1] in self.file_list[resp]['value'] ):
                        if Check['PTx'][2]:
                            Pres=self.Payload_Details(PacketName=Check['PTx'][0],Index=resp,PayLoads=Check['PTx'][3],Receiver=False)
                            if len(Pres)>0:res.extend(Pres)
                        res.append([f'PTx sent Response- {Check['PTx'][0]} for the DSR/POLL Packet at @ID {DSR[2]}.', 'Pass'])
                        PTxresponse+=1
                    else:res.append([f'PTx sent Response for the DSR/POLL data packet at @ID {DSR[2]} is {  self.file_list[resp]['pktType']},Exp: {Check['PTx'][0]}', 'Inconclusive'])
                else:res.append([f'PTx did not sent Response for the DSR/POLL data packet at @ID {DSR[2]},Exp: {Check['PTx'][0]}', 'Inconclusive'])
                id=DSR[2]+1
            else:break
        if PTxresponse < Check['Pkt_count']:res.append([f'PTx sent only {PTxresponse} {Check['PTx'][0]} data packets, Exp :{Check['Pkt_count']}', 'Fail' if Check.get('Fail',False) else'Inconclusive'])
        return res
            
    def ADC(self, CTSCheck, Check, flows, flwID):
        # find PRX ADC data packet
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ADCpkt=False
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            ADC=self.PktMethod.GetPacketDetails(packet="ADC", limit=[id,self.Flow_limit[1]])
            if len(ADC)>2:
                ADCpkt=True
                # self.PktMethod.GetPayloadDetails(pkt_Details[2],items['Name1'])[0]['sRawData']
                Payload=self.PktMethod.GetPayloadDetails(ADC[2],"Request")[0]['sRawData']
                if Payload in Check['ADC']:
                    res.append([f'Prx sent ADC Data packet with Parameter {Payload} at Id {ADC[2]}', 'Pass'])
                else: res.append([f'Prx sent ADC Data packet with Parameter {Payload} at Id {ADC[2]} which is not in set {Check['ADC']}.', 'Pass'])
                id=ADC[2]+1
            else:id+=1
        if not ADCpkt:res.append([f'Prx  did not sent ADC Data packet .', 'Pass'])
        return res

    def ADT(self, CTSCheck, Check, flows, flwID):
        # find Consecutive ADT Rx packets
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ADTpkt=False
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            ADT=self.PktMethod.GetPacketDetails(packet="ADT", limit=[id,self.Flow_limit[1]])
            if len(ADT)>2:
                # find Excepected Response
                resp=self.PktResponse(ADT[2]+1,self.Flow_limit[1])
                if ( resp is None and (Check['ADT'][0] is None)) or (resp is not None and (resp[0] in Check['ADT'])) :
                    # find next Immediate ADT pkt
                    ADT2=self.PktMethod.GetPacketDetails(packet="ADT", limit=[ADT[2]+1,self.Flow_limit[1]])
                    if len(ADT2)>2:
                        if self.file_list[ADT[2]]['pktType']==self.file_list[ADT2[2]]['pktType']:
                            res.append([f'Prx sent { self.file_list[ADT[2]]['pktType']} Data packet at @Id {ADT[2]}, { self.file_list[ADT2[2]]['pktType']} Data packet at @Id {ADT2[2]}.', 'Pass'])
                        else: res.append([f'Prx sent { self.file_list[ADT[2]]['pktType']} Data packet at @Id {ADT[2]}, { self.file_list[ADT2[2]]['pktType']} Data packet at @Id {ADT2[2]}.', 'Fail'])
                        id=ADT2[2]+1
                        ADTpkt=True  
                    else:id=ADT[2]+1
                else:  id=ADT[2]+1        
            else:break
        if not ADTpkt:res.append([f'Prx  did not sent ADT Data packet .', 'Pass'])
        return res

    def DSR_Nego(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            while id < self.Flow_limit[1]:
                PTxpkt=self.PktMethod.GetPacketDetails(packet="Power Transmitter Capability", Type='Response',limit=[id,self.Flow_limit[1]])
                if len(PTxpkt)>2:
                    # Log the first DSR or Nego Pkt
                    ATN=self.PktMethod.GetPacketDetails(packet="ATN",Type='Response', limit=[PTxpkt[2]+1,self.Flow_limit[1]])
                    if len(ATN)>2:# check dsr pkt
                        i=PTxpkt[2]+1
                        while i < ATN[2]:
                            Type=self.PktMethod.GetPacketType(i)
                            if Type=='Packet':
                                if self.file_list[i]['pktType']=="Renegotiate"  :
                                    res.append([f'Prx sent DSR{self.file_list[i]['value']} Data packet at @Id {i} for PTx Packet at @Id {PTxpkt[2]}.', 'Pass'])                                                                
                                    break
                                elif  self.file_list[i]['pktType']=="DSR":
                                    if "ACK" in  self.file_list[i]['value']:res.append([f'Prx sent DSR{self.file_list[i]['value']} Data packet at @Id {i} for PTx Packet at @Id {PTxpkt[2]}.', 'Pass'])  
                                    else: res.append([f'Prx sent DSR{self.file_list[i]['value']} Data packet at @Id {i} for PTx Packet at @Id {PTxpkt[2]}.', 'Fail'])
                                    break
                                else:i+=1
                            else:i+=1
                        id=ATN[2]+1    
                    else:break
                else:break
        else:res.append([f'Prx did not Entered PT Phase', 'Inconclusive'])
        return res

    def S18_S20(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        def checks(id,limit,Vlimit,ping='S18'):
            # find detach time
            self.AllChannelData = self.PlotMethod.GetAllChannelData('2',self.JapiData)
            vrectS20 = self.CalculateVoltTwindow(id[2],self.AllChannelData,at="start",measure="before")  
            res.append([f"Measured Inverter Voltage for the {ping} ping is {round(vrectS20[0],2)} V, Limit: {Vlimit[0]} V ~ {Vlimit[1]} V", "Fail" if round(vrectS20[0],2) <Vlimit[0] or round(vrectS20[0],2) > Vlimit[1] else "Pass"]) 
            sd=self.PktMethod.GetPacketDetails(packet="Shutdown",Type="TesterMsg",limit=limit)
            timing=round((sd[0]-id[1])*1000,2) 
            res.append([f'PTx detached after {timing} mS after the Signal Strength at {{{id[2]}}} ,Limit : <20 mS', 'Inconclusive' if timing >20 else 'Pass'])
           
        #Get Last SS20 value
        SS20 = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=self.Flow_limit)
        if len(SS20)>2:
            S20Val = GeneralMethods.GetFloatFromStr(self.file_list[SS20[2]]['value'])
            checks(SS20,limit=[self.Flow_limit[0],len(self.file_list)-1],Vlimit=[19.9,20.1],ping='S20')
            SS18 = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[self.Flow_limit[0],0])
            if len(SS18)>2:
                S18Val = GeneralMethods.GetFloatFromStr(self.file_list[SS18[2]]['value'])                           
                checks(SS18,limit=[SS18[2]+1,self.Flow_limit[0]],Vlimit=[17.9,18.1])
                result='Fail' if S18Val[0] >= S20Val[0] or  S20Val[0]==255 or S18Val[0]==255 else 'Pass'
                res.append([f'Measured Signal Strength Val at S18 Ping is {S18Val[0]} and at S20 Ping is {S20Val[0]} , Limit : S18 < S20 < 255', result])
               
            else:res.append([f'PTx did not Initiated S18 Ping', 'Inconclusive'])
        else:res.append([f'PTx did not Initiated S20 Ping', 'Inconclusive'])
        return res

    def ADC_Auth(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            A=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth", limit=[id,self.Flow_limit[1]])
            if len(A)>2:
                # check ADT packet
                ADT=self.PktMethod.GetPacketDetails(packet="ADT", limit=[A[2]+1,self.Flow_limit[1]])
                if len(ADT)>2:
                    if 'e' in self.file_list[ADT[2]]['pktType']:res.append([f'Prx sent {self.file_list[ADT[2]]['pktType']} Packet after ADC/Auth at @Id{A[2]} .', 'Pass'])
                    else:res.append([f'Prx sent {self.file_list[ADT[2]]['pktType']} Packet after ADC/Auth at @Id{A[2]} .', 'Fail'])
                    id=ADT[2]+1
                else:
                    res.append([f'Prx did not sent ADT Packet after ADC/Auth at @Id{A[2]} .', 'Inconclusive'])
                    id+=1
            else:break
        return res

    def PTphasePkts(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        pkts=["ADC","ADT","Control Error","Charge Status","DSR","End Power Transfer","PROP","16 bit Received Power"]
        res=[]
        id=self.Flow_limit[0]
        while id< self.Flow_limit[1]:
            Type=self.PktMethod.GetPacketType(id)
            if Type=='Packet'and self.file_list[id]['description']=="PT":
                ExpPacket=False
                for pkt in pkts:
                    if pkt in self.file_list[id]['pktType']:
                        ExpPacket=True
                        break
                if not ExpPacket:res.append([f'Prx sent {self.file_list[id]['pktType']} at @Id{id} .', 'Fail'])
            id+=1
        if len(res)==0:res.append([f'Prx sent ALL data Packets which are in the set :{pkts}', 'Pass'])
        else:res=res
        return res

    def Auth(self, CTSCheck, Check, flows, flwID):
        # check Authentication initiated or not
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        A=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth", limit=[self.Flow_limit[0],self.Flow_limit[1]])
        if len(A)>2:
            res.append([f'Prx initiated Authentication at @Id {A[2]}', 'Pass'])
        else:res.append([f'Prx did not initiated Authentication in first 250 packets', 'Inconclusive'])
        return res

    def PktsCountCTS(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Pktscount=0
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            TypeCheck=self.PktMethod.GetPacketType(id)
            if TypeCheck=='Packet' :Pktscount+=1
            id+=1
        res.append([f'PRx sent {Pktscount} Data packets.', 'Inconclusive'  if Pktscount < Check['Pkt_count'] else 'Pass'])
        return res

    def Tdsr(self, CTSCheck, Check, flows, flwID):
        #Find RP0
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            while id < self.Flow_limit[1]:
                # find Exp PTx Response
                PTXresp=self.PktMethod.GetPacketDetails(packet=Check['PTx'],Type="Response", limit=[id,self.Flow_limit[1]])
                if len(PTXresp)>2:
                    # Find Next ATN
                    ATN2=self.PktMethod.GetPacketDetails(packet="ATN",Type="Response" ,limit=[PTXresp[2]+1,self.Flow_limit[1]])
                    if len(ATN2)>2:
                        DSR=self.PktMethod.GetPacketDetails(packet="DSR", limit=[PTXresp[2]+1 , ATN2[2]])
                        if len(DSR)>2:
                            time=round((DSR[0]-PTXresp[1])*1000,2)
                            res.append([f'Prx sent DSR Packet at @Id {DSR[2]} ,{Check['Timing']}={time} mS', 'Pass' if time < 500 else 'Fail'])
                            id=DSR[2]+1
                        else:
                            res.append([f'Prx did not sent DSR Packet for the PTX- {Check['PTx']} at @Id {PTXresp[2]} ,{Check['Timing']}=-1ms', 'Fail'])
                            id=PTXresp[2]+1                                                    
                    else:
                        DSR=self.PktMethod.GetPacketDetails(packet="DSR", limit=[PTXresp[2]+1 , self.Flow_limit[1]])
                        if len(DSR)>2:
                            time=round((DSR[0]-PTXresp[1])*1000,2)
                            res.append([f'Prx sent DSR Packet at @Id {DSR[2]} ,{Check['Timing']}={time} mS', 'Pass' if time < 500 else 'Fail'])
                            id=DSR[2]+1
                        else:id+=1
                else:break
        else:res.append([f'Prx did not Entered PT Phase', 'Inconclusive'])
        return res

    def DSRPkts(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        Pktscount=0
        while id < self.Flow_limit[1]:

            DSR=self.PktMethod.GetPacketDetails(packet="DSR", limit=[id ,self.Flow_limit[1]])
            if len(DSR)>2:
                Pktscount+=1
                if "ND" in self.file_list[DSR[2]]['value'] or "POLL" in self.file_list[DSR[2]]['value'] or "ACK" in self.file_list[DSR[2]]['value'] or "NAK" in self.file_list[DSR[2]]['value']:
                    res.append([f'Prx sent DSR/{self.file_list[DSR[2]]['value']} pkt at @Id {DSR[2]}', 'Pass'])
                else:res.append([f'Prx sent DSR/{self.file_list[DSR[2]]['value']} pkt at @Id {DSR[2]},Exp :DSR/ND or DSR/POLL or DSR/NAK or DSR/ACK', 'Fail'])
                id=DSR[2]+1
            else:id+=1

        if Pktscount < 40:res.append([f'Prx  did not sent 40 DSR Pkts', 'Inconclusive'])
        return res
        
    def GeneralRequest(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Generalrequest=False
        PhaseLimit=self.FindPhase(self.Flow_limit[0],Check['SeqPhase'])
        if PhaseLimit is not None:
            id=PhaseLimit[0]
            while id < PhaseLimit[1]:
                TypeCheck=self.PktMethod.GetPacketType(id)
                if TypeCheck=='Packet' :
                    if self.file_list[id]['pktType']=="General Request":
                        Generalrequest=True
                        pktval=self.file_list[id]['value'].replace('{','').replace('}','').split(':')[0]
                        if pktval not in Check['ExpPkts']:
                            res.append([f'Prx sent the GRQ/{pktval} which is not Expected','Fail'])
                        else: res.append([f'Prx sent the GRQ/{pktval} data packet','Pass'])
                id+=1
            if not Generalrequest:res.append([f'Prx did not sent the General Request Packet','Pass'])
        else:res.append([f'Prx did not entered the {Check['SeqPhase']} Phase', 'Fail'])
        return res
        
    def PacketDetails(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id = self.Flow_limit[0]
        for ExpPacket in Check['ExpectedPacket']:
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=ExpPacket[0], value=ExpPacket[1], limit=[id,self.Flow_limit[1]])
            DataPacket= str(f'{ExpPacket[0]}{'_' + ExpPacket[1].replace('{','').replace('}','').replace(':','_') if ExpPacket[1] is not None else ''}')
            if len(ExpectedPacket_Details)>2:
                res.append([f'PRx sent the {DataPacket} datapacket.', "Pass"]) 
                if ExpPacket[2]: 
                    Pres=self.Payload_Details(PacketName=DataPacket,Index=ExpectedPacket_Details[2],PayLoads=ExpPacket[3])
                    if len(Pres)>0: res.extend(Pres) 
                id=ExpectedPacket_Details[2]+1
            else:res.append([f'PRx did not sent the {DataPacket} datapacket.', "Fail"])  
        return res
    
    def PacketDetails2(self, CTSCheck, Check, flows, flwID):
        
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        DataPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        id = self.Flow_limit[0]
        Pkt=False
        while id < self.Flow_limit[1]:
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=[id,self.Flow_limit[1]])
            if len(ExpectedPacket_Details)>2:
                if Check['ExpectedPacket'][2]: 
                    Pres=self.Payload_Details(PacketName=DataPacket,Index=ExpectedPacket_Details[2],PayLoads=Check['ExpectedPacket'][3])
                    if len(Pres)>0: res.extend(Pres) 
                id=ExpectedPacket_Details[2]+1
                Pkt=True
                res.append([f'PRx sent the {DataPacket} datapacket at @Id {ExpectedPacket_Details[2]}', "Pass"]) 
            else:break
        if not Pkt: res.append([f'PRx did not sent the {DataPacket} datapacket.', "Inconclusive"]) 
        return res
            
  
    def Tsignal_Tnext(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        res=[]
        id=0
        count=0
        SScount=0
        while id < len(self.file_list):
            pkt = self.PktMethod.GetPacketDetails(packet="Ping Initiated",limit=[id,len(self.file_list)],Type="TesterMsg")
            if len(pkt)>2:
                sd = self.PktMethod.GetPacketDetails(packet='CoilVoltpkpk',limit=[pkt[2],len(self.file_list)],Type="TesterMsg")
                if len(sd)>2:
                    count+=1
                    res.append([f'Sequence : {count}','Pass'])
                    Timing=round((float(sd[0]) - float(pkt[1]))*1000,2)
                    Limit=[round(Check['Tsignal'][0]-Check['Tsignal'][1],2),round(Check['Tsignal'][0]+Check['Tsignal'][1],2)]
                    res.append([f'TPT removed Power Signal within {Timing} mS after Initiating the Digital ping at {{{pkt[2]}}} , Limit : {Limit[0]} mS ~ {Limit[1]} mS', 'Pass' if Timing >= Limit[0] and Timing <= Limit[1] else "Inconclusive"])
                    if Check['SScheck']:
                            SS = self.PktMethod.GetPacketDetails(packet="Signal strength",limit=[pkt[2],sd[2]])
                            if len(SS)>2:SScount+=1

                    # Next Ping
                    dp = self.PktMethod.GetPacketDetails(packet="Ping Initiated",limit=[sd[2]+1,len(self.file_list)],Type="TesterMsg")
                    if len(dp)>2:
                        Timing=round((float(dp[1]) - float(sd[1]))*1000,2)
                        Limit=[round(Check['Tnext'][0]-Check['Tnext'][1],2),round(Check['Tnext'][0]+Check['Tnext'][1],2)]
                        res.append([f'TPT Initiated Next Digital ping at {{{dp[2]}}} within {Timing} mS from {round(sd[1],3)} Secs ,  : {Limit[0]} mS ~ {Limit[1]} mS', 'Pass' if Timing >= Limit[0] and Timing <= Limit[1] else "Inconclusive"])
                        id=dp[2]
                    else:break
                else:break
            else:break
        if count < Check['Pings']:res.append([f'TPT sent only {count} pings , Limit : {Check['Pings']}','Inconclusive'])
        if Check['SScheck']:res.append([f'PRx sent {SScount} Signal Strength Packets , Limit :10', 'Pass' if SScount >=10 else 'Fail']) 

        res=res
        return res

    def DeviceIDMatch(self, CTSCheck, Check, flows, flwID):
        #Get All ID packets and match it's Device ID
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id = 0
        DevID = []
        while id < len(self.file_list):
            if 'Identification' in self.file_list[id]['pktType']:
                IDPayload = self.PktMethod.GetPayloadDetails(id,"Basic_Device_identifier")
                if len(IDPayload)>0: DevID.append(IDPayload[0]['sRawData'])   
            id+=1
        if len(DevID)>1: res.append([f'PRx sent the Basic -Device Identifiers {DevID} for the Identification Packets.','Pass' if DevID[0]== DevID[1] else 'Fail'])
        else: res.append([f'Prx did not sent the sufficient Identification packets' ,'Inconclusive'])
        return res

    def CFG_S06_BPX(self, CTSCheck, Check, flows, flwID):

        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration", value="Neg:true",limit=self.Flow_limit)
        if len(CFG)>2:
            Response=self.PktResponse(CFG[2]+1,self.Flow_limit[1])
            if Response is not None:
                if Response[0] in Check['Response']:
                    res.append([f'TPT sent {Response[0]} response for the CFG/ep Packet, Expected: {Check["Response"]} ', 'Pass'])
                    if self.RP8_2nd([Response[1]+1,self.Flow_limit[1]]):
                        id=Response[1]+1
                        pkts=" , ".join(Check['Expkts'])
                        PktsCheck=True
                        while id < self.Flow_limit[1]:
                            if self.PktMethod.GetPacketType(id)=='Packet':
                                pktfound=False
                                for pkt in Check['Expkts']:
                                    if pkt in self.file_list[id]['pktType']:
                                        pktfound=True
                                        break
                                if not pktfound : 
                                    PktsCheck=False
                                    res.append ([f'PRx sent {self.file_list[id]['pktType']} pkt at index@ {id} which is not in the set {{{pkts}}}','Fail'])
                            id+=1
                        if PktsCheck: res.append([f'PRx sent all the Packets which are in the set {{{pkts}}}', 'Pass'])
                    else:  res.append([f'PRx did not sent second RP8 packet after the CFG/ep Packet', 'Inconclusive'])
                else:  res.append([f'TPT sent {Response[0]} response for the CFG/ep Packet, Expected:{Check["Response"]}', 'Inconclusive'])
            else:res.append([f'TPT did not sent Response for the CFG Packet', 'Inconclusive'])  
        else:res.append([f'Prx did not sent CFG/ep Packet', 'Inconclusive'])
        return res

    def NEG_S07_BPX(self, CTSCheck, Check, flows, flwID):

        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        pkt=f'{Check['pkt'][0]}_{Check['pkt'][1]}'
        FOD=self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1],limit=self.Flow_limit)
        if len(FOD)>2:
            res.append([f'PRx sent {pkt} packet at {{{FOD[2]}}}', 'Pass'])
            Response=self.PktResponse(FOD[2]+1,self.Flow_limit[1])
            if Response is not None:
                if Response[0] in Check['Response']:
                    res.append([f'TPT sent {Response[0]} response for the {pkt} Packet, Expected: {Check["Response"]} ', 'Pass'])
                    if self.RP8_2nd([Response[1]+1,self.Flow_limit[1]]):
                        # check if there any other FOD Packets
                        id=Response[1]+1
                        Fi=[]
                        while id <  self.Flow_limit[1]:
                            NFOD=self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1],limit=[id,self.Flow_limit[1]])
                            if len(NFOD)>2: 
                                Fi.append(NFOD[2])
                                if Check['pkt'][1] in self.file_list[NFOD[2]]['value']:
                                    res.append([f'PRx sent {pkt} packet at {{{NFOD[2]}}}', 'Pass'])
                                    Response=self.PktResponse(NFOD[2]+1,self.Flow_limit[1])
                                    if Response is not None:  res.append([f'TPT sent {Response[0]} response for the {pkt} Packet, Expected: {Check["Response"]} ', 'Pass' if Response[0] in Check['Response'] else 'Inconclusive' ])
                                    else:res.append([f'TPT did not sent Response for the {pkt} Packet', 'Inconclusive'])
                                id=NFOD[2]+1
                            else:break    
                        iid =FOD[2] + 1
                        pkts = " , ".join(Check['Expkts'])
                        PktsCheck = True
                        pktfound=False
                        count=0
                        while iid < self.Flow_limit[1]:
                            if self.PktMethod.GetPacketType(iid) == 'Packet':
                                count+=1
                                # Check whether current packet is a FOD packet
                                if iid in Fi:
                                    if pktfound: 
                                        PktsCheck =False
                                        res.append([f'PRx sent FOD packet at index@ {iid} after a packet from the set {{{pkts}}} was already received', 'Fail'])
                                else:
                                    # Check that it belongs to the allowed packet set.
                                    pktfound = True
                                    setpkt=False
                                    for pkt in Check['Expkts']:
                                        if pkt in  self.file_list[iid]['pktType']:
                                            setpkt = True
                                            break
                                    if not setpkt:
                                        PktsCheck = False
                                        res.append([f'PRx sent {self.file_list[iid]['pktType']} pkt at index@ {iid} which is not in the set {{{pkts}}}', 'Fail'])    
                            iid += 1
                        if count <0:res.append([f'PRx did not sent any packets', 'Inconclusive'])
                        elif PktsCheck:res.append([f'PRx sent all the Packets which are in the set {{{pkts}}}', 'Pass'])
                    else:  res.append([f'PRx did not sent second RP8 packet after the {pkt} Packet', 'Inconclusive'])
                else:  res.append([f'TPT sent {Response[0]} response for the {pkt} Packet, Expected:{Check["Response"]}', 'Inconclusive'])
            else:res.append([f'TPT did not sent Response for the {pkt}  Packet', 'Inconclusive'])  
        else:res.append([f'PRx did not sent {pkt} Packet', 'Inconclusive'])
        return res
     
    def DataPktsCheck(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],Check['SeqPhase'])
        if PhaseLimit is not None:
            Pktscount=self.PktsCount(PhaseLimit)
            if Check['PktsCount']:res.append([f'PRx sent {Pktscount+1} data packets Exp: {Check['PktsCount']}','Pass' if Pktscount+1 >= Check['PktsCount'] else "Inconclusive"])
            id=PhaseLimit[0]
            PktCheck=False
            Seqcheck=True
            # Check 2nd RP8 Data Packet and then chck the set
            rpcheck= self.RP8_2nd(PhaseLimit) if Check.get("RPCheck",True) else True
            if rpcheck:
                pkts=[]
                while id <= PhaseLimit[1]:
                    TypeCheck=self.PktMethod.GetPacketType(id)
                    if TypeCheck=='Packet':
                        if "Control Error" in self.file_list[id]['pktType'] :
                            if "Control Error" not in pkts:pkts.append(self.file_list[id]['pktType'])
                        elif "8 bit Received Power" in self.file_list[id]['pktType']:
                            if "8 bit Received Power" not in pkts:pkts.append(self.file_list[id]['pktType'])
                        elif "16 bit Received Power" in self.file_list[id]['pktType']:
                            if "16 bit Received Power" not in pkts:pkts.append(self.file_list[id]['pktType'])
                        else:
                            pkts.append(f'{self.file_list[id]['pktType']}_{self.file_list[id]['value']}')
                        if self.file_list[id]['pktType'].split("/")[0] not in  Check['Expkts'] and Check['PktCheck'] == "In": 
                            res.append([f'PRx sent {self.file_list[id]['pktType']}_{self.file_list[id]['value']} data packet which is not in Exp: {Check['Expkts']}','Fail'])
                            Seqcheck=False
                        if  Check['PktCheck'] == "Compulsory":
                            if self.file_list[id]['pktType'].split("/")[0]  in  Check['Expkts']: PktCheck=True                                
                    id+=1
                if PktCheck:res.append([f'PRx sent the {Check['Expkts'][0] } data packet','Pass'])
                elif Seqcheck :res.append([f'PRx sent the data packets :{pkts} within the List :{Check['Expkts']}','Pass'])
                else: 
                    if Check['PktCheck'] == "Compulsory":res.append([f'PRx did not sent the {Check['Expkts'][0] }data packet','Fail' ])
            else:res.append([f'Prx did not sent the 2nd RP8 data packet' ,'Inconclusive'])
        else:res.append([f'Prx did not entered the {Check['SeqPhase']} Phase','Pass'  if not Check['SeqPhaseCheck'] else 'Inconclusive'])
        return res
            
    def Response_TPT(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=self.Flow_limit)
        DataPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        if len(ExpectedPacket_Details)>2:
            resp = self.PktMethod.GetPacketResponse(ExpectedPacket_Details,[ExpectedPacket_Details[2]+1,self.Flow_limit[1]])
            if resp is not None:
                if self.file_list[resp]['pktType'] in Check['ExpResponse']:
                    res.append([f'PTx sent the {self.file_list[resp]['pktType']} as Response for the {DataPacket} datapacket ','Pass'])
                else: res.append([f'PTx sent the {self.file_list[resp]['pktType']} as Response for the {DataPacket} datapacket which is Not Expected.','Fail'])
            else:   res.append([f'PTx sent the {self.file_list[resp]['pktType']} as Response for the {DataPacket} datapacket ','Fail'])
        else: 
            result="Inconclusive" 
            if Check['Pkt']=='Compulsory':result="Fail"
            if Check['Pkt']=='NotMandatory':result="Pass"
            res.append([f'Prx did not sent the {DataPacket} datapacket.', result])  
        return res

    def LogPkts(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            if  Check['EndRequired']:
                EndPacket= str(f'{Check['EndPacket'][0]}{'_' + Check['EndPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['EndPacket'][1] is not None else ''}')
                EndPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['EndPacket'][0], value=Check['EndPacket'][1], limit=[StartPacket_Details[2]+1,self.Flow_limit[1]])
            else: EndPacket_Details=[0,0,self.Flow_limit[1]]
            if len(EndPacket_Details)>2:
                LoggedPkts=self.LogPackets([StartPacket_Details[2]+1,EndPacket_Details[2]])
                ExpPkts=True
                PktCheck=3
                for Pkt in LoggedPkts:
                    if Check['Pkt'] :
                        if Pkt[0] in Check['ExpPkts'][0]:                                                        
                            if self.packet_matches(packet_id=Pkt[1],Pkt=Pkt[0],PktVal=Check['ExpPkts'][1]):
                                res.append([f'Prx sent {Pkt[0]}_{Check['ExpPkts'][1] if Check['ExpPkts'][1] is not None else ''} datapacket at index @{Pkt[1]}','Pass'])
                                if Check['ExpPkts'][2]:
                                    PktCheck+=1
                                    Pres=self.Payload_Details(PacketName=f"{Pkt[0]}_{Check['ExpPkts'][1] if Check['ExpPkts'][1] is not  None else ''}",Index=Pkt[1],PayLoads=Check['ExpPkts'][3])
                                    if len(Pres)>0:res.extend(Pres)
                                ExpPkts=False                                                        
                    else:
                        if Pkt[0] not in Check['ExpPkts']: 
                            res.append([f'Prx sent {Pkt[0]} datapacket at index @{Pkt[1]}','Fail'])
                            ExpPkts=False
                if ExpPkts and not Check['Pkt']: res.append([f'Prx sent all datapackets which are in List :{Check['ExpPkts']}','Pass'])
                elif ExpPkts and Check['Pkt'] and Check['ExpPkts'][PktCheck]=="Compulsory": res.append([f'Prx did not sent {Check['ExpPkts'][0]}_{Check['ExpPkts'][1] if Check['ExpPkts'][1] is not  None else ''} datapacket','Fail'])
                elif ExpPkts and Check['Pkt']: res.append([f'Prx did not sent {Check['ExpPkts'][0]}_{Check['ExpPkts'][1] if Check['ExpPkts'][1] is not  None else ''} datapacket','Pass'])
            else:res.append([f'TPT did not found {EndPacket} datapacket','Inconclusive'])
        else:res.append([f'PRx did not entered  {Check['Phase']} Phase','Inconclusive'])
        return res

    def PktsCheck(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            EndPacket= str(f'{Check['EndPacket'][0]}{'_' + Check['EndPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['EndPacket'][1] is not None else ''}')
            EndPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['EndPacket'][0], value=Check['EndPacket'][1], limit=[StartPacket_Details[2]+1,self.Flow_limit[1]])
            if len(EndPacket_Details)>2:
                LoggedPkts=self.LogPackets([StartPacket_Details[2],EndPacket_Details[2]])
                ExpPkts=True
                pkts=[]
                for pkt in Check['ExpPkts']:
                    pktcheck=False
                    if pkt[1] is not None:
                        pkts.append(f'{pkt[0]}_ {pkt[1]}')
                        for pair in [(p[0], p[2]) for p in LoggedPkts]:
                            if pkt[0] in pair[0] and pkt[1] in pair[1]:pktcheck=True

                        if Check['Pkts']=="All" and not pktcheck:
                            res.append([f'Prx did not sent {pkt[0]} {'' if pkt[1] is None else pkt[1]} datapacket','Inconclusive' if Check.get('Inconclusive_Check',False) else 'Fail'])
                            ExpPkts=False 
                        else: 
                            if not pktcheck:res.append([f'Prx did not sent {pkt[0]} {'' if pkt[1] is None else pkt[1]} datapacket','Pass'])      
                
                    else:
                        pkts.append(pkt[0])
                        if pkt[0] not in [p[0] for p in LoggedPkts]:
                            if Check['Pkts']=="All":
                                res.append([f'Prx did not sent {pkt[0]} {'' if pkt[1] is None else pkt[1]} datapacket','Inconclusive' if Check.get('Inconclusive_Check',False) else 'Fail'])
                                ExpPkts=False 
                            else: res.append([f'Prx did not sent {pkt[0]} {'' if pkt[1] is None else pkt[1]} datapacket','Pass'])      
                   
                    if pktcheck:
                        pkt_ids = [p[1] for p in LoggedPkts if p[0] == pkt[0]]
                        for pkt_id in pkt_ids:
                            if self.packet_matches(packet_id=pkt_id, Pkt=pkt[0], PktVal=pkt[1]):
                                res.append([f'Prx sent {pkt[0]}_{pkt[1]} datapacket at index @{pkt_id}','Pass'])
                                Tres=self.RspTimngCheck(f"{pkt[0]}_{pkt[1]}", pkt, pkt_id)                                                          
                                if len(Tres) > 0: res.extend(Tres)
                                break    
                if ExpPkts and Check['Pkts']=="All": res.append([f'Prx sent all datapackets which are in List :{pkts}','Pass'])               
            else:res.append([f'TPT did not found {EndPacket} datapacket','Inconclusive'])
        else:res.append([f'TPR did not entered  {Check['Phase']} Phase','Inconclusive'])
        return res

    def Nchanged(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=self.Flow_limit)
        ExpectedPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        if len(ExpectedPacket_Details)>2 :
            resp = self.PktMethod.GetPacketResponse(ExpectedPacket_Details,[ExpectedPacket_Details[2]+1,self.Flow_limit[1]])
            if resp is not None:
                if self.file_list[resp]['pktType'] =="ACK":
                    res.append([f'TPT sent the {self.file_list[resp]['pktType']} as Response for the {ExpectedPacket} datapacket due to  Nchanged of elements changed in the Power Transfer Contract are Equal ','Pass'])
                else: res.append([f'TPT sent  the {self.file_list[resp]['pktType']} as Response for the {ExpectedPacket} datapacket due to Nchanged of elements changed in the Power Transfer Contract are not Equal','Fail'])
            else:  res.append([f'TPR Received the {self.file_list[resp]['pktType']} as Response for the {ExpectedPacket} datapacket ','Fail'])
            
        else:
            res.append([f'PRx did not entered  {Check['Phase']} Phase','Inconclusive'])
        return res

    def PacketDetails_TPT(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id = self.Flow_limit[0]
        ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet= Check['ExpectedPacket'][0], value= Check['ExpectedPacket'][1], limit=[id,self.Flow_limit[1]],Type="Response")
        DataPacket= str(f'{ Check['ExpectedPacket'][0]}{'_' +  Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if  Check['ExpectedPacket'][1] is not None else ''}')
        if len(ExpectedPacket_Details)>2:
            if  Check['ExpectedPacket'][2]: 
                Pres=self.Payload_Details(PacketName=DataPacket,Index=ExpectedPacket_Details[2],PayLoads= Check['ExpectedPacket'][3],Receiver=False)
                if len(Pres)>0: res.extend(Pres) 
            id=ExpectedPacket_Details[2]+1
            res.append([f'TPT sent the {DataPacket} Response.', "Pass"]) 
        else:res.append([f'TPT did not sent the {DataPacket} Response.', "Inconclusive"])   
        return res

    def PhasePkts(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],Check['SeqPhase'])
        if PhaseLimit is not None:
            if Check['Count']:
                Pktscount=self.PktsCount(PhaseLimit)
                if  Pktscount >= Check['PktsCount'] :res.append([f'PRx sent {Pktscount} data packets Exp: {Check['PktsCount']}','Pass'])
                else:res.append([f'PRx sent {Pktscount} data packets Exp: {Check['PktsCount']}','Inconclusive'])
            else:res.append([f'PRx entered in to {Check['SeqPhase'] } Phase','Pass'])
        else:res.append([f'PRx did not entered in to {Check['SeqPhase'] } Phase','Inconclusive' if not  Check['PhaseCheck'] else 'Fail'])
        return res

    def Renego(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            i=RP0[2]+1
            Renegotiate=False
            while i < self.Flow_limit[1]:
                # Log the first DSR or Nego Pkt
                Type=self.PktMethod.GetPacketType(i)
                if Type=='Packet':
                    if self.file_list[i]['pktType']==Check['Pkt'][0]  :
                        res.append([f'Prx sent Renegotiate Data packet at @Id {i} .', 'Pass']) 
                        Renegotiate=True   
                        if Check['Pkt'][2]:
                            Pres=self.Payload_Details(Check['Pkt'][0],i,Check['Pkt'][3])
                            res.extend(Pres) 
                i+=1
            if not Renegotiate:res.append([f'Prx did not sent Renegotiate Data packet', 'Pass'])
                        
        else:res.append([f'Prx did not Entered PT Phase', 'Inconclusive'])
        return res

    def ADTSeq(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            while id < self.Flow_limit[1]:
                ADCAuth=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth", limit=[id,self.Flow_limit[1]])
                if len(ADCAuth)>2:
                    ADCEnd=self.PktMethod.GetPacketDetails(packet="ADC",value="End", limit=[ADCAuth[2]+1,self.Flow_limit[1]])
                    if len(ADCEnd)>2:
                        #Find ADT Pkts Between AUth sequence
                        iD =ADCAuth[2]+1
                        ADTPkts=[]
                        while iD < ADCEnd[2]:
                            ADT=self.PktMethod.GetPacketDetails(packet="ADT", limit=[iD,ADCEnd[2]])
                            if len(ADT)>2:
                                ADTPkts.append(ADT[2])
                                iD=ADT[2]+1
                            else:break
                        if len(ADTPkts)==1:res.append([f'Prx sent only One {self.file_list[iD-1]['pktType']} at @Id {iD-1} in between the Sequence From {self.file_list[ADCAuth[2]]['pktType']} at @Id {ADCAuth[2]} to {self.file_list[ADCEnd[2]]['pktType']} at @Id {ADCEnd[2]}', 'Pass'])                                                    
                        elif len(ADTPkts)==0:res.append([f'Prx did not sent any ADT data Packets in bewtween the sequence', 'Inconclusive'])
                        else:
                            for i,j in zip(ADTPkts,ADTPkts[1:]):
                                if self.file_list[i]['pktType'][-1] != self.file_list[j]['pktType'][-1]:
                                    res.append([f'Prx sent different {self.file_list[i]['pktType']} at @Id {i},{self.file_list[j]['pktType']} at @Id {j} in between the Sequence From {self.file_list[ADCAuth[2]]['pktType']} at @Id {ADCAuth[2]} to {self.file_list[ADCEnd[2]]['pktType']} at @Id {ADCEnd[2]}', 'Pass'])
                                else:res.append([f'Prx sent same {self.file_list[i]['pktType']} at @Id {i},{self.file_list[j]['pktType']} at @Id {j} in between the Sequence From {self.file_list[ADCAuth[2]]['pktType']} at @Id {ADCAuth[2]} to {self.file_list[ADCEnd[2]]['pktType']} at @Id {ADCEnd[2]}', 'Fail'])
                        id=ADCEnd[2]+1
                    else:break
                else:break                
        else:res.append([f'Prx did not Entered PT Phase', 'Inconclusive'])
        return res

    def RPPkts(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id =self.Flow_limit[0]
        Pktscount=0
        RP={ "1":[0,"NAK"],"2":[0,"NAK"],"0":[0,"NAK"],"4":[0,"NAK"] }
        RPSeq=True

        def Response(mode):
            resp=self.PktMethod.GetPacketResponse(index=id+1,limit=[id+1,self.Flow_limit[1]])
            if resp is not None:RP[mode]=[RP[mode][0]+1, self.file_list[resp]['pktType']]

        def Breakseq(RPMode,id,description):
            res.append([f'Prx sent 16 Bit RP Packet with Mode :{RPMode} at @ID {id} {description}', 'Fail'])
            return False
            
        while id < self.Flow_limit[1]:
            Type=self.PktMethod.GetPacketType(id)
            if Type=='Packet':
                if self.file_list[id]['pktType']== "16 bit Received Power":
                    Pktscount+=1
                    RPMode=self.file_list[id]['value'].split(',')[0][-1]
                    if RPMode=="1":
                        if RP['2'][0] <1:Response(mode="1")
                        else:
                            RPSeq=Breakseq(RPMode,id,description='even after the  Previous Mode:2')
                            break  
                    elif RPMode=="2":
                        if RP['1'][1]=="ACK":
                            if RP['0'][0]<1:Response(mode="2")
                            else:
                                RPSeq=Breakseq(RPMode,id,description='even after the  Previous Mode:0')
                                break
                        else:
                            RPSeq=Breakseq(RPMode,id,description='even before the ACK of Previous Mode:1')
                            break
                    elif RPMode=="0":
                        if RP['2'][1]=="ACK":Response(mode="0")
                        else:
                            RPSeq=Breakseq(RPMode,id,description='even before the ACK of Previous Mode:2')
                            break
                    elif RPMode=="4":
                        if RP['2'][1]=="ACK":Response(mode="4")
                        else:
                            RPSeq=Breakseq(RPMode,id,description='even before the ACK of Previous Mode:2')
                            break
                    else:
                        RPSeq=Breakseq(RPMode,id,description='')
                        break
            id+=1
        if RPSeq:
            if Pktscount ==0:
                res.append([f'PRx did not sent any RP Packets in the Sequence', 'Fail'])
            else: res.append([f'Prx sent ALL RP data packets with mode 1,2,0 or 4', 'Pass'])
        return res

    def Tinterval_Treceived(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Timings=[]
        PktsCount=0
        FailCount=0
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            pkt1= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=[id,self.Flow_limit[1]])
            if len(pkt1)>2:
                PktsCount+=1
                pkt2=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1], limit=[pkt1[2]+1,self.Flow_limit[1]])
                if len(pkt2)>2:
                    Tinterval=round((pkt2[0]-pkt1[0])*1000,2)
                    Timings.append(Tinterval)
                    if Tinterval > Check['Limit'][1] :FailCount+=1
                    # res.append([f'Measured {Check['TimingCheck']} from {Check['Pkt'][0]} at Id {pkt1[2]} to {Check['Pkt'][0]} at Id {pkt2[2]} is {Tinterval} mS', "Fail" if Tinterval > Check['Limit'][1] else 'Pass'])
                    id=pkt2[2]
                else:break
            else:break

        if FailCount >  int(0.05 * len(Timings)):
            res.append([f'Measured  Max {Check['TimingCheck']} is {max(Timings)} mS ,Min {Check['TimingCheck']} is {min(Timings)} mS Limit : <={Check['Limit'][1] }', "Fail"])
            res.append([f'More than 5% of the Intervals met the fail criteria', "Fail"])
        else:res.append([f'Measured  Max {Check['TimingCheck']} is {max(Timings)} mS ,Min {Check['TimingCheck']} is {min(Timings)} mS Limit : <={Check['Limit'][1] }', "Pass"])
        if PktsCount< Check['Pkts']:res.append([f'Prx sent {PktsCount} {Check['Pkt'][0]} data packets only', "Inconclusive"])
        return res
    
    def PktReponses(self, CTSCheck, Check, flows, flwID):
   
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PKT= str(f'{Check['Pkt'][0]}{'_' + Check['Pkt'][1].replace('{','').replace('}','').replace(':','_') if Check['Pkt'][1] is not None else ''}')
        id=self.Flow_limit[0]
        Pkts=False
        while id < self.Flow_limit[1]: 
            Pkt=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=[id,self.Flow_limit[1]])
            if len(Pkt)>2:
                #Check the Response defined in CTS Checks
                Pkts=True
                resp=self.PktResponse(Pkt[2]+1,self.Flow_limit[1])
                if resp is None and  Check['response'] is None: res.append([f'PTx did not sent any Response for {PKT} Data packet at @Id {Pkt[2]}','Pass'])
                else:
                    if resp is not None and resp[0] in Check['response']:
                        res.append([f'PTx sent Response {resp[0]} for {PKT} Data packet at @Id {Pkt[2]}','Pass'])
                        if Check['Timing']:
                            ResponseTime= round(( self.file_list[resp[1]]['startTime']-self.file_list[Pkt[2]]['stopTime'])*1000,3)
                            res.append([f'Measured response Time Between {PKT} and {resp[0]} is {ResponseTime} mS ','Fail'if ResponseTime < Check['ExpTime'][0]-Check['ExpTime'][1] or ResponseTime >Check['ExpTime'][0]+Check['ExpTime'][1] else "Pass"])
                    else:
                        if resp is None:res.append([f'PRx did not Entered PT phase','Inconclusive'])
                        else:res.append([f'PTx sent Response {resp[0]} for {PKT} Data packet at @Id {Pkt[2]}','Fail'])
                id=Pkt[2]+1
            else:id+=1   

        if not Pkts:res.append([f'Prx did not sent {PKT} data packets', "Pass"])
        return res

    def Tcontrol_Tdelay(self, CTSCheck, Check, flows, flwID):

        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Pchtime=self.PchTime(Check['Neg'])
        PktsCount=0
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            pkt1= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=[id,self.Flow_limit[1]])
            if len(pkt1)>2:
                PktsCount+=1
                nextid=self.findTypeid(limit=[pkt1[2]+1,self.Flow_limit[1]],Type='Packet')
                if nextid is not None:
                    TDC=round((self.file_list[nextid]['startTime']-self.file_list[pkt1[2]]['stopTime'])*1000,2)
                    result= 'Pass' if TDC+Pchtime>Pchtime+24 else 'Fail'
                    res.append([f'Measured Timing between Control Error at @ Id {pkt1[2]} and {self.file_list[nextid]['pktType']} at @Id {nextid} is {TDC} mS  Limit: >= {Pchtime+24} mS', result])
                    id=nextid
                else:break
            else:break
        
        if PktsCount< Check['Pkts']:res.append([f'Prx sent {PktsCount} {Check['Pkt'][0]} data packets only', "Inconclusive"])
        return res

    def TsilentChecks(self, CTSCheck, Check, flows, flwID):
        
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PktsCount=0
        id=self.Flow_limit[0]
        
        def nextPkt(nextid,id,PktsCount):
            TDC=round((self.file_list[nextid]['startTime']-self.file_list[id]['stopTime'])*1000,2)
            result= 'Pass' if TDC>=6 else 'Fail'
            res.append([f'Measured Timing between {self.file_list[id]['pktType']} at @ Id {id} and {self.file_list[nextid]['pktType']} at @Id {nextid} is {TDC} mS  Limit: >= 6 mS', result])
            id=nextid
            return id

        while id < self.Flow_limit[1]:
            Type=self.PktMethod.GetPacketType(id)
            if Type=='Packet':
                if Check['combine']:PktsCount+=1 
                if any(key in self.file_list[id]['pktType'] for key in Check['Pkt']):
                        if not Check['combine']:PktsCount+=1 
                        # find next packet
                        nextid=self.findTypeid(limit=[id+1,self.Flow_limit[1]],Type='Packet')
                        if nextid is not None:id=nextPkt(nextid,id,PktsCount)  
                        else:break
                else:
                    if Check['EPP'] and any(key in self.file_list[id]['pktType'] for key in Check['Pkt2']):
                        if not Check['combine']:PktsCount+=1 
                        resp=self.PktResponse(id+1,self.Flow_limit[1])
                        if resp is not None:
                            # find next packet
                            nextid=self.findTypeid(limit=[resp[1]+1,self.Flow_limit[1]],Type='Packet')
                            if nextid is not None:id=nextPkt(nextid,resp[1],PktsCount)
                            else:break
                        else:break
                    else:id+=1
            else:id+=1
        if PktsCount< Check['Pkts']:res.append([f'Prx sent {PktsCount} {Check['Pkt'][0]} data packets only', "Inconclusive"])
        return res

    def ResponseNak(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        Count=0
        while id < self.Flow_limit[1]:
            if Count >=Check['Count']:break
            RP1=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:1", limit=[id,self.Flow_limit[1]])
            if len(RP1)>2:
                Count+=1
                resp=self.PktResponse(RP1[2]+1,self.Flow_limit[1])
                if resp is not None:
                    res.append([f'PTx sent response as {resp[0]} to RP Packet at @Id {RP1[2]}', "Pass" if Check['response'] in resp[0] else 'Fail'])
                else:res.append([f'PTx did not sent response  to RP Packet at @Id {RP1[2]}', "Inconclusive"])
                id=RP1[2]+1
            else:break
        if Count < Check['Count']:res.append([f'Prx did not sent only {Count} RP1 data packets', "Inconclusive"])
        return res

    def TimeBetweenPkts(self, CTSCheck, Check, flows, flwID):
       
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        pkt1=self.find_pkt(Check,self.Flow_limit[0],self.Flow_limit[1],Pktstr="Pkt1")            
        if len(pkt1)>2:
            pkt2=self.find_pkt(Check,pkt1[2]+1,self.Flow_limit[1],Pktstr="Pkt2") 
            if len(pkt2)>2:      
                Tinterval=round((pkt2[0]-pkt1[1])*1000,2)
                res.append([f'Measured {Check['TimingCheck']} from {Check['Pkt1'][0]} at Id {pkt1[2]} to {Check['Pkt2'][0]} at Id {pkt2[2]} is {Tinterval} mS Limit: <={Check['Limit'][1]}', "Fail" if Tinterval > Check['Limit'][1] else 'Pass'])
            else:res.append([f'Prx did not sent the {Check['Pkt2'][0]} Pkt.', "Inconclusive"])   
        else:res.append([f'Prx did not sent the {Check['Pkt1'][0]} Pkt.', "Inconclusive"])   
        return res
            
    def WDW(self, CTSCheck, Check, flows, flwID):

        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration",limit=self.Flow_limit)
        if len(CFG)>2:
            Toffset=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(CFG[2],"Window_Offset")[0]['sRawData'])
            Twindow=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(CFG[2],"Window_Size")[0]['sRawData'])
            Pchtime=self.PchTime(Check['Neg'])
            pktCount=0
            id=CFG[2]+1
            while id < self.Flow_limit[1]:
                RP= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=[id,self.Flow_limit[1]])
                if len(RP)>2:
                    # find the previous pkt
                    i=RP[2]-1
                    while i > self.Flow_limit[0]:
                        Type=self.PktMethod.GetPacketType(i)
                        if Type=='Packet':
                            Timing=round((RP[0]-self.file_list[i]['stopTime'])*1000,2)
                            result= 'Pass' if Timing+5.5 >= (Pchtime + (Twindow*4)+(Toffset*4)+6) else 'Fail'
                            if self.file_list[i]['pktType']=="Control Error":result= 'Pass' if Timing+5.5 >= (Pchtime + (Twindow*4)+(Toffset*4)+24) else 'Fail' 
                            res.append([f'Measured Timing from { self.file_list[i]['pktType']} at Id {i} to {Check['Pkt'][0]} at Id {RP[2]} is {Timing+5.5} mS', result])
                            break
                        else:i-=1
                    id=RP[2]+1
                    pktCount+=1
                else:break
            if pktCount < Check['Pkts']:res.append([f'PRx sent only {pktCount} {Check['Pkt'][0]} pkts', "Inconclusive"])   
        else:res.append([f'Prx did not sent the CFG Packet', "Inconclusive"])   
        return res

    def RenegoTiming(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Reneg=False
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            # find the renegotiate packet
            Renego=self.PktMethod.GetPacketDetails(packet="Renegotiate", limit=[id,self.Flow_limit[1]])
            if len(Renego)>2:
                Reneg=True
                # find RP0 before the renegotiate pkt
                AfterRP0=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1], limit=[Renego[2]+1,self.Flow_limit[1]])
                if len(AfterRP0)>2:
                    BeforeRP0=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1], limit=[Renego[2],self.Flow_limit[0]])
                    Timing=round((AfterRP0[0]-BeforeRP0[0])*1000,2)
                    res.append([f'Measured {Check['TimingCheck']} from {Check['Pkt'][0]} at Id {BeforeRP0[2]} to {Check['Pkt'][0]} at Id {AfterRP0[2]} is {Timing} mS', "Fail" if Timing > Check['Limit'][1] else 'Pass'])
                    id=AfterRP0[2]+1
                else:res.append([f'Prx did not sent the {Check['Pkt'][0]} after Renego Packet', "Inconclusive"])        
            else:break
        if not Reneg:res.append([f'Prx did not sent the Renegotaite Packet', "Inconclusive"])   
        return res
        
    def RenegoTimingSeq(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            i=RP0[2]+1
            PTCAP=self.PktMethod.GetPacketDetails(packet="Power Transmitter Capability",Type='Response', limit=[i,self.Flow_limit[1]])
            if len(PTCAP)>2:
                # find renego seq limits
                phaselimit=self.FindPhase(PTCAP[2]+1,Phase="ReNego")
                if phaselimit is not None:
                    #find SRQ/GP in the Reneg seqence
                    GP=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Guaranteed Load Power", limit=phaselimit)
                    if len(GP)>2:
                        GPval=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(GP[2],'Guaranteed_Power_Value')[0]['sRawData'])
                        res.append([f'Prx sent SRQ/GP  with value {GPval/2}in the  Sequence at @Id {GP[2]}', "Fail"  if GPval > 10 else 'Pass'])   
                    else:res.append([f'Prx did not Initiated SRQ/GP in the  Sequence ', "Inconclusive"])   
                else: 
                    # Check for EPT
                    EPT=self.PktMethod.GetPacketDetails(packet="End Power Transfer", limit=[PTCAP[2]+1,self.Flow_limit[1]])
                    if len(EPT)>2:res.append([f'PRx sent EPT Data Packet at @Id {EPT[2]}', "Pass"])   
                    else:res.append([f'PRx did not Initiated ReNego Sequence', "Inconclusive"])   
            else:res.append([f'PTx did not sent the PT-CAP Packet', "Inconclusive"])   
        else:res.append([f'Prx did not Entered PT Phase', "Inconclusive"])   
        return res

    def TC8437(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            i=RP0[2]+1
            RenegPkt=False
            while i < self.Flow_limit[1]:
                # find renego packet
                Renego=self.PktMethod.GetPacketDetails(packet="Renegotiate", limit=[i,self.Flow_limit[1]])
                if len(Renego)>2:
                    RenegPkt=True
                    # find the Response for Renego
                    resp=self.PktResponse(Renego[2]+1,self.Flow_limit[1])
                    if resp is not None:
                        res.append([f'TPT sent Response :{resp[0]} for Renegotaite Pkt at @ID {Renego[2]}', "Pass" if resp[0] in Check['Response'] else "Inconclusive"])   
                        # find Next received pkt
                        nextid=self.findTypeid(limit=[resp[1]+1,self.Flow_limit[1]],Type='Packet')
                        if nextid is not None:
                            if 'PROP' in self.file_list[nextid]['pktType']:continue
                            else:
                                if any(key in self.file_list[nextid]['pktType'] for key in Check['Pkt']):
                                    res.append([f'Prx sent pkt: {self.file_list[nextid]['pktType']}at id {nextid} after the Renegotaite Pkt at @ID {Renego[2]}', "Pass"]) 
                                else:res.append([f'Prx sent pkt: {self.file_list[nextid]['pktType']} at id {nextid} after the Renegotaite Pkt at @ID {Renego[2]}', "Fail"]) 
                    else:res.append([f'TPT did not sent Response for Renegotaite Pkt at @ID {Renego[2]}', "Inconclusive"])   
                    i=Renego[2]+1
                else:break
            if not RenegPkt:res.append([f'Prx did not sent Renego Packet', "Pass"])     
        else:res.append([f'Prx did not Entered PT Phase', "Inconclusive"])   
        return res
    
    def TC8436(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            i=RP0[2]+1
            RenegPkt=False
            # find renego seq limits
            phaselimit=self.FindPhase(i,Phase="ReNego")
            if phaselimit is not None:
                k=i
                while k < self.Flow_limit[1]:
                    phaselimit=self.FindPhase(k,Phase="ReNego")
                    if phaselimit is not None:
                        # find all Reneg seq
                        j=phaselimit[0]
                        while j < phaselimit[1]:
                            if any(
                                    (key in self.file_list[j]['pktType']) if value is None else (key in self.file_list[j]['pktType'] and value in self.file_list[j]['value'])
                                    for key, value in Check['Pkt']
                                ):res.append([f'Prx sent pkt: {self.file_list[j]['pktType']}_{self.file_list[j]['value']} at id {j} in the Reneg Sequence', "Pass"]) 
                            else:res.append([f'Prx sent pkt: {self.file_list[j]['pktType']}_{self.file_list[j]['value']} at id {j} in the Reneg Sequence', "Fail"]) 
                            j+=1
                        k=phaselimit[1]+1
                    else:break
            else:
                GP=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Guaranteed Load Power", limit=[self.Flow_limit[0],i])
                GPval=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(GP[2],'Guaranteed_Power_Value')[0]['sRawData'])
                if GPval <=10 :res.append([f'Prx sent SRQ/GP  with value {GPval/2}in the  Sequence at @Id {GP[2]}', 'Pass'])   
                else:res.append([f'Prx dis not Initiated Renego sequence .', 'Inconclusive'])   
        else:res.append([f'Prx did not Entered PT Phase', "Inconclusive"])   
        return res

    def ResponseAfterPkt(self, CTSCheck, Check, flows, flwID):
    
        # check the ATN response for 2nd rp Packet
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CE=self.PktMethod.GetPacketDetails(packet="Control Error",limit=self.Flow_limit)
        if len(CE)>2:
            id =CE[2]+1
            while id < self.Flow_limit[1]:
                # find Next response pkt
                resid=self.findTypeid(limit=[id,self.Flow_limit[1]],Type='Response')
                if resid is not None:
                    nextid=self.findTypeid(limit=[resid,self.Flow_limit[1]],Type='Packet')
                    if nextid is not None:
                        if any(key in self.file_list[nextid]['pktType'] for key in Check['Pkt']):
                            res.append([f'Prx sent pkt: {self.file_list[nextid]['pktType']} at id {nextid} after the Response at ID {resid}', "Pass"]) 
                        else:res.append([f'Prx sent pkt: {self.file_list[nextid]['pktType']} at id {nextid} after the Response at ID {resid}', "Fail"]) 
                        id=nextid+1
                    else:break
                else:break
        else:res.append([f'Prx did not sent CE Pkts', 'Inconclusive'])
        return res

    def FtQt(self, CTSCheck, Check, flows, flwID):

        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        for pkt in Check['pkts']:
            FODpkt=self.PktMethod.GetPacketDetails(packet= "FOD Status",value=pkt[0],limit=self.Flow_limit)
            if len(FODpkt)>2:
                FODpktval=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(FODpkt[2],'FOD_support_data')[0]['sRawData'])
                if pkt[0]=="Rf":FODpktval=(72+FODpktval)*0.5
                SDFval=self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel'][pkt[1]]
                result='Pass' if SDFval > (FODpktval-(FODpktval*pkt[2]/100)) and SDFval< (FODpktval+(FODpktval*pkt[2]/100)) else 'Fail'
                res.append([f'Prx sent FOD/{pkt[0]} Pkt with val {FODpktval} and in SDF it was set to {SDFval}', result])
                if pkt[0]=="Qf":res.append([f'Prx sent FOD/{pkt[0]} Pkt with Val {FODpktval}', 'Fail' if FODpktval < 25 else 'Pass'])
            else:res.append([f'Prx did not sent FOD/{pkt[0]} Pkt', 'Fail'])
        return res

    def SRQCheck(self, CTSCheck, Check, flows, flwID):
       
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        FP=self.PktMethod.GetPacketDetails(packet= Check['inpkt'][0],value=Check['inpkt'][1],limit=self.Flow_limit)
        if len(FP)>2:
            EP=self.PktMethod.GetPacketDetails(packet= Check['enpkt'][0],value=Check['enpkt'][1],limit=[FP[2]+1,self.Flow_limit[1]])
            if len(EP)>2:
                id =FP[2]+1
                while id < EP[2]:
                    if self.file_list[id]['pktType'] in ["SRQ [0x20] "]:
                        if any ( value not in self.file_list[id]['value'] for value in Check['values']):
                                  res.append([f'Prx sent pkt: {self.file_list[id]['pktType']}_{self.file_list[id]['value']} at id {id} ', "Pass"]) 
                        else:res.append([f'Prx sent pkt: {self.file_list[id]['pktType']}_{self.file_list[id]['value']} at id {id}', "Fail"]) 
                    id+=1
            else:res.append([f'Prx did not sent {Check['enpkt'][0]} _{Check['enpkt'][1] }Pkt', 'Inconclusive'])
        else:res.append([f'Prx did not sent {Check['inpkt'][0]} _{Check['inpkt'][1] }Pkt', 'Inconclusive'])
        return res

    def Tsient_Nego(self, CTSCheck, Check, flows, flwID):
        # find the reponse from 
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        FP=self.PktMethod.GetPacketDetails(packet= Check['inpkt'][0],value=Check['inpkt'][1],limit=self.Flow_limit)
        if len(FP)>2:
            EP=self.PktMethod.GetPacketDetails(packet= Check['enpkt'][0],value=Check['enpkt'][1],limit=[FP[2]+1,self.Flow_limit[1]])
            if len(EP)>2:
                id=FP[2]+1
                while id < EP[2]-1:
                    resid=self.findTypeid(limit=[id,self.Flow_limit[1]],Type='Response')
                    if resid is not None:
                        nextid=self.findTypeid(limit=[resid,self.Flow_limit[1]],Type='Packet')
                        if nextid is not None:
                            Tstart=round(((self.file_list[nextid]['startTime']-self.file_list[resid]['stopTime'])*1000)+5.5,2)
                            Tsilent=round((self.file_list[nextid]['startTime']-self.file_list[resid]['stopTime'])*1000,2)
                            res.append([f'Measured Tsilent Timing from Response:{self.file_list[resid]['pktType']} at Id {resid} to pkt :{self.file_list[nextid]['pktType']}_{self.file_list[nextid]['value']} at Id {nextid} is {Tsilent} mS', 'Pass' if Tsilent >6 else 'Fail'])
                            res.append([f'Measured Tstart Timing from Response:{self.file_list[resid]['pktType']} at Id {resid} to pkt :{self.file_list[nextid]['pktType']}_{self.file_list[nextid]['value']} at Id {nextid} is {Tstart} mS', 'Fail' if Tstart >19 or Tstart<11.5 else 'Pass'])
                            id=nextid+1
                        else:break
                    else:break
            else:res.append([f'Prx did not sent {Check['enpkt'][0]} _{Check['enpkt'][1] }Pkt', 'Inconclusive'])
        else:res.append([f'Prx did not sent {Check['inpkt'][0]} _{Check['inpkt'][1] }Pkt', 'Inconclusive'])
        return res

    def GP(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        res=[]
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration",limit=self.Flow_limit)
        if len(CFG)>2:
            # find Test Stop
            Timing= round((self.file_list[len(self.file_list)-2]['stopTime']-self.file_list[CFG[2]]['stopTime'])*1000,2)
            res.append([f'Prx satyed in Power Transfer phase for {round(Timing / 60000, 3)} mins , Limit :>= {Check['Time']/60000} mins', 'Fail' if Timing <Check['Time'] else 'Pass'])
            if Check['EPP']:
                PTCAP=self.PktMethod.GetPacketDetails(packet= "Power Transmitter Capability",limit=[CFG[2]+1,self.Flow_limit[1]],Type='Response')
                PTCAPval=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PTCAP[2],'Potential_Power_Value')[0]['sRawData'])
                res.append([f'PTx sent PT-CAP packet with Potential Load Power value :{PTCAPval} at id : {PTCAP[2]}', 'Pass' if PTCAPval==10 else 'Fail']) 
                # check for RP
                RP=self.PktMethod.GetPacketDetails(packet="8 bit Received Power",limit=[PTCAP[2]+1,self.Flow_limit[1]])
                if len(RP)>2:res.append([f'Prx sent RP8 data packet at id :{RP[2]} in the Power Transfer Phase', 'Fail'])
                else:res.append([f'Prx did not sent RP8 data packet in the Power Transfer Phase', 'Pass'])
            if Check['PFO']:
                id=CFG[2]+1
                powers=[]
                while id < self.Flow_limit[1]:
                    Tx=self.PktMethod.GetPacketDetails(packet="Estimated_Transmitted_Power_Value",Type="TesterMsg" ,limit=[id,self.Flow_limit[1]])
                    if len(Tx)>2:    
                        Txval=float(self.file_list[Tx[2]]['value'].split(',')[0].replace('W','')) 
                        powers.append([Tx[2],Txval])
                        id=Tx[2]+1
                    else:break
                if powers:
                    min_item = min(powers, key=lambda x: x[-1])
                    max_item = max(powers, key=lambda x: x[-1])
                    res.append([f'Measured Max Estimated Transmitted Power Level at {{{max_item[0]}}} is {max_item[-1]} W , Limit < 7.5W','Pass' if max_item[-1] <7.5 else 'Fail'])
                    res.append([f'Measured Min Estimated Transmitted Power Level at {{{min_item[0]}}} is {min_item[-1]} W , Limit < 7.5W','Pass' if min_item[-1] <7.5 else 'Fail'])

        else:res.append([f'Prx did not entered Power Transfer Phase', 'Fail'])
        res=res
        return res

    def CRC(self, CTSCheck, Check, flows, flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        WPIDPkt=False
        while id < self.Flow_limit[1]:
            WPID=self.PktMethod.GetPacketDetails(packet="WPID",limit=[id,self.Flow_limit[1]])
            if len(WPID)>2:
                WPIDPkt=True
                segment=(self.PktMethod.GetPayloadDetails(WPID[2],'WPID')[0]['sRawData']).replace("0x","")
                SW_CRC=self.PktMethod.GetPayloadDetails(WPID[2],'CRC')[0]['sRawData']
                CRC = f"0x{self.crc16_aug_ccitt(bytes.fromhex(segment)):04X}"
                resp=self.PktResponse(WPID[2]+1,self.Flow_limit[1])
                if resp is not None :
                    if self.file_list[resp[1]]['pktType']=="ACK":res.append([f'TPT sent Response : {resp[0]} for the {self.file_list[WPID[2]]['pktType']} at Id {WPID[2]}', 'Pass'])
                    else:res.append([f'TPT sent Response : {resp[0]} for the {self.file_list[WPID[2]]['pktType']} at Id {WPID[2]},Exp :ACK', 'Inconclusive'])
                    if SW_CRC==CRC:
                        res.append([f'CRC in logged WPID data packet is consistent with the WPID Segment', 'Pass'])
                    else:res.append([f'CRC in logged WPID data packet is :{SW_CRC}  and Calcualted CRC value is {CRC}', 'Fail'])
                id=WPID[2]+1
            else:break

        if not WPIDPkt:res.append([f'PRx did not sent WPID Packet', 'Inconclusive'])
        return res

    def CheckRP(self, CTSCheck, Check, flows, flwID):
      
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RPCount=0
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            RP=self.PktMethod.GetPacketDetails(packet="16 bit Received Power", limit=[id,self.Flow_limit[1]])
            if len(RP)>2:
                RPCount+=1
                id=RP[2]+1
            else:break
        res.append([f'PRx sent {RPCount} 16 Bit Received Power Packets Exp: Atleast One RP', 'Pass' if RPCount >=1 else 'Fail'])




#-------------------------------------------------------------End of CTS Checks Functions -------------------------------------------------------------------------#
    
    #Packet Payload function
        return res
    def Payload_Details(self,PacketName,Index,PayLoads=[],Receiver=True):
        res=[]
        Pd_id=0
        while Pd_id < len(PayLoads):
            Check=False
            for payload in self.PktMethod.GetGeneralPayloadDetails(name=PayLoads[Pd_id].get("Name"),index=Index,Byte=PayLoads[Pd_id].get("Byte"),Bit=PayLoads[Pd_id].get("Bit")):
                raw_data = payload.get('sRawData')
                if raw_data:
                    result, actual_val = self.PktMethod.compare_hex_to_expected(raw_hex=raw_data, expected_values=PayLoads[Pd_id].get("Exp"),comparator= PayLoads[Pd_id].get("comp", "EQL"),Type=PayLoads[Pd_id].get("Type","DEC"))
                    status = ( "Pass" if result else (  "Inconclusive" if PayLoads[Pd_id].get("Inconclusive_Check", False) else "Fail" ) )
                    if (not PayLoads[Pd_id].get("Result_check",True) and not result) or PayLoads[Pd_id].get("Result_check",True):
                        desp=CommonMethods.GetCompDes(PayLoads[Pd_id].get("Exp"),PayLoads[Pd_id].get("comp"))
                        res.append( [f'{'PRx'if Receiver else 'PTx'} sent the {PayLoads[Pd_id].get("Name")} Field with Val {actual_val} , Exp: {desp}', status])
                        # res.append( [f'{'PRx'if Receiver else 'PTx'} sent the {PayLoads[Pd_id].get("Name")} Field with Val {actual_val}  for the  {PacketName} datapacket at Id @{Index}, Exp:{PayLoads[Pd_id].get("Exp")},Comp :{PayLoads[Pd_id].get("comp")}.', f'{ "Pass" if result else "Fail"}'])
                    Check=True
            if not Check:res.append([f'{'PRx'if Receiver else 'PTx'} did not sent Expected {PayLoads[Pd_id].get("Name")} in the {PacketName} DataPacket  at Id @{Index}, Exp:{PayLoads[Pd_id].get("Exp")} , Comp :{PayLoads[Pd_id].get("comp")}.','Fail'])   
            Pd_id+=1
        return res

    def PktsCount(self,limit,Type='Packet'):
        id=limit[0]
        Count=0
        while id < limit[1]:
            TypeCheck=self.PktMethod.GetPacketType(id)
            if TypeCheck==Type:Count+=1
            id+=1
        return Count

    def find_pkt(self,Check, start_id,end,Pktstr):
        pkt = self.PktMethod.GetPacketDetails( packet=Check[Pktstr][0], value=Check[Pktstr][1], limit=[start_id, end] )
        if len(pkt) <= 2: return pkt
        if not Check[Pktstr][2]:return pkt
        i = pkt[2] + 1
        last_pkt = pkt

        while i < end:
            pkt = self.PktMethod.GetPacketDetails(packet=Check[Pktstr][0],value=Check[Pktstr][1],limit=[i, end] )
            if len(pkt) <= 2:break
            last_pkt = pkt
            i = pkt[2] + 1
        return last_pkt
           
    def FindPhase(self,id,Phase):
        PhaseLimit=[0,0]
        start=False
        while id < self.Flow_limit[1]:
            if self.file_list[id]['description']==Phase :
                if not start :
                    PhaseLimit[0]=id
                    start=True
                else: PhaseLimit[1]=id

            if start and self.file_list[id]['description']!=Phase and self.file_list[id]['description']!="":break
            id+=1
        if PhaseLimit[1]==0:PhaseLimit[1]=self.Flow_limit[1]
        if PhaseLimit[0]==0:return None
        else:return PhaseLimit
        

    def CheckseqPkts(self,limit,SeqPkts):
     
        SeqPackets=''
        results=[]
        id=limit[0]
        for SeqPkt in SeqPkts:
            SeqPktDataPacket= str(f'{SeqPkt[0]}{'_' + SeqPkt[1].replace('{','').replace('}','').replace(':','_') if SeqPkt[1] is not None else ''}')
            SeqPackets+="--"+SeqPktDataPacket
            seqpktDetails=self.PktMethod.GetPacketDetails(packet=SeqPkt[0],value=SeqPkt[1],limit=[id,limit[1]])
            if len(seqpktDetails)>2:
                if SeqPkt[2]:
                    res=self.Payload_Details(PacketName=SeqPktDataPacket,Index=seqpktDetails[2],PayLoads=SeqPkt[3])
                    if len(res)>0:results.extend(res) 
                id=seqpktDetails[2]+1
            else:
                results.append([f'Prx did not sent {SeqPktDataPacket} in the Sequence','Fail'])
                break  
        return results

    def LogPackets(self,Limit):
        id=Limit[0]
        LoggedPkts=[]
        while id < Limit[1]:
            Type=self.PktMethod.GetPacketType(id)
            if Type=="Packet":LoggedPkts.append([self.file_list[id]['pktType'].split("/")[0],id,self.file_list[id]['value']])
            id+=1
        return LoggedPkts

    # Fun to check if a packet matches expected PktType and value
    def packet_matches(self, packet_id, Pkt, PktVal):
        if PktVal is None:return Pkt in self.file_list[packet_id]['pktType'] 
        return (Pkt in self.file_list[packet_id]['pktType'] and PktVal in self.file_list[packet_id]['value'])
                
    # Fun to find the next packet of a specific type
    def findTypeid(self, limit=[], Type="Packet"):

        if limit[0] <= limit[1]:
            id=limit[0]
            while id <= limit[1]:
                if self.PktMethod.GetPacketType(id) == Type:
                    return id
                id+=1
        else:
            id =limit[0]
            while id > limit[1]:
                if self.PktMethod.GetPacketType(id) == Type:
                    return id
                id-=1

        return None

    def findType(self,start,end):
        id=start
        while id < end:
            Type=self.PktMethod.GetPacketType(id)
            if Type in ['Packet','Response']: return [Type,id]
            id+=1
        return None
    
    def PktResponse(self,start,end):
        res=self.findType(start,end)
        if res is not None:
            if res[0]=="Response": return [self.file_list[res[1]]['pktType'],res[1]]
        return None

    
    def RspTimngCheck(self,ExpPktDataPacket,ExpPkt,PktorResId):
        results=[]
        ResponseIndex=3
        if ExpPkt[2]:
            res=self.Payload_Details(PacketName=ExpPkt[0],Index=PktorResId,PayLoads=ExpPkt[3])
            ResponseIndex+=1
            if len(res)>0:results.extend(res) 
        #Check for the response for the ExpPkt
        Responsecheck=ExpPkt[ResponseIndex][0]['ResponseCheck']
        ResTimngId=ResponseIndex+1
        ResponseTimgcheck=ExpPkt[ResTimngId][0]['TimingCheck']
        if Responsecheck or ResponseTimgcheck:
            Resid=PktorResId+1
            resp=self.PktResponse(Resid,self.Flow_limit[1])
            if resp is not None:
                if ResponseTimgcheck and ExpPkt[ResTimngId][0]['Result_check']:
                    ResponseTime= round(( self.file_list[resp[1]]['startTime']-self.file_list[PktorResId]['stopTime'])*1000,3)
                    results.append([f'Measured response Time Between {ExpPktDataPacket} and {resp[0]} is {ResponseTime} mS ','Fail'if ResponseTime < ExpPkt[ResTimngId][0]['ExpTime'][0]-ExpPkt[ResTimngId][0]['ExpTime'][1] or ResponseTime >ExpPkt[ResTimngId][0]['ExpTime'][0]+ExpPkt[ResTimngId][0]['ExpTime'][1] else "Pass"])
                RespresPkt=False
                if Responsecheck:
                    for ExpRes in ExpPkt[ResponseIndex][0]['ExpResp']: 
                        if self.packet_matches(packet_id=resp[1],Pkt=ExpRes[0],PktVal=ExpRes[1]):
                            if ExpPkt[ResponseIndex][0]['Result_check']: 
                                results.append([f'PTx sent response {resp[0]} for the {ExpPktDataPacket} data packet','Pass'])
                                if ExpRes[2]:
                                    res=self.Payload_Details(PacketName=resp[0],Index=resp[1],PayLoads=ExpRes[3])
                                    if len(res)>0:results.extend(res) 
                            RespresPkt=True
                        if RespresPkt:break   
                if not RespresPkt and ExpPkt[ResponseIndex][0]['Result_check'] and Responsecheck: results.append([f'PTx sent response {resp[0]} for the {ExpPktDataPacket} data packet','Fail'])
            else:
                results.append([f'PTx did not sent any response for the {ExpPktDataPacket} data packet','Fail'])

        return results
         
    def Pch(self):
        pchcount=0
        Pchval=[]
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            PCH=self.PktMethod.GetPacketDetails(packet= "Power control hold off", limit=[id,self.Flow_limit[1]])
            if len(PCH)>2:
                pchcount+=1
                Pchval.append(GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PCH[2],"Power_Control_Hold_Off_Time")[0]['sRawData'])[0])
                id=PCH[2]+1
            else :break
        return pchcount,Pchval
    
    def PchTime(self,Neg):
        pchtime=5
        pchcount,Pchval=self.Pch()
        if pchcount>0:pchtime=Pchval[pchcount-1]
        if Neg:
            id=self.Flow_limit[0]
            while id < self.Flow_limit[1]:
                Pch=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Power Control Hold Off",limit=[id,self.Flow_limit[1]])
                if len(Pch)>2:
                    pchtime=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pch[2],"Power_Control_Hold_Off_Time")[0]['sRawData'])[0]
                    id=Pch[2]+1
                else:break

        return pchtime
    
    def CalculateVoltTwindow(self,indx,AllChannelData,winsize=[5,8],at='start',measure='before',max = False): #[8,11]
        if at == "start":
            xceEtime = self.file_list[indx].get('startTime')*1000
        elif at == 'end':
            xceEtime = self.file_list[indx].get('stopTime')*1000
        if measure == 'before':
            xceSindex = int((xceEtime-(winsize[1]))/AllChannelData['Interval'])
            xceEindex = int((xceEtime-winsize[0])/AllChannelData['Interval'])
            # print("xceStime:",xceEtime-winsize[1],"xceEtime:",xceEtime-winsize[0])
        elif measure == 'after':
            xceSindex = int((xceEtime+(winsize[0]))/AllChannelData['Interval'])
            xceEindex = int((xceEtime+winsize[1])/AllChannelData['Interval'])
            # print("xceStime:",xceEtime+winsize[0],"xceEtime:",xceEtime+winsize[1])
       
        id = xceSindex
        VRlist=[]
        Vrectmax = 0
        max = max
        while id <= xceEindex:
            VRlist.append(abs(AllChannelData['RV']['displayDataChunk'][id]))
            # print("voltages:",abs(AllChannelData['RV']['displayDataChunk'][id]))
            if max:
                if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) > Vrectmax or Vrectmax==0:
                    Vrectmax = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
                    # print("Vrectmax:",Vrectmax)
            id+=1
        # print("Vrectmax:",Vrectmax)
        return [Vrectmax] if max else [round((sum(VRlist)/len(VRlist)),5), id-1]       
    

    def RP8_2nd(self,limit):
        count=0
        id=limit[0]
        while id <limit[1]:
            RP=self.PktMethod.GetPacketDetails(packet="8 bit Received Power",limit=[id,limit[1]])
            if len(RP)>2:
                count+=1
                id=RP[2]+1
            else:break
        return True if count>=2 else False
    
    def CheckPkt(self,id,Pkts):
        PktFound=False
        PktsList=''
        for pkt in Pkts:
            if pkt[0] in self.file_list[id]['pktType'] and True if pkt[1] is None else pkt[1] in self.file_list[id]['value']:
                PktFound=True
                break

        for pkt in Pkts:
            PktsList += str(pkt[0]) + ("" if pkt[1] is None else str(pkt[1])) + ","
        return PktFound,PktsList
    
    
    def crc16_aug_ccitt(self,data: bytes):
        crc = 0xFFFF
        poly = 0x1021
        # Process each byte MSB first (serial bit stream)
        for byte in data:
            for i in range(7, -1, -1):          # MSB first
                bit = (byte >> i) & 1
                if crc & 0x8000:
                    crc = ((crc << 1) & 0xFFFF) ^ poly ^ bit
                else:
                    crc = ((crc << 1) & 0xFFFF) ^ bit

        # Clock in 16 zero bits after data (per spec)
        for _ in range(16):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFF

        return crc



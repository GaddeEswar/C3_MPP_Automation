import traceback
import io
import pandas as pd
import zipfile
from asn1crypto import x509
import csv
import json
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods


class CommonCTSChecks:
    def __init__(self,file_list,Header,JapiData,BackupJson,Product,Mode):
        self.file_list=file_list
        self.Product=Product
        self.Mode=Mode
        self.JapiData = JapiData
        self.Header=Header
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
        self.PktMethod = PacketMethods(file_list,Header)
        self.PlotMethod = PlotMethods(Header)
        self.TestResultsjson = JsonOperations("json/TestResults.json")
        self.TestData = self.TestResultsjson.read_file()
        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        self.Auth_file_list = self.AuthPktAPI.GetRequest()

    # --------------------------------------------------------------------------------- Thermal Tests ----------------------------------------------------------------------------------------#

    # 5.2.1 Test #24: thermal performance of TPR-THERMAL-5W
    def Thermal_5W(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.AllChannelData_Volatge = self.PlotMethod.GetAllChannelData2('2',self.JapiData)  #  Voltage Plot
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  # Current  Plot
        self.Flow_limit = flows[flwID]['Limit']
        phaseCheck=self.CheckPhase(self.Flow_limit[0],"PT")
        if phaseCheck is not None:
            # Check target operating voltage reached or not
            VR=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[phaseCheck,self.Flow_limit[1]])
            if len(VR)>2:
                Loadvrect = self.CalculateVoltTwindow(VR[2],self.AllChannelData_Volatge,at="start",measure="before")
                res.append([f'while TPR Regulating to its Operating Voltage Measured Voltage is : {Loadvrect[0]} V -> Limits : 4.116 V ~ 4.284 V', 
                            'Pass' if Loadvrect[0] >= 4.116 and Loadvrect[0] <= 4.284 else 'Inconclusive'])
                self.id =VR[2]+1
                # Check Loads are applied or not
                results,LoadFlag=self.CheckLoads(Check)
                res.extend(results)
                # Get Voltages and Temperature data
                res.extend(self.Measure_Voltage_Current_Plot(phaseCheck,LoadFlag,Check)) 
            else:res.append([f'TPR did not regulated to its operating voltage','Inconclusive'])
        else : res.append([f'PRx did not entered PT Phase','Inconclusive'])
        return res
    
    # 5.2.2 Test PTX-POW-TEMP-EPP: thermal performance of TPR-THERMAL-15W
    def Thermal_15W(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)  #  Voltage Plot
        self.AllChannelData_Current = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  # Current  Plot
        self.Flow_limit = flows[flwID]['Limit']
        phaseCheck=self.CheckPhase(self.Flow_limit[0],"PT")
        if phaseCheck is not None:
            # Check target operating voltage reached or not
            VR=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[phaseCheck,self.Flow_limit[1]])
            if len(VR)>2:
                Loadvrect = self.CalculateVoltTwindow(VR[2],self.AllChannelData,at="start",measure="before")
                res.append([f'while TPR Regulating to its Operating Voltage , Measured Voltage is {Loadvrect[0]} V -> Limits : 11.4 V ~ 12.6 V', 'Pass' if Loadvrect[0] >= 11.4 and Loadvrect[0] <= 12.6 else 'Inconclusive'])
                id =VR[2]+1
                LoadFlag=False
                # Check Negotiable Load Power Reached or not
                PTCAP=self.PktMethod.GetPacketDetails(packet="Power Transmitter Capability",Type="Response",limit=[self.Flow_limit[0],id])
                if len(PTCAP)>2:
                    NPower=float(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PTCAP[2],'Guaranteed_Power_Value')[0]['sRawData']))/2
                    Current=(self.CalculateVoltTwindow(VR[2],self.AllChannelData_Current,at="start",measure="before"))
                    Power=round(Loadvrect[0]*Current[0],3)
                    NPLimit=[round((NPower - ((NPower*5)/100)),2), round((NPower +((NPower*5)/100)),2)]
                    res.append([f'While regulating to Load Voltage (12 ± 5%) V, Measured Load power is {Power} W -> Limits : {NPLimit[0]} W ~ {NPLimit[1]} W',
                                    'Pass' if Power >= NPLimit[0] and Power <= NPLimit[1] else 'Inconclusive'])

                else:
                    res.append([f'Could not found Power Transmitter capabilities packet ','Inconclusive'])
                    LoadFlag=False
                # Get Voltages and Temperature data
                res.extend(self.Measure_Voltage_Current_Plot(phaseCheck,LoadFlag,Check))  
            else:res.append([f'TPR did not regulated to its operating voltage','Inconclusive'])
        else : res.append([f'PRx did not entered PT Phase','Inconclusive'])
        return res
      
    #-----------------------------------------------------------Negotiation Phase Tests------------------------------------------------------------------------- #
    
    def Nego_SRQ_GPX(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # find GRQ PT-Cap
        GRQ_CAP=self.PktMethod.GetPacketDetails(packet="General Request",value='PT-CAP',limit=self.Flow_limit)
        if len(GRQ_CAP)>2:
            # Take the PT-CAP Response Power Value
            PT_CAP=self.PktMethod.GetPacketDetails(packet="Power Transmitter Capability",Type="Response",limit=[GRQ_CAP[2]+1,self.Flow_limit[1]])
            if len(PT_CAP)>2:
                NPower=float(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PT_CAP[2],'Guaranteed_Power_Value')[0]['sRawData']))/2
                # Find SRQ/GP 
                SRQ_GP=self.PktMethod.GetPacketDetails(packet="SRQ [0x20]",value="Guaranteed Load Power",limit=[PT_CAP[2]+1,self.Flow_limit[1]])
                if len(SRQ_GP)>2:
                    res.append([f'TPR sent SRQ/GP packet at {{{SRQ_GP[2]}}}','Pass'])
                    # Verify the Guranteed Load Power according to CTS
                    GPower=float(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(SRQ_GP[2],'Guaranteed_Power_Value')[0]['sRawData']))/2
                    if Check.get('0.5',False):
                        res.append([f'TPR set Guranteed_Power value to {GPower}_W , which is { '' if GPower==NPower+0.5 else 'not'} equal to PT-CAP Negotaible load power ({NPower})_W + 0.5 W','Pass' if GPower==NPower+0.5 else 'Inconclusive'])
                    else:
                        if 'GPX_002' in self.Header['TestcaseID'] :
                            res.append([f'TPR set Guranteed_Power value to {GPower}_W  in SRQ/GP packet, Expected 3W','Pass' if GPower==3 else 'Inconclusive'])
                        else:
                            res.append([f'TPR set Guranteed_Power value to {GPower}_W , which is {'' if GPower==NPower else 'not'} equal to PT-CAP Negotaible load power ({NPower})_W','Pass' if GPower==NPower else 'Inconclusive'])

                    # Verify SRQ/GP Response
                    id= SRQ_GP[2]+1
                    PF=[]
                    while id < self.Flow_limit[1]:
                        if self.PktMethod.GetPacketType(id)=='Packet':
                            if self.file_list[SRQ_GP[2]]['pktType'] in self.file_list[id]['pktType'] and self.file_list[SRQ_GP[2]]['value'] in self.file_list[id]['value']:
                                SRQ_GP=[self.file_list[id]['startTime'],self.file_list[id]['stopTime'],id]
                                id+=1
                                continue
                            else:
                                PF.append([f"TPR sent packet {self.file_list[id]['pktType']}_{self.file_list[id]['value']} at {{{id}}} without getting response for {self.file_list[SRQ_GP[2]]['pktType']}_{self.file_list[SRQ_GP[2]]['value']}",'Inconclusive'])
                                break
                        elif self.PktMethod.GetPacketType(id)=='Response':
                            PF.append([f'PTx sent {self.file_list[id]['pktType']} response for SRQ/GP packet, Expected - {Check['Response']}','Pass' if Check['Response'] in self.file_list[id]['pktType'] else 'Fail'])
                            break
                        id+=1
                        
                    if PF==[]:PF.append([f'PTx did not sent response for SRQ/GP packet','Inconclusive'])
                    res.extend(PF)

                else: res.append([f'TPR did not sent SRQ/GP in the Sequence after GRQ/PT-CAP','Inconclusive'])
                    
            else: res.append([f'Power Transmitter Capability response is not found','Inconclusive'])
                    
        else: res.append([f'TPR did not sent GRQ/ PT-CAP packet in the sequence ','Inconclusive'])
                
        return res

    def Nego_SRQ_GPX5(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # find GRQ PT-Cap
        GRQ_CAP=self.PktMethod.GetPacketDetails(packet="General Request",value='PT-CAP',limit=self.Flow_limit)
        if len(GRQ_CAP)>2:
            # Take the PT-CAP Response Power Value
            PT_CAP=self.PktMethod.GetPacketDetails(packet="Power Transmitter Capability",Type="Response",limit=[GRQ_CAP[2]+1,self.Flow_limit[1]])
            if len(PT_CAP)>2:
                NPower=float(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PT_CAP[2],'Guaranteed_Power_Value')[0]['sRawData']))/2
                GPowerStart=31.5
                id=PT_CAP[2]+1
                while id < self.Flow_limit[1]:
                    SRQ_GP=self.PktMethod.GetPacketDetails(packet="SRQ [0x20]",value="Guaranteed Load Power",limit=[id,self.Flow_limit[1]])
                    if len(SRQ_GP)>2:
                        # Verify SRQ/GP Response
                        iid= SRQ_GP[2]+1
                        PF=[]
                        while iid < self.Flow_limit[1]:
                            if self.PktMethod.GetPacketType(iid)=='Packet':
                                if self.file_list[SRQ_GP[2]]['pktType'] in self.file_list[iid]['pktType'] and self.file_list[SRQ_GP[2]]['value'] in self.file_list[iid]['value']:
                                    SRQ_GP=[self.file_list[iid]['startTime'],self.file_list[iid]['stopTime'],iid]
                                    iid+=1
                                    continue
                                else:
                                    PF.append([f"TPR sent packet {self.file_list[iid]['pktType']}_{self.file_list[iid]['value']} at {{{iid}}} without getting response for {self.file_list[SRQ_GP[2]]['pktType']}_{self.file_list[SRQ_GP[2]]['value']}",'Inconclusive'])
                                    break
                            elif self.PktMethod.GetPacketType(iid)=='Response':
                                ExpResponse= 'ACK' if GPowerStart <= NPower else 'NAK' 
                                PF.append([f'TPR sent SRQ/GP packet at {{{SRQ_GP[2]}}}','Pass'])
                                 # Verify the Guranteed Load Power according to CTS
                                GPower=float(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(SRQ_GP[2],'Guaranteed_Power_Value')[0]['sRawData']))/2
                                PF.append([f'TPR set Guranteed_Power value to {GPower} W, Expected - {GPowerStart}_W','Pass' if GPower==GPowerStart else 'Inconclusive'])
                                PF.append([f'PTx sent {self.file_list[iid]['pktType']} response for SRQ/GP packet , Expected: {ExpResponse}','Pass' if ExpResponse in self.file_list[iid]['pktType'] else 'Fail'])
                                break
                            iid+=1
                            
                        if PF==[]:
                            res.append([f'PTx did not sent response for SRQ/GP packet','Inconclusive'])
                            break
                        res.extend(PF)
                        id=iid+1
                        GPowerStart-=0.5
                    else: 
                        res.append([f'TPR did not sent SRQ/GP in the Sequence after GRQ/PT-CAP','Inconclusive'])
                        break
                    if GPowerStart==0: break # Break the Loop if GP power reaches 0W
            else: res.append([f'Power Transmitter capability response is not found','Inconclusive'])
        else: res.append([f'TPR did not sent GRQ/PT-CAP packet in the sequence ','Inconclusive'])
                
        return res
        
    #-----------------------------------------------------------Power Transfer Phase Tests------------------------------------------------------------------------- #

    def POW_RP8(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        phaseCheck=self.CheckPhase(self.Flow_limit[0],"Calib")
        if phaseCheck is not None:
            count=0
            id=phaseCheck+1
            RP8Check=False
            last_RP8=None
            while id < self.Flow_limit[1]:
                if count%3==2:
                    RP8=self.PktMethod.GetPacketDetails(packet="8 bit Received Power", limit=[id,self.Flow_limit[1]])
                    if len(RP8)>2:
                        res.append([f'TPR sent 8-Bit Received_Power packet at index@ {{RP8[2]}} after 3 RP packets','Pass'])
                        id=RP8[2]+1
                        RP8Check=True
                        last_RP8=RP8
                        count=0 # Reset count to check the next sequence of RP packets
                    else:
                        res.append([f'TPR did not send RP/8 packet after 3 RP packets','Inconclusive'])
                        break
                else:
                    RP=self.PktMethod.GetPacketDetails(packet="16 bit Received Power", limit=[id,self.Flow_limit[1]])
                    if len(RP)>2:
                        count+=1
                        id=RP[2]+1
                    else:break
            # Check Tterminate
            if RP8Check:
                iid=last_RP8[2]+1
                while iid< self.Flow_limit[1]:
                    if self.PktMethod.GetPacketType(iid) in ["Response","Packet"]:
                        res.append([f'PTx did not detach after the last RP/8 packet ','Inconclusive'])
                    else:
                        if 'shutdown' in self.file_list[iid]['pktType'] or 'CoilVoltpkpk' in self.file_list[iid]['pktType']:
                            Timing=round((self.file_list[iid]['startTime']-last_RP8[1])*1000,3)
                            res.append([f'Measured t_terminate from last RP/8 packet at {{{last_RP8[2]}}} is {Timing}_mS ,Limit[≤ 28 mS]','Pass' if Timing <=28 else 'Fail'])
                        break
                    iid+=1
            else:res.append([f'TPR did not send RP/8 packet or 3 RP packets before RP/8 packet','Inconclusive'])         
        else:res.append([f'TPR did not enter into PT phase','Inconclusive'])
        return res
  
    

    def ADC(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # find PTX ADC data packet
        ADCpktCount=0
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            ADC=self.PktMethod.GetPacketDetails(packet="ADC", Type='Response',limit=[id,self.Flow_limit[1]])
            if len(ADC)>2:
                ADCpktCount+=1
                Payload=self.PktMethod.GetPayloadDetails(ADC[2],"Request")[0]['sRawData']
                if Payload in Check['ADC']:
                    res.append([f'PTx sent ADC data packet with parameter {Payload} at index@ {ADC[2]}', 'Pass'])
                else: res.append([f'PTx sent ADC data packet with parameter {Payload} at index@ {ADC[2]} which is not in set {Check["ADC"]}.', 'Pass'])
                id=ADC[2]+1
            else:id+=1
        if ADCpktCount<10:res.append([f'PTx did not sent 10 ADC Data packets', 'Inconclusive'])
        return res

    def ADT(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # find PTX ADC data packet
        ADCpktCount=0
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]:
            ADC=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth", Type='Response',limit=[id,self.Flow_limit[1]])
            if len(ADC)>2:
                ADCpktCount+=1
                res.append([f'PTx sent ADC/auth data packet at index@ {ADC[2]}', 'Pass'])
                ADT1=self.PktMethod.GetPacketDetails(packet="ADT",Type='Response', limit=[ADC[2]+1,self.Flow_limit[1]])
                if len(ADT1)>2:
                    if Check["DSRNAK"]:
                        # find DSR-NAK and then find next ADT
                        i=ADT1[2]+1
                        while i < self.Flow_limit[1]:
                            if self.file_list[i]['pktType']=="DSR":
                                if "NAK" in  self.file_list[i]['value']: res.append([f'PRx sent DSR/Nak at index@ {i} packet after the ADT packet at index@ {ADT1[2]}.', 'Pass'])
                                else:res.append([f'PRx did not sent DSR/Nak packet after the ADT packet at index@ {ADT1[2]}.', 'Inconclusive'])
                                break
                            else:i+=1
                        ADT2=self.PktMethod.GetPacketDetails(packet="ADT", Type='Response',limit=[i+1,self.Flow_limit[1]])
                        if len(ADT2)>2:
                            if self.file_list[ADT1[2]]['pktType']==self.file_list[ADT2[2]]['pktType']:
                                res.append([f'PRx sent { self.file_list[ADT1[2]]["pktType"]} data packet at index@ {ADT1[2]}, { self.file_list[ADT2[2]]["pktType"]} data packet at index@ {ADT2[2]}.', 'Pass'])
                            else: res.append([f'PRx sent { self.file_list[ADT1[2]]["pktType"]} data packet at index@ {ADT1[2]}, { self.file_list[ADT2[2]]["pktType"]} data packet at index@ {ADT2[2]}.', 'Fail'])
                            id=ADT2[2]+1
                        else:
                            res.append([f'PTx did not sent next ADT packet after the ADT packet at index@ {ADT1[2]}.', 'Inconclusive'])
                            id=i+1
                    else:
                        if 'e' in self.file_list[ADT1[2]]['pktType']:res.append([f'PTx sent {self.file_list[ADT1[2]]["pktType"]} Packet after ADC/Auth at @Id{ADC[2]} .', 'Pass'])
                        else:res.append([f'PTx sent {self.file_list[ADT1[2]]["pktType"]} packet after ADC/Auth at index@ {ADC[2]} .', 'Fail'])
                        id=ADT1[2]+1
                else:
                    res.append([f'PTx did not sent ADT Packet after ADC/auth at index@ {ADC[2]}.', 'Inconclusive'])
                    id+=1
            else:break
        if ADCpktCount<5:res.append([f'PTx did not sent 5 {Check["PktCheck"]} data packets.', 'Inconclusive'])
        return res

   
    def ADTSeq(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            count=0
            while id < self.Flow_limit[1]:
                if count >=5 :break
                # find get CeRTIFICATE FROM tpr
                Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[id,self.Flow_limit[1]])
                if len(Get_Certificate)>2:
                    count+=1
                    res.append([f'Sequence - {count}','Pass'])
                    results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                    if len(results)>0:res.extend(results)
                    ADCAuth=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth",Type='Response', limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                    if len(ADCAuth)>2:
                        ADCEnd=self.PktMethod.GetPacketDetails(packet="ADC",value="End", Type='Response',limit=[ADCAuth[2]+1,self.Flow_limit[1]])
                        if len(ADCEnd)>2:
                            #Find ADT Pkts Between AUth sequence
                            iD =ADCAuth[2]+1
                            ADTPkts=[]
                            while iD < ADCEnd[2]:
                                ADT=self.PktMethod.GetPacketDetails(packet="ADT",Type='Response', limit=[iD,ADCEnd[2]])
                                if len(ADT)>2:
                                    ADT2=self.PktMethod.GetPacketDetails(packet="ADT",Type='Response', limit=[ADT[2]+1,ADCEnd[2]])
                                    if len(ADT2)>2:
                                        if self.file_list[ADT[2]]['pktType']== self.file_list[ADT2[2]]['pktType']:
                                            DSR_Nak=self.PktMethod.GetPacketDetails(packet="DSR",value='NAK', limit=[ADT[2]+1,ADT2[2]])
                                            DSR_Poll=self.PktMethod.GetPacketDetails(packet="DSR",value='POLL', limit=[ADT[2]+1,ADT2[2]])
                                            if len(DSR_Nak)< 2 and len(DSR_Poll)<2:  ADTPkts.append(ADT[2]) 
                                        else: ADTPkts.append(ADT[2]) 
                                    else:
                                        ADTPkts.append(ADT[2])
                                        break
                                    iD=ADT[2]+1
                                else:break

                            # Validate
                            if len(ADTPkts)==1:res.append([f'PTx sent only one {self.file_list[iD-1]['pktType']} at index@ {iD-1} in between the sequence from {self.file_list[ADCAuth[2]]['pktType']} at index@ {ADCAuth[2]} to {self.file_list[ADCEnd[2]]['pktType']} at @index@ {ADCEnd[2]}', 'Pass'])                                                    
                            elif len(ADTPkts)==0:res.append([f'PTx did not sent any ADT data packets in bewtween the sequence -{count}', 'Inconclusive'])
                            else:
                                for i,j in zip(ADTPkts,ADTPkts[1:]):
                                    if self.file_list[i]['pktType'][-1] != self.file_list[j]['pktType'][-1]:
                                        res.append([f'PTx sent different {self.file_list[i]['pktType']} at index@ {i},{self.file_list[j]['pktType']} at index@ {j} in between the sequence from {self.file_list[ADCAuth[2]]['pktType']} at index@ {ADCAuth[2]} to {self.file_list[ADCEnd[2]]['pktType']} at index@ {ADCEnd[2]}', 'Pass'])
                                    else:res.append([f'PTx sent same {self.file_list[i]['pktType']} at index@ {i},{self.file_list[j]['pktType']} at index@ {j} in between the sequence from {self.file_list[ADCAuth[2]]['pktType']} at index@ {ADCAuth[2]} to {self.file_list[ADCEnd[2]]['pktType']} at index@ {ADCEnd[2]}', 'Fail'])
                            id=ADCEnd[2]+1
                        else:
                            res.append([f'PTx did not sent ADC/end response in sequence -{count}', 'Inconclusive'])
                            id=ADCAuth[2]+1
                            
                    else:
                        res.append([f'PTx did not sent ADC/auth response in sequence -{count}', 'Inconclusive'])
                        id=Get_Certificate[2]+1
                
                else:
                    res.append([f'TPR did not sent Get_Certificate request','Inconclusive'])
                    break
            
            if count <5 :res.append([f'TPR cannot log the data packets of five complete data transport streams','Inconclusive'])
        else:res.append([f'Prx did not entered PT phase', 'Inconclusive'])

        return res

    def SFX(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
         # simple flow
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
            res.extend(result)
            if seq :
                if Check.get("Challenge",True) and self.CertificateChainValid():
                    result,id,seq=self.AuthSequence(id,Authvalue1="Challenge",Authvalue2="Challenge_Auth",Payload2=[])
                    res.extend(result) 
                    if seq :
                        # Check Signature Valid
                        Signature=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="Valid" ,Type="TesterMsg",limit=[0,self.Flow_limit[1]])
                        if len(Signature)>2:res.append([f'Signature contained in Challenge_auth is valid', 'Pass'])
                        else:res.append([f'Signature contained in Challenge is not valid', 'Fail'])
                else:res.append([f'Certificate chain is not valid or not found', 'Inconclusive'])
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])
                        
        return res

    def FWC(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Get_Digests",Payload1=Check['Get_Digests'],Authvalue2="Digests",Payload2=Check['Digests'])
            res.extend(result)
            if seq:
                result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
                res.extend(result)
                if seq :
                    if Check.get("Challenge",True) and self.CertificateChainValid():
                        result,id,seq=self.AuthSequence(id,Authvalue1="Challenge",Authvalue2="Challenge_Auth",Payload2=[])
                        res.extend(result) 
                        if seq :
                            # Check Signature Valid
                            Signature=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="Valid" ,Type="TesterMsg",limit=[0,self.Flow_limit[1]])
                            if len(Signature)>2:res.append([f'Signature contained in Challenge_auth is valid', 'Pass'])
                            else:res.append([f'Signature contained in Challenge is not valid', 'Fail'])
                    else:res.append([f'Certificate chain is not valid or not found', 'Inconclusive'])
               
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res

    def CFF(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Challenge",Authvalue2="Challenge_Auth",Payload2=[])
            res.extend(result)
            if seq:
                # Check Signature Valid
                Signature=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="Valid" ,Type="TesterMsg",limit=[0,self.Flow_limit[1]])
                if len(Signature)>2:res.append([f'Signature contained in Challenge_auth is valid', 'Pass'])
                else:res.append([f'Signature contained in Challenge is not valid', 'Fail'])
                result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
                res.extend(result)
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res

    def CertificateChain(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
            res.extend(result)

        return res

    def SimpleFlow(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # simple flow
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
            res.extend(result)
            if seq and Check.get("Challenge",True):
                result,id,seq=self.AuthSequence(id,Authvalue1="Challenge",Authvalue2="Challenge_Auth",Payload2=[])
                res.extend(result) 
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res

    def FlowWithCaching(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Get_Digests",Payload1=Check['Get_Digests'],Authvalue2="Digests",Payload2=Check['Digests'])
            res.extend(result)
            if seq:
                result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
                res.extend(result)
                if seq:
                    result,id,seq=self.AuthSequence(id,Authvalue1="Challenge",Authvalue2="Challenge_Auth",Payload2=[])
                    res.extend(result) 
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res

    def ChallengeFirstFlow(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Challenge",Authvalue2="Challenge_Auth",Payload2=[])
            res.extend(result)
            if seq:
                result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
                res.extend(result)
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res

    def SDF_PayLoad(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        for pkt in Check['Pkts']:
            pkt_Details=self.PktMethod.GetPacketDetails(packet=pkt[0],value=pkt[1], limit=self.Flow_limit,Type= 'Packet' if not pkt[3] else 'Response')
            if len(pkt_Details)>2:
                
                for items in pkt[2]:
                    SDF_Check=False
                    Pkt_val1=None
                    Pkt_val2=None
                    if items['SDF']:SDF_Check=True
                    match items['Type']:
                        case "DEC":
                            if not SDF_Check:
                                Pkt_val1=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(pkt_Details[2],items['Name1'])[0]['sRawData'])
                            else:
                                if items['Name1']=="PotentialLoadPower":
                                    if 'ExtendedProtocol' in self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SupportedOptionalProtocols']  and self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['PowerProfile'] not in [ "BPP","EPP","EPP5"]:items['Name1']='PotentialLoadPowerEP'
                                Pkt_val1=self.PktMethod.hex_to_decimal(self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields'][items['Name1']])
                                if 'Power' in items['Name1']:Pkt_val1=Pkt_val1*2
                            Pkt_val2=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(pkt_Details[2],items['Name2'])[0]['sRawData'])
                        
                        case "Boolean":
                            Pkt_val1=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields'][items['Name1']]
                            Pkt_val2=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(pkt_Details[2],items['Name2'])[0]['sRawData'])
                            if Pkt_val1 and Pkt_val2==1:Pkt_val2=True
                            else: Pkt_val2=False
                        
                    if items['comp']=="EQL":  res.append([f'{items['Name2']} field is set to {Pkt_val2} in data packet, {f'and {items['Name1']} field is set to {Pkt_val1} in data packet,' if not SDF_Check else f'in SDF it was set to {Pkt_val1} '}, Comp :{items['comp']}', 'Pass'  if Pkt_val1==Pkt_val2 else 'Fail'])  
                    elif items['comp']=="GEQL": res.append([f'{items['Name2']} filed is set to {Pkt_val2} in data packet, {f'and {items['Name1']} field is set to {Pkt_val1} in data packet,' if not SDF_Check else f'in SDF it was set to {Pkt_val1} '}, Comp :{items['comp']}', 'Pass'  if Pkt_val1>=Pkt_val2 else 'Fail'])  
            
            else: res.append([f'{'PRx' if not pkt[3] else "PTx"} did not sent {pkt[0]} data packet','Fail'])
                        
        return res

    def Pkt_PktComp(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Pkt_vals=[]
        Descriptions=[]
        for pkt in Check['Pkts']:
            #find pkt
            PD=self.PktMethod.GetPacketDetails(packet=pkt[0],value=pkt[1] ,Type=pkt[3],limit=self.Flow_limit)
            if len(PD)>2:
                Pkt_val=self.PktMethod.GetPayloadDetails(PD[2],pkt[2][0]['Name'])[0]['sRawData']
                if pkt[2][0]['Type']=="DEC":Pkt_val=self.PktMethod.hex_to_decimal(Pkt_val)
                Pkt_vals.append(Pkt_val)
                Descriptions.append(f'Measured {pkt[2][0]['Name']} at index@ {PD[2]} is {Pkt_val}')
            else: res.append([f'Test did not found {pkt[0]} data packet','Inconclusive'])

        if Check['Addval']:
            i=0
            while i< len(Pkt_vals)-1:
                Pkt_vals[i]=Pkt_vals[i]+Check['Addval'][i+1]
                i+=1
        if Check['Comp']=="NEQ": res.append([f'{', '.join(Descriptions)} Comp :{Check['Comp']}','Inconclusive' if Pkt_vals[0]==Pkt_vals[1] else 'Pass'])

        return res

    def ReplacedPkt(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id = self.Flow_limit[0]
        pktCount=0
        RepPkt=False
        DataPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        # AllMeasures_exp = f"TPR should send {DataPacket} datapacket"
        while id < self.Flow_limit[1]:
            if self.PktMethod.GetPacketType(id)=='Packet':
                if pktCount==Check['ReplacedPktCount'][0]:
                    RepPkt=True
                    # AllMeasures_exp = f"TPR should send {DataPacket} datapacket"
                    if (Check['ExpectedPacket'][1]is None and Check['ExpectedPacket'][0] in self.file_list[id].get('pktType')) or (Check['ExpectedPacket'][0] in self.file_list[id].get('pktType') and (Check['ExpectedPacket'][1] in self.file_list[id].get('value'))):
                        res.append([f"TPR sent {DataPacket} dataPacket","Pass"])   
                    else:  res.append([f"TPR sent {self.file_list[id].get('pktType')} packet instead of {DataPacket}","Fail"])
                    break
                pktCount+=1
            id+=1
        if not RepPkt: res.append([f"TPR did not sent complete {DataPacket} due to voltage drop ","Pass"])

        return res
    def SignalStrengthCheck(self,CTSCheck,Check,flows,flwID):
        res=[]
        ST= self.PktMethod.GetPacketDetails(packet="Test_Status",value="Execution_Started" ,Type="TesterMsg" ,limit=[0,len(self.file_list)-1])
        SP=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[len(self.file_list)-1,0])
        if len(ST)>2 and len(SP)>2:
            # check signal Strength Packet
            SS = self.PktMethod.GetPacketDetails(packet='Signal strength',limit=[ST[2]+1,SP[2]])
            if len(SS)>2:
                res.append([f'Tester sent Signal_strength packet at index@ {{{SS[2]}}}','Fail'])
            else:res.append([f'Tester did not sent Signal_strength packet','Pass'])

        else:res.append([f'test_stop [or] test_start is missing','Inconclusive'])
        
        return res

    def FODPrePower(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        FOD1=self.PktMethod.GetPacketDetails(packet="FOD Status",value="Qf" ,limit=self.Flow_limit)
        FOD2=self.PktMethod.GetPacketDetails(packet="FOD Status",value="Rf", limit=self.Flow_limit)
        shutdown=self.PktMethod.GetPacketDetails(packet="Shutdown", Type="TesterMsg",limit=[self.Flow_limit[0],self.Flow_limit[1]+1])

        def Tfod():
            # find the Timing between NAK and shutdown
            Tfod=round((shutdown[1]- self.file_list[resp]['stopTime'])*1000,2)
            if Check['ACK_Check']:  res.append([f"PTx sent { self.file_list[resp]['pktType']} response for FOD packet","Fail"])
            else:
                res.append([f"Measured t_fod timing is {Tfod} mS","Fail" if Tfod >1500 else "Pass"]) 


        if len(FOD1)>2:
            # check FOD value
            Pkt_val1=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(FOD1[2],'FOD_support_data')[0]['sRawData'])
            Specval=Check['defaultVal'][0]+(Check['defaultVal'][0] *10)/100 if Check['defaultVal'][2]=="Greater" else Check['defaultVal'][0]-(Check['defaultVal'][0] *10)/100 
            res.append([f"Measured FOD/qf is {Pkt_val1} at index@ {FOD1[2]}, expected val should be {Check['defaultVal'][2]} than 10% of default value :{Check['defaultVal'][0]}",'Fail' if Pkt_val1 <= Specval else 'Pass'])
            resp = self.PktMethod.GetPacketResponse(FOD1,[FOD1[2]+1,self.Flow_limit[1]])
            if self.file_list[resp]['pktType'] =="ACK":
                if len(FOD2)>2:
                    Pkt_val2=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(FOD2[2],'FOD_support_data')[0]['sRawData'])
                    Specval=Check['defaultVal'][1]+(Check['defaultVal'][1] *2)/100 if Check['defaultVal'][3]=="Greater" else Check['defaultVal'][0]-(Check['defaultVal'][0] *10)/100 
                    res.append([f"Measured FOD/rf is {Pkt_val2} at index@ {FOD2[2]}, expected val should be {Check['defaultVal'][3]} than 2% of default value :{Check['defaultVal'][1]}",'Fail' if Pkt_val2 >=Specval else 'Pass'])
                    resp = self.PktMethod.GetPacketResponse(FOD2,[FOD2[2]+1,self.Flow_limit[1]])
                    if self.file_list[resp]['pktType'] =="ACK":res.append([f"PTx sent ACK response for both FOD packets","Pass"])       
                    else: 
                        if self.file_list[resp]['pktType'] =="NAK":Tfod()  
                        else:  res.append([f"PTx sent {self.file_list[resp]['pktType']} response for FOD packet","Inconclusive"])       
                        
            else:
                if Check['FodCheck']:
                    if len(FOD2)<2:res.append([f"PRx did not sent FOD/rf packet","Inconclusive"])
                else:
                    if self.file_list[resp]['pktType'] =="NAK":Tfod()  
                    else:  res.append([f"PTx sent {self.file_list[resp]['pktType']} response for FOD packet","Inconclusive"])       
        else:res.append([f"PRx did not sent FOD packet","Inconclusive"])

        return res

    def Tcalibrate(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Find SRQ/EN Packet
        SrqEN=self.PktMethod.GetPacketDetails(packet="SRQ [0x20]",value="End Negotiation" ,limit=self.Flow_limit)
        if len(SrqEN)>2:
            # Find ACK response
            resp = self.PktMethod.GetPacketResponse(SrqEN,[SrqEN[2]+1,self.Flow_limit[1]])
            if  self.file_list[resp]['pktType'] =="ACK":
                # find response ACK for RP/2
                id=resp+1
                while id < self.Flow_limit[1]:
                    RP2=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:2" ,limit=[id,self.Flow_limit[1]])
                    if len(RP2)>2:
                        # Find ACK response
                        resp2 = self.PktMethod.GetPacketResponse(RP2,[RP2[2]+1,self.Flow_limit[1]])
                        if  self.file_list[resp]['pktType'] =="ACK":
                            Tcalibrate=round((self.file_list[resp2]['stopTime']-self.file_list[resp]['stopTime'])*1000,2)
                            res.append([f"Measured t_calibrate time is {Tcalibrate} mS",'Pass' if Tcalibrate <=10000 else 'Fail'])
                            break
                        else:id=resp2+1    
                    else:
                        res.append([f"PRx did not sent RP/2 data packet with ACK","Inconclusive"])    
            else:res.append([f"PTx sent { self.file_list[resp]['pktType']} response for SRQ/en packet","Inconclusive"])
        else: res.append([f"PRx did not sent SRQ/en packet","Inconclusive"])
                        
        return res

    def Response(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=self.Flow_limit)
        # AllMeasures_exp=f'Logged Response Pattern should be in {Check['ExpResponse']}'
        DataPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        if len(ExpectedPacket_Details)>2:
            resp = self.PktMethod.GetPacketResponse(ExpectedPacket_Details,[ExpectedPacket_Details[2]+1,self.Flow_limit[1]])
            if resp is not None:
                if self.file_list[resp]['pktType'] in Check['ExpResponse']:
                    res.append([f'TPR received {self.file_list[resp]['pktType']} response for the {DataPacket} datapacket ','Pass'])
                    if Check.get("ResponseTiming",False):
                        Timing= round((self.file_list[resp]['startTime']-ExpectedPacket_Details[1])*1000,3)
                        res.append([f'Measured t_response is {Timing} mS Limit [3 ≤ t_response ≤ 10]mS', 'Pass' if Timing >=3 and Timing <=10 else 'Fail'])
                else: res.append([f'TPR received {self.file_list[resp]['pktType']} response for the {DataPacket} datapacket which is Not expected.','Fail'])
            else:   res.append([f'TPR received {self.file_list[resp]['pktType']} response for the {DataPacket} datapacket ','Fail'])
        else: res.append([f'TPR did not sent the {Check['ExpectedPacket'][0]} datapacket.','Inconclusive'])

        return res

    def ExpectedPackets(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # AllMeasures_exp=""
        ExpPkts={}   
        for ExpectedPacket in Check['ExpectedPacket']:   
            id = self.Flow_limit[0]
            while id < self.Flow_limit[1]:
                ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=ExpectedPacket[0], value=ExpectedPacket[1], limit=[id,self.Flow_limit[1]])
                if len(ExpectedPacket_Details)>2:
                    id=ExpectedPacket_Details[2]+1
                    if ExpectedPacket[0] not in ExpPkts:ExpPkts[ExpectedPacket[0]]=1
                    else: ExpPkts[ExpectedPacket[0]]+=1 
                else: id +=1

        if len(ExpPkts)>0:
            for ExpectedPacket in Check['ExpectedPacket']:   
                if ExpectedPacket[0] not in ExpPkts: res.append([f'TPR did not sent the {ExpectedPacket[0]} datapacket .', "Inconclusive" if Check['Inconclusive'] else 'Fail']) 
                else: 
                    if ExpPkts[ExpectedPacket[0]] < ExpectedPacket[2]:
                        res.append([f'TPR sent the {ExpectedPacket[0]} datapacket {ExpPkts[ExpectedPacket[0]]} times which is less than expected {ExpectedPacket[2]} times.', "Inconclusive" if Check['Inconclusive'] else 'Fail'])
                    else:res.append([f'TPR sent the {ExpectedPacket[0]} datapacket {ExpPkts[ExpectedPacket[0]]} times.', "Pass"])
                # AllMeasures_exp+=f'TPR should send the Packet {ExpectedPacket[0]};'
        else: res.append([f'TPR did not sent the {ExpectedPacket[0]} datapacket.', "Inconclusive" if Check['Inconclusive'] else 'Fail'])

        return res

    def Tterminate(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Validate Tterminate Measurent across ALL Phases.
        # AllMeasures_exp=f'Tterminate Limit should be in {Check['expected']}'
        TestCaseLimit=[0,len(self.file_list)] if Check['Phase'] == 'Ping' else self.Flow_limit
        Trestart=True if self.Certification =="2.3.0"  and Check['ExpectedPacket'][0]!="End Power Transfer" else False
        if Check['Phase']!='Ping' and Check['ExpectedPacket'][0]=="End Power Transfer" and Check['ExpectedPacket'][1]=="[EPT/nul]":Trestart=True
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        DataPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        Start_Details= self.PktMethod.GetPacketDetails(packet="Test_Status" if Check['Phase'] =='Ping' else Check['StartPacket'][0],value=": Execution_Started" if Check['Phase'] == 'Ping' else Check['StartPacket'][1],Type="TesterMsg" if Check['Phase'] == 'Ping' else 'Packet',limit=TestCaseLimit)
        if len(Start_Details)>2:
            Stop_Details=self.PktMethod.GetPacketDetails(packet="Test_Status",value=": Test_Stop",Type="TesterMsg",limit=[Start_Details[2],len(self.file_list)])   if Check['Phase'] =='Ping' else [1,1,TestCaseLimit[1]]
            if len(Stop_Details)>2:
                if Check['Phase'] == 'Ping': res.append([f"Test executed for {round((Stop_Details[0]-Start_Details[0]),3)} seconds after placing the TPR coil on the PTx Product",'Pass' if round((Stop_Details[0]-Start_Details[0]),3) > 30 else 'Fail' ])
                ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=[Start_Details[2],Stop_Details[2]+1])
                if len(ExpectedPacket_Details)>2:
                        # check shutdown
                    SD=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[ExpectedPacket_Details[2]+1, Stop_Details[2]])
                    if len(SD)>2:
                        #Measure the first Ping Calculation
                        TterminateVal=round((SD[1] - ExpectedPacket_Details[1]) * 1000, 3)
                        res.append([f'Measured t_terminate for packet {DataPacket} is {TterminateVal} mS ,Limit:{Check['expected']} ','Fail' if TterminateVal > Check['expected'][1] else 'Pass'])
                        if Trestart:
                            res=self.TrestartCheck(DataPacketName=DataPacket,PktId=ExpectedPacket_Details[2],CoilPkpk=SD)
                            if len(res)>0:res.extend(res)
                        #find ALL pings for Ping Phase
                        TterminateList,res=self.calculate_Tterminate(SD[2]+1,Stop_Details[2],ExpPkt=Check['ExpectedPacket'][0],result=res,TterminateLimit=Check['expected'],PacketDetailsCheck=Check['ExpectedPacket'][2],PayLoads=Check['ExpectedPacket'][3] if Check['ExpectedPacket'][2] else [],DataPacketName=DataPacket,Trestart=Trestart)
                        res=res
                    else:
                        res.append([f'voltage drops below 200mV[pk=pk] level before reaching the end of the {DataPacket} datapacket.','Pass'])
                        res.append([f'Measured t_terminate is 0.0 mS','Pass'])   
                else:
                    res.append([f'voltage drops below 200mV[pk=pk] level before reaching the end of the {DataPacket} datapacket.','Pass'])
                    res.append([f'Measured t_terminate is 0.0 mS','Pass'])
                    if Trestart:
                        SD=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[Start_Details[2]+1, Stop_Details[2]])
                        res=self.TrestartCheck(DataPacketName=DataPacket,PktId="None",CoilPkpk=SD)
                        if len(res)>0:res.extend(res)
            else:  res.append(['Test did not find the Test_Stop assertion','Fail'])
        else: res.append([f'Test did not entered {Check['Phase']}','Inconclusive'])

        return res

    def PreviousPacket(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        #Get the Data packet just before the mentioned data packet.
        EndDataPacket= str(f'{Check['EndPacket'][0]}{'_' + Check['EndPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['EndPacket'][1] is not None else ''}')
        PreviousPacket=str(f'{Check['PreviousPacket'][0]}{'_' + Check['PreviousPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['PreviousPacket'][1] is not None else ''}')
        EndPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['EndPacket'][0], value=Check['EndPacket'][1], limit=self.Flow_limit)
        if len(EndPacket_Details)>2 :
            if Check['EndPacket'][2]: 
                res.append([f'TPR sent {EndDataPacket} data packet','Pass'])
                Pres=self.Payload_Details(PacketName=EndDataPacket,Index=EndPacket_Details[2],PayLoads=Check['EndPacket'][3])
                if len(Pres)>0:res.extend(Pres)  
            id =EndPacket_Details[2]-1
            while id > self.Flow_limit[0]:
                if self.PktMethod.GetPacketType(id)=="Packet":
                    if (Check['PreviousPacket'][1] is None and Check['PreviousPacket'][0] in self.file_list[id]['pktType'] ) or ( Check['PreviousPacket'][0] in self.file_list[id]['PktType'] and Check['PreviousPacket'][1] in self.file_list[id]['value']) :
                        res.append([f'TPR sent {PreviousPacket} data packet','Pass'])
                        if Check['PreviousPacket'][2]:
                            Pres=self.Payload_Details(PacketName=PreviousPacket,Index=id,PayLoads=Check['PreviousPacket'][3])
                            if len(Pres)>0:res.extend(Pres)     
                    else:res.append([f'TPR did not sent {PreviousPacket} data packet','Inconclusive'])
                    break
                id-=1
        else: res.append([f'TPR did not sent {EndDataPacket} data packet','Inconclusive'])

        return res

    def SeqPackets(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        #Get the Sequence of Data packets Mentioned after the start packet.
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            if Check['StartPacket'][2]:
                Pres=self.Payload_Details(PacketName=StartDataPacket,Index=StartPacket_Details[2],PayLoads=Check['StartPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            id=StartPacket_Details[2]+1
            ExpPkts=[]
            for SeqPkt in Check['ExpectedPacket']:
                SeqPktDataPacket= str(f'{SeqPkt[0]}{'_' + SeqPkt[1].replace('{','').replace('}','').replace(':','_') if SeqPkt[1] is not None else ''}')
                ExpPkts.append(SeqPktDataPacket)
                Seqcheck=True
                while id < self.Flow_limit[1]:
                    if self.PktMethod.GetPacketType(id)=="Packet":
                        if (SeqPkt[1] is None and SeqPkt[0] in self.file_list[id]['pktType'] ) or (SeqPkt[0] in self.file_list[id]['pktType'] and SeqPkt[1] in self.file_list[id]['value'] ) :
                            res.append([f'TPR sent {SeqPktDataPacket} data packet','Pass'])
                            if SeqPkt[2]:res.extend(self.Payload_Details(PacketName=SeqPktDataPacket,Index=id,PayLoads=SeqPkt[3]))     
                        else: 
                            res.append([f'TPR did not sent {SeqPktDataPacket} data packet','Inconclusive'])
                            Seqcheck=False
                        id+=1
                        break
                    id+=1
                if  not Seqcheck: break
            # AllMeasures_exp=f'TPR should send {ExpPkts} in the Sequence'  
        else: res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])   

        return res

    def SeqRespTimng(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            if Check['StartPacket'][2]:
                Pres=self.Payload_Details(PacketName=StartDataPacket,Index=StartPacket_Details[2],PayLoads=Check['StartPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            id=StartPacket_Details[2]+1
            # Check Response and then Continue [Tester retries if there is no response]
            resp=self.PktResponse(id,self.Flow_limit[1])
            if resp is None:
                # find the response
                ResId=self.findTypeid(limit=[id,self.Flow_limit[1]],Type="Response")
                if ResId is not None: id=ResId+1
            else:id=resp[1]
            ExpPkts=[]
            for SeqPkt in Check['ExpectedPacket']:
                SeqPktDataPacket= str(f'{SeqPkt[0]}{'_' + SeqPkt[1].replace('{','').replace('}','').replace(':','_') if SeqPkt[1] is not None else ''}')
                ExpPkts.append(SeqPktDataPacket)
                Seqcheck=True
                PktorResId=self.findTypeid(limit=[id,self.Flow_limit[1]],Type="Packet")
                if PktorResId is not None:
                    if self.packet_matches(packet_id=PktorResId,Pkt=SeqPkt[0],PktVal=SeqPkt[1]):
                        res.append([f'TPR sent {SeqPktDataPacket} data packet at index@ {PktorResId}','Pass'])
                        if Check['Pktretry']:
                            i=PktorResId+1
                            if i==self.Flow_limit[1]:
                                res.append([f'PTx did not sent response for {SeqPktDataPacket}','Inconclusive'])
                            while  i < self.Flow_limit[1]:
                                # Check the reponse for the pkt and continue for next Pkt
                                resp=self.PktResponse(i,self.Flow_limit[1])
                                if resp is not None:
                                    #Check for the response or Timng for the SeqPkt
                                    Tres=self.RspTimngCheck(SeqPktDataPacket,SeqPkt,resp[1]-1)
                                    if len(Tres)>0:res.extend(Tres)   
                                    id=i+1
                                    break
                                else:
                                    if i==self.Flow_limit[1]-1:
                                        res.append([f'PTx did not sent response for {SeqPktDataPacket}','Inconclusive'])
                                        i+=1
                                    else:
                                        i+=1
                                        continue
                    else:
                        res.append([f'TPR sent {self.file_list[PktorResId]['pktType']}_{self.file_list[PktorResId]['value']} packet instead of {SeqPktDataPacket} data packet','Inonclusive'])
                        Seqcheck=False
                
                if  not Seqcheck: break
            # AllMeasures_exp=f'TPR should send {ExpPkts} in the Sequence'  
        else: res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])

        return res
    
    def ResponseSequence(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # find the start Packet and then check the seq of Packets
        Start = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(Start)>2:
            #Fun to find the Pkt after a sequence and its reponse 
            beforePkt= f'{Check['StartPacket'][0]}' if Check['StartPacket'][1] is None else f'{Check['StartPacket'][0]}_{Check['StartPacket'][1]}'
            id= Start[2]+1
            pktid=0
            seqCheck=True
            while pktid < len(Check['SeqPkts']):
                pkt=Check['SeqPkts'][pktid]
                pkt_Name=f'{pkt[0]}' if pkt[1] is None else f'{pkt[0]}_{pkt[1]}'
                pktfound=False
                while id < self.Flow_limit[1]:
                    if pktfound:break
                    if  self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                        if  (pkt[0] in self.file_list[id]['pktType']) if pkt[1] is None else  (pkt[0] in self.file_list[id]['pktType'] and  pkt[1] in self.file_list[id]['value']):
                            res.append([f'TPR sent {pkt_Name} at index@ {{{id}}}','Pass'])
                            pktfound=True
                            if pkt[2]: # Check Paylod data if required
                                Pres=self.Payload_Details(PacketName=pkt_Name,Index=id,PayLoads=pkt[3])
                                if len(Pres)>0:res.extend(Pres)
                            # Check its response
                            Type=self.findType(id+1,self.Flow_limit[1])
                            if Type is not None:
                                if Type[0] == 'Packet':
                                    if  (pkt[0] in self.file_list[Type[1]]['pktType']) if pkt[1] is None else  (pkt[0] in self.file_list[Type[1]]['pktType'] and  pkt[1] in self.file_list[Type[1]]['value']):
                                        pktfound=False
                                        continue
                                    else:# Stop the TestCase if TPR sends next packet without any response for the previous packet
                                        res.append([f'TPR sent {self.file_list[Type[1]]['pktType']}_{self.file_list[Type[1]]['value']} without any response for {pkt_Name}','Inconclusive']) 
                                        seqCheck=False
                                        break
                                else: 
                                    if pkt[-2][0]['ResponseCheck']: # Check the CTS Pass/Fail Criteria
                                        ResFound=False
                                        for ExRes in pkt[-2][0]['ExpResp']:
                                            if ExRes[0] in self.file_list[Type[1]]['pktType']:
                                                res.append([f'PTx responded with {self.file_list[Type[1]]['pktType']} for {pkt_Name}','Pass'])
                                                ResFound=True
                                        if not ResFound: res.append([f'PTx responded with {self.file_list[Type[1]]['pktType']} for {pkt_Name}','Fail'])

                                    # if 'ND' in  self.file_list[Type[1]]['pktType']: # Stop Validating the TestCase if PTx responds with ND response
                                    #     res.append([f'PTx responded with ND Response for {pkt_Name} at {{{id}}}','Inconclusive'])
                                    #     seqCheck=False        
                            else:
                                res.append([f'PTx did not sent response for {pkt_Name} at index@ {{{id}}}','Inconclusive'])
                                seqCheck=False
                            if not seqCheck:break 
                        else:
                            res.append([f'TPR did not sent {pkt_Name} after {beforePkt}','Inconclusive'])
                            beforePkt=pkt_Name
                            seqCheck=False
                            break
                        id+=1
                    else:id+=1
                if not seqCheck : break
                pktid+=1
        else:res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])

        return res

    def PktInsertAfterSeq(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        #Fun to find the Pkt after a sequence and its reponse or Timing Measures
        id= self.Flow_limit[0]
        SeqCount=0
        ExpPackets=''
        while id < self.Flow_limit[1]:
            if SeqCount >= Check['SeqCount']:break
            Seq=False
            SeqPackets=''
            for SeqPkt in Check['SeqPkts']:
                SeqPktDataPacket= str(f'{SeqPkt[0]}{'_' + SeqPkt[1].replace('{','').replace('}','').replace(':','_') if SeqPkt[1] is not None else ''}')
                SeqPackets+="--"+SeqPktDataPacket
                seqpktDetails=self.PktMethod.GetPacketDetails(packet=SeqPkt[0],value=SeqPkt[1],limit=[id,self.Flow_limit[1]])
                if len(seqpktDetails)>2:
                    if SeqPkt[2]:
                        Pres=self.Payload_Details(PacketName=SeqPktDataPacket,Index=seqpktDetails[2],PayLoads=SeqPkt[3])
                        if len(Pres)>0:res.extend(Pres) 
                    Seq=True
                    id=seqpktDetails[2]+1
                if  not Seq: 
                    res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])
                    break    
            if  not Seq: break
            SeqCount+=1
            for ExpPkt in Check['ExpPkts']:
                ExpPktDataPacket= str(f'{ExpPkt[0]}{'_' + ExpPkt[1].replace('{','').replace('}','').replace(':','_') if ExpPkt[1] is not None else ''}')
                ExpPackets+="--"+ExpPktDataPacket
                PktorResId=self.findTypeid(limit=[id,self.Flow_limit[1]],Type="Packet")
                if PktorResId is not None:
                    if self.packet_matches(packet_id=PktorResId,Pkt=ExpPkt[0],PktVal=ExpPkt[1]):
                        res.append([f'TPR sent {ExpPktDataPacket} data packet index@ {PktorResId} after the sequence {SeqPackets}','Pass'])
                        #Check for the response or Timng for the ExpPkt
                        Tres=self.RspTimngCheck(ExpPktDataPacket,ExpPkt,PktorResId)
                        if len(Tres)>0:res.extend(Tres) 
                        id=PktorResId+1
                    else:
                        res.append([f'TPR did not sent {ExpPktDataPacket} data packet after the sequence {SeqPackets}','Inconclusive'])
                        break
                else:
                    res.append([f'TPR did not sent {ExpPktDataPacket} data packet after the sequence {SeqPackets}','Inconclusive'])  
                    break  
                SeqPackets+="--"+ExpPktDataPacket
        # AllMeasures_exp=f'TPR should send {ExpPackets} in the Sequence.'  

        return res

    def PktInsertAtTime(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        InsertedDataPacket= str(f'{Check['ExpPkts'][0]}{'_' + Check['ExpPkts'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpPkts'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            if Check['StartPacket'][2]:
                Pres=self.Payload_Details(PacketName=StartDataPacket,Index=StartPacket_Details[2],PayLoads=Check['StartPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            id=StartPacket_Details[2]+1
            Timing1=round(StartPacket_Details[0],2)
            SeqCount=0
            while id< self.Flow_limit[1]:
                if SeqCount >= Check['SeqCount']:break
                InPktDetails=self.PktMethod.GetPacketDetails(packet=Check['ExpPkts'][0],value=Check['ExpPkts'][1],limit=[id,self.Flow_limit[1]])
                if len(InPktDetails)>2:                                            
                    #Check for the response or Timng for the ExpPkt
                    Tres=self.RspTimngCheck(InsertedDataPacket,Check['ExpPkts'],InPktDetails[2])
                    if len(Tres)>0:res.extend(Tres) 
                    id=InPktDetails[2]+1
                    Time=round((round(InPktDetails[0],2)-Timing1),2)
                    res.append([f'Timing differnce between {InsertedDataPacket} at {round(InPktDetails[0],2)}S and {StartDataPacket} at {Timing1}S is {Time} sec ','Pass' if Time > Check['TimeInterval'][0] <8 and Time < Check['TimeInterval'][1] else 'Fail'])
                    Timing1=round(InPktDetails[0],2)
                    StartDataPacket=InsertedDataPacket
                    SeqCount+=1
                else:
                    res.append([f'TPR did not sent {InsertedDataPacket} data packet after {StartDataPacket}','Inconclusive'])
                    break
            res.append([f'TPR sent {SeqCount} {InsertedDataPacket} data packets','Pass' if SeqCount >=Check['SeqCount'] else 'Inconclusive'])
        else:res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])

        return res

    def PktInsertAtTime2(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        EndDataPacket=str(f'{Check['EndPacket'][0]}{'_' + Check['EndPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['EndPacket'][1] is not None else ''}')
        InsertedDataPacket= str(f'{Check['ExpPkts'][0]}{'_' + Check['ExpPkts'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpPkts'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            EndPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['EndPacket'][0], value=Check['EndPacket'][1], limit=[StartPacket_Details[2]+1,self.Flow_limit[1]]) 
            if len(EndPacket_Details)>2:
                id=StartPacket_Details[2]+1
                SeqCount=0
                while id< EndPacket_Details[2]:
                    if SeqCount >= Check['SeqCount']:break
                    InPktDetails=self.PktMethod.GetPacketDetails(packet=Check['ExpPkts'][0],value=Check['ExpPkts'][1],limit=[id,self.Flow_limit[1]])
                    if len(InPktDetails)>2:
                        SeqCount+=1
                        Tres=self.RspTimngCheck(InsertedDataPacket,Check['ExpPkts'],InPktDetails[2])
                        if len(Tres)>0:res.extend(Tres) 
                        id=InPktDetails[2]+1
                    else:id+=1
                res.append([f'TPR sent {SeqCount} {InsertedDataPacket} data packets','Pass' if SeqCount >=Check['SeqCount'] else 'Fail'])
            else: res.append([f'TPR did not sent {EndDataPacket} data packet','Fail'])
        else:res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])

        return res

    def SeqPacketsRenego(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            if Check['StartPacket'][2]:
                Pres=self.Payload_Details(PacketName=StartDataPacket,Index=StartPacket_Details[2],PayLoads=Check['StartPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            #Check NEGO packet and its response
            NegoPacket_Details = self.PktMethod.GetPacketDetails(packet="Renegotiate", limit=[StartPacket_Details[2]+1,self.Flow_limit[1]])
            if len(NegoPacket_Details)>2:
                resp=self.PktResponse(NegoPacket_Details[2]+1,self.Flow_limit[1])
                if resp is not None and resp[0]=="ACK":
                    # Check the sequence and log only the expected Responses
                    id=NegoPacket_Details[2]-1
                    SeqCount=0
                    SeqPkts=''
                    LoggedResponse={}
                    while id < self.Flow_limit[1]:
                        if SeqCount >= Check['SeqCount']:break
                        Seq=False
                        SeqPackets=''
                        for SeqPkt in Check['SeqPkts']:
                            SeqPktDataPacket= str(f'{SeqPkt[0]}{'_' + SeqPkt[1].replace('{','').replace('}','').replace(':','_') if SeqPkt[1] is not None else ''}')
                            SeqPackets+="--"+SeqPktDataPacket
                            seqpktDetails=self.PktMethod.GetPacketDetails(packet=SeqPkt[0],value=SeqPkt[1],limit=[id,self.Flow_limit[1]])
                            if len(seqpktDetails)>2:
                                res.append([f'TPR sent {SeqPktDataPacket} at {{{seqpktDetails[2]}}}','Pass'])
                                ReponseCheckid=3
                                if SeqPkt[2]:
                                    Pres=self.Payload_Details(PacketName=SeqPktDataPacket,Index=seqpktDetails[2],PayLoads=SeqPkt[3])
                                    if len(Pres)>0:res.extend(Pres) 
                                    ReponseCheckid+=1
                                if SeqPkt[ReponseCheckid][0]['ResponseCheck']:
                                    resp=self.PktResponse(seqpktDetails[2]+1,self.Flow_limit[1])
                                    if resp is not None:
                                        if resp[0] not in LoggedResponse:LoggedResponse[resp[0]]=1
                                        else:LoggedResponse[resp[0]]+=1
                                Seq=True
                                id=seqpktDetails[2]+1
                            else: 
                                res.append([f'TPR did not entered ReNego phase at Seq_Count: {SeqCount+1}','Inconclusive'])
                                Seq=False
                                break
                        SeqPkts=SeqPackets
                        if  not Seq: break
                        SeqCount+=1
                    if SeqCount >= Check['SeqCount']:
                        for resp in Check['ExpResponse'][0].keys():
                            if resp in LoggedResponse:
                                if  LoggedResponse[resp] >= Check['ExpResponse'][0][resp]:res.append([f'Tester seen upto {LoggedResponse[resp]}-{resp} responses','Pass'])
                                else:res.append([f'Tester seen upto {LoggedResponse[resp]}-{resp}  responses Exp: {Check['ExpResponse'][0][resp]}','Fail'])
                            else:res.append([f'TPR could not able to log {resp} response for atleast one sequence','Fail'])
                    res.append([f'TPR sent the sequence {SeqPkts}-{SeqCount} times','Pass' if SeqCount >= Check['SeqCount'] else 'Inconclusive'])
                else:res.append([f'PTx did not supports ReNeg phase','Inconclusive'])
            else:res.append([f'TPR did not sent ReNeg packet','Inconclusive'])
        else:res.append([f'TPR did not entered {Check['Phase']} phase','Inconclusive'])

        return res

    def PacketDetails(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id = self.Flow_limit[0]
        for ExpPacket in Check['ExpectedPacket']:
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=ExpPacket[0], value=ExpPacket[1], limit=[id,self.Flow_limit[1]])
            DataPacket= str(f'{ExpPacket[0]}{'_' + ExpPacket[1].replace('{','').replace('}','').replace(':','_') if ExpPacket[1] is not None else ''}')
            if len(ExpectedPacket_Details)>2:
                if ExpPacket[2]: 
                    Pres=self.Payload_Details(PacketName=DataPacket,Index=ExpectedPacket_Details[2],PayLoads=ExpPacket[3])
                    if len(Pres)>0: res.extend(Pres) 
                id=ExpectedPacket_Details[2]+1
                res.append([f'TPR sent the {DataPacket} datapacket.', "Pass"]) 
            else:res.append([f'TPR did not sent the {DataPacket} datapacket.', "Fail"])   

        return res

    def NotPackets(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Fun to find mentioned data packet NOT in the Testcase.
        DataPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        id=self.Flow_limit[0]
        pktCount=0
        while id < self.Flow_limit[1]:
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=[id,self.Flow_limit[1]])
            if len(ExpectedPacket_Details)>2:
                pktCount+=1
                if pktCount> Check['PktsCount']:
                    #add (If second packet sent then timer of 2nd packet and it's result)
                    res.append([f'TPR sent the {DataPacket} data packet {pktCount} times. Expected: Not more than {Check['PktsCount']} times','Fail'])
                    break
                id=ExpectedPacket_Details[2]+1
            else:id+=1
        if pktCount <= Check['PktsCount']: 
            if Check['PktsCount']==1:res.append([f'TPR can not send second {DataPacket} data packet.','Pass'])
            else:res.append([f'TPR did not sent the {DataPacket} data packet more than {Check['PktsCount']} times.','Pass'])
                        
        return res

    def Tnopower(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # AllMeasures_exp=f'Tnopower Limit should be in {Check['expected']}'
        ExpectedPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=self.Flow_limit)
        if len(ExpectedPacket_Details)>2:
            if Check['ExpectedPacket'][2]:
                Pres=self.Payload_Details(ExpectedPacket,ExpectedPacket_Details[2],Check['ExpectedPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            Shutdown_details=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[ExpectedPacket_Details[2]+1, self.Flow_limit[1]])
            if len(Shutdown_details)>2:
                Pktid=self.findTypeid(limit=[Shutdown_details[2],self.Flow_limit[0]],Type="Packet")
                if Pktid is not None:
                    Time=round((self.file_list[Pktid]['stopTime']-ExpectedPacket_Details[1]),3)
                    if Time >0 : res.append([f'PRx stopped sending packets after {Time}S from the {ExpectedPacket} packet','Pass'])
                    else:res.append([f'PRx did not sent any data packets after {ExpectedPacket}','Pass'])
                #find next ping  
                NextPing_details=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[Shutdown_details[2]+1, len(self.file_list)-1])
                if len(NextPing_details)>2:
                    tnopower=round((NextPing_details[0]-Shutdown_details[1])*1000,3)
                    res.append([f'Measured t_nopower from {round(NextPing_details[1],3)}Sec to {round(Shutdown_details[1],3)}Sec   is {tnopower} mS', 'Pass' if  tnopower > Check['expected'][1] else 'Fail'])
                else:
                    Time=round((self.file_list[len(self.file_list)-1]['startTime']-Shutdown_details[1])*1000,3)
                    if Time > Check['expected'][1]:res.append([f'Measured t_nopower is greater than {Check['expected'][1]} mS','Pass'])
                    else:res.append([f'Measured t_nopower is {Time} mS','Fail'])
                    # res.append(['PTx did not Initiated next Ping','Fail'])
            else: res.append([f'PTx did not detached after {ExpectedPacket}','Fail'])
        else: res.append([f'Test did not entered {Check['Phase']}','Inconclusive'])

        return res

    def Ttotal(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # AllMeasures_exp=f'Ttotal Limit should be in {Check['expected']}'
        ExpectedPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
        ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=self.Flow_limit)
        if len(ExpectedPacket_Details)>2:
            if Check['ExpectedPacket'][2]:
                Pres=self.Payload_Details(ExpectedPacket,ExpectedPacket_Details[2],Check['ExpectedPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            resp=self.PktResponse(ExpectedPacket_Details[2]+1,self.Flow_limit[1])
            if resp is not None:
                res.append([f'PTx responded with {resp[0]} for the {ExpectedPacket} data packet','Pass'])
                Shutdown_details=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[resp[1], self.Flow_limit[1]])
                if len(Shutdown_details)>2:
                    #find Total=Tnegotiate+Tterminate 
                    Ttotal=round((Shutdown_details[1]-self.file_list[resp[1]]['stopTime'])*1000,3)
                    res.append([f'Measured t_negotiate + t_terminate from {round(Shutdown_details[1],3)}Sec to {round(self.file_list[resp[1]]['stopTime'],3)}Sec is {Ttotal} mS, Limit [≤ 528mS]', 'Fail' if  Ttotal > Check['expected'][1] else 'Pass'])
                else: res.append([f'PTx did not detached after {ExpectedPacket}','Fail'])
            else:  res.append([f'PTx did not sent response for the {ExpectedPacket} data packet','Fail'])
        else: res.append([f'Test did not entered {Check['Phase']} phase','Inconclusive'])

        return res

    def Tnextping(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # AllMeasures_exp=f'Tnextping Limit should be in {Check['expected']}'
        StartDataPacket= str(f'{Check['StartPacket'][0]}{'_' + Check['StartPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['StartPacket'][1] is not None else ''}')
        StartPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['StartPacket'][0], value=Check['StartPacket'][1], limit=self.Flow_limit)
        if len(StartPacket_Details)>2:
            if Check['StartPacket'][2]:
                Pres=self.Payload_Details(PacketName=StartDataPacket,Index=StartPacket_Details[2],PayLoads=Check['StartPacket'][3])
                if len(Pres)>0:res.extend(Pres)
            ExpectedPacket= str(f'{Check['ExpectedPacket'][0]}{'_' + Check['ExpectedPacket'][1].replace('{','').replace('}','').replace(':','_') if Check['ExpectedPacket'][1] is not None else ''}')
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=Check['ExpectedPacket'][0], value=Check['ExpectedPacket'][1], limit=[StartPacket_Details[2]+1,self.Flow_limit[1]])
            if len(ExpectedPacket_Details)>2:
                if Check['ExpectedPacket'][2]:
                    Pres=self.Payload_Details(ExpectedPacket,ExpectedPacket_Details[2],Check['ExpectedPacket'][3])
                    if len(Pres)>0:res.extend(Pres)
                Shutdown_details=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[ExpectedPacket_Details[2]+1, self.Flow_limit[1]])
                if len(Shutdown_details)>2:
                    #find next ping 
                    NextPing_details=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[Shutdown_details[2], len(self.file_list)-1])
                    if len(NextPing_details)>2:
                        tnextping=round((NextPing_details[0]-  (ExpectedPacket_Details[1] if Check['Measurefrom']=='Pkt' else Shutdown_details[1]))*1000,3)
                        ValidationLimit=Check['expected']
                        if Check['Type'] =="Between":
                            Tnextpingres= "Pass" if tnextping >= Check['expected'][0] and tnextping <= Check['expected'][1] else 'Fail'
                        elif Check['Type'] =="GTE":
                            Tnextpingres= "Pass" if tnextping >= Check['expected'][1]  else 'Fail'
                            ValidationLimit=Check['expected'][1]
                        elif Check['Type']=='referPkt':
                            repingTime=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ", value="Re ping delay", limit=self.Flow_limit)[2],'Re_ping_time')[0]['sRawData'])/5
                            Check['expected']=[(80*repingTime/100)*1000,(120*repingTime/100)*1000]
                            Tnextpingres= "Pass" if tnextping >= Check['expected'][0] and tnextping <= Check['expected'][1] else 'Fail'
                            ValidationLimit=Check['expected']
                        res.append([f'Measured t_nextping from the {ExpectedPacket} at index@: {ExpectedPacket_Details[2]} ending from {round(ExpectedPacket_Details[1] if Check['Measurefrom']=='Pkt' else Shutdown_details[1],3)} Sec to {round(NextPing_details[1],3)} Sec is {tnextping}mS ,Limit :{ValidationLimit},Comp:{Check['Type']}.', Tnextpingres])
                    else: 
                        Time=round((self.file_list[len(self.file_list)-1]['startTime']-Shutdown_details[1])*1000,3)
                        if Time > Check['expected'][1]:res.append([f'Measured t_nextping from the {ExpectedPacket} at index@: {ExpectedPacket_Details[2]} ending from {round(ExpectedPacket_Details[1],2)} Sec is greater than {Check['expected'][1]} mS','Pass'])
                        else:res.append([f'Measured t_nextping is {Time} mS','Fail'])
                        # res.append(['PTx did not Initiated next Ping','Fail'])
                else: res.append([f'PTx did not detached after {ExpectedPacket}','Fail'])
        else: res.append([f'Test did not entered {Check['phase']}','Inconclusive'])

        return res

    def EPT_RST(self,CTSCheck,Check,flows,flwID):
       
        return self.EPT_Helper(Check,flows[flwID]['Limit'])
       
       
    def EPT_Reping(self,CTSCheck,Check,flows,flwID):
        res=[]
        PktName=Check["EPT"][0]+" "+Check["EPT"][1] if Check["EPT"][1]is not None else Check["EPT"][0]
        self.Flow_limit = flows[flwID]['Limit']
        # find SRQ/rpr
        SRQ_RPR=self.PktMethod.GetPacketDetails(packet="SRQ [0x20]", value="Received Power reporting", limit=self.Flow_limit)
        if len(SRQ_RPR)>2:
            reping_time=12.4
            # find srq/rep
            id=SRQ_RPR[2]+1
            while id < self.Flow_limit[1]:
                if self.file_list[id]['isTesterPkt'] and not self.file_list[id]['isFWTestermessage']:
                    if "SRQ [0x20]" in self.file_list[id]['pktType'] and 'Received Power reporting' in self.file_list[id]['value']:
                        id+=1
                        continue
                    else:
                        if "SRQ [0x20]" in self.file_list[id]['pktType'] and "Re ping delay" in self.file_list[id]['value']:
                            res.append([f'TPR sent SRQ/rep packet at index@ {{{id}}}','Pass'])
                            reping_time=float(self.file_list[id]['value'].split(":")[1].split('Re-Ping value')[1].replace('}',''))/5

                            if 'REP_002' in self.Header['TestcaseID']:  res.append([f'TPR set Re-Ping delay value to {reping_time} Secs','Pass' if reping_time== 12.4 else 'Inconclusive'])
                            else:  res.append([f'TPR set Re-Ping delay value to {reping_time} Secs','Pass' if reping_time >=0.2 and reping_time <=12.6 else 'Inconclusive'])
                            break
                        else:
                            res.append([f'TPR did not sent SRQ/rep packet at index@ {{{id}}} after SRQ/rpr', 'Inconclusive']) 
                            break
                else:id+=1
            # find SRQ/ en packet
            SRQ_En=self.PktMethod.GetPacketDetails(packet="SRQ [0x20]", value="End Negotiation", limit=[id,self.Flow_limit[1]])
            if len(SRQ_En)>2:
                id=SRQ_En[2]+1
                while id < self.Flow_limit[1]:
                    if not self.file_list[id]['isTesterPkt'] and not self.file_list[id]['isFWTestermessage']:
                        res.append([f'TPR sent SRQ/en packet at index@ {{{SRQ_En[2]}}}','Pass'])
                        count=float(self.file_list[SRQ_En[2]]['value'].split(":")[1].replace('}',''))
                        res.append([f'End_Negotiation count was set to {{{count}}}, Exp: 2','Pass' if count==2 else 'Inconclusive'])
                        if 'ACK' in self.file_list[id]['pktType']: res.append([f'Received ACK for SRQ/en packet at index@ {{{id}}}','Pass'])
                        else:res.append([f'PTx sent {self.file_list[id]['pktType']} at index@ {{{id}}}','Fail'])
                        break
                    elif self.file_list[id]['isTesterPkt'] and not self.file_list[id]['isFWTestermessage']:
                        if "SRQ [0x20]" in self.file_list[id]['pktType'] and 'End Negotiation' in self.file_list[id]['value']:
                            SRQ_En[2]=id
                            id+=1
                            continue
                        else:
                            res.append([f'PTx did not sent response for SRQ/En packet at index@ {{{SRQ_En[2]}}}', 'Inconclusive'])
                            break
                    else:id+=1
                
                # Check Nexping
                res.extend(self.EPT_Helper(Check,[id,self.Flow_limit[1]],reping_time if 'REP_003' in self.Header['TestcaseID'] else None ))

            else:res.append([f'TPR did not sent SRQ/en packet', 'Inconclusive'])
        else:res.append([f'TPR did not sent SRQ/rpr Packet','Inconclusive'])
        

        return res

    def EPT_NextPing(self,CTSCheck,Check,flows,flwID):
        res=[]
        PktName=Check["EPT"][0]+" "+Check["EPT"][1] if Check["EPT"][1]is not None else Check["EPT"][0]
        self.Flow_limit = flows[flwID]['Limit']
        EPT = self.PktMethod.GetPacketDetails(packet=Check['EPT'][0], value=Check['EPT'][1], limit=self.Flow_limit)
        if len(EPT)>2:
            res.append([f'TPR sent {PktName} at {{{EPT[2]}}}', 'Pass'])
            CoilPkPk=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[EPT[2]+1, self.Flow_limit[1]])
            if len(CoilPkPk)>2:
                Stop=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[CoilPkPk[2]+1,len(self.file_list)])  
                if len(Stop)>2:
                    NextPing=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[CoilPkPk[2], Stop[2]])
                    if len(NextPing)>2:
                        Timing=round((NextPing[0]-EPT[1])*1000,3)
                        res.append([f'PTx initiated next ping at index@ {{{NextPing[2]}}}, Measured t_next ping from end of End Power Transfer packet is: {Timing} mS , Limit: GTE {Check['Limit']} mS', 'Pass' if Timing >= Check['Limit'] else 'Fail'])
                    else:res.append([f'PTx did not initiated next ping for  {Check['Limit']} mS, Limit: GTE {Check['Limit']} mS', 'Pass'])
                else: res.append([f'Test_stop did not found','Inconclusive'])
            else:res.append([f'PTx did not detached after sending {PktName} ','Fail'])
        else:res.append([f'TPR did not sent {PktName} packet ','Inconclusive'])

        return res

    def EPT_NR3(self,CTSCheck,Check,flows,flwID):
        res=[]
        Stop=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[len(self.file_list)-1,0])
        if len(Stop)>2:
            id=0
            count=0
            while id < Stop[2]:
                EPT = self.PktMethod.GetPacketDetails(packet="End Power Transfer", value="[EPT/nr]", limit=[id,Stop[2]])
                if len(EPT)>2:
                    count+=1
                    res.append([f'Found EPT/nr packet at {{{EPT[2]}}}','Pass'])
                    id=EPT[2]+1
                else:break
            
            if count <3:res.append([f'Test did not found 3 EPT/nr sequences','Inconclusive'])
            elif count==3:
                NextPing=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[id+1, Stop[2]])
                if len(NextPing)>2:
                    Timing=round((NextPing[0]-self.file_list[id-1]['stopTime'])*1000,3)
                    res.append([f'PTx initiated next ping at index@ {{{NextPing[2]}}}, Measured t_next ping from end of End Power Transfer packet is: {Timing} mS , Limit : >= 10 mins', 'Pass' if Timing >=600000 else 'Fail'])
                else:res.append([f'PTx did not initiated next ping for 10 mins', 'Pass'])
            else:res.append([f'Found {count} EPT/nr packets','Fail'])

                
        else: res.append([f'Test_stop did not found','Inconclusive'])
        return res


    def TimingChecks(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CE= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=self.Flow_limit)
        if len(CE)>2:
            CE2=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1], limit=[CE[2]+1,self.Flow_limit[1]])
            if len(CE2)>2:
                Tinterval=round((CE2[0]-CE[0])*1000,2)
                res.append([f'Measured timing from {round(CE[0],3)}_sec at index@ {CE[2]} to {round(CE2[0],3)}_sec at index@ {CE2[2]} is {Tinterval}_mS Limit: {Check['Limit']}', 'Inconclusive' if Tinterval < Check['Limit'][0]-Check['Tolerance'] or Tinterval > Check['Limit'][1]+Check['Tolerance'] else'Pass'])
            else:res.append([f'TPR sent only one {Check['Pkt'][0]} data packet','Fail'])
        else:res.append([f'Test did not entered PT phase','Inconclusive'])

        return res

    def PktReponses(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PKT= str(f'{Check['Pkt'][0]}{'_' + Check['Pkt'][1].replace('{','').replace('}','').replace(':','_') if Check['Pkt'][1] is not None else ''}')
        Pkt_count= 0
        count=Check.get('PktsCount')
        id=self.Flow_limit[0]
        while id < self.Flow_limit[1]: 
            Pkt=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=[id,self.Flow_limit[1]])
            
            if len(Pkt)>2:
                #Check the Response defined in CTS Checks
                Pkt_count += 1
                id=Pkt[2]+1

                resp=self.PktResponse(Pkt[2]+1,self.Flow_limit[1])
                if resp is None and  Check['response'] is None: res.append([f'PTx did not sent any response for {PKT} data packet at index@ {Pkt[2]}','Pass'])
                else:
                    if resp is not None and (resp[0] in Check['response'] if Check['response'] is not None else False) :
                        res.append([f'PTx responded with {resp[0]} for {PKT} data packet at index@ {Pkt[2]}','Pass'])
                        if Check['Timing']:
                            ResponseTime= round(( self.file_list[resp[1]]['startTime']-self.file_list[Pkt[2]]['stopTime'])*1000,3)
                            res.append([f'Measured response time between {PKT} and {resp[0]} is {ResponseTime} mS ','Fail'if ResponseTime < Check['ExpTime'][0]-Check['ExpTime'][1] or ResponseTime >Check['ExpTime'][0]+Check['ExpTime'][1] else "Pass"])
                    else:
                        if resp is None:res.append([f'PTx did not sent response for {Check['Pkt'][0]} at index@ {Pkt[2]}','Inconclusive'])
                        else:res.append([f'PTx responded with {resp[0]} for {PKT} data packet at index@ {Pkt[2]}','Fail'])
                id=Pkt[2]+1
            else:id+=1
        if count is not None: res.append([f'TPR sent {PKT} data packet {Pkt_count} times, Expected at least {Check['PktsCount']} times', 'Pass' if Pkt_count >= Check['PktsCount'] else 'Fail'])

        return res

    def ReplaceRP(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        pktcount=0
        s1 = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Execution_Started", Type="TesterMsg", limit=[0, len(self.file_list)-1])
        s2 = self.PktMethod.GetPacketDetails(packet="Test_Status", value="Test_Stop", Type="TesterMsg", limit=[0, len(self.file_list)])

        if len(s1) > 2 and len(s2) > 2:
            id = s1[2] + 1
            while id < s2[2]:
                Pkt = self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0], value=Check['Pkt'][1], limit=[id, s2[2]])
                if len(Pkt) > 2:
                    pktcount += 1
 #                   res.append([f"PTx sent {Check['Pkt'][0]} data packet at index@ {Pkt[2]}", 'Pass'])
                    id = Pkt[2] + 1
                else:
                    break
            res.append([f'TPR sent {Check["Pkt"][0]}_{Check["Pkt"][1]} data packet {pktcount} times, test executed for {round(s2[0]-s1[0],3)} Secs. Limit: at least 5 responses within 1 minute', 'Pass' if s2[0]-s1[0] <= 60 or pktcount < 5 else 'Inconclusive'])
        else:
            if len(s1) <= 2 or len(s2) <= 2:
                res.append(['Test_Status assertions are not found in the capture', 'Inconclusive'])

        return res

    def RP_Response(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"Nego")
        if PhaseLimit is not None:
            id=PhaseLimit[1]
            RpCount=0
            for pkt in Check['Pkts']:
                PKT= str(f'{pkt[0]}{'_' + pkt[1].replace('{','').replace('}','').replace(':','_') if pkt[1] is not None else ''}')
                PktFound=False
                while id < self.Flow_limit[1]: 
                    RP=self.PktMethod.GetPacketDetails(packet=pkt[0],value=pkt[1] ,limit=[id,self.Flow_limit[1]])
                    if len(RP)>2:
                        # Check Response Timing
                        Response=self.PktResponse(RP[2]+1,self.Flow_limit[1])
                        if Response is not None:
                            res.append([f'PTx responded with {Response[0]} for {PKT} data packet at index@ {RP[2]}','Pass'])
                            ResponseTime=round((self.file_list[Response[1]]['startTime']-self.file_list[RP[2]]['stopTime'])*1000,3)
                            res.append([f'Measured response time between {PKT} and {Response[0]} is {ResponseTime} mS ,Limit [3 ≤ t_response ≤ 10] ms','Fail'if ResponseTime < 3 or ResponseTime > 10 else "Pass"])
                            PktFound=True
                            RpCount+=1
                        id=RP[2]+1
                    else:break
                if not PktFound : res.append([f'Test did not found at least one {PKT} with response in the sequence','Inconclusive'])  
            if RpCount <4:res.append([f'Test did not found at least 4 16-Bit RP packets with responses in the sequence','Inconclusive'])  
        else:res.append([f'PRx did not entered Neg phase','Inconclusive'])

        return res

    def Tds(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Limit=self.Flow_limit
        ADT1=self.PktMethod.GetPacketDetails(packet="ADT",Type="Response" ,limit=Limit)
        if len(ADT1)>2:
            id=ADT1[2]+1
            Time1=[self.file_list[ADT1[2]]['startTime'],ADT1[2]]
            while id < Limit[1]:
                ADT2=self.PktMethod.GetPacketDetails(packet="ADT",Type="Response" ,limit=[id,Limit[1]])
                if len(ADT2)>2:
                    Tds=round((self.file_list[ADT2[2]]['startTime']-Time1[0])*1000,2)
                    res.append([f'Measured T_dts time between ADT index@ {Time1[1]} and ADT at index@ {ADT2[2]} is {Tds} mS','Pass' if Tds <=1500 else 'Fail'])
                    Time1=[self.file_list[ADT2[2]]['startTime'],ADT2[2]]
                    id=ADT2[2]+1
                else:break
        else:res.append([f'PTx did not sent any ADT data packets','Fail'])

        return res

    def uro(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check TPR has applied its final Load or not
        CoilLoad="19.6" if self.Header['Coil']=='TPR#1F' else "3.5"
        Load=self.PktMethod.GetPacketDetails(packet=CoilLoad,Type="TesterMsg" ,limit=self.Flow_limit)
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        if len(Load)>2:
            # Check the Final Load is Regulated or not
            Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[Load[2],self.Flow_limit[1]])
            if len(Regulated)>2:
                count=0
                id=Regulated[2]+1
                while id < self.Flow_limit[1]:
                    if count>=Check['cnt']:break
                    # Find CE-60 Pkt
                    CE60=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],value=Check['Pkt'][1] ,limit=[id,self.Flow_limit[1]])
                    if len(CE60)>2:
                        count+=1
                        # Find Uro1
                        vrect1 = self.CalculateVoltTwindow(CE60[2],self.AllChannelData,at=Check['t1a'][1],measure=Check['t1a'][2],winsize=Check['t1a'][0])
                        print("Vrect1",vrect1)
                        res.append([f"Measured Uro{count} is {vrect1[0]} V at {Check['Pkt'][0]} index @{CE60[2]}", "Pass"])
                        #Find Vro1
                        vrect2 = self.CalculateVoltTwindow(CE60[2],self.AllChannelData,at=Check['t2a'][1],measure=Check['t2a'][2],winsize=Check['t2a'][0])
                        if Check['NextPkt']:
                            nextpktid=self.findTypeid(limit=[CE60[2]+1,self.Flow_limit[1]])
                            if nextpktid is not None:vrect2 = self.CalculateVoltTwindow(nextpktid,self.AllChannelData,at=Check['t2a'][1],measure=Check['t2a'][2],winsize=Check['t2a'][0])
                        print("Vrect2",vrect2)
                        res.append([f"Measured Vro{count} is {vrect2[0]} V", "Pass"])
                        ChkRes = CommonMethods.check_measure(Check['exp'],round(abs((vrect1[0]-vrect2[0])*1000),3),Check['comp'])
                        print("Chkres",ChkRes)
                        res.append([f"The measured |U_ro{count}-V_ro{count}| is: {ChkRes[3]} mV, Limit: {ChkRes[2]}mV", ChkRes[1]])
                        id=CE60[2]+1
                    else:
                        res.append([f'PRx sent only {count} CE-60 data packets','Inconclusive'])
                        break

            else:res.append([f'PRx did not regulated to its final Load','Inconclusive'])
        else:res.append([f'PRx did not applied {CoilLoad}_ohms load','Inconclusive'])

        return res

    def VoltageRegulation(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check the Final Load is Regulated or not
        Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=self.Flow_limit)
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        if len(Regulated)>2:
            # Find Regulated CE Pkt
            CE=self.PktMethod.GetPacketDetails2(packet="Control Error",value="0" ,limit=[Regulated[2]+1,self.Flow_limit[1]])
            if len(CE)>2:
                vrect = self.CalculateVoltTwindow(CE[2],self.AllChannelData,at="end",measure="after")
                res.append([f"Measured U_L is {vrect[0]}V at index@ {CE[2]}, Limit: {Check['RegulationLimit']}", "Fail" if vrect[0] < Check['RegulationLimit'][0] or vrect[0] > Check['RegulationLimit'][1] else "Pass"])
                CE60=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0] ,value=Check['Pkt'][1],limit=[CE[2]+1,self.Flow_limit[1]])
                if len(CE60)>2:
                    Voltages=[]
                    for Voltage in Check['Voltages'][0].values():
                        Calvrect = self.CalculateVoltTwindow(CE60[2],self.AllChannelData,at=Voltage[1],measure=Voltage[2],winsize=Voltage[0])
                        Voltages.extend([round(Calvrect[0],2)])
                    Voltages.extend([min(Voltages),max(Voltages)])
                    # Perform Voltage Validation
                    cnt=1
                    for VL in Check['VoltageLimits'][0].values():
                        Limit=VL['Limit']
                        if VL['Formula']:Limit=[round(eval(VL['Limit'][0]),2),round(eval(VL['Limit'][1]),2)]
                        ChkRes = CommonMethods.check_measure(Limit,Voltages[cnt-1])
                        res.append([f"The measured V{cnt} is: {ChkRes[3]}V, Limit: {ChkRes[2]}", ChkRes[1]])
                        cnt+=1
                    PktsCountBefore=self.CECount(Limit=[CE[2],CE60[2]],Packet=Check['Pkt'][0],value="0")
                    PktsCountAfter=self.CECount(Limit=[CE60[2],self.Flow_limit[1]],Packet="Control Error",value="0")
                    res.append([f'PRx sent sequence of {PktsCountBefore} CE 0 before {Check['Pkt'][0]} with value {Check['Pkt'][1]} data packet.','Fail' if PktsCountBefore < Check['PktsCount'] else "Pass"])
                    res.append([f'PRx sent sequence of {PktsCountAfter} CE 0 after {Check['Pkt'][0]} with value {Check['Pkt'][1]} data packet.','Fail' if PktsCountAfter < Check['PktsCount'] else "Pass"])
                else: res.append([f'PRx did not sent CE {Check['Pkt'][1]}','Inconclusive'])
            else: res.append([f'PRx did not regulated to its final Load','Inconclusive'])
        else:res.append([f'PRx did not regulated to its final Load','Inconclusive'])

        return res

    def Tstabilize(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        #Default Configuration Check
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration",limit=self.Flow_limit)
        ID=self.PktMethod.GetPacketDetails(packet="Identification",limit=self.Flow_limit)
        if len(CFG)>2 and len(ID)>2:
            PCH=self.PktMethod.GetPacketDetails(packet="Power control hold off",limit=[ID[2]+1,CFG[2]])
            if len(PCH)>2:
                PCHTime=float(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PCH[2],'Power_Control_Hold_Off_Time')[0]['sRawData']))
                res.append([f'TPR sent PCH packet at index@ {{{PCH[2]}}} in between Identification and Configuration Packets','Pass'])
                res.append([f'TPR set PowerControlHold Off Time to {PCHTime} mS , Exp : 100 mS','Pass' if PCHTime==100 else 'Inconclusive'])
                Count=int(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(CFG[2],'Count')[0]['sRawData']))
                res.append([f'TPR set Count field to {Count} in Configuration Packet , Exp : 1', 'Pass' if Count==1 else 'Inconclusive'])
            else: res.append([f'TPR did not sent PCH Packet in between ID and  CFG','Inconclusive'])
        # Check the Final Load is Regulated or not
        Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=self.Flow_limit)
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        if len(Regulated)>2:
            # Find Regulated CE Pkt
            CE=self.PktMethod.GetPacketDetails2(packet="Control Error",value="0" ,limit=[Regulated[2]+1,self.Flow_limit[1]])
            if len(CE)>2:
                vrect = self.CalculateVoltTwindow(CE[2],self.AllChannelData,at="end",measure="after")
                res.append([f"Measured U_L is {vrect[0]}V at  index@ {CE[2]}, Limit:{Check['RegulationLimit']}", "Fail" if vrect[0] < Check['RegulationLimit'][0] or vrect[0] > Check['RegulationLimit'][1] else "Pass"])
                CE60=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0] ,value=Check['Pkt'][1],limit=[CE[2]+1,self.Flow_limit[1]])
                if len(CE60)>2:
                    PktsCountBefore=self.CECount(Limit=[CE[2],CE60[2]],Packet=Check['Pkt'][0],value="0")
                    PktsCountAfter=self.CECount(Limit=[CE60[2],self.Flow_limit[1]],Packet="Control Error",value="0")
                    res.append([f'PRx sent sequence of {PktsCountBefore} CE 0 before {Check['Pkt'][0]} with value {Check['Pkt'][1]} data packet.','Fail' if PktsCountBefore < Check['PktsCount'] else "Pass"])
                    res.append([f'PRx sent sequence of {PktsCountAfter} CE 0 after {Check['Pkt'][0]} with value {Check['Pkt'][1]} data packet.','Fail' if PktsCountAfter < Check['PktsCount'] else "Pass"])
                    vrect = self.CalculateVoltTwindow(CE60[2],self.AllChannelData,at="end",measure="after",winsize=[1,101])
                    result="Fail" if vrect[0] > 7.2 else "Pass"
                    res.append([f"Measured T_stabilize from end of packet at index@ {CE60[2]} to votlage crosses 7.2V is  {'greater than 100 ms' if result =='Pass' else 'less than 100 ms'} Limit >= 100 ms", result])
                else:res.append([f'PRx did not sent CE 0 {Check['Pkt'][1]}','Inconclusive'])
            else:res.append([f'PRx did not regulated to its final Load','Inconclusive'])
        else:res.append([f'PRx did not regulated to its final Load','Inconclusive'])

        return res

    def OverVoltageProtection(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check the Final Load is Regulated or not
        Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=self.Flow_limit)
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        if len(Regulated)>2:
            #find Initial Load
            if Check['EPP']:
                ILD=self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Load']}",Type="TesterMsg" ,limit=[Regulated[2]+1,self.Flow_limit[1]])
                if len(ILD)>2:res.append([f'PRx applied the Load {Check['InitialLoad']}_ohms','Pass'])
                else:res.append([f'PRx did not applied the Load {Check['InitialLoad']}_ohms','Inconclusive'])

            # Find the Load
            LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Load']}",Type="TesterMsg" ,limit=[Regulated[2]+1,self.Flow_limit[1]])
            if len(LD)>2:
                #Check 10CE packets are sent or not before applying the Load
                PktsCountBefore=self.CECount(Limit=[LD[2],self.Flow_limit[0]],value=["+1","0","-1"])
                res.append([f'PRx sent sequence of {PktsCountBefore} CE Packets with -1, 0, 1 before the Load: {Check['Load']}_ohms.','Fail' if PktsCountBefore < Check['PktsCount'] else "Pass"])
                MaxValue = 0
                MaxIndex = 0
                #Get the max voltage received time for the PD start to end
                sindex = int((LD[0]*1000)+0.50/self.AllChannelData['Interval'])
                eindex = int((self.file_list[self.Flow_limit[1]-1]['startTime']*1000)/self.AllChannelData['Interval'])
                id = sindex
                while id <= eindex:
                    value = round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),3)
                    if value > MaxValue:
                        MaxValue=value
                        MaxIndex=id
                    id+=1
                if MaxValue !=0:
                    res.append([f'Measured max voltage at {round((self.AllChannelData['Interval']*MaxIndex)/1000,3)}sec  is {MaxValue}V , Limit <20V', 'Fail' if MaxValue >20 else 'Pass'])
                    res.append([f'Load voltage {'does not exceed' if MaxValue <16 else' exceeded'} 16V at any time in between data packets from 500 ms after switching the Load to {Check['Load']}_ohms', 'Fail' if MaxValue >16 else 'Pass'])

            else:res.append([f'PRx did not applied Load: {Check['Load']}_ohms','Inconclusive'])
        else:res.append([f'PRx did not regulated to its final Load','Inconclusive'])

        return res

    def LoadVoltage(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check the TPR has regulated to its load power and Volatge or not
        Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=self.Flow_limit)
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        self.AllChannelData3 = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
        if len(Regulated)>2:
            #Find the Control Error before Voltage Regualtion
            CE=self.PktMethod.GetPacketDetails(packet="Control Error" ,limit=[Regulated[2],self.Flow_limit[0]])
            vrect = self.CalculateVoltTwindow(CE[2],self.AllChannelData,at="start",measure="before")
            res.append([f"Measured U_L is {vrect[0]}V at index@ {CE[2]}, Limit:{Check['RegulationLimit']}", "Fail" if vrect[0] < Check['RegulationLimit'][0] or vrect[0] > Check['RegulationLimit'][1] else "Pass"])
            if Check['PowerLimit'][0]:
                # Find the Power level 
                Prect=round(vrect[0]*(self.CalculateVoltTwindow(CE[2],self.AllChannelData3,at="start",measure="before"))[0],2)
                res.append([f"Measured regualated Load power is {Prect}W at index@ {CE[2]}", "Fail" if Prect < Check['PowerLimit'][1][0] or Prect > Check['PowerLimit'][1][1] else "Pass"])
                #Check CE packets and voltage regulation if there is no Load  assertion for Test_ID= "Guaranteed_Load_Power_23d_2"
            elif self.Header['TestcaseID'] in ['Guaranteed_Load_Power_23d_2']:
                pkt = self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[Regulated[2]+1,self.Flow_limit[1]])
                if len(pkt)>2:
                    PktsCountBefore=self.CECount(Limit=[Regulated[2],pkt[2]],value=["+1","0","-1"])
                    res.append([f'PRx sent sequence of {PktsCountBefore} CE packets with -1, 0, 1','Fail' if PktsCountBefore < Check['PktsCount'] else "Pass"])
                    res.append([f"Measured U_L is {vrect[0]}V at index@ {pkt[2]}, Limit:{Check['RegulationLimit']}", "Fail" if vrect[0] < Check['RegulationLimit'][0] or vrect[0] > Check['RegulationLimit'][1] else "Pass"])

            # Check the Appropriate Loads applied or not
            id=Regulated[2]+1
            for Load in Check['Loads']:
                # Find the Load
                LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load {Load}",Type="TesterMsg" ,limit=[id+1,self.Flow_limit[1]])
                if len(LD)>2:
                    #Check 10CE packets are sent or not before applying the Load
                    PktsCountBefore=self.CECount(Limit=[LD[2],self.Flow_limit[0] if Load ==Check['Loads'][0] else id],value=["+1","0","-1"])
                    res.append([f'PRx sent sequence of {PktsCountBefore} CE packets with -1, 0, 1 before Load: {Load}_ohms.','Fail' if PktsCountBefore < Check['PktsCount'] else "Pass"])
                    # Check Regulated or not after applying the Load
                    Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[LD[2]+1,self.Flow_limit[1]])
                    if len(Regulated)>2:
                        # find the Applied Load is correct or not
                        LoadCE=self.PktMethod.GetPacketDetails2(packet="Control Error",value=["0","+1","-1"] ,limit=[Regulated[2],LD[2]+1])
                        Loadvrect = self.CalculateVoltTwindow(LoadCE[2],self.AllChannelData,at="start",measure="before")
                        LoadResistance=round(Loadvrect[0]/(self.CalculateVoltTwindow(LoadCE[2],self.AllChannelData3,at="start",measure="before"))[0],2)
                        res.append([f"Measured LoadResistance: {LoadResistance}_ohms at index@ {LoadCE[2]}", "Fail" if LoadResistance > round((LoadResistance + ((LoadResistance*0.2)/100)),2) or LoadResistance < round((LoadResistance-((LoadResistance*0.2)/100)),2) else "Pass"])
                        if Load ==Check['Loads'][-1]:
                            PktsCountAfter=self.CECount(Limit=[LD[2],self.Flow_limit[1]],value=["+1","0","-1"])
                            res.append([f'PRx sent sequence of {PktsCountAfter} CE Packets with -1, 0, 1 after Load: {Load}_ohms.','Fail' if PktsCountBefore < Check['PktsCount'] else "Pass"])
                            res.append([f"Measured U_L is {Loadvrect[0]}V at index@ {LoadCE[2]}, Limit:{Check['RegulationLimit']}", "Fail" if Loadvrect[0] < Check['RegulationLimit'][0] or Loadvrect[0] > Check['RegulationLimit'][1] else "Pass"])
                        id=LD[2]+1
                    else:
                        res.append([f'PRx did not regulated after appying the Load: {Load}_ohms','Inconclusive']) 
                        break
                else: 
                    res.append([f'PRx did not applied Load: {Load}_ohms','Inconclusive'])
                    break
        else:res.append([f'PRx did not regulated to its final Load','Inconclusive'])

        return res

    
    def AttemptLoadVoltage(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']

        phaseCheck=self.CheckPhase(self.Flow_limit[0],"PT")
        if phaseCheck is not None:
            # Check target operating voltage reached or not
            LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load {Check['Load']}",Type="TesterMsg" ,limit=[phaseCheck,self.Flow_limit[1]])
            if len(LD)>2:
                res.append([f'Prx Applied its final Load : {Check['Load']} Ohms','Pass'])
                VR=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[LD[2]+1,self.Flow_limit[1]])
                if len(VR)>2:
                    self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)  #  Voltage Plot
                    self.AllChannelData_Current = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  # Current  Plot
                    Loadvrect = self.CalculateVoltTwindow(VR[2],self.AllChannelData,at="start",measure="before")
                    LoadCurrent=self.CalculateVoltTwindow(VR[2],self.AllChannelData_Current,at="start",measure="before")
                    LoadResistance=round(Loadvrect[0]/LoadCurrent[0],3)
                    RLimit=[round((Check['Load'] - ((Check['Load']*Check['LoadTolerance'])/100)),3), round((Check['Load'] +((Check['Load']*Check['LoadTolerance'])/100)),3)]
                    res.append([f"Measured load resistance: {LoadResistance}_ohms, Limit:[{RLimit[0]}_ohms ~ {RLimit[1]}_ohms]", 
                                    'Pass' if LoadResistance >= RLimit[0] and LoadResistance <= RLimit[1] else 'Inconclusive'])
                    VLimit= [round((Check['Voltage'] - ((Check['Voltage']*Check['VoltageTolerance'])/100)),3), round((Check['Voltage'] +((Check['Voltage']*Check['VoltageTolerance'])/100)),3)]

                    res.append([f'while TPR Regulating to its Operating Target Load Voltage -> Measured Voltage is : {Loadvrect[0]} V ,Limits : {VLimit[0]} V ~ {VLimit[1]} V', 
                                'Pass' if Loadvrect[0] >=VLimit[0]  and Loadvrect[0] <= VLimit[1] else 'Inconclusive'])
                    Power=round(Loadvrect[0]*LoadCurrent[0],3)
                    PLimit= [round((Check['Power'] - ((Check['Power']*Check['PowerTolerance'])/100)),3), round((Check['Power'] +((Check['Power']*Check['PowerTolerance'])/100)),3)]
                    res.append([f"Measured target load power: {Power} W, Limit: {PLimit[0]} W ~ {PLimit[1]} W", 
                                    'Pass' if Power >= PLimit[0] and Power <= PLimit[1] else 'Inconclusive'])
                    
                    # Check Sequence of Continuous -1,0,+1 Packets
                    count=self.ContinuousPackets([LD[2]+1,VR[2]])
                    res.append([f'TPR sent {count} CE packets, Exp: Atleast 40 continuous CE packets','Pass' if count >= 40 else 'Inconclusive'])

                    # find the CE Range (0-3)
                    res.extend(self.CE3_Voltage([VR[2]+1,self.Flow_limit[1]],Check))


                else:res.append([f'PRx did not regulated to its final load {Check['Load']}_ohms','Inconclusive'])
            else:res.append([f'TPR did not switched to its final load {Check['Load']}_ohms to reach Target Load Power'])
        else : res.append([f'PRx did not entered PT Phase','Inconclusive'])
        
        return res
    
    def ContinuousPackets(self,limit):
        count=0
        id=limit[0]
        while id < limit[1]:
            if count >=40:break
            if self.file_list[id]['pktType']=="Control Error" :
                if self.file_list[id]['value'] in ["0","-1","+1"]:
                    count+=1
                else:
                    count=0
            id+=1
        return count
    
    def CE3_Voltage(self,limit,Check):
        res=[]
        id=limit[0]
        CE3=True
        StopTime=None
        while id < limit[1]:
            if self.file_list[id]['pktType']=="Control Error" :
                if self.file_list[id]['value'] not in ["0","+2","+3","+1"]:
                    CE3=False
                    res.append([f'TPR sent CE packet with value { self.file_list[id]['value']} which is not in range of (0-3)','Inconclusive'])  
                StopTime=self.file_list[id]['stopTime']
            id+=1

        # Test Duration
        if StopTime is not None:
            if CE3 : res.append([f' Tester sent CE packets which are in range of (0-3) only','Pass'])
            # Measure Voltage throught the Ramping
            Values=self.MonitorVoltage(limit[0],self.Flow_limit[1]-2) 
            if Values[1] !=0 and  Values[3] !=0:
                res.append([f' Measured max voltage U_L at {round((self.AllChannelData['Interval']*Values[0])/1000,3)} sec is {Values[1]}_V and  min voltage U_L at {round((self.AllChannelData['Interval']*Values[2])/1000,3)} sec is {Values[3]}_V , Limit [<= {Check['limit']} V] ', 
                            'Pass' if  Values[1] <= Check['limit'] else 'Fail'])

            Timing= round(StopTime-self.file_list[limit[0]]['startTime'],3)
            res.append([f'Stayed {round(Timing/60,3)} mins during load voltage regulation ramp, Exp: Atleast 2 mins','Pass' if Timing/60 >=2  else 'Inconclusive'])
        else: res.append([f'Did not found CE packets which are in range of (0-3)','Inconclusive'])

        return res



    def Fop_UL(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        FRlimit={
            "A2":[137,143],"A3":[102,143], "A4":[127,133], "A6":[170,180],"A7":[102,143],"A8":[120,140],"A10":[170,180],"A11":[170,180],"A11a":[145,148],
            "A12":[160,180],"A13":[105,115],"A14":[132,152], "A15":[102,143],"A16":[170,180],
            "MP-A1":[170,180],"MP-A2":[135,145], "MP-A3":[160,180], "MP-A4":[170,180],"MP-A5":[126.1,133.9],"MP-A6":[140,150],"MP-A7":[170,180],"MP-A8":[170,180],
            "MP-A9":[120,130],"MP-A10":[155,171],"MP-A11":[120,130],"MP-A12":[108,114],"MP-A13":[112,128],"MP-A14":[118,138],"MP-A15":[120,136],"MP-A16":[145.5,150]
        }
        # find Execution Started and then validate the First Ping
        ST= self.PktMethod.GetPacketDetails(packet="Test_Status",value="Execution_Started" ,Type="TesterMsg" ,limit=[0,len(self.file_list)-1])
        SP=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[0,len(self.file_list)])
         
        if len(ST) > 2 and len(SP) > 2:
            self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
            id=ST[2]
            Vrect_Pings=[]
            while id < SP[2]:
                pkt=self.PktMethod.GetPacketDetails(packet=Check['pkt'][0],Type=Check['pkt'][1] ,limit=[id,SP[2]])
                if len(pkt)>2:
                    vrect = self.CalculateVoltTwindow(pkt[2],self.AllChannelData,at=Check['t1a'][1],measure=Check['t1a'][2],winsize=Check['t1a'][0])
                    if vrect[0] >3 :
                        Vrect_Pings.append([vrect[0],pkt[2]])
                        # find FOP
                        fop=self.PktMethod.GetPacketDetails(packet="Fop",Type="TesterMsg" ,limit=[pkt[2]+1,SP[2]])
                        if len(fop)>2:
                            Fop_val=GeneralMethods.GetFloatFromStr(self.file_list[fop[2]]['value'].split(',')[0])
                            if self.Certification=="1.3.3":Check['FV'][0]=FRlimit[self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['PTxDesign']]
                            ChkRes = CommonMethods.check_measure( Check['FV'][0],Fop_val[0])
                            res.append([f"Measured F_op value at index@ {fop[2]} is {Fop_val[0]}kHz, Limit: [{ChkRes[2]}] kHz", ChkRes[1]])
                            ChkRes = CommonMethods.check_measure( Check['FV'][1],vrect[0])
                            res.append([f"Measured U_L is {vrect[0]}V at index@ {pkt[2]}, Limit: [{ChkRes[2]}] Volts", ChkRes[1]])
                        else:res.append([f'Test did not found F_op assertion','Inconclusive'])
                        break
                    id=pkt[2]+1
                else:break
            if len(Vrect_Pings) == 0:res.append([f'PRx could not able to find the V_rect Ping > 3V','Fail'])                    
        else: res.append([f'Test did not found Test_Start or Test_Stop assertions','Inconclusive'])
        return res

    def Fop_UL_SignalStrength(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        FRlimit={
            "A2":[137,143],"A3":[102,143], "A4":[127,133], "A6":[170,180],"A7":[102,143],"A8":[120,140],"A10":[170,180],"A11":[170,180],"A11a":[145,148],
            "A12":[160,180],"A13":[105,115],"A14":[132,152], "A15":[102,143],"A16":[170,180],
            "MP-A1":[170,180],"MP-A2":[135,145], "MP-A3":[160,180], "MP-A4":[170,180],"MP-A5":[126.1,133.9],"MP-A6":[140,150],"MP-A7":[170,180],"MP-A8":[170,180],
            "MP-A9":[120,130],"MP-A10":[155,171],"MP-A11":[120,130],"MP-A12":[108,114],"MP-A13":[112,128],"MP-A14":[118,138],"MP-A15":[120,136],"MP-A16":[145.5,150]
        }
        # find Execution Started and then validate the First Ping
        pkt=self.PktMethod.GetPacketDetails(packet=Check['pkt'][0],Type=Check['pkt'][1] ,limit=self.Flow_limit)
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        if len(pkt)>2:
            # find FOP
            fop=self.PktMethod.GetPacketDetails(packet="Fop",Type="TesterMsg" ,limit=[pkt[2]+1,self.Flow_limit[1]])
            if len(fop)>2:
                Fop_val=GeneralMethods.GetFloatFromStr(self.file_list[fop[2]]['value'].split(',')[0])
                if self.Certification=="1.3.3":Check['FV'][0]=FRlimit[self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['PTxDesign']]
                ChkRes = CommonMethods.check_measure( Check['FV'][0],Fop_val[0])
                res.append([f"Measured F_op value at index@ {fop[2]} is {Fop_val[0]}kHz, Limit: [{ChkRes[2]}] kHz", ChkRes[1]])
                vrect = self.CalculateVoltTwindow(pkt[2],self.AllChannelData,at=Check['t1a'][1],measure=Check['t1a'][2],winsize=Check['t1a'][0])
                ChkRes = CommonMethods.check_measure( Check['FV'][1],vrect[0])
                res.append([f"Measured U_L is {vrect[0]}V at index@ {pkt[2]}, Limit: [{ChkRes[2]}] Volts", ChkRes[1]])
            else:res.append([f'Test did not found F_op Assertion','Inconclusive'])
        else:res.append([f'Test did not found {Check['pkt'][0]}','Inconclusive'])

        return res

    def Twake(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ping = self.PktMethod.GetPacketDetails(packet="Ping Detected",limit=self.Flow_limit,Type="TesterMsg")
        if len(ping)>2:
            #Find the First Packet
            id=ping[2]
            while id < self.Flow_limit[1]:
                TypeCheck=self.PktMethod.GetPacketType(id)
                Twake=round((self.file_list[id]['startTime']-ping[1])*1000,3)+5.50
                
                if TypeCheck=='Packet' and self.file_list[id]['pktType'] == "Signal strength": 
                    res.append([f'Measured t_wake from {round(ping[1],3)}Sec to {round(self.file_list[id]['startTime'],3)+5.5}Sec  is {Twake} mS ,Limit : {Check['Limit']}', 'Inconclusive' if Twake <Check['Limit'][0] or Twake > Check['Limit'][1] else 'Pass'])
                    break
                else:
                    if 'Shutdown' in self.file_list[id]['pktType']:
                        res.append([f'could not able to find the Ping packet', 'Fail'])
                    id+=1

        else: res.append([f'could not able to find the Ping', 'Fail'])

        return res

    def TimingCheck(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        for TC in Check['TimingCheck']:
            
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
                            if TC=='Tstart':res.append([f'Measured {TC} from {firstPKt} packet at time: {round(firstPktTime,3)} Sec to {self.file_list[id]['pktType']} packet at time: {round(self.file_list[id]['startTime'],3)} Sec  is {Timing} mS, Limit:{Limit}', 'Fail' if Timing <Limit[0]-0.1 or Timing > Limit[1]+0.1 else 'Pass'])
                            else:res.append([f'Measured {TC} from {firstPKt} packet at time: {round(firstPktTime,3)} Sec to {self.file_list[id]['pktType']} packet at time: {round(self.file_list[id]['startTime'],3)} Sec  is {Timing} mS, Limit:{Limit}', 'Fail' if Timing <Limit[0] else 'Pass'])
                            break
                        else:id+=1
                else: id+=1
                        
        return res

    def FODTempCheck(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        if Check['PTCheck']:
            PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
            if PhaseLimit is not None:
                res.extend(self.GetTemperature(Check))
            else: res.append([f'PRx did not entered PT phase','Pass'])
                        
        return res

    def Tstart_Nego(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # find the reponse from 
        FP=self.PktMethod.GetPacketDetails(packet= Check['inpkt'][0],value=Check['inpkt'][1],limit=self.Flow_limit)
        if len(FP)>2:
            EP=self.PktMethod.GetPacketDetails(packet= Check['enpkt'][0],value=Check['enpkt'][1],limit=[FP[2]+1,self.Flow_limit[1]])
            if len(EP)>2:
                id=FP[2]+1
                while id < EP[2]:
                    resid=self.findTypeid(limit=[id,self.Flow_limit[1]],Type='Response')
                    if resid is not None:
                        nextid=self.findTypeid(limit=[resid,self.Flow_limit[1]],Type='Packet')
                        if nextid is not None:
                            Tstart=round(((self.file_list[nextid]['startTime']-self.file_list[resid]['stopTime'])*1000)+5.5,2)
                            # Tsilent=round((self.file_list[nextid]['startTime']-self.file_list[resid]['stopTime'])*1000,2)
                            # res.append([f'Measured Tsilent Timing from Response:{self.file_list[resid]['pktType']} at Id {resid} to pkt :{self.file_list[nextid]['pktType']}_{self.file_list[nextid]['value']} at Id {nextid} is {Tsilent}', 'Pass' if Tsilent >6 else 'Fail'])
                            res.append([f'Measured t_start timing from response:{self.file_list[resid]['pktType']} at index@ {resid} to packet :{self.file_list[nextid]['pktType']}_{self.file_list[nextid]['value']} at index@ {nextid} is {Tstart} mS Limit:{Check['Limit']}', 'Fail' if Tstart >Check['Limit'][1]+0.1 or Tstart<Check['Limit'][0]-0.1 else 'Pass'])
                            id=nextid+1
                        else:break
                    else:break
            else:res.append([f'PRx did not sent {Check['enpkt'][0]} _{Check['enpkt'][1] }packet', 'Inconclusive'])
        else:res.append([f'PRx did not sent {Check['inpkt'][0]} _{Check['inpkt'][1] }packet', 'Inconclusive'])
                    
        return res

    def Thermal(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
        if PhaseLimit is not None:
            id=PhaseLimit[0]
            if Check['Load']:
                for Load in Check['Loads']:
                        # Find the Load
                    LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load {Load}",Type="TesterMsg" ,limit=[id,self.Flow_limit[1]])
                    if len(LD)>2:
                        res.append([f"PRx applied Load: {Load}_ohms at index@ {LD[2]}", "Pass"])
                        id=LD[2]+1
                    else: 
                        res.append([f"PRx did not applied Load: {Load}_ohms", "Inconclusive"]) 
                        break

            # monitor current or voltage
            if Check['Current']:self.AllChannelData = self.PlotMethod.GetAllChannelData2('3',self.JapiData)
            else:self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
            MaxValues=self.MonitorVoltage(id,self.Flow_limit[1]-2) 
            if MaxValues[1] !=0:
                res.append([f'Measured max {'Voltage' if not Check['Current'] else 'Current'} at {round((self.AllChannelData['Interval']*MaxValues[0])/1000,3)}sec  is {MaxValues[1]} {Check['unit']} , Limit :{Check['limit']}', 'Fail' if MaxValues[1] <Check['limit'][0] or MaxValues[1] >Check['limit'][1] else 'Pass'] )
            #Get Max, min Temperatures
            templist = []
            self.AllChannelData11= self.PlotMethod.GetAllChannelData2('12',self.JapiData)
            for temp in self.AllChannelData11['RV']['displayDataChunk']: templist.append(temp)  
            res.append([f"Measured coil temperature is {max(templist)} °C,Measured ambient temperature is :{templist[0]} °C", "Pass"]) 
            res.append([f"Difference in temperature is {round((max(templist)-templist[2]),2)} °C", "Pass" if round((max(templist)-templist[2]),2) <12 else 'Fail']) 
            # Find Tc execution Timing
            Timing=round(((self.file_list[self.Flow_limit[1]]['stopTime']-self.file_list[self.Flow_limit[0]]['startTime'])*1000)/60000,3)
            res.append([f'Test executed for {Timing} mins , Limit >=60 mins','Pass' if Timing>=60 else 'Inconclusive'])

        else:res.append([f'PTx did not entered into PT Phase','Inconclusive'])

        return res
   
    def FalseFOD(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
        if PhaseLimit is not None:
            LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load 1000mA",Type="TesterMsg" ,limit=[PhaseLimit[0],self.Flow_limit[1]])
            if len(LD)>2:
                Timing=round((self.file_list[self.Flow_limit[1]]['stopTime']-LD[1])*1000,2)
                res.append([f'PRx stayed in Power Transfer Phase after applying the Load: 1000 mA {Timing}mS','Fail' if Timing < 60000 else 'Pass'])
            else:res.append([f'PTx removed power signal before applying the Load: 1000 mA','Fail'])
        else:res.append([f'PRx did not entered PT phase','Inconclusive'])

        return res

    def FOD_Temperature(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
        if PhaseLimit is not None:
            CEPkts=False
            id=PhaseLimit[0]
            while id < self.Flow_limit[1]:
                
                if self.file_list[id]['pktType']=="Control Error" and  self.file_list[id]['value'] in ["0","-1","+1"]:
                    # Verify contious Sequence of CE +0,-1,+1
                    CEcnt=0
                    while id < self.Flow_limit[1]:
                        if self.PktMethod.GetPacketType(id) == 'Packet' :
                            if self.file_list[id]['pktType']=="Control Error" :
                                if self.file_list[id]['value'] in ["0","-1","+1"]:CEcnt+=1
                                else:break
                            if CEcnt >=10:break
                        id+=1
                    
                    if CEcnt >=10:
                        res.append([f'PRx sent continuous {CEcnt} CE packets with values "0","-1","+1"  after stabilization',"Pass"])
                        CEPkts=True
                        break
                id+=1
            if not CEPkts:res.append([f'PRx did not sent continuous {CEcnt} CE packets with values "0","-1","+1"  after stabilization ','Inconclusive'])
            res.extend(self.GetTemperature(Check))
        else:res.append([f'PRx did not entered PT phase','Inconclusive'])


        return res

    def FrequencyModulation(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        
        # if self.Certification not in ["2.2.1","2.2.0","1.3.3","2.1.0"]:
        results=[]
        for TCdata in self.BKjsonData['testBkpTestResultsandPath']:
            if self.Header['TestcaseID'] in TCdata['testcaseDetails']['m_TestId']:
                if len(TCdata['testinformation']['Measurements'])>1:
                    for measures in TCdata['testinformation']['Measurements']:
                        results.append([measures['MeasurementName'],measures['Value']])
                else:break
        if len(results)>0: 
            for Res in results:
                result,val= self.PktMethod.compare_hex_to_expected(Res[1],Check[Res[0]][0:-1],Check[Res[0]][-1])
                res.append([f'Measured {Res[0]} is {round(Res[1],2)} nS, limits:{Check[Res[0]][0:-1]} , Comp:{Check[Res[0]][-1]}', 'Pass' if result else 'Fail'])
        else: res.append([f' Standard deviations measurements did not found ', 'Inconclusive'])
       

        return res

    def LoadModulation(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Start= self.PktMethod.GetPacketDetails(packet="Test_Status" ,value="Execution_Started" ,Type="TesterMsg" ,limit=[0,len(self.file_list)-1])
        if len(Start)>2:
            Stop=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[Start[2],len(self.file_list)])  
            if len(Stop)>2:
                # find Pings between Start and Stop
                pings=self.GetPings(Start,Stop)
                # print(pings)
                PTPhaseCount=0
                for pinglimit in pings:
                    self.Flow_limit=pinglimit
                    PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
                    if PhaseLimit is not None:
                        PTPhaseCount+=1
                        Timing=round((self.file_list[PhaseLimit[1]]['stopTime']-self.file_list[PhaseLimit[0]]['startTime'])*1000,2)
                        res.append([f'PTx proceed to Power Transfer phase and stayyed for {Timing}mS, Limit >= 30Sec','Pass' if Timing >=30000 else 'Inconclusive'])
                res.append([f'PTx enters the Power Tranfer Phase {PTPhaseCount} times and maintain communications throughout the test in each repetition','Pass' if  PTPhaseCount >=3 else 'Fail'])
            else:res.append([f'Test did not found Test_Stop ','Inconclusive'])
        
        return res

    def SelectionPhase(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check the Test Duration
        Start= self.PktMethod.GetPacketDetails(packet="Test_Status" ,value="Execution_Started" ,Type="TesterMsg" ,limit=[0,len(self.file_list)-1])
        if len(Start)>2:
            Stop=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[Start[2],len(self.file_list)])  
            if len(Stop)>2:
                pings=self.GetPings(Start,Stop)  # find Pings between Start and Stop
                # print(pings)
                PTPhaseCount=0
                self.AllChannelData_Volatge = self.PlotMethod.GetAllChannelData2('2',self.JapiData)  #  Voltage Plot
                self.AllChannelData = self.PlotMethod.GetAllChannelData2('3',self.JapiData)  # Current  Plot
                # Validate Each Ping
                LoadFlag=False
                for pinglimit in pings:
                    self.Flow_limit=pinglimit
                    phaseCheck=self.CheckPhase(self.Flow_limit[0],"PT")
                    if phaseCheck is not None:
                        PTPhaseCount+=1
                        if PTPhaseCount >3:
                            res.append([f'PRx entered PT phase more than three times','Fail'])
                            break
                         # Check target operating voltage reached or not
                        Regulated=self.PktMethod.GetPacketDetails(packet="Voltage_regulation",Type="TesterMsg" ,limit=[phaseCheck,self.Flow_limit[1]])
                        if len(Regulated)>2:
                            Loadvrect = self.CalculateVoltTwindow(Regulated[2],self.AllChannelData_Volatge,at="start",measure="before")
                            res.append([f'Measured voltage is {Loadvrect[0]}V, Limit [4.116 V ~ 4.284 V]', 
                                            'Pass' if Loadvrect[0] >= 4.116 and Loadvrect[0] <= 4.284 else 'Inconclusive'])
                            self.id =Regulated[2]+1
                            # Check Loads are applied or not
                            results,LoadFlag=self.CheckLoads(Check)
                            res.extend(results)

                            if not LoadFlag:
                                # find EPT nr pkt
                                EPT=self.PktMethod.GetPacketDetails(packet="End Power Transfer",value= "[EPT/nr]",limit=[self.id,self.Flow_limit[1]])
                                if len(EPT)>2:
                                    Timing=round((EPT[0]-self.file_list[self.id-1]['stopTime']),3)
                                    res.append([f'PRx  sent End_Power_Transfer packet at index@ {EPT[2]} within {Timing}_Secs from end of 3.5_ohms load at index@ {self.id-1},  Exp : Atleast after 30_Secs ','Pass' if Timing >=30 else 'Inconclusive'])
                                    # Check the PTx detached or not
                                    SD= self.PktMethod.GetPacketDetails(packet='Shutdown',Type="TesterMsg",limit=[EPT[2],self.Flow_limit[1]+1])
                                    if len(SD)>2: res.append([f'PTx detached after End_Power_Transfer packet is sent at index@ {EPT[2]}','Pass'])
                                    else:
                                        res.append([f'PTx did not detached after End_Power_Transfer packet is sent at index@ {EPT[2]}','Fail'])
                                        LoadFlag=True

                                else: 
                                    res.append([f'PRx did not sent End_Power_Transfer packet','Inconclusive'])
                                    LoadFlag=True
                        else:
                            res.append([f'TPR did not regulated to its operating voltage 4.2V','Inconclusive'])
                            LoadFlag=True
                    if LoadFlag: break
                if PTPhaseCount==0 :res.append([f'TPR did not entered in to PT phase atleast one time','Inconclusive'])
                if PTPhaseCount <=3 : res.append([f'TPR entered PT phase at most 3 Times','Pass'])
                # Check Time Duration of the Test Case
                Timing=round((Stop[0]-Start[1])/60,3)
                res.append([f'Tester stayed {Timing} mins in contact with PTx, Limit: [Atleast 10 Mins]','Pass' if Timing >= 10 else "Inconclusive"])
            else:res.append([f'Test did not found Test_Stop assertion','Inconclusive'])
           
        return res

    

    def CerificateLength(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # simple flow
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            result,id,seq=self.AuthSequence(id,Authvalue1="Get_Certificate",Payload1=Check['Certificate'],Authvalue2="Certificate",Payload2=[])
            res.extend(result)
            if seq:
                AuthResp=self.PktMethod.GetPacketDetails(packet=Check['resp'][0],value=Check['resp'][1],Type='Response',limit=[RP0[2]+1,self.Flow_limit[1]])
                if len(AuthResp)>2:
                    ChainLength=None
                    id=0
                    while id < len(self.Auth_file_list):
                        if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                            payloadvalue=self.GetAuthPayloadDetails(id,"Certificate_Chain_Segment","B1_B76","[7:0]")[0]['sRawData']
                            if payloadvalue is not None:ChainLength=payloadvalue
                            break
                        id+=1
                    Length=len(ChainLength.split("-")) if ChainLength is not None else 0
                    res.append([f'PTx sent {Check['resp'][0]}_{Check['resp'][1]} response at index@ {AuthResp[2]} with  Certificate_Chain_Segment length of {Length} Bytes Limit :{Check['limit']}','Fail' if Length > Check['limit'][1] or Length <=Check['limit'][0] else 'Pass'])
                else:res.append([f'PTx did not sent {Check['resp'][0]}_{Check['resp'][1]} packet','Inconclusive'])

        return res



    

    def BytesCheck(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ADCAuth_TPT=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth" ,Type="Response",limit=self.Flow_limit)
        if len(ADCAuth_TPT)>2:
            Bytes=self.file_list[ADCAuth_TPT[2]]['value'].split(':')[1].replace('}','')
            Length=int("".join([c for c in Bytes if c.isdigit()]))
            if Check['Formula']:
                digests=self.PktMethod.GetPacketDetails(packet="ADT",value="Digests" ,Type="Response",limit=[ADCAuth_TPT[2],self.Flow_limit[1]])
                slot=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(digests[2],'Slots_Returned_Mask')[0]['sRawData'])
                if slot ==1:
                    res.append([f'PTx responded with ADC/auth packet at index@ {ADCAuth_TPT[2]} with {Length} Bytes', 'Pass' if Length== (slot*32)+2 else 'Fail'])
                else: res.append([f'PTx responded with digests with Slots_Returned_Mask {slot} Expected: 1', 'Fail'])
            else:res.append([f'PTx responded with ADC/auth packet at index@ {ADCAuth_TPT[2]} with {Length} Bytes', 'Pass' if Length== Check['Length'] else 'Fail'])   
        else:res.append([f'PTx did not responded with ADC/auth packet', 'Inconclusive']) 

        return res

    def ErrorResponse(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=0
        AuthDetails={ 
            "Error_Code":[],
            "Error_Data":[]
            }
        while id < len(self.Auth_file_list):
            if self.Auth_file_list[id]['pktType']=="ERROR":
                for payload in Check['Auth']:
                    payloadvalue=self.PktMethod.hex_to_decimal(self.GetAuthPayloadDetails(id,payload['Name'],payload['Byte'],payload['Bit'])[0]['sRawData'])
                    if payloadvalue is not None:AuthDetails[payload['Name']].append(payloadvalue)
            id+=1

        for val in AuthDetails:
            if len(AuthDetails[val])>0:res.append([f'Received {val} :{AuthDetails[val][0]} in the sequence','Pass' if AuthDetails[val][0]==Check[val] else 'Fail'])  
            else:res.append([f'TPR did not received {val} bit in the sequence','Fail' if Check['BitsCheck'] else 'Inconclusive'])
        
        return res



    def OVP_MaximumPower(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
        if PhaseLimit is not None:
            LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load 820",Type="TesterMsg" ,limit=[PhaseLimit[0],self.Flow_limit[1]])
            if len(LD)>2:
                res.append([f'Tester applied the Load: 820 Ohms at index@ {LD[2]}', 'Pass'])
                #Monitor  Voltage Before Load
                self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
                Voltages=self.MonitorVoltage(self.Flow_limit[0],LD[2])
                if Voltages[1] !=0:
                    res.append([f'Measured max voltage at index@ {round((self.AllChannelData['Interval']*Voltages[0])/1000,3)}sec  is {Voltages[1]} V before the load: 820 ohms., Limit : <{Check['Voltage1']}', 'Inconclusive' if  Voltages[1] >Check['Voltage1'] else 'Pass'] )
                # Check Positive CE pkts
                Assertion=self.PktMethod.GetexactPacketDetails(packet="TPR_Position_Adjust_to_Incr_V_rect",Type="TesterMsg",limit=[LD[2],self.Flow_limit[1]])
                if len(Assertion)>2:
                    count=0
                    id=Assertion[2]+1
                    while id < self.Flow_limit[1]:
                        if self.file_list[id]['pktType']=="Control Error" and int(self.file_list[id]['value'])>0:count+=1
                        id+=1
                    res.append([f'Tester sent {count} positive CE packets', 'Inconclusive' if count < Check['CEcount'] else 'Pass'] )
                    #Monitor Final Voltage
                    FinalVoltages=self.MonitorVoltage(Assertion[2],self.Flow_limit[1])
                    if FinalVoltages[1] !=0:
                        res.append([f'Measured max voltage at {round((self.AllChannelData['Interval']*FinalVoltages[0])/1000,3)}sec  is {FinalVoltages[1]}V at the final step, Limit : <{Check['Voltage2']}', 'Fail' if  FinalVoltages[1] >Check['Voltage2'] else 'Pass'] )
            else:res.append([f'PTx removed power signal before applying the Load 820 ohms','Inconclusive'])
        else:res.append([f'PRx did not entered PT phase','Inconclusive'])

        return res

    def Ping_Terminate(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Trestart=self.TrestartBool(Check['pkt'])
        Packet= f'{Check['pkt'][0] if Check['pkt'][1] is None else Check['pkt'][0]+" "+Check['pkt'][1]}'
        ST= self.PktMethod.GetPacketDetails(packet="Test_Status",value="Execution_Started" ,Type="TesterMsg" ,limit=[0,len(self.file_list)-1])
        SP=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[0,len(self.file_list)])
        if len(ST) > 2 and len(SP) > 2:
            res.append([f"Test executed {round((SP[0]-ST[0]),3)} seconds after placing the TPR on the PTx product",'Pass' if round((SP[0]-ST[0]),3) > 28 else 'Inconclusive' ])
            ILL = self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1], limit=[ST[2],SP[2]+1])
            if len(ILL)>2:
                # Print first Ping Measurement
                Coilpk=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[ILL[2]+1,SP[2]])
                if len(Coilpk)>2:
                    TterminateVal=round((Coilpk[1] - ILL[1]) * 1000, 3)
                    res.append([f'Measured t_terminate value for packet: {Packet} is {TterminateVal} mS at {{{ILL[2]}}} ,Limit [<=28 mS] ','Fail' if TterminateVal > 28 else 'Pass'])  

                    # Validate Remaining Ping Measurements
                    rem=self.ValidTterminate([ILL[2]+1,SP[2]],Check,Packet)
                    if len(rem)>0:res.extend(rem)
                else:
                    res.append([f'TPR sent {Packet} at {{{ILL[2]}}} , but did not recieved Coil_voltage pk-pk assertion before test_stop.','Pass'])
                    res.append([f'Measured t_terminate value is 0.0 mS','Pass'])

            else:
                res.append([f'voltage drops below 200mV[pk=pk] level before reaching the end of the {Packet} data packet.','Pass'])
                res.append([f'Measured t_terminate value is 0.0 mS','Pass'])
            # Check TrestartIllegal and VRECT
            if Trestart:
                rs=self.Trestart_Vrect(limit=[ST[2],SP[2]],DataPacketName=Packet,CTSCheck=CTSCheck)
                if len(rs)>0:res.extend(rs)
                

        else:res.append([f'Test did not found Test_start or Test_stop assertions','Inconclusive'])  
        return res
    
    def T_terminate(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Trestart= True if self.Header['TestcaseID'] in ['TEST_PTX_CPX_CFG_S02_ILL_003','TEST_PTX_CPX_CFG_S03_ILL_003','TEST_PTX_CPX_CFG_S04_ILL_003'] and self.Certification not in ["2.2.1","2.1.0","1.3.3","2.0.0"] else self.TrestartBool(Check['pkt'])
        Packet= f'{Check['pkt'][0] if Check['pkt'][1] is None else Check['pkt'][0]+" "+Check['pkt'][1]}'
        OP= f'{Check['sp'][0] if Check['sp'][1] is None else Check['sp'][0]+" "+Check['sp'][1]}'
        ST= self.PktMethod.GetPacketDetails(packet="Test_Status",value="Execution_Started" ,Type="TesterMsg" ,limit=[0,len(self.file_list)-1])
        SP=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Test_Stop",Type="TesterMsg",limit=[0,len(self.file_list)])
        if len(ST) > 2 and len(SP) > 2:
            # find the start packet and c heck the replaced pkt
            Start=self.PktMethod.GetPacketDetails(packet=Check['sp'][0], value=Check['sp'][1], limit=self.Flow_limit) # why self.Flow_limit instead of [ST[2],SP[2]]  ?
            if len(Start)>2:
                if Check['sp'][2] : res.extend(self.Payload_Details(PacketName=OP,Index=Start[2],PayLoads= Check['sp'][3])) 
                id=Start[2]+1
                count=0
                if Check['Phase'] not in ['PT']:
                    # find the Replaced Pkt
                    while id < self.Flow_limit[1]:
                        if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                            if Check['pkt'][0] in self.file_list[id]['pktType'] if Check['pkt'][1] is None else Check['pkt'][0] in self.file_list[id]['pktType'] and Check['pkt'][1] in self.file_list[id]['value']:
                                res.append([f'TPR sent {Packet} packet after the {OP} packet at index@ {{{Start[2]}}}','Pass'])
                                count+=1
                                break
                            else:
                                if Check['Phase'] in ['Nego']:
                                    if Check['sp'][0] in self.file_list[id]['pktType'] and True if Check['sp'][1] is None else Check['sp'][1] in self.file_list[id]['value']:
                                        Start[2]=id
                                    else: res.append([f'TPR did not sent {Packet} packet after {OP} packet','Inconclusive'])
                                else:
                                    res.append([f'TPR did not sent {Packet} packet after {OP} packet','Inconclusive'])
                        id+=1
                if Check['Phase'] in ['PT']:
                    previousStartTime=Start[1]
                    while id < self.Flow_limit[1]:
                        ILL = self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1], limit=[id,self.Flow_limit[1]])
                        if len(ILL)>2:
                            if Check.get('Timing',False):
                                Timing=round((ILL[0]-previousStartTime)*1000,3)
                                res.append([f"Measured timing between {Packet if count>0 else "Control Error"} packet at index@ {{{id-1}}} and {Packet} packet at index@ {{{ILL[2]}}} is {Timing}mS Limit: {Check['Timing'][0]}±{Check['Timing'][1]}Sec",'Pass' if Timing/1000 >=Check['Timing'][0]-Check['Timing'][1] and Timing/1000 <= Check['Timing'][0]+Check['Timing'][1] else 'Fail'])
                                previousStartTime=ILL[0]
                            id=ILL[2]+1
                            count+=1
                        else:break

                # find sequence of pkts
                if count >0:
                    previousStartTime=self.file_list[id]['startTime']
                    y=id+1
                    if Check['Phase'] in ['Nego']:
                        while y < self.Flow_limit[1]:
                            ILL = self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1], limit=[y,self.Flow_limit[1]])
                            if len(ILL)>2:
                                if Check.get('Timing',False):
                                    Timing=round((ILL[0]-previousStartTime)*1000,3)
                                    res.append([f"Measured timing between {Packet} packet at index@ {{{y-1}}} and {Packet} packet at index@ {{{ILL[2]}}} is {Timing}mS Limit: {Check['Timing'][0]}±{Check['Timing'][1]}mS",'Pass' if Timing >=Check['Timing'][0]-Check['Timing'][1] and Timing <= Check['Timing'][0]+Check['Timing'][1] else 'Fail'])
                                    previousStartTime=ILL[0]
                                y=ILL[2]+1
                                count+=1
                            else:break
                    if Check['Phase'] not in ['Config']: res.append([f'TPR sent {count} {Packet} packets in the sequence','Pass'])
                    y=y-2 if Check['Phase'] in ['PT'] else y-1
                    # Find Tterminate
                    if Check['pkt'][2] : res.extend(self.Payload_Details(PacketName=Packet,Index=y,PayLoads= Check['pkt'][3])) 
                    Coilpk=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[y,self.Flow_limit[1]])
                    if len(Coilpk)>2:
                        TterminateVal=round((Coilpk[1] - self.file_list[y]['stopTime']) * 1000, 3)
                        res.append([f'Measured t_terminate value for {Packet} packet at index@ {y} is {TterminateVal}mS, Limit [≤ 28mS]','Fail' if TterminateVal > 28 else 'Pass']) 
                          # Check TrestartIllegal and VRECT
                        if Trestart:
                            rs=self.Trestart_Vrect(limit=[self.Flow_limit[0],SP[2]],DataPacketName=Packet,CTSCheck=CTSCheck)
                            if len(rs)>0:res.extend(rs)

                    else:res.append([f'PTx did not detached after the {Packet} packet at index@ {{{y}}}','Inconclusive'])
                else:
                    res.append([f'voltage drops below 200mV [pk-pk] level before reaching the end of the {Packet} packet.','Pass'])
                    res.append([f'Measured t_terminate value is 0.0 mS','Pass'])
              
            else:res.append([f'Test did not found {OP} packet','Inconclusive'])
        else:res.append([f'Test did not found test_start or test_stop assertions','Inconclusive'])
        return res

    def CheckTerminate(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Packet= f'{Check['pkt'][0] if Check['pkt'][1] is None else Check['pkt'][0]+" "+Check['pkt'][1]}'
        # OP= f'{Check['sp'][0] if Check['sp'][1] is None else Check['sp'][0]+" "+Check['sp'][1]}'
        ILL = self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1], limit=self.Flow_limit)
        if len(ILL)>2:
            res.append([f'TPR sent {Packet} at index@ {{{ILL[2]}}}','Pass'])
            # Print first Ping Measurement
            if Check['pkt'][2] : res.extend(self.Payload_Details(PacketName=Packet,Index=ILL[2],PayLoads= Check['pkt'][3])) 
            # check Ptx detached or not
            Detach=True
            id=ILL[2]+1
            while id < self.Flow_limit[1]:
                if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    res.append([f'PTx did not detached after sending {Packet} at index@ {{{ILL[2]}}}','Inconclusive'])
                    Detach=False
                    break
                id+=1
            if Detach:
                Coilpk=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[ILL[2]+1,self.Flow_limit[1]])
                TterminateVal=round((Coilpk[1] - ILL[1]) * 1000, 3)
                res.append([f'Measured t_terminate value for packet: {Packet} is {TterminateVal}mS at {{{ILL[2]}}}, Limit[ <= {Check['Tterminate'][1]}] mS ','Fail' if TterminateVal > Check['Tterminate'][1] else 'Pass'])  

        else:
            res.append([f'voltage drops below 200mV [pk-pk] level before reaching the end of the {Packet} data packet.','Pass'])
            res.append([f'Measured t_terminate value is 0.0 mS','Pass'])

        return res


    def VMC(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        ID=self.PktMethod.GetPacketDetails(packet="Identification",limit=self.Flow_limit)
        if len(ID)>2:
            res.append([f'TPR sent configuration packet at index@ {{{ID[2]}}}','Pass'])
            for Payload in Check['PayLoads']:
                HexVal=self.PktMethod.GetPayloadDetails(ID[2],Payload['Name'])[0]['sRawData']
                Val=self.PktMethod.hex_to_decimal(HexVal)
                result='Inconclusive'
                values=[int(x,16) for x in Payload['Exp'] ]if type(Payload['Exp'][0]) is not int else Payload['Exp']
                match Payload['comp']:
                    case 'EQL':
                        result='Pass' if Val in values else 'Inconclusive'
                    case 'NEQ':
                        result='Pass' if Val not in values else 'Inconclusive'
                    case 'ANY':
                        result='Pass'
                desp=CommonMethods.GetCompDes(Payload['Exp'],Payload['comp'])
                res.append([f'Obtained {Payload['Name']} is {HexVal if Payload['Name']=='Manufacturer_Code' else int(Val) }, Exp : {desp}',result])
            # Check for Power Transfer Timing
            PhaseLimit=self.FindPhase(ID[2]+1,"Calib" if 'EPP' in self.Header['TestcaseID']  else 'PT')
            if PhaseLimit is not None:
                Duration= round((self.file_list[self.Flow_limit[1]]['stopTime']-self.file_list[PhaseLimit[0]]['startTime']),3)
                res.append([f'TPR stayed in Power Transfer phase for {Duration} Secs , Exp :>= 5 secs','Inconclusive' if Duration <5 else 'Pass' if 'EPP' in self.Header['TestcaseID'] else 'Fail' if Duration  <5 else 'Pass'])
                # Rp check
                if 'EPP' in self.Header['TestcaseID'] :
                    RP=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",limit=PhaseLimit)
                    if len(RP)>2:
                        Duration= round((RP[0]-self.file_list[self.Flow_limit[0]]['startTime']),3)
                        res.append([f'TPR sent 16-Bit RP packet at index@ {{{RP[2]}}} within {Duration} Secs from digital ping','Fail' if Duration > 3 else 'Pass'])                      
                    else:res.append([f'TPR did not sent 16-Bit RP packet in PT phase','Fail'])
            else:res.append(['TPR did not entered Power Transfer phase','Inconclusive' if 'EPP' in self.Header['TestcaseID'] else 'Fail'])
        else:res.append(['Test did not found ID Packet','Inconclusive'])
        return res


###------------------------------------------------------------------------- Authentication Tests -------------------------------------------------------------------------###

    def Check_Digests(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            # Check Flow with Caching
            Get_Digests=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Digests",limit=[RP0[2]+1,self.Flow_limit[1]])
            if len(Get_Digests)>2:
                if Check.get('Compliment',False):
                    slotMask=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Get_Digests[2],'Slot_Mask')[0]['sRawData'])
                    if "TEST_PTX_APX_DIG_SRM_002" in  self.TestData['TestResults']:
                        res.append([f'Earlier slots populated mask was set to  {self.TestData['TestResults']["TEST_PTX_APX_DIG_SRM_002"]}, current slot mask was set to  {int(slotMask)} in Get_Digests packet at {{{Get_Digests[2]}}}','Pass' if int((~ self.TestData['TestResults']["TEST_PTX_APX_DIG_SRM_002"]) & 0b1111 )== int (slotMask) else 'Inconclusive'])
                    else:
                        res.append([f'Test result of TEST_PTX_APX_DIG_SRM_002 is not Available.','Inconclusive'])
                else:
                    results=self.Payload_Details(PacketName='Get_Digests',Index=Get_Digests[2],PayLoads=Check['Get_Digests'])
                    if len(results)>0:res.extend(results)

                # check Digets Response
                Digests=self.PktMethod.GetPacketDetails(packet="ADT",value='Digests', Type="Response",limit=[Get_Digests[2]+1,self.Flow_limit[1]])
                if len(Digests)>2:
                    # CTS Pass/ Fail Criteria
                    if Check.get("Authentication_Protocol_Version",False):
                        ProtocolVersion=self.PktMethod.GetPayloadDetails(Digests[2],'Authentication_Protocol_Version')[0]['sRawData']
                        res.append([f'PTx sent Authentication Protocol version in the DIGESTS authentication response at {{{Digests[2]}}} is {ProtocolVersion}, Exp :0x01','Pass' if ProtocolVersion =='0x01' else 'Fail'])
                    if Check.get('Slots_Mask',False):
                        slot_populated=self.PktMethod.GetPayloadDetails(Digests[2],'Slots_Populated_Mask')[0]['sRawData']
                        slot_returned=self.PktMethod.GetPayloadDetails(Digests[2],'Slots_Returned_Mask')[0]['sRawData']
                        if Check.get('Compare_slots',False):
                            self.TestData['TestResults'][self.Header['TestcaseID']]=int(slot_populated,16) 
                            self.TestResultsjson.update_file(self.TestData)
                            if slot_populated == slot_returned:res.append([f'PTx sent populated mask {slot_populated} matches the returned mask {slot_returned} in the DIGESTS authentication response at {{{Digests[2]}}}', 'Pass'])
                            else:res.append([f' PTx sent both populated mask: {slot_populated} & returned mask: {slot_returned} are not equal in the DIGESTS authentication response at {{{Digests[2]}}}','Fail'])
                        else:
                            res.append([f'PTx sent slots populated mask in the DIGESTS authentication response at {{{Digests[2]}}} is {slot_populated}, Exp: 0x01','Pass' if slot_populated =='0x01' else 'Fail'])
                            res.append([f'PTx sent slots returned mask in the DIGESTS authentication response at {{{Digests[2]}}} is {slot_returned}, Exp: 0x01','Pass' if slot_returned =='0x01' else 'Fail'])

                    # Check Digest in Cache
                    Cache_Msg=self.PktMethod.GetPacketDetails(packet="Digest",value="not in cache",Type='TesterMsg',limit=[Digests[2]+1,self.Flow_limit[1]])
                    if len(Cache_Msg)>2:
                        res.append([f'Digests not in cache found at {{{Cache_Msg[2]}}}','Pass'])
                        # CTS Pass/ Fail Criteria
                        if Check.get('BytesCheck',False):
                            Bytes=self.BytesCount([Digests[2],Cache_Msg[2]])
                            if self.Header['TestcaseID'] in ['TEST_PTX_APX_DIG_DRX_001']:
                                slot_returned=self.PktMethod.GetPayloadDetails(Digests[2],'Slots_Returned_Mask')[0]['sRawData']
                                res.append([f'Slot returned mask was set to {int(slot_returned,16)}, Exp N=1', 'Pass' if int(slot_returned,16)==1 else 'Fail'])
                                res.append([f'Digest Authentication response consists of {Bytes} bytes, Exp: N x 32 +2 Where N={int(slot_returned,16)} ','Pass' if Bytes == (int(slot_returned,16)*32 +2) else 'Fail'])
                            else:res.append([f'Digest Authentication response consists of {Bytes} bytes','Pass' if Bytes ==2 else 'Fail'])

                        # Check Simple Flow
                        Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[Cache_Msg[2]+1,self.Flow_limit[1]])
                        if len(Get_Certificate)>2:
                            results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                            if len(results)>0:res.extend(results)
                            # Check Certificate Response
                            Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                            if len(Certificate)>2:
                                Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,self.Flow_limit[1]])
                                if len(Chain_Msg)>2:
                                    res.append([f'Certificate chain valid found at {{{Chain_Msg[2]}}}','Pass'])
                                    # Check Challenge Sequence
                                    Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[Chain_Msg[2]+1,self.Flow_limit[1]])
                                    if len(Challenge)>2:
                                        Slot_Number=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Challenge[2],'Slot_Number')[0]['sRawData'])
                                        res.append([f'TPR sent slot number: {int(Slot_Number)} in the Challenge packet at {{{Challenge[2]}}}, Exp: 0','Pass' if Slot_Number ==0 else 'Inconclusive'])
                                        # check Digets Response
                                        Challenge_Auth=self.PktMethod.GetPacketDetails(packet="ADT",value='Challenge_Auth', Type="Response",limit=[Challenge[2]+1,self.Flow_limit[1]])
                                        if len(Challenge_Auth)>2:
                                            Challenge_Msg=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="-Valid",Type='TesterMsg',limit=[Challenge_Auth[2]+1,self.Flow_limit[1]])
                                            if len(Challenge_Msg)>2:
                                                res.append([f'Challenge Auth found at {{{Challenge_Msg[2]}}}','Pass'])
                                            else:res.append([f'Test did not found Challenge valid message', 'Inconclusive'])
                                        else:res.append([f'PTx did not sent Challenge_Auth response', 'Inconclusive'])
                                    else:res.append([f'TPR did not sent Challenge Request','Inconclusive'])
                                else:res.append([f'Test did not found Certificate chain valid message', 'Inconclusive'])
                            else:res.append([f'PTx did not sent Certificate Response', 'Inconclusive'])
                        else:res.append([f'TPR did not sent Get_Certificate Request','Inconclusive'])
                    else:res.append([f'Test did not found Digest not in Cache message', 'Inconclusive'])
                else:res.append([f'PTx did not sent Digests Response', 'Inconclusive'])
            else:res.append([f'TPR did not sent Get_Digests Request','Inconclusive'])
        else:res.append([f'Prx did not Entered PT Phase', 'Inconclusive'])

        return res

    def Digests(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Digests_Returned=[]
        id=0
        while id < len(self.Auth_file_list):
            if self.Auth_file_list[id]['pktType']=="DIGESTS":
                payloadvalue=self.PayloadDetails_Auth(id,"Digests_Returned")
                if payloadvalue is not None: Digests_Returned.append(payloadvalue[0]['sRawData'])
            id+=1
        if len(Digests_Returned)==5:
            count=1
            for Digest in Digests_Returned[1:]:
                count+=1
                if Digests_Returned[0]== Digest:
                    res.append([f'Digests 1 == Digests {count}','Pass'])
                else: res.append([f'Digests 1 != Digests {count}','Fail'])
        else: res.append([f'Test did not found 5 Digests Responses to validate','Inconclusive'])    

        return res
    
    def Content_Check(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Limits=[self.FirstPing(flows[flwID]['Limit']),flows[flwID]['Limit']]
        print(f'First Ping Limit : {Limits[0]} , Second PingLimit : {Limits[1]}')
      
       
        #Get PTMC value from PT-ID
        AuthDetails={  "subject_attribute1":[], "issuer":[] }
        serialnum=[]
                        
        PT_ID=self.PktMethod.GetPacketDetails(packet="Power Transmitter Identification",Type='Response', limit=self.Flow_limit)
        if len(PT_ID)>2:
            PTX_PRMC=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PT_ID[2],"Manufacturer_Code")[0]['sRawData'])
            SDF_QIID=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['QIID']
            
             #  Validate First ping
            if Limits[0] is not None:
                res.append([f'Sequence :1','Pass'])
                res.extend(self.SimpleFlow_Check(Check,Limits[0]))
            else:res.append(['Limit was not avaialble for the  first Ping','Inconclusive'])  
            #  Validate Second ping
            if Limits[1] is not None:
                Limit=Limits[1]
                res.append([f'Sequence :2','Pass'])
                res.extend(self.SimpleFlow_Check(Check,Limits[1]))
            else:res.append(['Limit was not avaialble for the  second Ping','Inconclusive'])  

            if  Limits[0] is not None and  Limits[1] is not None:
                id=0
                while id < len(self.Auth_file_list):
                    if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                        if  self.Header['TestcaseID'] in ['PTX_APX_CONTENT_SUB_REG']:

                            Subject_attribute=self.PayloadDetails_Auth(id,'subject_attribute1')
                            if Subject_attribute is not None:
                                Subject_attribute=Subject_attribute[0]['sDescription'].split('-')[0]
                                val=self.PktMethod.hex_to_decimal(Subject_attribute)
                                if val is not None:AuthDetails['subject_attribute1'].append(val)

                            issuer=self.PayloadDetails_Auth(id,'issuer')
                            if issuer is not None:
                                issuer=f'0x{issuer[1]['sDescription'].split('-')[0]}'
                                val=self.PktMethod.hex_to_decimal(issuer)
                                if val is not None:AuthDetails['issuer'].append(val)
                        else:
                            for payload in Check['Auth']:
                                payloadvalue=self.PayloadDetails_Auth(id,payload['Name'])
                                if payloadvalue is not None:
                                    serialnum.append(payloadvalue[0]['sRawData'] if payload['Name'] == 'Extensions_1_extnValue' else payloadvalue[1]['sRawData'])

                    id+=1
                if  self.Header['TestcaseID'] in ['PTX_APX_CONTENT_SUB_REG']:
                    for val in AuthDetails:
                        if len(AuthDetails[val])>1:
                            if AuthDetails[val][0]==AuthDetails[val][1]:
                                if val=="subject_attribute1":
                                    if AuthDetails['subject_attribute1'][0]==float(SDF_QIID):
                                        res.append([f'Received {Check[val]} in the flow is {AuthDetails[val]} equal to SDF QI-ID: {SDF_QIID}', 'Pass']) 
                                    else:res.append([f'Received {Check[val]} in the flow is {AuthDetails[val]}  not equal to SDF QI-ID: {SDF_QIID}', 'Fail']) 
                                else:
                                    if AuthDetails['issuer'][0]==PTX_PRMC:
                                        res.append([f'Received  {Check[val]} in the flow is {AuthDetails[val]} equal to PTx-PTMC: {PTX_PRMC}', 'Pass']) 
                                    else:res.append([f'Received  {Check[val]}  in the flow is {AuthDetails[val]}  not equal to PTx-PTMC: {PTX_PRMC}', 'Fail']) 
                                
                            else:res.append([f'Received {Check[val]} in the flow is {AuthDetails[val]} are not equal', 'Fail']) 
                        else:res.append([f'Received {Check[val]} are less than expected','Inconclusive'])
                else:
                    if len(serialnum)>1:
                        res.append([f'Received {Check['CheckName']} in the flow is {serialnum}','Pass'   if serialnum[0]!=serialnum[1] else 'Fail']) 
                    else:res.append([f'Received {Check['CheckName']}  are less than expected','Inconclusive'])

        else: res.append([f'PTx did not sent PT-ID in the sequence','Inconclusive'])
        return res
    
    def ContentChain(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Limits=[self.FirstPing(flows[flwID]['Limit']),flows[flwID]['Limit']]
        print(f'First ping limit : {Limits[0]} , Second ping limit : {Limits[1]}')
        

        AuthDetails={
                "Root_Certificate_Hash":[],
                "Product_Unit_CA_Certificate":[],
                "Manufacturer_CA_Certificate":[]
        }

        #  Validate First ping
        if Limits[0] is not None:
            res.append([f'Sequence :1','Pass'])
            res.extend(self.SimpleFlow_Check(Check,Limits[0]))
        else:res.append(['Limit was not avaialble for the  first ping','Inconclusive'])  
        #  Validate Second ping
        if Limits[1] is not None:
            Limit=Limits[1]
            res.append([f'Sequence :2','Pass'])
            res.extend(self.SimpleFlow_Check(Check,Limits[1]))
        else:res.append(['Limit was not avaialble for the second ping','Inconclusive'])  

        if  Limits[0] is not None and  Limits[1] is not None:
            id=0
       
            while id < len(self.Auth_file_list):
                if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                    # if self.Auth_file_list[id]['subpackets'][len( self.Auth_file_list[id]['subpackets'])-5]['index'] < flow[1] and self.Auth_file_list[id]['subpackets'][len( self.Auth_file_list[id]['subpackets'])-5]['index'] > flow[0]:
                    for payload in Check['Auth']:
                        payloadvalue=self.PayloadDetails_Auth(id,payload)
                        if payloadvalue is not None:AuthDetails[payload].append(payloadvalue[0]['sRawData'])
                
                id+=1
            
            for val in AuthDetails:
                if val=="Root_Certificate_Hash":
                    if len(AuthDetails[val])==2 and AuthDetails[val][0]==AuthDetails[val][1] and AuthDetails[val][0]==Check['CAHash']:
                        res.append([f'Received {val} are proper in the flow: {AuthDetails[val]}','Pass'])   
                    else:res.append([f'Received {val} are not proper in the flow: {AuthDetails[val]}','Fail'])
                if val =="Manufacturer_CA_Certificate":
                    if len(AuthDetails[val])==2 and AuthDetails[val][0]==AuthDetails[val][1] :
                        res.append([f'Received {val} are proper in the flow: {AuthDetails[val]}','Pass'])
                            
                    else:res.append([f'Received {val} are not proper in the flow: {AuthDetails[val]}','Fail'])

                if val in ['Product_Unit_CA_Certificate','Manufacturer_CA_Certificate']:
                    if len(AuthDetails[val])==2 :
                        first_two = AuthDetails[val][0].split("-")[:2]
                        if first_two[0]=="30" and first_two[1]=="82":
                            res.append([f'The first two bytes of {val} are proper {first_two}','Pass'])
                        else: res.append([f'The first two bytes of {val} are not proper {first_two}','Fail'])
                            
                    else:res.append([f'Received only one {val} flow','Inconcluisive'])

        return res
    
    def ContentSubject(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Limits=[self.FirstPing(flows[flwID]['Limit']),flows[flwID]['Limit']]
        print(f'First ping limit: {Limits[0]} , Second ping limit : {Limits[1]}')
        #  Validate First ping
        if Limits[0] is not None:
            res.append([f'Sequence :1','Pass'])
            res.extend(self.SimpleFlow_Check(Check,Limits[0]))
        else:res.append(['Limit was not avaialble for the first ping','Inconclusive'])  
        #  Validate Second ping
        if Limits[1] is not None:
            Limit=Limits[1]
            res.append([f'Sequence :2','Pass'])
            res.extend(self.SimpleFlow_Check(Check,Limits[1]))
        else:res.append(['Limit was not avaialble for the second ping','Inconclusive'])  

        if  Limits[0] is not None and  Limits[1] is not None:
            Certificates=[]
            id=0
            while id < len(self.Auth_file_list):
                if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                    Manufacturee_certificate = self.PayloadDetails_Auth(id, "Product_Unit_CA_Certificate")
                    if Manufacturee_certificate is not None:
                        Certificates.append(Manufacturee_certificate[0]['sRawData'].strip().replace("-"," "))
                id+=1
            
            if len(Certificates) > 1:
                try:
                    res.extend(self.ValidateChainNames(Certificates[0],1)) # Leaf 1
                    res.extend(self.ValidateChainNames(Certificates[1],2)) # Leaf 2

                except Exception as e:
                    print(e)
                    # Catch any parsing errors and append to res
                    res.append([f"Leaf certificate parsing failed: {e}", "Fail"])
            else:
                res.append([f'Did not found more than one Certificate in the flow', 'Inconclusive'])           
        return res
    

    def ContentAttr(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        AuthDetails={ 
            "signature_algorithm":[],
            "subjectPublic_KeyInfo_algorithm":[],
            "subjectPublic_KeyInfo_algorithm1":[]
            }
        
        id=0
        while id < len(self.Auth_file_list):
            if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                version=self.PayloadDetails_Auth(id,'Version')[0]['sDescription']
                if version is not None :res.append([f'Received version: {version} in the Product_CA_Certificate at index@ {{{id}}}','Pass' if int(version)==2 else 'Fail'])
                for payload in Check['Auth']:
                    payloadvalue=self.PayloadDetails_Auth(id,payload['Name'])[0]['sDescription']
                    if payloadvalue is not None:AuthDetails[payload['Name']].append(payloadvalue)
            id+=1

        for val in AuthDetails:
            if len(AuthDetails[val])>1 and AuthDetails[val][0]==AuthDetails[val][1] and AuthDetails[val][0]==Check[val]:
                res.append([f'Received {val} are proper in the flows: {AuthDetails[val]}','Pass'])   
            else:res.append([f'Received {val} are not proper in the flows: {AuthDetails[val]}','Fail'])
                        
        return res

    def SerialNumber(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        serialnum=[]
        id=0
        try:
            while id < len(self.Auth_file_list):
                if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                    for payload in Check['Auth']:
                        payloadvalue=self.GetAuthPayloadDetails(id,payload['Name'],payload['Byte'],payload['Bit'])[0]['sRawData']
                        if payloadvalue is not None:serialnum.append(payloadvalue)
                id+=1
        except Exception as e:print(e)
        if len(serialnum)>1:
            res.append([f'Received {Check['CheckName']} in the flows are: {serialnum}','Pass'   if serialnum[0]!=serialnum[1] else 'Fail']) 
        else:res.append([f'Received {Check['CheckName']} are less than Expected','Inconclusive']) 

        return res
    
    def Check_Certificate(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
           
            # Check Simple Flow
            Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[RP0[2]+1,self.Flow_limit[1]])
            if len(Get_Certificate)>2:
                results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                if len(results)>0:res.extend(results)
                # Check Certificate Response
                Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                if len(Certificate)>2:
                    # CTS Pass/ Fail Criteria
                    if Check.get("Authentication_Protocol_Version",False):
                        ProtocolVersion=self.PktMethod.GetPayloadDetails(Certificate[2],'Authentication_Protocol_Version')[0]['sRawData']
                        res.append([f'PTx sent Authentication protocol version in the Certificate authentication response at index@ {{{Certificate[2]}}} is {ProtocolVersion}, Exp :0x01','Pass' if ProtocolVersion =='0x01' else 'Fail'])
                    Challenge_Seq=True
                    
                    if self.Header['TestcaseID']  in ['PTX_APX_CRT_LEN_001','PTX_APX_CRT_LEN_002','PTX_APX_CRT_LEN_003','PTX_APX_CRT_OFS_001']:
                        Challenge_Seq=False
                        # Validate Certificate Chain Segment Length in certificate response
                        id=0
                        while id < len(self.Auth_file_list):
                            if self.Auth_file_list[id]['pktType']=="CERTIFICATE":break
                            id+=1
                        if self.Header['TestcaseID']  in ['PTX_APX_CRT_OFS_001']:
                            productCertificate=self.PayloadDetails_Auth(id,"Product_Unit_CA_Certificate")
                            if productCertificate is not None:
                                res.append([f'Product_Unit_Certificate found in CERTIFICATE response','Pass'])
                            else:res.append([f'Product_Unit_Certificate did not found in CERTIFICATE response','Fail'])
                            
                        else:
                            payloadvalue=self.PayloadDetails_Auth(id,"Certificate_Chain_Segment")
                            if payloadvalue is not None:  
                                ChainLength=payloadvalue[0]['sRawData'].split("-")
                                res.append([f'Certificate Chain Segment in the CERTIFICATE authentication response has a length of: {len(ChainLength)}, Exp: 1- {Check['Length'][1]} Bytes','Pass' if len(ChainLength) <=Check['Length'][1] and len(ChainLength)>=1 else 'Fail'])
                            else:res.append([f'Did not found Certificate_Chain_Segment in Certificate response','Inconclusive'])
                        
                    if Challenge_Seq:
                        Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,self.Flow_limit[1]])
                        if len(Chain_Msg)>2:
                            res.append([f'Certificate chain valid found at {{{Chain_Msg[2]}}}','Pass'])
                            # Check Challenge Sequence
                            Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[Chain_Msg[2]+1,self.Flow_limit[1]])
                            if len(Challenge)>2:
                                Slot_Number=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Challenge[2],'Slot_Number')[0]['sRawData'])
                                res.append([f'TPR sent slot number: {int(Slot_Number)} in the Challenge packet at index@ {{{Challenge[2]}}}, Exp: 0','Pass' if Slot_Number ==0 else 'Inconclusive'])
                                # check Digets Response
                                Challenge_Auth=self.PktMethod.GetPacketDetails(packet="ADT",value='Challenge_Auth', Type="Response",limit=[Challenge[2]+1,self.Flow_limit[1]])
                                if len(Challenge_Auth)>2:
                                    Challenge_Msg=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="-Valid",Type='TesterMsg',limit=[Challenge_Auth[2]+1,self.Flow_limit[1]])
                                    if len(Challenge_Msg)>2:
                                        res.append([f'Challenge_Auth found at {{{Challenge_Msg[2]}}}','Pass'])
                                    else:res.append([f'Test did not found Challenge valid message', 'Inconclusive'])
                                else:res.append([f'PTx did not sent Challenge_Auth response', 'Inconclusive'])
                            else:res.append([f'TPR did not sent Challenge Request','Inconclusive'])
                        else:res.append([f'Test did not found Certificate chain valid message', 'Inconclusive'])
                else:res.append([f'PTx did not sent Certificate Response', 'Inconclusive'])
            else:res.append([f'TPR did not sent Get_Certificate Request','Inconclusive'])
                   
        else:res.append([f'Prx did not entered PT Phase', 'Inconclusive'])

        return res

    def ErrorCode(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[RP0[2]+1,self.Flow_limit[1]])
            if len(Get_Certificate)>2:
                results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                if len(results)>0:res.extend(results)

                # Check Certificate Response
                Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                if len(Certificate)>2:
                   
                    # Now check the second sequence of Get Certificate
                    Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[Certificate[2]+1,self.Flow_limit[1]])
                    if len(Get_Certificate)>2:
                        ChainLength=[]
                        id=0
                        while id < len(self.Auth_file_list):
                            if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                                payloadvalue=self.PayloadDetails_Auth(id,"Certificate_Chain_Segment")
                                if payloadvalue is not None:  
                                    ChainLength=payloadvalue[0]['sRawData'].split("-")
                                break
                            id+=1
                        if len(ChainLength)==2:
                            Offset_70=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Get_Certificate[2],'Offset70')[0]['sRawData'])
                            Offset_A8=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Get_Certificate[2],'OffsetA8')[0]['sRawData'])
                            res.append([f'TPR sent Offset_A8 field as {int(Offset_A8)} in the second Get_Certificate packet at index@ {{{Get_Certificate[2]}}}, Exp: {ChainLength[0]}', 'Pass' if int(Offset_A8)== int(ChainLength[0]) else 'Inconclusive' ])
                            res.append([f'TPR sent Offset_70 field as {int(Offset_70)} in the second Get_Certificate packet at index@ {{{Get_Certificate[2]}}}, Exp: {int(ChainLength[1],16)}', 'Pass' if int(Offset_70)== int(ChainLength[1],16) else 'Inconclusive' ])
                        else:res.append(['Test did not found Chain length','Inconclusive'])

                        Length_70=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Get_Certificate[2],'Length70')[0]['sRawData'])
                        Length_A8=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Get_Certificate[2],'LengthA8')[0]['sRawData'])
                        res.append([f'TPR sent Length_A8 field as {int(Length_A8)} in the second Get_Certificate packet at index@ {{{Get_Certificate[2]}}}, Exp: 1', 'Pass' if int(Length_A8)==1 else 'Inconclusive' ])
                        res.append([f'TPR sent Length_70 field as {int(Length_70)} in the second Get_Certificate packet at index@ {{{Get_Certificate[2]}}}, Exp: 1', 'Pass' if int(Length_70)==1 else 'Inconclusive' ])

                        # Check Error code
                        res.extend(self.ErrorResponseCheck(Check))
                    else:res.append([f'TPR did not sent second Get_Certificate Request','Inconclusive'])

                else:res.append([f'PTx did not sent Certificate Response', 'Inconclusive'])
            else:res.append([f'TPR did not sent Get_Certificate Request','Inconclusive'])

        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res
    
    def Error_Response(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            value="Get_Digests" if Check.get("Get_Digests_Check",False) else "Get_Certificate"
            Get_Packet=self.PktMethod.GetPacketDetails(packet="ADT",value=value,limit=[RP0[2]+1,self.Flow_limit[1]])
            if len(Get_Packet)>2:
                results=self.Payload_Details(PacketName=value,Index=Get_Packet[2],PayLoads=Check[value])
                if len(results)>0:res.extend(results)

                if Check.get('Simple_Flow',False):
                    Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Packet[2]+1,self.Flow_limit[1]])
                    if len(Certificate)>2:
                        Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,self.Flow_limit[1]])
                        if len(Chain_Msg)>2:
                            res.append([f'Certificate chain valid found at index@ {{{Chain_Msg[2]}}}','Pass'])
                        # Check Challenge Sequence
                            Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[Chain_Msg[2]+1,self.Flow_limit[1]])
                            if len(Challenge)>2:
                                results=self.Payload_Details(PacketName='Challenge',Index=Challenge[2],PayLoads=Check['Challenge'])
                                if len(results)>0:res.extend(results)
                                # Check Error code
                                res.extend(self.ErrorResponseCheck(Check))
                            else:res.append([f'TPR did not sent Challenge_Request','Inconclusive'])
                        else:res.append([f'Test did not found Certificate chain valid message', 'Inconclusive'])
                    else:res.append([f'PTx did not sent Certificate_Response', 'Inconclusive'])
                else:
                    # Check Error code
                    res.extend(self.ErrorResponseCheck(Check))
            else:res.append([f'TPR did not sent {value} Request','Inconclusive'])
        else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        return res

    def TcertReady_Digests(self,CTSCheck,Check,flows,flwID):
        res=[]

        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            # Check Flow with Caching
            Get_Digests=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Digests",limit=[RP0[2]+1,self.Flow_limit[1]])
            res.append([f'TPR sent Get_Digests at {{{Get_Digests[2]}}}','Pass'])
            if len(Get_Digests)>2:
                ADC_End=self.PktMethod.GetPacketDetails(packet="ADC",value="End" ,limit=[Get_Digests[2]+1,self.Flow_limit[1]])
                if len(ADC_End)>2:
                     # check Digets Response
                    Digests=self.PktMethod.GetPacketDetails(packet="ADT",value='Digests', Type="Response",limit=[Get_Digests[2]+1,self.Flow_limit[1]])
                    if len(Digests)>2:
                        # CTS Pass/ Fail Criteria
                        res.append([f'PTx sent DIGEST_Response at {{{Digests[2]}}}','Pass'])
                        ATN=self.PktMethod.GetPacketDetails(packet="ATN",Type="Response",limit=[Digests[2],ADC_End[2]])
                        Timing=round((ATN[0]-ADC_End[1])*1000,2)
                        res.append([f'Measured timing t_Cert_Ready between ADC_End at {{{ADC_End[2]}}} to ATN response at {{{ATN[2]}}} is {Timing}mS, Limit[<= {Check['limit']} mS]','Fail' if Timing > Check['limit'] else 'Pass'])
                        # Check Digest in Cache
                        Cache_Msg=self.PktMethod.GetPacketDetails(packet="Digest",value="not in cache",Type='TesterMsg',limit=[Digests[2]+1,self.Flow_limit[1]])
                        if len(Cache_Msg)>2:
                            res.append([f'Digests not in cache found at {{{Cache_Msg[2]}}}','Pass'])
                            # Check Simple Flow
                            Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[Cache_Msg[2]+1,self.Flow_limit[1]])
                            if len(Get_Certificate)>2:
                                results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                                if len(results)>0:res.extend(results)
                                # Check Certificate Response
                                Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                                if len(Certificate)>2:
                                    Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,self.Flow_limit[1]])
                                    if len(Chain_Msg)>2:
                                        res.append([f'Certificate chain valid found at {{{Chain_Msg[2]}}}','Pass'])
                                        # Check Challenge Sequence
                                        Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[Chain_Msg[2]+1,self.Flow_limit[1]])
                                        if len(Challenge)>2:
                                            Slot_Number=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Challenge[2],'Slot_Number')[0]['sRawData'])
                                            res.append([f'TPR sent slot number: {int(Slot_Number)} in the Challenge packet at {{{Challenge[2]}}}, Exp :0','Pass' if Slot_Number ==0 else 'Inconclusive'])
                                            # check Digets Response
                                            Challenge_Auth=self.PktMethod.GetPacketDetails(packet="ADT",value='Challenge_Auth', Type="Response",limit=[Challenge[2]+1,self.Flow_limit[1]])
                                            if len(Challenge_Auth)>2:
                                                Challenge_Msg=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="-Valid",Type='TesterMsg',limit=[Challenge_Auth[2]+1,self.Flow_limit[1]])
                                                if len(Challenge_Msg)>2:
                                                    res.append([f'Challenge Auth found at {{{Challenge_Msg[2]}}}','Pass'])
                                                else:res.append([f'Test did not found Challenge valid message', 'Inconclusive'])
                                            else:res.append([f'PTx did not sent Challenge_Auth Response', 'Inconclusive'])
                                        else:res.append([f'TPR did not sent Challenge Request','Inconclusive'])
                                    else:res.append([f'Test did not found Certificate chain valid message', 'Inconclusive'])
                                else:res.append([f'PTx did not sent Certificate_Response', 'Inconclusive'])
                            else:res.append([f'TPR did not sent Get_Certificate Request','Inconclusive'])
                        else:res.append([f'Test did not found Digest Not in Cache message', 'Inconclusive'])
                    else:res.append([f'PTx did not sent Digests_Response', 'Fail'])
                else:res.append([f'Prx did not sent ADC_End packet','Inconclusive'])
            else:res.append([f'TPR did not sent Get_Digests Request','Inconclusive'])
        else:res.append([f'Prx did not entered PT phase', 'Inconclusive'])

        return res


    def TcertReady(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            # Check Simple Flow
            Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[RP0[2]+1,self.Flow_limit[1]])
            if len(Get_Certificate)>2:
                results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                if len(results)>0:res.extend(results)
                ADC_End=self.PktMethod.GetPacketDetails(packet="ADC",value="End" ,limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                if len(ADC_End)>2:
                    # Check Certificate Response
                    Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                    if len(Certificate)>2:
                        # CTS Pass/ Fail Criteria
                        if self.Header['TestcaseID']  in ['PTX_APX_TIM_002']:
                            res.append([f'PTx sent CERTIFICATE Response  at {{{Certificate[2]}}}','Pass'])
                            ATN=self.PktMethod.GetPacketDetails(packet="ATN",Type="Response",limit=[Certificate[2],ADC_End[2]])
                            Timing=round((ATN[0]-ADC_End[1])*1000,2)
                            res.append([f'Measured timing t_Cert_Ready between ADC_End at {{{ADC_End[2]}}} to ATN response at {{{ATN[2]}}} is {Timing}mS, Limit [<= {Check['limit']} mS]','Fail' if Timing > Check['limit'] else 'Pass'])

                        Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,self.Flow_limit[1]])
                        if len(Chain_Msg)>2:
                            res.append([f'Certificate chain valid found at {{{Chain_Msg[2]}}}','Pass'])
                            # Check Challenge Sequence
                            Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[Chain_Msg[2]+1,self.Flow_limit[1]])
                            if len(Challenge)>2:
                                Slot_Number=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Challenge[2],'Slot_Number')[0]['sRawData'])
                                res.append([f'TPR sent slot number : {int(Slot_Number)} in the Challenge packet at {{{Challenge[2]}}}, Exp: 0','Pass' if Slot_Number ==0 else 'Inconclusive'])
                                ADC_End=self.PktMethod.GetPacketDetails(packet="ADC",value="End" ,limit=[Challenge[2]+1,self.Flow_limit[1]])
                                if len(ADC_End)>2:
                                    # Check Certificate Response
                                    Challenge_Auth=self.PktMethod.GetPacketDetails(packet="ADT",value='Challenge_Auth', Type="Response",limit=[ADC_End[2]+1,self.Flow_limit[1]])
                                    if len(Challenge_Auth)>2:
                                        # CTS Pass/ Fail Criteria
                                        if self.Header['TestcaseID']  in ['PTX_APX_TIM_003']:
                                            res.append([f'PTx sent CHALLENGE_AUTH response at {{{Challenge_Auth[2]}}}','Pass'])
                                            ATN=self.PktMethod.GetPacketDetails(packet="ATN",Type="Response",limit=[Challenge_Auth[2],ADC_End[2]])
                                            Timing=round((ATN[0]-ADC_End[1])*1000,2)
                                            res.append([f'Measured timing t_Cert_Ready between ADC_End at {{{ADC_End[2]}}} to ATN response at {{{ATN[2]}}} is {Timing}mS, Limit[<= {Check['limit']} mS]','Fail' if Timing > Check['limit'] else 'Pass'])
                                        Challenge_Msg=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="-Valid",Type='TesterMsg',limit=[Challenge_Auth[2]+1,self.Flow_limit[1]])
                                        if len(Challenge_Msg)>2:
                                            res.append([f'Challenge_Auth message found at {{{Challenge_Msg[2]}}}','Pass'])
                                        else:res.append([f'Test did not found Challenge valid message', 'Inconclusive'])
                                    else:res.append([f'PTx did not sent Challenge_Auth response', 'Fail' if self.Header['TestcaseID']  in ['PTX_APX_TIM_003'] else 'Inconclusive' ])
                                else:res.append([f'PRx did not sent ADC_End packet after Challenge packet at {{{Challenge[2]}}}','Inconclusive'])
                               
                            else:res.append([f'TPR did not sent Challenge_Request','Inconclusive'])
                        else:res.append([f'Test did not found Certificate chain valid message', 'Inconclusive'])
                    else:res.append([f'PTx did not sent Certificate_Response', 'Fail' if self.Header['TestcaseID']  in ['PTX_APX_TIM_002'] else 'Inconclusive' ])
                else:res.append([f'PRx did not sent ADC_End packet','Inconclusive'])
            else:res.append([f'TPR did not sent Get_Certificate request','Inconclusive'])
        else:res.append([f'Prx did not entered PT phase', 'Inconclusive'])
        return res
    
    def NDS_Check(self,CTSCheck,Check,flows,flwID):
        res=[]
       
        Limits=[self.FirstPing(flows[flwID]['Limit']),flows[flwID]['Limit']]
        print(f'First ping limit: {Limits[0]} , Second ping limit: {Limits[1]}')
      
        #  Validate First ping
        if Limits[0] is not None:
            res.append([f'Sequence :1','Pass'])
            res.extend(self.SimpleFlow_Check(Check,Limits[0]))

        else:res.append(['Limit was not avaialble for the first ping','Inconclusive'])

        #  Validate Second ping
        if Limits[1] is not None:
            Limit=Limits[1]
            res.append([f'Sequence :2','Pass'])
            RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=Limit)
            if len(RP0)>2:

                # Check Challenge Sequence
                Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[RP0[2]+1,Limit[1]])
                if len(Challenge)>2:
                    res.append([f'TPR sent Challenge packet at {{{Challenge[2]}}}','Pass'])
                    Slot_Number=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Challenge[2],'Slot_Number')[0]['sRawData'])
                    res.append([f'TPR sent slot number: {int(Slot_Number)} in the Challenge packet at {{{Challenge[2]}}}, Exp :0','Pass' if Slot_Number ==0 else 'Inconclusive'])
                    # check Digets Response
                    Challenge_Auth=self.PktMethod.GetPacketDetails(packet="ADT",value='Challenge_Auth', Type="Response",limit=[Challenge[2]+1,Limit[1]])
                    if len(Challenge_Auth)>2:
                        res.append([f'PTx sent Challenge_Auth response at {{{Challenge_Auth[2]}}}','Pass'])
                        Challenge_Msg=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="-Valid",Type='TesterMsg',limit=[Challenge_Auth[2]+1,Limit[1]])
                        if len(Challenge_Msg)>2:
                            res.append([f'Challenge_Auth found at {{{Challenge_Msg[2]}}}','Pass'])
                            # Check Simple Flow
                            Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[Challenge_Msg[2]+1,Limit[1]])
                            if len(Get_Certificate)>2:
                                res.append([f'TPR sent Get_Certificate packet at {{{Get_Certificate[2]}}}','Pass'])
                                results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                                if len(results)>0:res.extend(results)
                                # Check Certificate Response
                                Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,Limit[1]])
                                if len(Certificate)>2:
                                    res.append([f'PTx sent CERTIFICATE response at {{{Certificate[2]}}}','Pass'])
                                    Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,Limit[1]])
                                    if len(Chain_Msg)>2:
                                        res.append([f'Certificate chain valid found at {{{Chain_Msg[2]}}}','Pass'])
                                    
                                    else:res.append([f'Test did not found Certificate chain valid message', 'Inconclusive'])
                                else:res.append([f'PTx did not sent Certificate_Response', 'Inconclusive'])
                            else:res.append([f'TPR did not sent Get_Certificate request','Inconclusive'])

                        else:res.append([f'Test did not found Challenge valid message', 'Fail'])
                    else:res.append([f'PTx did not sent Challenge_Auth response', 'Inconclusive'])
                else:res.append([f'TPR did not sent Challenge_Request','Inconclusive'])

            else:res.append([f'PRx did not entered PT phase', 'Inconclusive'])

        else:res.append(['Limit was not avaialble for the  second ping','Inconclusive'])  

        # Validate ChallengeAuth Responses from Two Pings

        Signatures={"Signature_s":[],"Signature_r":[]}
        id=0
        count=0
        while id < len(self.Auth_file_list):
            if self.Auth_file_list[id]['pktType']=="CHALLENGE_AUTH":
                count+=1
                payloadvalue1=self.PayloadDetails_Auth(id,"Signature_r_Value")
                payloadvalue2=self.PayloadDetails_Auth(id,"Signature_s_Value")
                if payloadvalue1 is not None and payloadvalue2 is not None: 
                    Signatures['Signature_r'].append(payloadvalue1[0]['sRawData'])
                    Signatures['Signature_s'].append(payloadvalue2[0]['sRawData'])
                if count==2:break
            id+=1
        
        if len(Signatures['Signature_r'])>1 and len(Signatures['Signature_s'])>1:
            res.append([f'Signature_r values in both responses are {Signatures['Signature_r'][0]}, {Signatures['Signature_r'][1]}','Pass'])
            res.append([f'Signature_s values in both responses are {Signatures['Signature_s'][0]}, {Signatures['Signature_s'][1]}','Pass'])
            if Signatures['Signature_r'][0]!=Signatures['Signature_r'][1] and Signatures['Signature_s'][0]!=Signatures['Signature_s']:
                res.append([f'Signatures contained in two Challenge_Auth responses are different','Pass'])
            else: res.append([f'Signatures contained in two Challenge_Auth responses are same','Fail'])

        else:res.append([f'Test did not found Signature_r or Signature_s in challenge_Auth response','Inconclusive'])

        return res
    
    def MaxChainlength(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=self.Flow_limit)
        if len(RP0)>2:
            id=RP0[2]+1
            lid=0
            GetCertificate=False
            CerificateLength=0
            while id  < self.Flow_limit[1]:
                # Check Simple Flow
                Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[id,self.Flow_limit[1]])
                if len(Get_Certificate)>2:
                    res.append([f'Get_Certificate packet found at {{{Get_Certificate[2]}}}','Pass'])
                    GetCertificate=True
                    # Check Certificate Response
                    Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,self.Flow_limit[1]])
                    if len(Certificate)>2:
                        res.append([f'CERTIFICATE response found at {{{Certificate[2]}}}','Pass'])
                        ProtocolVersion=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Certificate[2],'Authentication_Protocol_Version')[0]['sRawData'])
                        certifiacte_Header=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Certificate[2],'Certificate')[0]['sRawData'])
                        if certifiacte_Header and ProtocolVersion:
                            res.append([f'Certificate response header starts with: 0x{int(ProtocolVersion)}{int(certifiacte_Header)}, Exp : 0x12', 'Pass' if ProtocolVersion==1 and certifiacte_Header==2 else 'Fail'])
                        else:res.append([f'Did not found header in Certificate response at {{{Certificate[2]}}}','Inconclusive'])
                        while lid < len(self.Auth_file_list):
                            if self.Auth_file_list[lid]['pktType']=="CERTIFICATE":
                                payloadvalue=self.PayloadDetails_Auth(lid,"Certificate_Chain_Segment")
                                if payloadvalue is not None:  
                                    ChainLength=len(payloadvalue[0]['sRawData'].split("-")) - CerificateLength
                                    CerificateLength+=ChainLength
                                    res.append([f'Certificate_Chain segment in the CERTIFICATE authentication response has a length of: {ChainLength}, Exp: 1- {Check['Length'][1]} Bytes','Pass' if ChainLength <=Check['Length'][1] and ChainLength>=1 else 'Fail'])
                                else:
                                    # check whether it was last or not . if Last skip it
                                    Cid=lid+1
                                    ChainSegment=False
                                    while Cid < len(self.Auth_file_list):
                                        if self.Auth_file_list[Cid]['pktType']=="CERTIFICATE":
                                            ChainSegment=True
                                            break
                                        Cid+=1
                                    if not ChainSegment:
                                        AuthResp=self.PktMethod.GetPacketDetails(packet="ADC",value="Auth",Type='Response',limit=[Certificate[2],self.Flow_limit[0]])
                                        if len(AuthResp)>2:
                                            Bytes=self.file_list[AuthResp[2]]['value'].split(':')[1].replace('}','')
                                            ChainLength=int("".join([c for c in Bytes if c.isdigit()]))-1
                                            res.append([f'Certificate_Chain segment in the CERTIFICATE authentication response has a length of: {ChainLength}, Exp: 1- {Check['Length'][1]} Bytes','Pass' if ChainLength <=Check['Length'][1] and ChainLength>=1 else 'Fail'])
                                    else:res.append([f'Did not found Certificate_Chain_Segment in Certificate response','Inconclusive'])
                                lid+=1
                                break
                            else:lid+=1
                     
                        id=Certificate[2]+1
                    else:
                        res.append([f'PTx did not sent CERTIFICATE response after Get_Certificate at {{{Get_Certificate[2]}}} ', 'Inconclusive'])
                        id=Get_Certificate[2]+1
                        break
                else:
                    if not GetCertificate: res.append([f'TPR did not sent Get_Certificate request','Inconclusive'])
                    break
            
            try:
                aid=len(self.Auth_file_list)-1
                while aid > 0:
                    if self.Auth_file_list[aid]['pktType']=="CERTIFICATE":
                        Full_certificate = self.Auth_file_list[aid]['header_Payload']['sFieldType'].split(":")[-1].strip()
                        modified_full_certificate = Full_certificate.replace("0x","").strip()
                        
                        WPC_root = self.PayloadDetails_Auth(aid, "Root_Certificate_Hash")
                        if WPC_root is not None:
                            modified_WPC_root = WPC_root[0]['sRawData'].strip().replace("-"," ")
                            res.append([f"Received complete certificate chain is {Full_certificate}", "Pass"])
                            res.append([f"WPC Root is {WPC_root}", "Pass"])
            
                            Manufacturee_certificate = self.PayloadDetails_Auth(aid, "Manufacturer_CA_Certificate")
                            if Manufacturee_certificate is not None:
                                modified_Manufacturee_certificate = Manufacturee_certificate[0]['sRawData'].strip().replace("-"," ")
                                res.append([f"Manufacturer certificate is {Manufacturee_certificate}", "Pass"])
                
                                if modified_WPC_root in modified_full_certificate and modified_Manufacturee_certificate in modified_full_certificate:
                                    res.append([f"Certificate chain is signed by WPC root certificate key", "Pass"])
                                else:
                                    res.append([f"Certificate chain is not signed by WPC root certificate key", "Fail"])
                            else:
                                res.append([f"Did not received Manufacturer_CA_Certificate", "Inconclusive"])

                        else:
                            res.append([f"Did not received WPC root chain", "Inconclusive"])
                                
                        break
                    aid-=1
    
            except Exception as e:
                res.append(f'Error - {e}','Inconclusive')

      
        return res
    
    def ContentPolicy(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        policyval=['00', '00', '00', '03']
        extensionval=None
        id=0
        try:
            while id < len(self.Auth_file_list):
                if self.Auth_file_list[id]['pktType']=="CERTIFICATE":
                    payloadvalue=self.PayloadDetails_Auth(id,"Extensions_2_extnValue")
                    if payloadvalue is not None: extensionval=payloadvalue[0]['sRawData'].split('-')[2:]   
                id+=1
        except Exception as e: print(e)
        if extensionval is not None:
            TwoBytes=True
            for i in range(len(policyval)):
                if policyval[i]!=extensionval[i]:TwoBytes=False
            res.append([f'Extensions.2.extnValue sub-object of the wpc-qi-policy extension (policy value) has bits is: {extensionval}, Exp: {policyval}','Fail' if not TwoBytes else 'Pass'])
        else:res.append([f'Extensions.2.extnValue is not received in the Auth_Sequence','Inconclusive'])
                        
        return res

    

        

################################################################################################################################################
#----------------------------------------------Functions Used in CTS Checks -------------------------------------------------------------------#
################################################################################################################################################

    def Measure_Voltage_Current_Plot(self,id,LoadFlag,Check):
        res=[]
        # Monitor Voltage/current throught the TestCase
        if not LoadFlag :
            Values=self.MonitorVoltage(id,self.Flow_limit[1]-2) 
            if Values[1] !=0 and  Values[3] !=0:
                res.append([f' Measured Max {Check['Name']} Val at {round((self.AllChannelData['Interval']*Values[0])/1000,3)} sec is {Values[1]} {Check['unit']} and  Min {Check['Name']} Val  at {round((self.AllChannelData['Interval']*Values[2])/1000,3)} sec is {Values[3]} {Check['unit']} , Limit : {Check['limit'][0]} {Check['unit']} ~ {Check['limit'][1]} {Check['unit']} ', 
                            'Pass' if Values[3] >= Check['limit'][0] and Values[1] <= Check['limit'][1] else 'Inconclusive'])

            # Find Ambient and Coil Temperature
            self.AllChannelData12= self.PlotMethod.GetAllChannelData2('12',self.JapiData) # Coil Temperature Plot
            self.AllChannelData11= self.PlotMethod.GetAllChannelData2('11',self.JapiData) # Ambient Temperature Plot
                #Get Max, min Temperatures
            templist1 =[]
            templist2= []
            for temp in self.AllChannelData11['RV']['displayDataChunk']: templist1.append(temp)  
            for temp in self.AllChannelData12['RV']['displayDataChunk']:  templist2.append(temp)  

            res.append([f"Measured coil temperature is {max(templist2)} °C ,Measured ambient temperature is {min(templist1)} °C ", "Pass"]) 
            res.append([f"Difference in temperature is {round(max(templist2)-min(templist1),2)} °C", "Pass" if round(max(templist2)-min(templist1),2) <12 else 'Fail']) 
                
        # Find Tc execution Timing
        Timing=round(((self.file_list[self.Flow_limit[1]]['stopTime']-self.file_list[self.Flow_limit[0]]['startTime'])*1000)/60000,3)
        res.append([f'Test executed for {Timing} mins , Exp [>=60 mins]','Pass' if Timing>=60 else 'Inconclusive'])
        return res
    
    def CheckLoads(self,Check):
        res=[]
          # Check Loads are applied or not
        LoadFlag=False
        for Load in Check['Loads']:
                # Find the Load
            LD=self.PktMethod.GetPacketDetails(packet=f"Set_Load {Load}",Type="TesterMsg" ,limit=[self.id,self.Flow_limit[1]])
            if len(LD)>2:
                # res.append([f"Prx Applied Load: {Load} Ohms at id :{LD[2]}", "Pass"])
                LoadCE=self.PktMethod.GetPacketDetails2(packet="Control Error",value=["0","+1","-1"] ,limit=[LD[2]+1, self.Flow_limit[1]])
                if len(LoadCE)>2:
                    vrect = self.CalculateVoltTwindow(LoadCE[2],self.AllChannelData_Volatge,at="start",measure="before")
                    LoadResistance=round(vrect[0]/(self.CalculateVoltTwindow(LoadCE[2],self.AllChannelData,at="start",measure="before"))[0],3)
                    RLimit=[round((Load - ((Load*Check['LoadTolerance'])/100)),3), round((Load +((Load*Check['LoadTolerance'])/100)),3)]
                    res.append([f"Measured load resistance: {LoadResistance}_ohms, Limit: {RLimit[0]} Ohms ~ {RLimit[1]}_ohms", 
                                    'Pass' if LoadResistance >= RLimit[0] and LoadResistance <= RLimit[1] else 'Inconclusive'])
                    # Measure Timing
                    Timing=round((LD[0]-self.file_list[self.id-1]['stopTime']),3)
                    if Load ==16 :res.append([f'TPR switched to {Load}_ohms within {round(Timing/60,3)} mins after target operating load, Exp: Atleast after 1 mins ' , 
                                                'Pass' if Timing /60 > 1 else 'Inconclusive'])
                    else: res.append([f'TPR switched to {Load}_ohms within {Timing} Secs before the previous load, Exp: Atleast after 10 Secs ' , 'Pass' if Timing > 10 else 'Inconclusive'])
                    self.id=LD[2]+1
                else: 
                    res.append([f'TPR did not regulated after applying {Load}_ohms','Inconclusive'])
                    LoadFlag=True
            else: 
                res.append([f"PRx did not applied {Load}_ohms", "Inconclusive"]) 
                LoadFlag=True
            if LoadFlag :break

        return res,LoadFlag

    def EPT_Helper(self,Check,Limit,Repingtime=None):
        res=[]
        PktName=Check["EPT"][0]+" "+Check["EPT"][1] if Check["EPT"][1]is not None else Check["EPT"][0]
        if Repingtime is not None:
            Check['TnextPing']=[(80*Repingtime/100)*1000,(120*Repingtime/100)*1000]
            Check['Desc']=f"{80*Repingtime/100} seconds ≤ Tnextping ≤ {(120*Repingtime/100)} seconds "

            
        CE=self.PktMethod.GetPacketDetails(packet="Control Error",limit=Limit)
        if len(CE)>2:
            time_start=CE[1]
            id=CE[2]+1
            EPTpkt=False
            while id < Limit[1]:
                EPT = self.PktMethod.GetPacketDetails(packet=Check['EPT'][0], value=Check['EPT'][1], limit=[id,Limit[1]])
                if len(EPT)>2:
                    Timing=round((EPT[0]-time_start)*1000,2)
                    res.append([f'TPR sent {PktName} at index@ {{{EPT[2]}}}','Pass'])
                    res.append([f'TPR sent {PktName} within {Timing} mS from {self.file_list[id-1]['pktType']} at index@ {{{id-1}}}', 'Pass' if Timing >= 2000 and Timing <=8000 else 'Inconclusive'])  
                    time_start=EPT[1] 
                    EPTpkt=True
                    id=EPT[2]+1                
                else: break
            # find the next ping and ignore Threshold ping
            if EPTpkt:
                EPTid=id-1
                NextPingMsg=False
                while id < len(self.file_list):
                    NextPing=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[id, len(self.file_list)-1])
                    if len(NextPing)>2:
                        NextPingMsg=True
                        # ensure the ping dose not contain threshold message
                        Shutdown=self.PktMethod.GetPacketDetails(packet="Shutdown", Type="TesterMsg",limit=[NextPing[2]+1, len(self.file_list)-1])
                        if len(Shutdown)>2:
                            Threshold=self.PktMethod.GetPacketDetails(packet="Threshold_status", Type="TesterMsg",limit=[NextPing[2]+1, Shutdown[2]])
                            if len(Threshold)>2:
                                id=Threshold[2]+1
                                continue
                        Timing=round((NextPing[0]-self.file_list[EPTid]['stopTime'])*1000,3)
                        unit = f'{round(Timing,3)} mS' if 'RST' in self.Header['TestcaseID'] else f'{round(Timing/1000,3)} Secs'
                        res.append([f'PTx initiated next ping at {{{NextPing[2]}}}, Measured t_nextping from end of End Power Transfer packet is :{unit}, Limit :{Check['Desc']}', 'Pass' if Timing >= Check['TnextPing'][0] and Timing <=Check['TnextPing'][1] else 'Fail'])
                        break
                    else:break
                if not NextPingMsg:res.append([f'PTx did not initiated next ping after {PktName} at index@ {{{EPTid}}}', 'Pass'])
            else: res.append([f'TPR did not sent {PktName}','Inconclusive'])
        else:res.append(['TPR did not enter PT phase','Inconclusive'])
        return res

    def ValidateChainNames(self,CertData,Seq):

        der = bytes.fromhex(CertData)
        cert = x509.Certificate.load(der)

        subject = cert["tbs_certificate"]["subject"]
        res=[]
        seen=set()
        rules = {
                    "2.5.4.3": ("Common Name", 6, 35),  # X.500 common name
                    "2.5.4.92": ("tagAfi", 1, 32),  # X.500 tagAfi
                    "0.9.2342.19200300.100.1.1": ("LDAP userID", 1, 32)  # LDAP userID
                }

        for rdn in subject.chosen:
            for attr in rdn:
                oid = attr["type"].dotted
                value = attr["value"].native
                if oid in seen:
                    res.append([f"Duplicate OID: {oid}- in seq {Seq}", "Fail"])
                    continue
                else: seen.add(oid)

                if isinstance(value, str): length = len(value.encode("utf-8"))
                elif isinstance(value, bytes): length = len(value)
                else: length = len(str(value).encode())

                if oid not in rules:
                    res.append([f"Unexpected OID: {oid}- in seq {Seq}",'Fail'])
                    continue
                else:
                    name, min_len, max_len = rules[oid]
                    if min_len <= length <= max_len:
                        res.append([f"{name} length ({length} bytes) is in range [{min_len}, {max_len}] - in seq {Seq}", "Pass"])
                    else:
                        res.append([f"{name} length ({length} bytes) not in range [{min_len}, {max_len}]- in seq {Seq}", "Fail"])

        # Validate all Names recived or not
        for oid in rules:
            if oid not in seen:res.append([f"Missing OID: {oid} in seq {Seq}", "Fail"])

        return res  if len(res)>0 else ['Did not found any data in seq {Seq}','Inconclusive']     

    def BytesCount(self,limit):
        id=limit[0]
        Bytes=0
        while id < limit[1]:
            ADT=self.PktMethod.GetPacketDetails(packet="ADT",Type="Response",limit=[id,limit[1]])
            if len(ADT)>2:
                Bytes+=int(''.join(filter(str.isdigit, self.file_list[ADT[2]]['pktType'])))
                id=ADT[2]+1
            else:break
        return Bytes
    
    def SimpleFlow_Check(self,Check,Limit):
        res=[]

        try:
            RP0=self.PktMethod.GetPacketDetails(packet="16 bit Received Power",value="Mode:0", limit=Limit)
            if len(RP0)>2:
                # Check Simple Flow
                Get_Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value="Get_Certificate",limit=[RP0[2]+1,Limit[1]])
                if len(Get_Certificate)>2:
                    res.append([f'TPR sent Get_Certificate packet at index@ {{{Get_Certificate[2]}}}','Pass'])
                    results=self.Payload_Details(PacketName='Get_Certificate',Index=Get_Certificate[2],PayLoads=Check['Get_Certificate'])
                    if len(results)>0:res.extend(results)
                    # Check Certificate Response
                    Certificate=self.PktMethod.GetPacketDetails(packet="ADT",value='Certificate', Type="Response",limit=[Get_Certificate[2]+1,Limit[1]])
                    if len(Certificate)>2:
                        res.append([f'PTx sent CERT response at index@ {{{Certificate[2]}}}','Pass'])
                        Chain_Msg=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="-Valid",Type='TesterMsg',limit=[Certificate[2]+1,Limit[1]])
                        if len(Chain_Msg)>2:
                            res.append([f'Certificate_chain valid found at {{{Chain_Msg[2]}}}','Pass'])
                            # Check Challenge Sequence
                            Challenge=self.PktMethod.GetPacketDetails(packet="ADT",value="Challenge",limit=[Chain_Msg[2]+1,Limit[1]])
                            if len(Challenge)>2:
                                res.append([f'TPR sent Challenge packet at {{{Challenge[2]}}}','Pass'])
                                Slot_Number=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(Challenge[2],'Slot_Number')[0]['sRawData'])
                                res.append([f'TPR sent slot_number : {int(Slot_Number)} in the Challenge packet at {{{Challenge[2]}}} , Exp :0','Pass' if Slot_Number ==0 else 'Inconclusive'])
                                # check Digets Response
                                Challenge_Auth=self.PktMethod.GetPacketDetails(packet="ADT",value='Challenge_Auth', Type="Response",limit=[Challenge[2]+1,Limit[1]])
                                if len(Challenge_Auth)>2:
                                    res.append([f'PTx sent Challenge_Auth response at {{{Challenge_Auth[2]}}}','Pass'])
                                    Challenge_Msg=self.PktMethod.GetPacketDetails(packet="Challenge_Auth",value="-Valid",Type='TesterMsg',limit=[Challenge_Auth[2]+1,Limit[1]])
                                    if len(Challenge_Msg)>2:
                                        res.append([f'Challenge_Auth found at {{{Challenge_Msg[2]}}}','Pass'])
                                    else:res.append([f'Test did not found Challenge valid message', 'Fail' if self.Header['TestcaseID'] in ['TEST_PTX_APX_CHA_NDS_001'] else 'Inconclusive'])
                                else:res.append([f'PTx did not sent Challenge_Auth response', 'Inconclusive'])
                            else:res.append([f'TPR did not sent Challenge_Request','Inconclusive'])
                        else:res.append([f'Test did not found CERT_chain valid message', 'Inconclusive'])
                    else:res.append([f'PTx did not sent Certificate response', 'Inconclusive'])
                else:res.append([f'TPR did not sent Get_Certificate Request','Inconclusive'])
            
            else:res.append([f'Prx did not entered PT Phase', 'Inconclusive'])
        except Exception as e :res.append([e,'Inconclusive'])

        return res

    def ErrorResponseCheck(self,Check):

        res=[]
        # Check Error code
        PktFound=False
        try:
            id=0
            while id < len(self.Auth_file_list):
                if self.Auth_file_list[id]['pktType']=="ERROR":
                    PktFound=True
                    ErrorCode=self.GetAuthPayloadDetails(id,"Error_Code","B1","[7:0]")[0]['sRawData']
                    ErrorData=self.GetAuthPayloadDetails(id,"Error_Data","B1","[7:0]")[0]['sRawData']
                    if ErrorCode and ErrorData is not None: 
                        if 'UPE' in self.Header['TestcaseID']:
                            res.append([f'PTx sent Error_Code as {int(ErrorCode,16)} -- Exp : 2 , Error data as {int(ErrorData,16)} -- Exp : 1 in the Error_response' , 'Pass' if int(ErrorCode,16) ==2 and int(ErrorData,16)==1 else 'Fail'])
                        else:
                            if 'IRE_001' in self.Header['TestcaseID']:
                                res.append([f'PTx sent Error_Code as {int(ErrorCode,16)} -- Exp : 1 , Error data as {int(ErrorData,16)} -- Exp : 0 in the Error_response' , 'Pass' if int(ErrorCode,16) ==1 and int(ErrorData,16)==0 else 'Fail'])
                            else:res.append([f'PTx sent Error_Code as {int(ErrorCode,16)} -- Exp : 1 (INVALID_REQUEST) in the Error_response', 'Pass' if int(ErrorCode,16) ==1 else 'Fail'])
                    
                    else:res.append([f'Test did not found Error_Code OR Error data field in Error_response','Inconclusive'])
                    break
                id+=1
        except Exception as e:print(e)
        if not PktFound: res.append([f'PTx did not sent Error_response','Inconclusive'])  
        return res
            
    def FirstPing(self,LastPing):
        limit = [0,LastPing[0]]
        ST= self.PktMethod.GetPacketDetails(packet="Test_Status" ,value="Execution_Started" ,Type="TesterMsg" ,limit=[0,LastPing[0]])
        if len(ST)>2:
            SP= self.PktMethod.GetPacketDetails(packet="Test_Status" ,value="Execution_Started" ,Type="TesterMsg" ,limit=[ST[2]+1,LastPing[0]])
            if len(SP)>2: limit=[ST[2],SP[2]]

            packets = {}
            cnt = 0
            id = limit[0]
            while id < limit[1]:
                start = 0
                end = 0
                if any(res in self.file_list[id].get('pktType') for res in ['Ping Detected','Ping Initiated']):
                    # print('pd',id)
                    #find Shutdown
                    sd= self.PktMethod.GetPacketDetails(packet='Shutdown',limit=[id,limit[1]],Type = "TesterMsg")
                    if len(sd)>2:
                        # print('sd',sd)
                        #ensure no PD recevied btw PD-SD
                        ilPD = self.PktMethod.GetPacketDetails(packet='Ping Detected',limit=[id+1,sd[2]],Type = "TesterMsg")
                        if len(ilPD)>1: id = ilPD[2]
                        #check TestStop recevied before SD
                        ilTS = self.PktMethod.GetPacketDetails(packet='Test_Stop',limit=[id,sd[2]],Type = "TesterMsg")
                        if len(ilTS)>1: sd = ilTS
                        start = id
                        end = sd[2]
                        id = end
                    else:
                        sd= self.PktMethod.GetPacketDetails(packet='Test_Stop',limit=[id,limit[1]],Type = "TesterMsg")
                        if len(sd)>2:
                            # print('ts',sd)
                            #ensure no PD recevied btw PD-SD
                            ilPD = self.PktMethod.GetPacketDetails(packet='Ping Detected',limit=[id+1,sd[2]],Type = "TesterMsg")
                            if len(ilPD)>1: id = ilPD[2]
                            start = id
                            end = sd[2]
                            id=end
                        else:
                            start = id
                            end = limit[1]
                            id=end
                    #consider seq. has length > 3 and ss in flow
                    SS = self.PktMethod.GetPacketDetails(packet='Signal strength',limit=[start,end])
                    # print(SS,start,end)
                    if len(SS)>2:
                        if (end -start) >= 10 and len(SS)>1:
                            cnt +=1                     
                            packets[cnt]={"Limit":[start,end],"Flow":1}
                    
                else: id+=1
            # print('Packetflow',packets)
            #consider last 2 seq.
            flow1=None
            flow2=None
            for seq in packets:
                if packets[seq]['Flow']!=0:
                    if packets[seq]['Flow']==1 and flow2==None:
                        flow1 = packets[seq]
            
            if flow1 is not None : 
                if flow1['Limit']==LastPing: return None
                else:return flow1['Limit']
            else: return None
            
        return None





    def TrestartBool(self,pkt):
        Trestart=False
        if self.Certification not in ["2.2.1","2.1.0","1.3.3","2.0.0"]:
            Trestart=True
            if pkt[0]=="End Power Transfer":Trestart=False

        return Trestart
    
    def ValidTterminate(self,limit,Check,DataPacketName):
        res=[]
        TterminateList=[]
        id=limit[0]
        while id < limit[1]:
            ILL = self.PktMethod.GetPacketDetails(packet=Check['pkt'][0], value=Check['pkt'][1], limit=[id,limit[1]])
            if len(ILL)>2:
                if Check['pkt'][2] : res.extend(self.Payload_Details(PacketName=DataPacketName,Index=ILL[2],PayLoads= Check['pkt'][3])) 
                Coilpk=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[ILL[2]+1,limit[1]])
                if len(Coilpk)>2:
                    TterminateVal=round((Coilpk[1] - ILL[1]) * 1000, 3)
                    TterminateList.append([round(ILL[1],3),round(Coilpk[0],3),ILL[2],TterminateVal])
                    id=ILL[2]+1
                else:break
            else:break
        if TterminateList:
            min_item = min(TterminateList, key=lambda x: x[-1])
            max_item = max(TterminateList, key=lambda x: x[-1])
            res.append([f"Measured max t_terminate from {max_item[0]}Sec to {max_item[1]}Sec for the {DataPacketName} packet at index@ {{{max_item[2]}}} is {max_item[-1]}mS , Limit: <= {Check['Tterminate'][1]}", 'Fail' if  max_item[-1] > Check['Tterminate'][1] else 'Pass'])
            res.append([f"Measured min t_terminate from {min_item[0]}Sec to {min_item[1]}Sec for the {DataPacketName} packet at index@ {{{min_item[2]}}} is {min_item[-1]}mS , Limit:<= {Check['Tterminate'][1]}", 'Fail' if  min_item[-1] > Check['Tterminate'][1] else 'Pass'])

        return res

    def Trestart_Vrect(self,limit,DataPacketName,CTSCheck):
        res=[]
        self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
        TrestartList=[]
        Vrectlist=[]
        id=limit[0]
        while id < limit[1]:
            if CTSCheck=='T_terminate' and len(TrestartList)>0: break # Need to validate only one ping after detach other than ping phases.
            FP=self.PktMethod.GetPacketDetails(packet="Ping Detected", Type="TesterMsg",limit=[id,limit[1]])
            if len(FP)>2:
                # Check Coilvoltpkpk Assertion
                NP=self.PktMethod.GetPacketDetails(packet="Ping Detected", Type="TesterMsg",limit=[FP[2]+1,limit[1]])
                if len(NP)>2:
                    Coilpk=self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk", Type="TesterMsg",limit=[FP[2]+1,NP[2]])
                    if len(Coilpk)>2:
                        Timing=round(( NP[0] - Coilpk[1]) * 1000, 3)
                        TrestartList.append([round(Coilpk[1],3),round(NP[0],3),FP[2],Timing])
                        # Check the VRECT value of the ping if there is only an SS packet [other than Ping phases]
                        if CTSCheck=='T_terminate' :
                            SS = self.PktMethod.GetPacketDetails(packet='Signal strength',limit=[NP[2]+1,len(self.file_list)])
                            if len(SS)>2:
                                SSNP=self.PktMethod.GetPacketDetails(packet="Ping Detected", Type="TesterMsg",limit=[SS[2]-1,NP[2]-1])
                                vrect = self.CalculateVoltTwindow(SSNP[2],self.AllChannelData,at="start",measure="after",winsize=[22,33])
                                Vrectlist.append([SSNP[2],vrect[0]])   
                            else:
                                vrect = self.CalculateVoltTwindow(NP[2],self.AllChannelData,at="start",measure="after",winsize=[22,33])
                                Vrectlist.append([NP[2],vrect[0]])
                        else:
                            vrect = self.CalculateVoltTwindow(NP[2],self.AllChannelData,at="start",measure="after",winsize=[22,33])
                            Vrectlist.append([NP[2],vrect[0]])
                    id=NP[2]
                else:break
            else:break
        if len(TrestartList)>1 :
            min_item = min(TrestartList, key=lambda x: x[-1])
            max_item = max(TrestartList, key=lambda x: x[-1])
            min_Vrect= min(Vrectlist, key=lambda x: x[-1])
            max_Vrect= max(Vrectlist, key=lambda x: x[-1])
            res.append([f'Measured max t_restart_after_illegal from {max_item[0]}Sec to {max_item[1]}Sec for the {DataPacketName} packet is {max_item[-1]}mS, Limit[≤ 500mS]', 'Fail' if  max_item[-1] > 500 else 'Pass'])
            res.append([f'Measured min t_restart_after_illegal from {min_item[0]}Sec to {min_item[1]}Sec for the {DataPacketName} packet is {min_item[-1]}mS, Limit[≤ 500mS]', 'Fail' if  min_item[-1] > 500 else 'Pass'])
            res.append([f"Measured max V_RECT is {max_Vrect[-1]}V at ping {{{max_Vrect[0]}}}, Limit[≤ 19V]", "Fail" if max_Vrect[-1] > 19 else "Pass"])
            res.append([f"Measured min V_RECT is {min_Vrect[-1]}V at ping {{{min_Vrect[0]}}}, Limit[≤ 19V]", "Fail" if min_Vrect[-1] > 19 else "Pass"])
        elif len(TrestartList)==1:
            res.append([f'Measured t_restart_after_illegal from {TrestartList[0][0]}Sec to {TrestartList[0][1]}Sec for the {DataPacketName} packet is {TrestartList[0][-1]}mS, Limit[≤ 500mS] ', 'Fail' if  TrestartList[0][-1] > 500 else 'Pass'])
            res.append([f"Measured V_RECT is {Vrectlist[0][-1]}V at ping {{{Vrectlist[0][0]}}}, Limit[≤ 19V]", "Fail" if Vrectlist[0][-1] > 19 else "Pass"])
        else:res.append([f'Test did not found any t_restart_after_illegal or V_RECT measurements','Inconclusive'])

        return res
    
     #get Tterminate Values
    def calculate_Tterminate(self,start_id, end_id,ExpPkt,result=[],TterminateLimit=[0,28],PacketDetailsCheck=False,PayLoads=[],DataPacketName='',Trestart=False):
        
        TterminateList=[]
        TrestartList=[]
        Vrectlist=[]
        res=result                
        while start_id < end_id:
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=ExpPkt, limit=[start_id, end_id])
            if len(ExpectedPacket_Details) > 2:
                if PacketDetailsCheck : res.extend(self.Payload_Details(PacketName=DataPacketName,Index=ExpectedPacket_Details[2],PayLoads=PayLoads))  
                detach_details = self.PktMethod.GetPacketDetails(packet="CoilVoltpkpk",Type="TesterMsg", limit=[ExpectedPacket_Details[2], end_id])
                Shutdown_details=self.PktMethod.GetPacketDetails(packet="Shutdown", Type="TesterMsg",limit=[ExpectedPacket_Details[2], end_id+1])
                if len(detach_details) > 2:
                    TterminateVal=round((detach_details[1] - ExpectedPacket_Details[1]) * 1000, 3)
                    TterminateList.append([round(ExpectedPacket_Details[1],3),round(detach_details[1],3),ExpectedPacket_Details[2],TterminateVal])
                    if Trestart:
                        if len(Shutdown_details)>2:
                            NextPing_details=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[Shutdown_details[2]+1, len(self.file_list)-1])
                            if len(NextPing_details)>2:
                                Trestart=round(( NextPing_details[0] - detach_details[1]) * 1000, 3)
                                TrestartList.append([round(detach_details[1],3),round(NextPing_details[0],3),NextPing_details[2],Trestart])
                                vrect = self.CalculateVoltTwindow(NextPing_details[2],self.AllChannelData,at="start",measure="after",winsize=[22,33])
                                Vrectlist.append([NextPing_details[2],vrect[0]])
                            else:
                                res.append([f'PTx did not initated next ping after the packet {DataPacketName} at index@ {ExpectedPacket_Details[2]}','Inconclusive'])

                    start_id = detach_details[2]+1
                else:break 
            else:break
      
        if TterminateList:
            min_item = min(TterminateList, key=lambda x: x[-1])
            max_item = max(TterminateList, key=lambda x: x[-1])
            res.append([f'Measured max t_terminate from {max_item[0]}Sec to {max_item[1]}Sec for the {DataPacketName} packet at index@ {max_item[2]} is {max_item[-1]}mS , Limit: {TterminateLimit}', 'Fail' if  max_item[-1] > TterminateLimit[1] else 'Pass'])
            res.append([f'Measured min t_terminate from {min_item[0]}Sec to {min_item[1]}Sec for the {DataPacketName} packet at index@ {min_item[2]} is {min_item[-1]}mS , Limit: {TterminateLimit}', 'Fail' if  min_item[-1] > TterminateLimit[1] else 'Pass'])
        if TrestartList and Trestart:
            min_item = min(TrestartList, key=lambda x: x[-1])
            max_item = max(TrestartList, key=lambda x: x[-1])
            min_Vrect= min(Vrectlist, key=lambda x: x[-1])
            max_Vrect= max(Vrectlist, key=lambda x: x[-1])
            res.append([f'Measured max t_restart_after_illegal from {max_item[0]}Sec to {max_item[1]}Sec for the {DataPacketName} packet at index@ {max_item[2]} is {max_item[-1]}mS , Limit <=500', 'Fail' if  max_item[-1] > 500 else 'Pass'])
            res.append([f'Measured min t_restart_after_illegal from {min_item[0]}Sec to {min_item[1]}Sec for the {DataPacketName} packet at index@ {min_item[2]} is {min_item[-1]}mS , Limit <=500', 'Fail' if  min_item[-1] > 500 else 'Pass'])
            res.append([f"Measured max V_RECT is {max_Vrect[-1]}V at  index @ {max_Vrect[0]}, Limit <=19V", "Fail" if max_Vrect[-1] > 19 else "Pass"])
            res.append([f"Measured min V_RECT is {min_Vrect[-1]}V at  index @ {min_Vrect[0]}, Limit <=19V", "Fail" if min_Vrect[-1] > 19 else "Pass"])

        return TterminateList,res
    
    def TrestartCheck(self,DataPacketName,PktId,CoilPkpk):

        res=[]          
        NextPing_details=self.PktMethod.GetPacketDetails(packet="Ping", Type="TesterMsg",limit=[CoilPkpk[2]+1, len(self.file_list)-1])
        if len(NextPing_details)>2:
            Trestart=round(( NextPing_details[0] - CoilPkpk[1]) * 1000, 3)
            res.append([f"Measured t_restart_after_illegal from {CoilPkpk[1]}Sec to {NextPing_details[0]}Sec is {Trestart}mS at  index@ {NextPing_details[2]}, Limit <=500", "Fail" if Trestart > 500 else "Pass"])
            vrect = self.CalculateVoltTwindow(NextPing_details[2],self.AllChannelData,at="start",measure="after",winsize=[22,33])
            res.append([f"Measured  V_RECT is {vrect[0]}V at  index@ {NextPing_details[2]}, Limit <=19V", "Fail" if vrect[0] > 19 else "Pass"])
        else:
            res.append([f'PTx did not initated next ping after the packet {DataPacketName} at index@ {PktId} ','Inconclusive'])
        return res

    #Packet Payload function
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
                        res.append( [f'{'PRx'if Receiver else 'PTx'} sent the {PayLoads[Pd_id].get("Name")} field with value {actual_val} for the {PacketName} data packet , Exp:{desp}', status])
                        # res.append( [f'{'PRx'if Receiver else 'PTx'} sent the {PayLoads[Pd_id].get("Name")} Field with Val {actual_val}  for the  {PacketName} datapacket at Id @{Index}, Exp:{PayLoads[Pd_id].get("Exp")},Comp :{PayLoads[Pd_id].get("comp")}.', status])
                    Check=True
            if not Check:res.append([f'{'PRx'if Receiver else 'PTx'} did not sent expected {PayLoads[Pd_id].get("Name")} in the {PacketName} data packet at index@ {Index}, Exp:{PayLoads[Pd_id].get("Exp")} , Comp :{PayLoads[Pd_id].get("comp")}.','Fail'])   
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

    def CheckPhase(self,id,Phase):
       
        while id < self.Flow_limit[1]:
            if self.file_list[id]['description']==Phase :
                return id
            id+=1
        return None


    def LogPkts(self,Limit):
        id=Limit[0]
        LoggedPkts=[]
        while id < Limit[1]:
            Type=self.PktMethod.GetPacketType(id)
            if Type=="Packet":LoggedPkts.append([self.file_list[id]['pktType'].split("/")[0],id])
            id+=1
        return LoggedPkts
    
    # Fun to check if a packet matches expected PktType and value
    def packet_matches(self, packet_id, Pkt, PktVal):
        if PktVal is None:return Pkt in self.file_list[packet_id]['pktType'] 
        return (Pkt in self.file_list[packet_id]['pktType'] and PktVal in self.file_list[packet_id]['value'])
                
    def CECount(self,Limit=[],Packet="Control Error",value=None):
        PktsCnt=0
        id=Limit[0]
        if Limit[0] <= Limit[1]:
            while id <= Limit[1]:
                if self.PktMethod.GetPacketType(id)=='Packet':
                    if Packet in self.file_list[id]['pktType']  and value is None:PktsCnt+=1
                    elif Packet in self.file_list[id]['pktType']  and self.file_list[id]['value'] in value:PktsCnt+=1
                id+=1
        else:           
            while id > Limit[1]:
                if self.PktMethod.GetPacketType(id)=='Packet':
                    if Packet in self.file_list[id]['pktType']  and value is None:PktsCnt+=1
                    elif Packet in self.file_list[id]['pktType']  and self.file_list[id]['value'] in value:PktsCnt+=1
                id-=1         
        return PktsCnt
    
    # Fun to find the next packet of a specific type
    def findTypeid(self, limit=[], Type="Packet"):
        id=limit[0]
        
        if limit[0] <= limit[1]:
            while id <= limit[1]:
                if self.PktMethod.GetPacketType(id) == Type:
                    return id
                id+=1
        else:           
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

    def AuthSequence(self,index,Authvalue1='Challenge',Payload1=[],Authvalue2='Challenge Auth',Payload2=[],FailCheck=False):
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
                            if not self.GetAuthSeqStatus():
                                seq=True
                                results.append([f'PRx & PTx sucessfully completed Authentication {Authvalue1} Chain sequence from index@ {ADC_Auth[2]} to index@ {ADC_End_TPT[2]}', 'Pass']) 
                            else: results.append([f'Complete Data Transport stream or proper Bytes in the  Authentication sequence-{Authvalue2} is not Found', 'Inconclusive'])   
                        else:results.append([f'PTx did not closed {Authvalue2} Authentication sequence', 'Inconclusive'])                                                        
                    else:results.append([f'PTx did not initiated {Authvalue2} Authentication sequence', 'Inconclusive'])
                else:results.append([f'Prx did not closed Authentication sequence', 'Inconclusive']) 
            else:results.append([f'Prx did not sent {Authvalue1}', 'Inconclusive']) 
        else:results.append([f'Prx did not initiated Authentication:{Authvalue1} sequence', 'Inconclusive'])
        return results,id,seq
    

    def RspTimngCheck(self,ExpPktDataPacket,ExpPkt,PktorResId):
        results=[]
        ResponseIndex=3
        if ExpPkt[2]:
            res=self.Payload_Details(PacketName=ExpPktDataPacket,Index=PktorResId,PayLoads=ExpPkt[3])
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
                    results.append([f'Measured response time between {ExpPktDataPacket} and {resp[0]} is {ResponseTime}mS, Limit[3mS ≤ t_response ≤ 10mS] ','Fail'if ResponseTime < ExpPkt[ResTimngId][0]['ExpTime'][0]-ExpPkt[ResTimngId][0]['ExpTime'][1] or ResponseTime >ExpPkt[ResTimngId][0]['ExpTime'][0]+ExpPkt[ResTimngId][0]['ExpTime'][1] else "Pass"])
                RespresPkt=False
                if Responsecheck:
                    for ExpRes in ExpPkt[ResponseIndex][0]['ExpResp']: 
                        if self.packet_matches(packet_id=resp[1],Pkt=ExpRes[0],PktVal=ExpRes[1]):
                            if ExpPkt[ResponseIndex][0]['Result_check']: 
                                results.append([f'PTx responded with {resp[0]} for the {ExpPktDataPacket} data packet at index@ {PktorResId}','Pass'])
                                if ExpRes[2]:
                                    res=self.Payload_Details(PacketName=resp[0],Index=resp[1],PayLoads=ExpRes[3],Receiver=False)
                                    if len(res)>0:results.extend(res) 
                            RespresPkt=True
                        if RespresPkt:break   
                if not RespresPkt and ExpPkt[ResponseIndex][0]['Result_check'] and Responsecheck: results.append([f'PTx responded with {resp[0]} for the {ExpPktDataPacket} data packet at index@ {PktorResId}','Fail'])
            else: results.append([f'PTx did not sent any response for the {ExpPktDataPacket} data packet','Fail'])

        return results

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
        # print(VRlist)
        return [Vrectmax] if max else [round((sum(VRlist)/len(VRlist)),3), id-1]       
    
    def GetAuthPayloadDetails(self,index,name,Byte,Bit):
        try:
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
            return result if len(result)>0 else None
        except Exception as e: return None

    
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

 

    def GetPings(self,Start,Stop):
        # find Pings between Start and Stop
        pings=[]
        id=Start[2]+1
        while id < Stop[2]:
            PD = self.PktMethod.GetPacketDetails(packet='Ping Detected',Type="TesterMsg",limit=[id,Stop[2]])
            if len(PD)>2:
                SD= self.PktMethod.GetPacketDetails(packet='Shutdown',Type="TesterMsg",limit=[PD[2],Stop[2]])
                if len(SD)>2:
                    pings.append([PD[2],SD[2]])
                    id=SD[2]+1
                else:
                    pings.append([PD[2],Stop[2]])
                    break      
            else:break
        return pings
    
    def MonitorVoltage(self,startid,stopid):

        # Return the Max Voltage within the given limit 
        MaxValue = 0
        MaxIndex = 0  

        MinValue=-1
        MinIndex=0                                  
        
        while startid < stopid:
            St=self.findTypeid(limit=[startid,stopid],Type='Packet')
            if St is not None:
                resp=self.PktResponse(St+1,stopid)
                Sp=self.findTypeid(limit=[St+1,stopid],Type='Packet')
                if Sp is not None:
                    fisPkt = self.file_list[St if resp is None else resp[1]].get('stopTime')*1000
                    NextPkt = self.file_list[Sp].get('startTime')*1000
                    # #Get the max voltage received time for the start to end
                    sindex = int((fisPkt+20)/self.AllChannelData['Interval'])
                    eindex = int((NextPkt-20)/self.AllChannelData['Interval'])
                    id = sindex
                    try:
                        while id <= eindex:
                            value = round(abs(self.AllChannelData['RV']['displayDataChunk'][id]),3)
                            if value > MaxValue:
                                MaxValue=value
                                MaxIndex=id
                            else :
                                MinValue=value
                                MinIndex=id
                            id+=1
                    except Exception as e: print(id)
                    startid=Sp
                else:break
            else:break
        return [MaxIndex,MaxValue,MinIndex,MinValue]

    def GetAuthSeqStatus(self):
       # Check the Bytes seq proper or not by check the FW Assertion
        InvalidSeq=self.PktMethod.GetPacketDetails(packet="Test_Status",value="Invalid Load" ,Type="TesterMsg",limit=[len(self.file_list)-1,0])
        if len(InvalidSeq)>2: return True
        else:return False

    def CertificateChainValid(self):
        # Check Certificate Valid
        Signature=self.PktMethod.GetPacketDetails(packet="Certificate_Chain",value="Valid" ,Type="TesterMsg",limit=[0,self.Flow_limit[1]])
        if len(Signature)>2:return True
        else :return False

    def GetTemperature(self,Check):
        res=[]
        templist = []
        self.AllChannelData11= self.PlotMethod.GetAllChannelData2('12',self.JapiData)
        # print(self.AllChannelData11)
        for temp in self.AllChannelData11['RV']['displayDataChunk']:
            templist.append(temp)
        if len(templist)>0:res.append([f"Found max FOD temperature {max(templist)} °C and minimum temperature {min(templist)} °C, limit: <= {Check['expected'][0]} °C","Pass" if max(templist)<=Check['expected'][0] else 'Fail'])
        else: res.append([f"Temperature data not found","Fail"])   
        return res

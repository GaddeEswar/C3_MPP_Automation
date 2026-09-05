import traceback
import io
import zipfile
import pandas as pd
import csv
import json
import re
import math
from MainModule import JsonOperations,APIOperations,GeneralMethods
from OfflineValidationModule import PacketMethods,PlotMethods,CommonMethods
from Enums import Enums




class CommonCTSChecks:
    def __init__(self,file_list,Header,JapiData,BackupJson,Product,Mode):
        self.file_list=file_list
        self.Product=Product
        self.Mode=Mode
        self.JapiData = JapiData
        self.Header=Header
        self.PktMethod = PacketMethods(file_list,Header)
        self.PlotMethod = PlotMethods(Header)
        BKjson = JsonOperations(BackupJson)
        self.BKjsonData = BKjson.read_file()
        self.AuthPktAPI = APIOperations(url=self.JapiData[self.Product][self.Mode]['Authmeassges'],retype='json')
        self.Auth_file_list = self.AuthPktAPI.GetRequest()
        self.Certification=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SpecificationSupported']
        self.TestResultsjson = JsonOperations("json/TestResults.json")
        self.TestData = self.TestResultsjson.read_file()
        CTS = JsonOperations('json/CTSvalidation/MPPTPT.json')
        self.JCTSData =CTS.read_file()


    def XCE_Measurement(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            id=PT[2]
            Timings=[]
            Handling=[]
            FailCount=0
            PchTime,PchPkt=self.PchTime()
            PktsCount=0
            res.append([f'PRx {''if PchPkt else 'did not' } sent PCH data packet . Tdelay was set to {PchTime} mS',Enums.TestResult.PASS])
            while id < self.Flow_limit[1]:
                pkt1= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[id,self.Flow_limit[1]])
                if len(pkt1)>2:
                    PktsCount+=1
                    nextid=self.findTypeid(limit=[pkt1[2]+1,self.Flow_limit[1]],Type='Packet')
                    if nextid is not None:
                        if 'XCEP_INTERVAL' in self.Header['TestcaseID']:
                            iid=id=nextid
                            while iid < self.Flow_limit[1]:
                                pkt2= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[iid,self.Flow_limit[1]])
                                if len(pkt2)>2:
                                    Tinterval=round((pkt2[0]-pkt1[0])*1000,2)
                                    Timings.append([Tinterval,round(pkt1[2],3),round(pkt2[2],3)])
                                    if Tinterval > Check['Limit'][1] :FailCount+=1
                                    id=pkt2[2]
                                break    
                        else:
                            TDC=round((self.file_list[nextid]['startTime']-self.file_list[pkt1[2]]['stopTime'])*1000,2)
                            # result= Enums.TestResult.PASS if TDC+PchTime>=PchTime+24+19 else Enums.TestResult.FAIL
                            Handling.append([TDC,round(self.file_list[pkt1[2]]['stopTime'],3),round(self.file_list[nextid]['startTime'],3)])
                            # res.append([f'Measured Timing between XCE at {{{pkt1[2]}}} and Next Packet at {{{nextid}}} is {TDC} mS  Limit: >= {PchTime+24+19}({PchTime}+24+19) mS', result])
                            id=nextid
                    else:break
                else:break
            if 'XCEP_INTERVAL' in self.Header['TestcaseID']:
                min_item = min(Timings, key=lambda x: x[0])
                max_item = max(Timings, key=lambda x: x[0])
                if FailCount >  int(0.05 * len(Timings)):res.append([f'More than 5% of the Intervals met the fail criteria', Enums.TestResult.FAIL])
                else:res.append([f'More than 95% of the Intervals met the Pass criteria', Enums.TestResult.PASS])
                res.append([f'Measured  Max {Check['TimingCheck']} from XCE at {max_item[1]}  to XCE at {max_item[2]}  is {max_item[0]} mS , Min {Check['TimingCheck']} from XCE at {min_item[1]}  to XCE at {min_item[2]}  is {min_item[0]} mS Limit : <={Check['Limit'][1] }', Enums.TestResult.PASS])

            if 'XCEP_HANDLING' in self.Header['TestcaseID']:
                min_item = min(Handling, key=lambda x: x[0])
                max_item = max(Handling, key=lambda x: x[0])
                res.append([f'Measured  Max Interval -- txce_responsetimeout + tdelay + tcontrol from {max_item[1]} Sec to {round(max_item[2],3)} Sec is {max_item[0]} mS , Limit : >={PchTime+24+19 }', Enums.TestResult.PASS if PchTime+24+19 else Enums.TestResult.FAIL])
                res.append([f'Measured  Min Interval -- txce_responsetimeout + tdelay + tcontrol from {min_item[1]} Sec to {round(min_item[2],3)} Sec  is {min_item[0]} mS , Limit : >={PchTime+24+19 }', Enums.TestResult.PASS if PchTime+24+19 else Enums.TestResult.FAIL])

            res.append([f'PRx sent {PktsCount} {Check['Pkt'][0]} data packets Expected :{Check['PktsCount']} Pkts', Enums.TestResult.INCONCLUSIVE if PktsCount< Check['PktsCount'] else Enums.TestResult.PASS])
        else:res.append([f'PRx did not Entered PT Phase',Enums.TestResult.INCONCLUSIVE])

        return res
    
    def PLA_Handling(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            id=PT[2]
            PktsCount=0
            Timings=[]
            while id < self.Flow_limit[1]:
                pkt1= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[id,self.Flow_limit[1]])                                  
                if len(pkt1)>2:
                    PktsCount+=1
                    # Check response
                    Response=self.PktResponse(pkt1[2]+1,self.Flow_limit[1])
                    if Response is not None:res.append([f'TPT sent Response for the {Check['Pkt'][0]} Packet at {{{pkt1[2]}}} is {Response[0]}', Enums.TestResult.INCONCLUSIVE if Response[0] !="ACK" else Enums.TestResult.PASS])  
                    else:res.append([f'TPT did not sent response for the {Check['Pkt'][0]} Packet at {{{pkt1[2]}}}',Enums.TestResult.INCONCLUSIVE]) 
                    nextid=self.findTypeid(limit=[pkt1[2]+1,self.Flow_limit[1]],Type='Packet')
                    if nextid is not None :
                        TDC=round((self.file_list[nextid]['startTime']-self.file_list[pkt1[2]]['stopTime'])*1000,2)
                        Timings.append(TDC)
                        result= Enums.TestResult.PASS if TDC>=44 else Enums.TestResult.FAIL
                        res.append([f'Measured Timing between {Check['Pkt'][0]} at {{{pkt1[2]}}} and Next Packet at {{{nextid}}} is {TDC} mS  Limit: >= 44 mS', result])
                        id=nextid
                    else:break
                else:break
            #min max average.
            res.append([f"Obtained min time: {min(Timings)} and max time: {max(Timings)}", Enums.TestResult.PASS])
            if PktsCount< Check['PktsCount']:res.append([f'PRx sent {PktsCount} {Check['Pkt'][0]} data packets only', Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered PT Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def PLA_Slow_Mode(self,CTSCheck,Check,flows,flwID):
        res=[]
        # find 5 pings with 360 mode
        pings_360=self.Get360Pings("360")
        if len(pings_360)>=6:
            count=0
            for ping in pings_360:               
                if count == 0: res.append([f"Main Test", Enums.TestResult.PASS])
                elif count != 0: res.append([f'Repeat -- {count}',Enums.TestResult.PASS])
                self.Flow_limit=ping
                Nego=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: Nego", Type="TesterMsg",limit=self.Flow_limit)
                if len(Nego)>2:
                    # find Pkt
                    pkt1= self.PktMethod.GetPacketDetails(packet=Check['Pkt1'][0],value=Check['Pkt1'][1],limit=[Nego[2],self.Flow_limit[1]])
                    if len(pkt1)>2:
                        pkt2= self.PktMethod.GetPacketDetails(packet=Check['Pkt2'][0],value=Check['Pkt2'][1],limit=[pkt1[2]+1,self.Flow_limit[1]])
                        if len(pkt2)>2:
                            Timing=round((self.file_list[pkt2[2]]['startTime']-self.file_list[pkt1[2]]['startTime'])*1000,2)
                                # Check response
                            Response=self.PktResponse(pkt2[2]+1,self.Flow_limit[1])
                            if Response is not None: res.append([f'TPT sent Response for the {Check['Pkt2'][0]} at {{{pkt1[2]}}} is {Response[0]}', Enums.TestResult.INCONCLUSIVE if Response[0] !="ACK" else Enums.TestResult.PASS]) 
                            else:res.append([f'TPT did not sent response for the {Check['Pkt2'][0]} at {{{pkt1[2]}}}',Enums.TestResult.INCONCLUSIVE])              
                            res.append([f'Measured Timing between {Check['Pkt1'][0]}_{Check['Pkt1'][1]} at {{{pkt1[2]}}} and PLA at {{{pkt2[2]}}} is {Timing} mS  Limit: <={Check['limit'][1]} mS', Enums.TestResult.PASS if Timing > Check['limit'][0] and Timing <= Check['limit'][1] else Enums.TestResult.FAIL])
                        else:res.append([f'PRx did not sent {Check['Pkt1'][0]} in the Count :{count}',Enums.TestResult.INCONCLUSIVE])
                    else:res.append([f'PRx did not sent {Check['Pkt1'][0]}_{Check['Pkt1'][1]} in the Count :{count}',Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'PRx did not Entered Nego Phase in the Count :{count}',Enums.TestResult.INCONCLUSIVE])
                count += 1
        else:res.append([f'TPT did not sent Enough Pings for measurements',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def PLA_Fast_Mode(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            id=PT[2]
            PktsCount=0
            while id < self.Flow_limit[1]:
                pkt1= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[id,self.Flow_limit[1]])                                
                if len(pkt1)>2:
                    PktsCount+=1
                    # Check response
                    Response=self.PktResponse(pkt1[2]+1,self.Flow_limit[1])
                    if Response is not None:
                        result=Enums.TestResult.PASS if 'ACK' in Response[0] and PktsCount <8 else Enums.TestResult.PASS if Check['Response'] in Response[0] and PktsCount >7 else Enums.TestResult.INCONCLUSIVE
                        res.append([f'TPT sent Response for the {Check['Pkt'][0]} at {{{pkt1[2]}}} is {Response[0]}', result])  
                    else:
                        if Check['Response'] is None and PktsCount>7:res.append([f'TPT did not sent response for the {Check['Pkt'][0]} at {{{pkt1[2]}}}',Enums.TestResult.PASS])
                        else:res.append([f'TPT did not sent response for the {Check['Pkt'][0]} at {{{pkt1[2]}}}',Enums.TestResult.INCONCLUSIVE])     
                    pkt2= self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[pkt1[2]+1,self.Flow_limit[1]])
                    if len(pkt2)>2:
                        if PktsCount >7:
                            Timing=round((self.file_list[pkt2[2]]['startTime']-self.file_list[pkt1[2]]['startTime'])*1000,2)
                            res.append([f'Measured Timing between {Check['Pkt'][0]} at {{{pkt1[2]}}} and {Check['Pkt'][0]} at {{{pkt2[2]}}} is {Timing} mS  Limit: <={Check['limit'][1]} mS', Enums.TestResult.PASS if Timing > Check['limit'][0] and Timing <= Check['limit'][1] else Enums.TestResult.FAIL])
                        id=pkt2[2]
                    else:break
                else:break
            if PktsCount< Check['PktsCount']:res.append([f'PRx sent {PktsCount} {Check['Pkt'][0]} data packets only', Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered PT Phase',Enums.TestResult.INCONCLUSIVE])

        return res
                       
    def ATN_Handling(self,CTSCheck,Check,flows,flwID):
        res=[]
        pings_360=self.Get360Pings("360")
        if len(pings_360)>=7:
            count=0
            for ping in pings_360:
                self.Flow_limit=ping
                if count != 0: res.append([f'Repeat -- {count}',Enums.TestResult.PASS])
                else: res.append([f"Main Test", Enums.TestResult.PASS])
                PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
                if len(PT)>2:
                    # Check for stabilization
                    Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[PT[2],self.Flow_limit[1]])
                    if len(Stable)>2:
                        # find Pkt
                        res.append([f'PRx Stabilized at {{{Stable[2]}}}',Enums.TestResult.PASS])
                        pkt1= self.PktMethod.GetPacketDetails(packet="ATN",Type="Response",limit=[Stable[2],self.Flow_limit[1]])
                        if len(pkt1)>2:
                            pkt2=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[pkt1[2]+1,self.Flow_limit[1]])
                            if len(pkt2)>2:
                                Timing=round((self.file_list[pkt2[2]]['startTime']-self.file_list[pkt1[2]]['stopTime'])*1000,2)
                                res.append([f'Measured Timing between ATN Response at {{{pkt1[2]}}} and DSR_POLL at {{{pkt2[2]}}} is {Timing} mS  Limit:<= 500 mS', Enums.TestResult.PASS if Timing > 0 and Timing <= 500 else Enums.TestResult.FAIL])
                            else:res.append([f'PRx did not sent DSR_POLL Packet in the Count :{count}',Enums.TestResult.INCONCLUSIVE])
                        else:res.append([f'TPT did not sent ATN Response in the Count :{count}',Enums.TestResult.INCONCLUSIVE])
                    else:res.append([f'PRx did not stabilized in the Count :{count}',Enums.TestResult.INCONCLUSIVE]) 
                else:res.append([f'PRx did not Entered PT Phase in the Count :{count}',Enums.TestResult.INCONCLUSIVE])
                count+=1
        else:res.append([f'TPT did not sent Enough Pings for measurements',Enums.TestResult.INCONCLUSIVE])
        return res

    def IllegalPackets(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Fun to find mentioned data packet NOT in the Testcase.
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            id=PT[2]
            res.append([f'PRx entered in to MPP Full Mode power transfer phase at {{{PT[2]}}}',Enums.TestResult.PASS])
            IllegalPkts=False
            EndPower=False
            count=0
            CEpkts=True
            while id < self.Flow_limit[1]:
                
                if count>=200:break
                if self.file_list[id]['pktType'] in Check['Pkts']:
                    IllegalPkts=True
                    res.append([f'PRx sent the Data Packet :{self.file_list[id]['pktType']} at {{{id}}}',Enums.TestResult.FAIL])
                if self.file_list[id]['pktType'] in ["Extended Control Error", "Power Loss Accounting"]:
                    Response=self.PktResponse(id+1,self.Flow_limit[1])
                    if Response is not None:
                        if "NAK" in Response[0]:
                            res.append([f'TPT sent NAK Response for the {self.file_list[id]['pktType']} Pkt at  {{{id}}}',Enums.TestResult.INCONCLUSIVE]) 
                            CEpkts=False
                    else:  res.append([f'TPT did not sent Response  for the {self.file_list[id]['pktType']} Pkt at  {{{id}}}',Enums.TestResult.INCONCLUSIVE]) 
                    if self.file_list[id]['pktType']=="Extended Control Error":count+=1
                if self.file_list[id]['pktType'] in ['End Power Transfer']:
                        res.append([f'PRx sent End Power Transfer Pkt at {{{id}}}',Enums.TestResult.PASS])
                        EndPower=True
                        break
                id+=1
            if CEpkts:res.append([f'TPT sent ACK Response for all XCE and PLA Packets',Enums.TestResult.PASS])
            if not IllegalPkts:res.append([f'PRx did not sent any Packets in the List :{Check['Pkts']}',Enums.TestResult.PASS])
            if not EndPower :res.append([f'PRx sent {count} XCE Packets Expected :>=200',Enums.TestResult.PASS if count >=200 else Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered MPP Full Mode power transfer phase',Enums.TestResult.INCONCLUSIVE])
        return res
    def TnegTransition(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # check the Restricted Bit
        MPP=self.PktMethod.GetPacketDetails(packet=Check['XID'], limit=self.Flow_limit)
        if len(MPP)>2:
            RestrictedBit=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(MPP[2],'Restricted')[0]['sRawData'])
            if RestrictedBit==1:
                PchTime,PchPkt=self.PchTime()
                res.append([f'PRx set Restricted Bit to One in the MPP-Extended Identification Packet at {{{MPP[2]}}}',Enums.TestResult.PASS])
                res.append([f'PRx {''if PchPkt else 'did not' } sent PCH data packet with Power Control Hold Off Time:{PchTime} mS',Enums.TestResult.PASS])
                End_Power=self.PktMethod.GetPacketDetails(packet="End Power Transfer", value= "[EPT/rst]",limit=[MPP[2]+1,self.Flow_limit[1]])
                if len(End_Power)<2:
                    res.append([f'PRx did not sent End Power Tranfer Packet _RST ',Enums.TestResult.PASS])
                    # find Renegotiate
                    Renego=self.PktMethod.GetPacketDetails(packet="Renegotiate", limit=[MPP[2],self.Flow_limit[1]])
                    if len(Renego)<2:res.append([f'PRx did not sent Renegotiate Packet to Switch from Restricted Mode to MPP-Full Mode',Enums.TestResult.INCONCLUSIVE])
                    else:
                        # find Renego Seq Packets
                        SRQ_En=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="End Negotiation", limit=[Renego[2],self.Flow_limit[1]])
                        if len(SRQ_En)<2:res.append([f'PRx did not Completed Renegotiation Sequence by not sending SRQ/En packet',Enums.TestResult.INCONCLUSIVE])
                        else:
                            results=self.CheckPkts(Renego[2]+1,SRQ_En[2],Check['Pkts'])
                            if len(results)>0:res.extend(results)
                            # find TnegTransition Timing
                            Response=self.PktResponse(SRQ_En[2]+1,self.Flow_limit[1])
                            if Response is not None:
                                res.append([f'TPT sent Response for the SRQ/End Negotiation at {{{SRQ_En[2]}}} is {Response[0]}', Enums.TestResult.INCONCLUSIVE if Response[0] !="ACK" else Enums.TestResult.PASS])  
                                Timing=round((self.file_list[Response[1]]['stopTime']-Renego[1])*1000,2)
                                res.append([f'Measured TnegTransition Timing from end of Packet at {{{Renego[2]}}} to Id at {{{Response[1]}}} is {Timing} mS Limit:<={Check['limit'][1]}',Enums.TestResult.PASS if Timing >Check['limit'][0] and Timing <= Check['limit'][1] else Enums.TestResult.FAIL])
                            else:res.append([f'TPT did not sent response for the SRQ/End Negotiation at {{{SRQ_En[2]}}}',Enums.TestResult.INCONCLUSIVE]) 
                else:res.append([f'PRx sent End Power Tranfer Packet _RST to Switch from Restricted Mode to MPP-Full Mode',Enums.TestResult.PASS])
            else:res.append([f'PRx did not set Restricted Bit to One in the MPP-Extended Identification Packet',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not sent MPP-Extended Identification Packet',Enums.TestResult.INCONCLUSIVE])
        return res
    def EPTR(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
            # Check for stabilization
        Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=self.Flow_limit)
        if len(Stable)>2:
            res.append([f'PRx Stablized at {{{Stable[2]}}}',Enums.TestResult.PASS])
            # Check ATN response for XCE packet 
            xce=self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[Stable[2],self.Flow_limit[1]])
            if len(xce)>2:
                # Check response
                Response=self.PktResponse(xce[2]+1,self.Flow_limit[1])
                if Response is not None:
                    res.append([f'TPT sent Response --{Response[0]} for the XCE Packet at {{{xce[2]}}}',Enums.TestResult.PASS if Response[0]=="ATN" else Enums.TestResult.INCONCLUSIVE])  
                else:res.append([f'TPT did not sent response for the XCE Packet at {{{xce[2]}}}',Enums.TestResult.INCONCLUSIVE]) 
                # check DSRPOll
                DSR=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[xce[2]+1,self.Flow_limit[1]])
                if len(DSR)>2:
                    # Check response
                    Response=self.PktResponse(DSR[2]+1,self.Flow_limit[1])
                    if Response is not None:
                        res.append([f'TPT sent Response as {Response[0]} for the DSR_POLL Packet at {{{DSR[2]}}}',Enums.TestResult.PASS if Response[0]=="EPTR [0x0A] " else Enums.TestResult.INCONCLUSIVE])
                            # find EPT Packet
                        End_Power=self.PktMethod.GetPacketDetails(packet="End Power Transfer", value= "[EPT/pmc]",limit=[Response[1]+1,self.Flow_limit[1]])
                        if len(End_Power)<2:
                            res.append([f'PRx did not sent EPT/pmc Packet',Enums.TestResult.FAIL])
                        else:
                            res.append([f'PRx sent EPT/pmc Packet at {{{End_Power[2]}}}',Enums.TestResult.PASS])
                            Timing=round((End_Power[0]-self.file_list[Response[1]]['startTime'])*1000,2)
                            res.append([f'Measured t_eptc Timing from end of Packet at {{{Response[1]}}} to Id at {{{End_Power[2]}}} is {Timing} mS Limit:<={Check['limit'][1]}',Enums.TestResult.PASS if Timing >Check['limit'][0] and Timing <= Check['limit'][1] else Enums.TestResult.FAIL])
                    else:res.append([f'TPT did not sent Response  for the DSR_POLL Packet at {{{DSR[2]}}}', Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'PRx did not sent DSR_POLL Packet ',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'Test did not found XCE-ATN sequence after Stabilization at {{{Stable[2]}}}',Enums.TestResult.INCONCLUSIVE]) 
        else: res.append([f'PRx did not stabilized ',Enums.TestResult.INCONCLUSIVE])
        return res

    def CAL_Pending(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # check Cal op Commit
        Cal_CMT=self.PktMethod.GetPacketDetails(packet="CAL_OP [0x23] ",value="Operation: CMT", limit=self.Flow_limit)
        if len(Cal_CMT)>2:
            res.append([f'PRx sent CAL_OP [COMMIT] data packet at {{{Cal_CMT[2]}}}',Enums.TestResult.PASS])
            # Check response for the CAL COMMIT
            Response=self.PktResponse(Cal_CMT[2]+1,self.Flow_limit[1])
            if Response is not None:
                result=Enums.TestResult.PASS if "CAL_OP_RSP [0x1B]" in self.file_list[Response[1]]['pktType'] and "Status: PENDING" in self.file_list[Response[1]]['value'] else Enums.TestResult.INCONCLUSIVE
                res.append([f'TPT  sent Response as {Response[0]}_{self.file_list[Response[1]]['value']} for the CAL_OP [COMMIT] Packet at {{{Cal_CMT[2]}}}', result])
                # Check next CAL COMMIT Pksts till CAL EXIT
                Cal_Exit=self.PktMethod.GetPacketDetails(packet="CAL_EXIT [0x2D]", limit=[self.Flow_limit[1],Cal_CMT[2]])
                if len(Cal_Exit)<2:res.append([f'PRx did not sent CAL[Exit] data packet ',Enums.TestResult.INCONCLUSIVE])
                else:
                    
                    id=Cal_CMT[2]+1
                    Pktfound=False
                    while id < Cal_Exit[2]:
                        Cal_CMT_Next=self.PktMethod.GetPacketDetails(packet="CAL_OP [0x23] ",value="Operation: CMT", limit=[id,Cal_Exit[2]])
                        if len(Cal_CMT_Next)>2:
                            Pktfound=True
                            res.append([f'PRx sent CAL_OP [COMMIT] data packet at {{{Cal_CMT_Next[2]}}}',Enums.TestResult.PASS])
                            Response=self.PktResponse(Cal_CMT_Next[2]+1,self.Flow_limit[1])
                            if Response is not None:
                                result=Enums.TestResult.PASS if "CAL_OP_RSP [0x1B]" in self.file_list[Response[1]]['pktType'] and "Status: ACCEPTED" in self.file_list[Response[1]]['value'] else Enums.TestResult.INCONCLUSIVE
                                res.append([f'TPT  sent Response as {Response[0]}_{self.file_list[Response[1]]['value']} for the CAL_OP[COMMIT] Packet at {{{Cal_CMT[2]}}}', result])
                            else:res.append([f'TPT did not sent Response  for the CAL_OP [COMMIT] Packet at {{{Cal_CMT[2]}}}', Enums.TestResult.INCONCLUSIVE])
                            id=Cal_CMT_Next[2]+1
                        else:break
                    if not Pktfound:
                        # Check the ATN,DSR/poll,CAL_OP_RSP[Status = ACCEPTED] if there is not  CAL_OP COMMIT pkt
                        seqFound=False
                        i=Cal_CMT[2]+1
                        while i <  Cal_Exit[2]:
                            Resid=self.findTypeid(limit=[i,Cal_Exit[2]],Type='Response')
                            if Resid is not None:
                                if 'ATN' in self.file_list[Resid]['pktType']:
                                    Pktid=self.findTypeid(limit=[Resid+1,Cal_Exit[2]],Type='Packet')
                                    if Pktid is not None:
                                        if 'DSR' in self.file_list[Pktid]['pktType'] and 'POLL' in self.file_list[Pktid]['value']:
                                            TPTid=self.findTypeid(limit=[Pktid+1,Cal_Exit[2]],Type='Response')
                                            if TPTid is not None:
                                                if "CAL_OP_RSP [0x1B]" in  self.file_list[TPTid]['pktType'] and "Status: ACCEPTED" in self.file_list[TPTid]['value']:
                                                    res.append([f'TPT sent CAL_OP_RSP Accepted Respponse at {{{TPTid}}} for ATN-DSR/POLL Sequence',Enums.TestResult.PASS])
                                                    seqFound=True
                                                i=TPTid+1
                                            else:break
                                        i=Pktid+1
                                    else:break
                                i=Resid+1
                            else:break
                   
                        if not seqFound:res.append([f'PRx did not sent the CAL_OP [COMMIT] Packets before CAL EXIT PKt at {{{Cal_Exit[2]}}}', Enums.TestResult.INCONCLUSIVE])
                    res.append([f'PRx sent CAL[Exit] data packet at {{{Cal_Exit[2]}}}',Enums.TestResult.PASS])
            else:res.append([f'TPT did not sent Response  for the CAL_OP COMMIT] Packet at {{{Cal_CMT[2]}}}', Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not sent CAL_OP [COMMIT] data packet ',Enums.TestResult.INCONCLUSIVE])
        return res

    def Q_Deflection(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CoilPlace=False
        Values={"Before":{"Q_Open":[],"F_Open":[]},"After":{"Q_mated":[],"F_mated":[]}}
        CTx=0
        id=0
        while id < len(self.file_list):
            if 'Ctx_Cclamp' in self.file_list[id]['pktType']: CTx= float(self.file_list[id]['pktType'].split('|')[1].split(';')[0].replace("nF",''))
            elif "Coil_Place_On_Base_Station" in self.file_list[id]['pktType']: CoilPlace=True
            elif "QMeasured Value"  in self.file_list[id]['pktType']:
                value = float(self.file_list[id]['pktType'] .split('|')[1] .replace(';', '').strip() )
                Values["After" if CoilPlace else "Before"][ "Q_mated" if CoilPlace else "Q_Open" ].append(value)
            elif 'Resonant_frequency' in self.file_list[id]['pktType']:
                value = float(self.file_list[id]['pktType'] .split('|')[1] .replace(';', '').strip() )
                Values["After" if CoilPlace else "Before"]["F_mated" if CoilPlace else "F_Open"].append(value)
            id+=1
        # Calcualte Obtained Values from Assertions
        Q_Open= round(sum(Values['Before']['Q_Open'])/len(Values['Before']['Q_Open']),3)
        Q_Mated=round(sum(Values['After']['Q_mated'])/len(Values['After']['Q_mated']),3)
        F_Open=round(sum(Values['Before']['F_Open'])/len(Values['Before']['F_Open']),3)
        F_Mated=round(sum(Values['After']['F_mated'])/len(Values['After']['F_mated']),3)
        # Assuming CTx will always be in nF and Frquency in kHz
        Q_Updated_open = Q_Open / ( 1 - ( 2 * math.pi * F_Open * 1000 * CTx * (10**-9) * 0.150 * Q_Open ) )
        Q_Updated_Mated = Q_Mated / ( 1 - ( 2 * math.pi * F_Mated * 1000 * CTx * (10**-9) * ( ( 0.0003 * F_Mated ) + 0.0679 ) * Q_Mated ) )
        # Find Q-Deflection
        Q_Deflection=round((1-(Q_Updated_Mated/Q_Updated_open))*100,3)
        res.append([f'Measured Q-Open is {round(Q_Updated_open,3)}',Enums.TestResult.PASS ])
        res.append([f'Measured Q-PRx is {round(Q_Updated_Mated,3)}',Enums.TestResult.PASS ])
        res.append([f'Measured Q-Deflection is {Q_Deflection} % , Expected :>20%',Enums.TestResult.PASS if Q_Deflection >20 else Enums.TestResult.FAIL])
        return res
    
    
                       
    def DPLoss_Valid(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            CAL_ENTER=self.PktMethod.GetPacketDetails(packet="CAL_ENTER_RSP [0x34] ",value="Reason: NO_ERR", Type="Response",limit=[PT[2],self.Flow_limit[1]])
            if len(CAL_ENTER)>2:
                res.append([f'TPT sent CAL_ENTER_RSP data packet at {{{CAL_ENTER[2]}}} ',Enums.TestResult.PASS])
                Cal_Exit=self.PktMethod.GetPacketDetails(packet="CAL_EXIT [0x2D]", limit=[CAL_ENTER[2],self.Flow_limit[1]])
                if len(Cal_Exit)<2:res.append([f'TPT did not sent CAL[Exit] data packet ',Enums.TestResult.INCONCLUSIVE])
                else:
                    # Update Negotiable Load Power in ECAP Pkt
                    EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
                    ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=[CAL_ENTER[2],Cal_Exit[2]])
                    if len(ECAP)>2:
                        GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                        NPowerCal = math.floor(((Check['Percentage']/100) * GPower) * 10) / 10
                        NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                        res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
                    else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])
                    res.append([f'PRx sent CAL[Exit]  data packet at {{{Cal_Exit[2]}}} ',Enums.TestResult.PASS])
                    #Measure Tcal Timing
                    Tcal=round((Cal_Exit[0]-CAL_ENTER[1])*1000,2)
                    res.append([f'Measured Tcal is {round(Tcal/(1000*60),3)} mins Expected <=5Mins',Enums.TestResult.PASS if Tcal <=300000 else Enums.TestResult.FAIL])
                    PrectVals=self.PrectValues(limit=[CAL_ENTER[2],Cal_Exit[2]])
                    res.append([f'No of Calibrations Points Received is {len(PrectVals)} Expected >=60',Enums.TestResult.PASS if len(PrectVals)>=60 else Enums.TestResult.FAIL])
                    # Group PRECT Values
                    Levels=self.Group_PRECT(PrectVals)
                    for Level in Levels.keys():
                        res.append([f'No of Points Received in PRECT LEVEL {Level} is {len(Levels[Level])} Expected >=18',Enums.TestResult.PASS if len(Levels[Level])>=18 else Enums.TestResult.FAIL])
                    res.append([f'Measured PRECT_Max is {max(PrectVals)} W and PRECT_Min is {min(PrectVals)} W . The Difference is {round((max(PrectVals)-min(PrectVals)),3)} W Expected >=5W',Enums.TestResult.PASS if (max(PrectVals)-min(PrectVals))>=5 else Enums.TestResult.FAIL])
                    # Validate DPLOSS Values
                    Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[Cal_Exit[2]+1,self.Flow_limit[1]])
                    if len(Stable)>2:
                        DplossVals=self.DplossValues(limit=[Stable[2]+1,self.Flow_limit[1]])
                        DPlossFlag=True
                        for val in DplossVals:
                            if -385.0 < val*1000 <= 385.0:continue
                            else:
                                DPlossFlag=False
                                res.append([f'Measured ΔPLOSS Value is {val} Limit :-385 mW to +385 mW',Enums.TestResult.FAIL])
                        if DPlossFlag: res.append([f'Measured Max ΔPLOSS Value is {max(DplossVals)} and min ΔPLOSS Value is {min(DplossVals)} Limit :-385 mW to +385 mW',Enums.TestResult.PASS])
                        
                        try: # check the power reached Target Load or not
                            pid=Stable[2]+1
                            FalseFlag=False
                            NpLimit=[round(NPowerCal-(NPowerCal*(10/100)),3),round(NPowerCal+(NPowerCal*(10/100)),3)]
                            print("Target NPlimit",NpLimit)
                            while pid < self.Flow_limit[1]:
                                TPLA=self.PktMethod.GetPacketDetails(packet='PLA_2 [0x88]',limit=[pid,self.Flow_limit[1]])
                                if len(TPLA)>2:
                                    TPRECT=float(self.file_list[TPLA[2]]['value'].split("|")[1].split(":")[1].replace("W",""))
                                    if TPRECT  < NpLimit[0]  or TPRECT > NpLimit[1]:
                                        res.append ([f'Observed PRECT power  in PLA2 Packet at {{{pid}}} is {TPRECT}W Expected Target Load : {NpLimit[0]} W -{NpLimit[1]} W ',Enums.TestResult.INCONCLUSIVE])
                                        FalseFlag=True
                                    pid=TPLA[2]+1
                                else:break
                            if not FalseFlag:res.append([f'ALL PRECT Values in PLA2 Packets are within 10% of  Target Load power : {NPowerCal} W i.e {NpLimit[0]} W ~ {NpLimit[1]} W after the Stabilization  ',Enums.TestResult.PASS])
                        except Exception as e:
                            res.append([f'Error while Check Target Load : {e}', Enums.TestResult.INCONCLUSIVE])

                        # Check run Time
                        RunTime=round((self.file_list[self.Flow_limit[1]]['startTime']-Stable[1])*1000,3)
                        res.append([f'Test Executed for {round(RunTime/(1000*60),3)} mins after Stabilization at {{{Stable[2]}}}, Exp :> 5mins',Enums.TestResult.INCONCLUSIVE if RunTime <300000 else Enums.TestResult.PASS])

                    else:res.append([f'PRx did not stabilized ',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'PRx did not Started DPLOSS Calibration by not sending CAL ENTER Pkt ',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered PT Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    
                          
    def Kest_Measure(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        KestMsg=self.PktMethod.GetPacketDetails(packet="K_est Value",Type="TesterMsg", limit=[0,len(self.file_list)-1])
        if len(KestMsg)>2:
            KestVal=float(self.file_list[KestMsg[2]]['pktType'].split("|")[1].replace(";",""))
            if 'P1' in self.Header['TestcaseID']:
                Kest=self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel']['kiActual_P1']
            else:Kest=self.BKjsonData['testBkpProjectConfiguration']['TesterConfigurationModel']['kiActual_P2']
            K_Error = round(abs(Kest - KestVal) / Kest,3)
            if Check['Response']:
                CFG=self.PktMethod.GetPacketDetails(packet="Configuration", limit=[0,len(self.file_list)-1])
                if len(CFG)>2:
                    # Check Response for CFG
                    Response=self.PktResponse(CFG[2]+1,self.Flow_limit[1])
                    if Response is not None:
                        res.append([f'TPT sent Response :{Response[0]} for the CFG data packet at {{{CFG[2]}}} ',Enums.TestResult.PASS if "NAK" in Response[0] else Enums.TestResult.INCONCLUSIVE])  
                        # Check KEST Pkt
                        KEST=self.PktMethod.GetPacketDetails(packet="KEST-COEFF [0x50]", limit=[CFG[2]+1,len(self.file_list)-1])
                        res.append([f'PRx {"" if len(KEST)>2 else "did not"} sent KEST-COEFF [0x50] data Packet {f"at {{{KEST[2]}}}" if len(KEST)>2 else ''}',Enums.TestResult.PASS if len(KEST)>2 else Enums.TestResult.INCONCLUSIVE])
                    else:res.append([f'TPT did not sent Response for the CFG data packet at {{{CFG[2]}}} ',Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'PRx did not sent Configuration data packet ',Enums.TestResult.INCONCLUSIVE])
            res.append([f'Measured K_est Val:{KestVal} , SDF Ki_Actual is :{Kest} ',Enums.TestResult.PASS])   
            res.append([f'Calculated K_est Error is :{K_Error} , Limit : <0.06 ',Enums.TestResult.PASS if K_Error <0.06 else Enums.TestResult.FAIL])   
        else:res.append([f'Did not found Kest Val in the Sequence',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def Load_RNEG(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            res.append([f'PRx entered Power Transfer Phase at {{{PT[2]}}}',Enums.TestResult.PASS])
            Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[PT[2],self.Flow_limit[1]])
            if len(Stable)>2:
                res.append([f'PRx Control Stabilized at {{{Stable[2]}}}',Enums.TestResult.PASS])
                Throttle_Start=self.PktMethod.GetPacketDetails(packet="Throttling_Power_Started",Type="TesterMsg",limit=[Stable[2]+1,self.Flow_limit[1]])
                if len(Throttle_Start)>2:
                    Throttle_End=self.PktMethod.GetPacketDetails(packet="Throttling_Power_Stopped",Type="TesterMsg",limit=[Throttle_Start[2]+1,self.Flow_limit[1]])
                    if len(Throttle_End)>2:
                        RecivedPowerVals,PrectVals=self.PLA_RRP_Prect(Check['Pkt'][0],limit=[Stable[2]+1,Throttle_Start[2]],Target=10)
                        PrectInitial=round(sum(PrectVals)/len(PrectVals),3)
                        res.append([f'Measured Avearge Rectified Power Prect_Initial is {PrectInitial} W for 10 PLA Packets',Enums.TestResult.PASS])
                        res.append([f'Throttle started at {{{Throttle_Start[2]}}}',Enums.TestResult.PASS])
                        # Check NAK Response for the PLA2 and XCE Packets
                        res.append([f'--------------- Verify The NAK Response from TPT during Throttle ---------------',Enums.TestResult.PASS])
                        result=self.CheckResponseForPkts(limit=[Throttle_Start[2]+1,Throttle_End[2]+1],pkts=[["Extended Control Error",None,"NAK"],[Check['Pkt'][0],None,"NAK"]])
                        if len(result)>0:res.extend(result)
                        # Check PLA_Fast Timing during Throttle
                        Tres=self.PLA2_Fast(Check['Pkt'][0],limit=[Throttle_Start[2]+1,Throttle_End[2]+1],TimeLimit=["LTE",300],Percentage=50)
                        if len(Tres)>0:res.extend(Tres)
                        res.append([f'Throttle Ended at {{{Throttle_End[2]}}}',Enums.TestResult.PASS])
                        # find Stabilization After Throttle
                        Stable2=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[Throttle_End[2]+1,self.Flow_limit[1]])
                        if len(Stable2)>2:
                            res.append([f'PRx Stabilized  at {{{Stable2[2]}}} after Throttle',Enums.TestResult.PASS])
                            # check ECAP response from TPT
                            EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
                            ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=[Stable2[2]+1,self.Flow_limit[1]])
                            if len(ECAP)<2:res.append([f'ECAP packet did not found after Throtlling',Enums.TestResult.INCONCLUSIVE])
                            else:
                                res.append([f'TPT sent ECAP Packet at {{{ECAP[2]}}} after Throtlling', Enums.TestResult.PASS])
                                NPower=float((self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10)
                                res.append([f'TPT set Negotiable Power to {NPower} W in ECAP packet',Enums.TestResult.PASS if abs(NPower-(PrectInitial/2))<0.5 else Enums.TestResult.INCONCLUSIVE])
                                # Check ACK Response for the PLA2 and XCE Packets
                                res.append([f'--------------- Verify The ACK Response from TPT after Renegotiation ---------------',Enums.TestResult.PASS])
                                result=self.CheckResponseForPkts(limit=[ECAP[2]+1,self.Flow_limit[1]],pkts=[["Extended Control Error",None,"ACK"],[Check['Pkt'][0],None,"ACK"]])
                                if len(result)>0:res.extend(result)
                                    # find Stabilization After renegotiate
                                Stable3=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[ECAP[2]+1,self.Flow_limit[1]])
                                res.append([f'Power {"did not" if len(Stable3)<2 else ''} Stabilized after ReNegotaition Phase ',Enums.TestResult.INCONCLUSIVE if len(Stable3)<2 else Enums.TestResult.PASS])  
                        else:res.append([f'Power did not Stabilized after Throttling ',Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'Throttling has not been Initialized',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'PRx did not stabilized to Negotiable Load Power',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered PT Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def MatedQ(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']

        MatedQ=self.PktMethod.GetPacketDetails(packet="MATEDQ-COEFF [0xA8] ", limit=self.Flow_limit)
        if len(MatedQ)>2:
            Vals=self.file_list[MatedQ[2]]['value'].removeprefix("-").replace("{","").replace("}","")
            res.append([f'PRx sent MATEDQ-COEFF [0xA8]  data packet with Prameters :{Vals} ',Enums.TestResult.PASS])
            # find TX MatedQ
            MatedQRes=self.PktMethod.GetPacketDetails(packet="MatedQ_Result ", Type="TesterMsg",limit=[MatedQ[2]+1,self.Flow_limit[1]])
            if len(MatedQRes)>2:
                value=self.file_list[MatedQRes[2]]['pktType'].split(':')[1].split('|')[0]
                res.append([f'PTx sent MATEDQ Result :{value} ',Enums.TestResult.PASS if "FO detected" in value else Enums.TestResult.FAIL])
            else:res.append([f'PTx did not sent MATEDQ Result ',Enums.TestResult.INCONCLUSIVE])  

            # Tx_MatedQ=self.PktMethod.GetPacketDetails(packet="MATEDQ_RES [0x40]", Type="Response",limit=[MatedQ[2]+1,self.Flow_limit[1]])
            # if len(Tx_MatedQ)>2:
            #     Value=self.file_list[Tx_MatedQ[2]]['value'].split(":")[1].replace("}","")
            #     res.append([f'PTx sent MATEDQ_RES [0x40]  data packet with Result :{Value} ',Enums.TestResult.PASS if "Foreign Object Detected" in Value else Enums.TestResult.FAIL])
            # else:res.append([f'PTx did not sent MATEDQ_RES [0x40]  data packet ',Enums.TestResult.INCONCLUSIVE])  
        else:res.append([f'PRx did not sent MATEDQ-COEFF [0xA8]  data packet ',Enums.TestResult.FAIL])
        return res
    
    def ErrorStatus(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        CFG=self.PktMethod.GetPacketDetails(packet="Configuration", limit=self.Flow_limit)
        if len(CFG)>2:
            # Check Response for CFG
            Response=self.PktResponse(CFG[2]+1,self.Flow_limit[1])
            if Response is not None:
                res.append([f'TPT sent Response :{Response[0]} for the CFG data packet at {{{CFG[2]}}} ',Enums.TestResult.PASS if "NAK" in Response[0] else Enums.TestResult.INCONCLUSIVE])
                # Check PRx GET Error Status
                Get_Error=self.PktMethod.GetPacketDetails(packet="Get Request",value="PTx Error Status", limit=[CFG[2]+1,self.Flow_limit[1]])
                if len(Get_Error)>2:
                    Response=self.PktResponse(Get_Error[2]+1,self.Flow_limit[1])
                    if Response is not None:
                        res.append([f'TPT sent Response :{Response[0]} for the GET[Error Status] data packet at {{{Get_Error[2]}}} ',Enums.TestResult.PASS if Response[0]=="PTx Error status" else Enums.TestResult.INCONCLUSIVE])
                        result=self.Payload_Details(PacketName=Response[0],Index=Response[1],PayLoads=Check['PTx'],Receiver=False)  
                        if len(result)>0:res.extend(result)   
                    else:res.append([f'TPT did not sent Response for the a GET[Error Status] data packet at {{{Get_Error[2]}}} ',Enums.TestResult.INCONCLUSIVE])
                
                if 'MPP1' in self.Header['Coil']:
                    # Check EPT packet
                    EPT=self.PktMethod.GetPacketDetails(packet="End Power Transfer",value="[EPT/rst]", limit=[CFG[2]+1,self.Flow_limit[1]])
                    res.append([f'PRx {"" if len(EPT)>2 else "did not"} sent EPT/rst data Packet {f"at {{{EPT[2]}}}" if len(EPT)>2 else ''}',Enums.TestResult.PASS if len(EPT)>2 else Enums.TestResult.FAIL])
                    # Check End Negotiation is not present
                    SRQ_En=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="End Negotiation", limit=[CFG[2]+1,self.Flow_limit[1]])
                    res.append([f'PRx {"" if len(SRQ_En)>2 else "did not"} sent SRQ/en data Packet {f"at {{{SRQ_En[2]}}}" if len(SRQ_En)>2 else ''} ',Enums.TestResult.FAIL if len(SRQ_En)>2 else Enums.TestResult.PASS])
                else:
                    # Check KEST Coefficients
                    KEST=self.PktMethod.GetPacketDetails(packet="KEST-COEFF [0x50]", limit=[CFG[2]+1,self.Flow_limit[1]])
                    if len(KEST)>2:
                        result=self.Payload_Details(PacketName="KEST_COEFF",Index=KEST[2],PayLoads=Check['PRx'])
                        if len(result)>0:res.extend(result)  
                    else:res.append([f'PRx did not sent KEST_COEFF data packet ',Enums.TestResult.FAIL])
            else:res.append([f'TPT did not sent Response for the CFG data packet at {{{CFG[2]}}} ',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not sent Configuration data packet ',Enums.TestResult.INCONCLUSIVE])
        return res

    def SwitchingReset(self,CTSCheck,Check,flows,flwID):
        res=[]
        pings_128=self.Get360Pings("128")
        if len(pings_128)>=2:
            ping1,ping2=pings_128[0],pings_128[1]
            # Respond ACK to SRQ/Fre sel in Ping1
            SRQ_FS=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Frequency Selection", limit=ping1)
            if len(SRQ_FS)>2:
                Response=self.PktResponse(SRQ_FS[2]+1,ping1[1])
                if Response is not None:res.append([f'TPT sent Response :{Response[0]} for the  SRQ/freqsel data packet at {{{SRQ_FS[2]}}} ',Enums.TestResult.PASS if Response[0]=="ACK" else Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'TPT did not sent Response for the SRQ/freqsel  data packet at {{{SRQ_FS[2]}}} ',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'PRx did not sent SRQ/freqsel data packet ',Enums.TestResult.INCONCLUSIVE])
            #Check CFG Response and BPP packets
            CFG=self.PktMethod.GetPacketDetails(packet="Configuration", limit=ping2)
            if len(CFG)>2:
                res.append([f'TPT removed Power signal at {{{ping1[1]}}} and re-enters Ping Phase at {{{ping2[0]}}}',Enums.TestResult.PASS])
                Response=self.PktResponse(CFG[2]+1,ping2[1])
                if Response is not None:
                    res.append([f'TPT sent Response :{Response[0]} for the CFG data packet at {{{CFG[2]}}} ',Enums.TestResult.PASS if "ACK" in Response[0] else Enums.TestResult.INCONCLUSIVE])
                    # Check BPP Pkts after CFG
                    CE=self.PktMethod.GetPacketDetails(packet="Control Error", limit=ping2)
                    res.append([f'PRx {"" if len(CE)>2 else "did not"} entered BPP Phase {f"at {{{CE[2]}}}" if len(CE)>2 else ''}',Enums.TestResult.PASS if len(CE)>2 else Enums.TestResult.FAIL])
                else:res.append([f'TPT did not sent Response for the CFG data packet at {{{CFG[2]}}} ',Enums.TestResult.INCONCLUSIVE])   
            else:res.append([f'PRx did not sent Configuration data packet in the Flow',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'Test did not found sufficient pings to validate Measurements',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def SRQ_Select(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"Nego")   
        if PhaseLimit is not None:
            if Check['flow']==1:
                SRQ_FS=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Frequency Selection", limit=PhaseLimit)
                if len(SRQ_FS)>2:
                    result=self.Payload_Details(PacketName="SRQ/freqsel",Index=SRQ_FS[2],PayLoads=Check['PRx'])
                    if len(result)>0:res.extend(result)       
                else:res.append([f'PRx did not sent SRQ/freqsel Pkt',Enums.TestResult.FAIL])
                # Check End Negotiation is not present
                SRQ_En=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="End Negotiation", limit=PhaseLimit)
                res.append([f'PRx {"" if len(SRQ_En)>2 else "did not"} sent SRQ/en data Packet {f"at {{{SRQ_En[2]}}}" if len(SRQ_En)>2 else ''} ',Enums.TestResult.PASS if len(SRQ_En)>2 else Enums.TestResult.FAIL])
                
                EPT=self.PktMethod.GetPacketDetails(packet="End Power Transfer",value="[EPT/rep]", limit=self.Flow_limit)
                res.append([f'PRx {"" if len(EPT)>2 else "did not"} sent EPT/rep data Packet {f"at {{{EPT[2]}}}" if len(EPT)>2 else ''}',Enums.TestResult.PASS if len(EPT)>2 else Enums.TestResult.FAIL])
            else:
                # check Nego Pkts
                result=self.NegoValidate(PhaseLimit,Check['NegPkts'])
                if len(result)>0:
                    res.append([f'----------- Nego Phase Validation -----------',Enums.TestResult.PASS])
                    res.extend(result)
                result=self.CheckPkts(PhaseLimit[0],PhaseLimit[1],Check['Pkts'])
                if len(result)>0:
                    res.append([f'----------- Pass Criteria Check ------------',Enums.TestResult.PASS])
                    res.extend(result)

        else:res.append([f'PRx did not entered in to Nego Phase',Enums.TestResult.INCONCLUSIVE])
        return res

    def Response_Valid_Device(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']                   
        # Update Negotiable Load Power in ECAP Pkt
        EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
        ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=self.Flow_limit)
        if len(ECAP)>2:
            GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
            NPowerCal = math.floor(((Check['Percentage']/100) * min(15, GPower)) * 10) / 10
            NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
            res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
        else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])

        # Check Enterred to PowerTransfer Phase
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
        if PhaseLimit is not None:
            if Check.get("Cloak",False): # Check Entered to Cloak Phase or not
                Cloak=self.PktMethod.GetPacketDetails(packet="Cloak",limit=[PhaseLimit[0]+1,self.Flow_limit[1]])
                if len(Cloak)>2:
                    res.append([f'PRx Entered in to Cloak Mode', Enums.TestResult.PASS])
                else:
                    result,PowerVals=self.PLA_MSR(NegotiablePower=NPower,Check=Check,limit=[PhaseLimit[0],self.Flow_limit[1]],NegotiablePercentage=15)
                    if len(result)>0: res.extend(result) 
                    if len(PowerVals)>0:
                        AveragePFO=[]
                        for Power in PowerVals: AveragePFO.append((Power[-1]-Power[1])*1000)
                        pkts=len (AveragePFO)
                        AveragePFO=round((sum(AveragePFO)/len(AveragePFO)),3) if len(AveragePFO)>1 else -1
                        if AveragePFO==-1:res.append([f'TPT Cannot Calculate the PFO', Enums.TestResult.FAIL])
                        else:
                            TestKey=f'{self.Certification}_Link'
                            if self.JCTSData[self.Product][self.Mode][self.Header['TestcaseID']].get(TestKey,False):
                                                           
                            # if Check.get("TestLink",False): # Check Average PFO form Other Tcs
                                TCExist=True
                                TCPFO=[]
                                for Tc in self.JCTSData[self.Product][self.Mode][self.Header['TestcaseID']][TestKey]["TestLink"]:
                                    if Tc not in self.TestData['TestResults']:TCExist=False
                                    else:TCPFO.append(self.TestData['TestResults'][Tc])
                                if TCExist:res.append([f'Average PFO calculated in the current Tc is {AveragePFO} mW --- for the {pkts} {Check['Pkt'][0]} Packets and max PFO value from {self.JCTSData[self.Product][self.Mode][self.Header['TestcaseID']][TestKey]["TestLink"]} is {max(TCPFO)} mW', Enums.TestResult.PASS if AveragePFO >= max(TCPFO) else Enums.TestResult.FAIL])  
                                else:res.append([f'Average PFO measurements of TCs { self.JCTSData[self.Product][self.Mode][self.Header['TestcaseID']][TestKey]["TestLink"]} are not available ', Enums.TestResult.INCONCLUSIVE])
                            else:res.append([f'Calculated Average PFO Value for the {pkts} {Check['Pkt'][0]} Packets  is {AveragePFO} mW  Expected >=0mW', Enums.TestResult.PASS if AveragePFO >=0 else Enums.TestResult.FAIL])                    
            else:
                result,PowerVals=self.PLA_MSR(NegotiablePower=NPower,Check=Check,limit=[PhaseLimit[0],self.Flow_limit[1]])
                if len(result)>0: res.extend(result) 
                result=self.PFOMeasures(Check,PowerVals)
                if len(result)>0:res.extend(result)
        
        else:res.append([f'PRx did not Entered PT Phase',Enums.TestResult.INCONCLUSIVE])
        return res 
    
    def ProtocolVersion(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit'] 
        random_data = Check.get('random',False)
        PhaseLimit=self.FindPhase(self.Flow_limit[0],"Nego")
        if PhaseLimit is not None:
            PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
            if len(PT)>2:
                Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[PT[2],self.Flow_limit[1]])
                if len(Stable)>2:
                    res.append([f'PRx stabilized to Negotaible Load Power at {{{Stable[2]}}} ',Enums.TestResult.PASS])
                    PTID=self.PktMethod.GetexactPacketDetails(packet="Power Transmitter Identification", Type="Response",limit=self.Flow_limit)
                    if len(PTID)>2:
                        res.append([f'TPT sent Power Transmitter Identification Pkt at {{{PTID[2]}}}',Enums.TestResult.PASS])   
                        if not random_data:
                            result=self.Payload_Details(PacketName="Power Transmitter Identification",Index=PTID[2],PayLoads=Check['PT-ID'],Receiver=False)
                            if len(result)>0:res.extend(result)
                        else:
                            major_minor = f"{self.PktMethod.GetPayloadDetails(PTID[2], 'Major_Version')[0]['sRawData'].split('x')[1][-1]}.{self.PktMethod.GetPayloadDetails(PTID[2], 'Minor_Version')[0]['sRawData'].split('x')[1][-1]}"
                            res.append([f'PTx Sent Major_Version: {major_minor.split('.')[0]} and Minor_Version: {major_minor.split('.')[1]} for the Power Transmitter Identification data packet, Exp: 2.2 or Higher[Random Generated]', Enums.TestResult.PASS if float(major_minor) >= 2.2 else Enums.TestResult.INCONCLUSIVE])
                    # else:res.append([f'TPT did not  sent Power Transmitter Identification Pkt ',Enums.TestResult.INCONCLUSIVE])
                    # Version select pkt
                    SRQ_VS=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Version select", limit=PhaseLimit)
                    if len(SRQ_VS)>2:
                        res.append([f'PRx sent SRQ/Version select Pkt at {{{SRQ_VS[2]}}} in Negotiation Phase',Enums.TestResult.PASS if Check['VersionSelect'] else Enums.TestResult.FAIL])
                        if Check['VersionSelect']:
                            result=self.Payload_Details(PacketName="SRQ/Version select",Index=SRQ_VS[2],PayLoads=Check['VS'])
                            if len(result)>0:res.extend(result)
                            #Check Nego Pkts

                            result=self.CheckPkts(PhaseLimit[0],PhaseLimit[1],Check['Pkts'])
                            if len(result)>0:
                                res.append([f'--- Validate Nego Packetes ---',Enums.TestResult.PASS])
                                res.extend(result)
                    else:res.append([f'PRx did not sent SRQ/Version select Pkt in Negotiation Phase',Enums.TestResult.PASS if not Check['VersionSelect'] else Enums.TestResult.FAIL])
                else:res.append([f'PRx did not stabilized to Negotaible Load Power ',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'PRx did not entered in to PT Phase',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not entered in to Nego Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def Param_Check(self,CTSCheck,Check,flows,flwID):
        res=[]
        pings_360=self.Get360Pings("360")
        if len(pings_360)>2:
            AveragePLoss={}
            Count=0
            for ping in pings_360:
                self.Flow_limit=ping
                Count+=1
                res.append([f'Sequence : {Count}',Enums.TestResult.PASS])
                PLAP=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0], Type="Response",limit=self.Flow_limit)
                if len(PLAP)>2:
                    gCoil_R=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(PLAP[2],'g_coil_R')[0]['sRawData']))/10000/(2 if Check['Pkt'][0]!="Power_Loss_Accounting_Parameters" else 1)
                    res.append([f'TPT sent {Check['Pkt'][0]} at {{{PLAP[2]}}} with gCoil_R :{gCoil_R}',Enums.TestResult.PASS ])
                    #Check PRx PLAP packet
                    RX_PLAP=self.PktMethod.GetPacketDetails(packet=Check['PRx_PLAP'][0],limit=self.Flow_limit)
                    if len(RX_PLAP)>2:
                        CoilVals=self.Get_Alpha(RX_PLAP[2],Check['Pkt'][0])
                        # Perform  validation
                        for key,value in Check['CoilVals'].items():
                            if key in CoilVals:
                                if value[0]:result= Enums.TestResult.PASS if CoilVals[key]>=value[1] and CoilVals[key] <=value[2] else Enums.TestResult.FAIL  
                                else:result=Enums.TestResult.PASS if  CoilVals[key]==value[1] else Enums.TestResult.FAIL
                                res.append([f'Measured {key} from {Check['PRx_PLAP'][0]} at id {RX_PLAP[2]} is {CoilVals[key]} Limit:{value[1:]}',result])
                        
                        Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[RX_PLAP[2]+1,self.Flow_limit[1]])
                        if len(Stable)>2: 
                            
                            RRP,PRECT=self.PLA_RRP_Prect(Check['PLA'][0],limit=[Stable[2]+1,self.Flow_limit[1]],Target=10)
                            AVGRRP,AVGPRECT=sum(RRP)/len(RRP),sum(PRECT)/len(PRECT)
                            AveragePLoss[Count]=[round(AVGRRP-AVGPRECT,3),gCoil_R,AVGPRECT,[round((AVGPRECT)-(AVGPRECT*5/100),3),round((AVGPRECT)+(AVGPRECT*5/100),3)]]
                            res.append([f'Stabilization found at {{{Stable[2]}}}',Enums.TestResult.PASS])
                            res.append([f'Measured Average Received Power is {round(AVGRRP,3)} W for {len(PRECT)} {Check['PLA'][0]} Packets',Enums.TestResult.PASS])
                            res.append([f'Measured Average Prect power is {round(AVGPRECT,3)} W for {len(PRECT)} {Check['PLA'][0]} Packets',Enums.TestResult.PASS])
                            res.append([f'Measured PLossAverage is {round(AVGRRP-AVGPRECT,3)} W for {len(PRECT)} {Check['PLA'][0]} Packets',Enums.TestResult.PASS])
                            # res.append([f'Measured Average Received Power is {round(AVGRRP,3)} W & Average Prect power is {round(AVGPRECT,3)} W, PLossAverage is {round(AVGRRP-AVGPRECT,3)} W',Enums.TestResult.PASS])
                            if Count >1:
                                res.append([f' Check Current PRECT_AVE : {round(AVGPRECT,3)} W is within 5% of TestP1 -PRECT_AVE :{round(AveragePLoss[1][2],3)} W  ',Enums.TestResult.PASS if AVGPRECT >= AveragePLoss[1][3][0] and AVGPRECT <= AveragePLoss[1][3][1] else Enums.TestResult.FAIL])
                            if Check['PLA'][0]=="PLA_2 [0x88]":
                                result=self.PLA2_Fast(Check['PLA'][0],limit=[Stable[2]+1,self.Flow_limit[1]],TimeLimit=["LTE",2050],Target=10)
                                if len(result)>0: res.extend(result)
                        else:  res.append([f'PRx did not Stabilized to Negotiable Power',Enums.TestResult.INCONCLUSIVE])  
                    else:res.append([f'PRx did not sent {Check['PRx_PLAP'][0]} PKt',Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'Test did not found {Check['Pkt'][0]}',Enums.TestResult.INCONCLUSIVE])
            res.append([f'Check Ploss Average form P2 {AveragePLoss[2][0]} W > Ploss Average P1 {AveragePLoss[1][0]} W',Enums.TestResult.PASS if AveragePLoss[2][0] > AveragePLoss[1][0] else Enums.TestResult.FAIL])
            res.append([f'Check Ploss Average form P1 {AveragePLoss[1][0]} W > Ploss Average P3 {AveragePLoss[3][0]} W',Enums.TestResult.PASS if AveragePLoss[1][0] > AveragePLoss[3][0] else Enums.TestResult.FAIL])

        else:res.append([f'Test did not found sufficient pings to validate Measurements',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def Power_Check(self,CTSCheck,Check,flows,flwID):
        
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Type= "Packet" if Check["pkt"][-1] else "Response"
        PktName=Check["pkt"][0]+" "+Check["pkt"][1] if Check["pkt"][1]is not None else Check["pkt"][0]
        pkt= self.PktMethod.GetPacketDetails(packet=Check["pkt"][0], value=Check["pkt"][1],Type=Type,limit=self.Flow_limit)
        if len(pkt)>2:
            res.append([f'{'PRx' if Type=='Packet' else 'TPT'} sent the {PktName} Packet at {{{pkt[2]}}}',Enums.TestResult.PASS])
            for Check_Name in Check['pkt'][2]:
                power=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(pkt[2],Check_Name['Name'])[0]['sRawData'])/10
                match Check_Name['comp']:
                    case 'EQL':
                        if power==Check_Name['power']:
                            res.append([f'{'PRx' if Type=='Packet' else 'TPT'}  sent the {Check_Name['Name']} with val {int(power)} W Exp :{Check_Name['power']} W',Enums.TestResult.PASS])
                        else: res.append([f'{'PRx' if Type=='Packet' else 'TPT'}  sent the {Check_Name['Name']} with val {int(power)} W Exp :{Check_Name['power']} W',Enums.TestResult.FAIL])
        else:res.append([f'{'PRx' if Type=='Packet' else 'TPT'} did not sent the {PktName} datapacket.', Enums.TestResult.INCONCLUSIVE])
        return res
    
    def PacketDetails(self,CTSCheck,Check,flows,flwID):
        
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id = self.Flow_limit[0]
        for ExpPacket in Check['ExpectedPacket']:
            Type= "Packet" if ExpPacket[-1] else "Response"
            ExpectedPacket_Details = self.PktMethod.GetPacketDetails(packet=ExpPacket[0], value=ExpPacket[1],Type=Type,limit=[id,self.Flow_limit[1]])
            DataPacket= str(f'{ExpPacket[0]}{'_' + ExpPacket[1].replace('{','').replace('}','').replace(':','_') if ExpPacket[1] is not None else ''}')
            if len(ExpectedPacket_Details)>2:
                res.append([f'{'PRx' if Type=='Packet' else 'TPT'}  sent the {DataPacket} datapacket at {{{ExpectedPacket_Details[2]}}}', Enums.TestResult.PASS]) 
                if ExpPacket[2]: 
                    result=self.Payload_Details(PacketName=DataPacket,Index=ExpectedPacket_Details[2],PayLoads=ExpPacket[3],Receiver= True if Type=="Packet" else False)
                    if len(result)>0: res.extend(result) 
                id=ExpectedPacket_Details[2]+1
            else:res.append([f'{'PRx' if Type=='Packet' else 'TPT'} did not sent the {DataPacket} datapacket.', Enums.TestResult.FAIL]) 
        return res
    
    
    def XID_Check(self,CTSCheck,Check,flows,flwID):
        
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        if Check.get('EPT',False):
            res.extend(self.XID_Flow(Check))
            # Check the EPT/ REP packet from PRx
            EPT=self.PktMethod.GetPacketDetails(packet="End Power Transfer", value= "[EPT/rep]", limit=self.Flow_limit)
            if len(EPT)>2:
                res.append([f'PRx sent EPT/rep Packet at {{{EPT[2]}}} to proceed to Digital Ping 360 kHz',Enums.TestResult.PASS])
            else:res.append([f'PRx did not sent EPT/rep Packet',Enums.TestResult.INCONCLUSIVE])
        else:res.extend(self.XID_Flow(Check))
        return res
    
    def XID_Flow(self,Check):

        res=[]

        SSID=self.findTypeid(limit=[self.Flow_limit[0],self.Flow_limit[1]],Type='Packet')
        if SSID is not None and self.file_list[SSID]['pktType'] in'Signal strength':
            ID=self.findTypeid(limit=[SSID+1,self.Flow_limit[1]],Type='Packet')
            if ID is not None and self.file_list[ID]['pktType'] in 'Identification':
                XID=self.findTypeid(limit=[ID+1,self.Flow_limit[1]],Type='Packet')
                if XID is not None and self.file_list[XID]['pktType'] in ["MPP_Extended_Identification","Extended Identification"]:
                    res.append([f'PRx sent the {self.file_list[XID]['pktType']} data packet at {{{XID}}} after Sequence Digital Ping - Signal Strength - Identification ',Enums.TestResult.PASS])
                    if Check.get("BitCheck",False):
                        FE_Check=self.PktMethod.GetPayloadDetails(XID,'XID_Selector')[0]['sRawData']
                        res.append([f'PRx sent the XID selector Field as : {FE_Check} ,Expected:0xFE ',Enums.TestResult.FAIL if FE_Check !="0xFE" else Enums.TestResult.PASS])
                else: res.append([f'PRx sent the {self.file_list[XID]['pktType']} data packet after Identification Packet',Enums.TestResult.FAIL])
            else:res.append([f'PRx did not send Identification Packet after SS Packet',Enums.TestResult.FAIL])
        else:res.append([f'PRx did not send Signal Strength Packet',Enums.TestResult.FAIL])

        return res

        

    def DSR_Sequence(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        RPcount=0
        count=0
        # start from PT phase as Power Loass accounting naming is same in Nego Phase
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            id=PT[2]
            while id < self.Flow_limit[1]:
                if count > Check['PktsCount']:break
                # find RP
                PLA=self.PktMethod.GetPacketDetails(packet=Check['PowerPkt'], limit=[id,self.Flow_limit[1]])
                if len(PLA)>2:
                    RPcount+=1
                    if RPcount %2==0:
                        # Check Response
                        Response=self.PktResponse(PLA[2]+1,self.Flow_limit[1])
                        if Response is not None:
                            res.append([f'TPT sent Response:{Response[0]} for the 2nd {Check['PowerPkt']} data packet at {{{PLA[2]}}}.', Enums.TestResult.INCONCLUSIVE if 'ATN' not in Response[0] else Enums.TestResult.PASS])
                            # Check DSR and TPT response
                            NextATN=self.Find_PLA_ATN(Response[1],Check)
                            DSR=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[id,NextATN])
                            if len(DSR)>2:
                                Response=self.PktResponse(DSR[2]+1,NextATN)
                                if Response is not None:
                                    if Check['Response'] in Response[0]:
                                        count+=1
                                        res.append([f'Sequence - {count}',Enums.TestResult.PASS])
                                        res.append([f'TPT sent Response : {Check['Response']} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.PASS])
                                        # find UUT packet
                                        UUTpkt=self.PktMethod.GetPacketDetails(packet="DSR",value="ND",limit=[Response[1],NextATN])
                                        if len(UUTpkt)>2:
                                            res.append([f'PRx  sent DSR/ND Packet at {{{UUTpkt[2]}}} for the PTx -{Check['Response']}', Enums.TestResult.PASS])
                                        else:res.append([f'PRx did not sent DSR/ND Packet for the PTx -{Check['Response']} at {{{Response[1]}}} until Next {Check['PowerPkt']} ATN at {{{NextATN}}} ', Enums.TestResult.FAIL])    
                                    else: res.append([f'TPT sent Response : {Response[0]} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.INCONCLUSIVE])     
                                else:res.append([f'TPT did not sent Response : {Check['Response']} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.INCONCLUSIVE])
                            else:res.append([f'PRx did not sent DSR/POLL Packet from the ATN at {{{Response[1]}}} to Next {Check['PowerPkt']} ATN at {{{NextATN}}} ', Enums.TestResult.INCONCLUSIVE])
                        else:res.append([f'TPT did not sent Response for the 2nd {Check['PowerPkt']} data packet at {{{PLA[2]}}}.', Enums.TestResult.INCONCLUSIVE])
                    id=PLA[2]+1
                else:break
            
            if count < Check['PktsCount'] :res.append([f'Test did not found {Check['PktsCount']} Protocol Sequences of {Check['Response']} Packets',Enums.TestResult.INCONCLUSIVE])
        else: res.append([f'PRx did not Entered in to Power Transfer Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    
    def Tdsr(self,CTSCheck,Check,flows,flwID):
        self.Flow_limit = flows[flwID]['Limit']
        res=[]
        Timings=[]
        count=0
        FailCount=0
        # start from PT phase as Power Loass accounting naming is same in Nego Phase
        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            id=PT[2]
            while id < self.Flow_limit[1]:
                if count > Check['PktsCount']:break
                ATN=self.Find_PLA_ATN(id,Check)
                # Check DSR and TPT response
                DSR=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[ATN,self.Flow_limit[1]])
                if len(DSR)>2:
                    NextATN=self.Find_PLA_ATN(DSR[2]+1,Check)
                    Response=self.PktResponse(DSR[2]+1,NextATN)
                    if Response is not None:
                        if Check['Response'] in Response[0]:
                            res.append([f'TPT sent Response : {Check['Response']} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.PASS])
                            count+=1
                            measurement=-1
                            UUTpkt=self.PktMethod.GetPacketDetails(packet="DSR",limit=[Response[1],NextATN])
                            if len(UUTpkt)<2: res.append([f'PRx did not sent DSR Packet after the TPT {Check['Response']} at {{{Response[1]}}}, so Tdsr =-1ms', Enums.TestResult.FAIL])  
                            else: measurement=round((self.file_list[UUTpkt[2]]['startTime']-self.file_list[Response[1]]['stopTime'])*1000,3)
                            if measurement < 0 and measurement >1000: FailCount+=1 
                            Timings.append(measurement)
                        else: 
                            if 'SADC' in Response[0]:id=Response[1]+1
                            else:res.append([f'TPT sent Response : {Response[0]} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.INCONCLUSIVE])     
                    else:res.append([f'TPT did not sent Response : {Check['Response']} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.INCONCLUSIVE])
                    id=DSR[2]+1
                else:break
                
            if FailCount >  int(0.05 * len(Timings)):
                res.append([f'Measured  Max Tdsr is {max(Timings)} mS ,Min Tdsr is {min(Timings)} mS Limit :0 < ≤ 1,000 ms ', Enums.TestResult.FAIL])
                res.append([f'More than 5% of the Intervals met the fail criteria', Enums.TestResult.FAIL])
            else:res.append([f'Measured  Max Tdsr is {max(Timings)} mS ,Min Tdsr is {min(Timings)} mS Limit :0 < Tdsr ≤ 1,000 ms ', Enums.TestResult.PASS])
            if count < Check['PktsCount'] :res.append([f'Test did not found {Check['PktsCount']} Protocol Sequences of {Check['Response']} Packets',Enums.TestResult.INCONCLUSIVE])
        else: res.append([f'PRx did not Entered in to Power Transfer Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    
    
    def FSK_Demod(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Pkt= "MPP_Extended_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Identification"
        MPP=self.PktMethod.GetPacketDetails(packet=Pkt, limit=self.Flow_limit)
        if len(MPP)>2:
            Flow2RestrictedBit=self.MPPRestrictedBit(MPP[2])
            if not Flow2RestrictedBit :
                res.append([f'PRx set Restricted Bit to Zero in MPP_Extended_Identification at {{{MPP[2]}}}', Enums.TestResult.PASS])
                # Update Negotiable Load Power in ECAP Pkt
                EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
                ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=self.Flow_limit)
                if len(ECAP)>2:
                    GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                    NPowerCal = math.floor(((Check['Percentage']/100) * min(15, GPower)) * 10) / 10 if Check['SDF'] else Check['NegotiablePower']
                    NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                    res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
                else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])

                PhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
                if PhaseLimit is not None :
                    res.append([f'PRx  Entered in to Power Transfer Phase',Enums.TestResult.PASS]) 
                    # Check Stabilization
                    Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[PhaseLimit[0],self.Flow_limit[1]])
                    if len(Stable)>2:
                        # Check 10%
                        PLA=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[Stable[2],PhaseLimit[0]])
                        #These function belongs to phy layer testcases not required to check before the stabilization.
                        # RRP,Power=self.FormatPLA(PLA[2],Check['Pkt'][0])
                        # res.append([f"Measured Prect_Power value in {Check['Pkt'][0]} pkt is {Power} W  at {{{PLA[2]}}}, Expected Range :[{round((NPowerCal-(10/100)*NPowerCal),2)},{round((NPowerCal+(10/100)*NPowerCal),2)}]", Enums.TestResult.INCONCLUSIVE if Power > (NPowerCal+(10/100)*NPowerCal) or Power < (NPowerCal-(10/100)*NPowerCal) else Enums.TestResult.PASS])
                        res.append([f'Stabilization happened at {{{Stable[2]}}}', Enums.TestResult.PASS])
                    else: res.append([f'Stabilization did not  happened', Enums.TestResult.FAIL])
                else:res.append([f'PRx did not Entered in to Power Transfer Phase',Enums.TestResult.FAIL]) 
            else:res.append([f'PRx set Restricted Bit to one in MPP_Extended_Identification at {{{MPP[2]}}}', Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered in to Power Transfer Phase',Enums.TestResult.FAIL]) 
        return res
    
    
    def ValidateEyeTest(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check Negotiation Phase
        Nego=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: Nego", Type="TesterMsg",limit=self.Flow_limit)
        if len(Nego)>2:
           
            #  # Update Negotiable Load Power in ECAP Pkt
            EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
            ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=[Nego[2],self.Flow_limit[1]])
            if len(ECAP)>2:
                ResultFlag=False
                GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                                            # min(100% PRxDUTMax power, 25 W)  # max(1W, min(20%PRxDUT Max power,5 W))
                NPowerCal =  math.floor(max(1,min(0.2*GPower,5))*10)/10 if Check.get('CPM',False) else math.floor((min((Check['Percentage']*GPower)/100,Check['PowerVal']))*10)/10 
                if not Check.get('CPM',False) and NPowerCal > 15:
                    Reason= self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Power_Limit_Reason')[0]['sRawData'])
                    res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet at {{{ECAP[2]}}} with Power limit reason:{int(Reason)} -- Before DPLoss Calibration. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if Reason==10 else Enums.TestResult.INCONCLUSIVE])   
                    ResultFlag=True
                else:
                    res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet at {{{ECAP[2]}}} Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
            else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])
            
            PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT", Type="TesterMsg",limit=self.Flow_limit)
            if len(PT)>2 :
                Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=[PT[2],self.Flow_limit[1]])
                if len(Stable)>2:
                    res.append([f'PRx Stabilized at {{{Stable[2]}}}',Enums.TestResult.PASS])
                    if ResultFlag:
                        ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=[PT[2]+1,self.Flow_limit[1]])
                        if len(ECAP)>2:
                            NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                            Reason= self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Power_Limit_Reason')[0]['sRawData'])
                            res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet at {{{ECAP[2]}}} with Power limit reason:{int(Reason)} -- After DPLoss Calibration. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if Reason==0 else Enums.TestResult.INCONCLUSIVE])   
                        else: res.append([f'Test did not found ECAP data pkt after DPLoss Calibration', Enums.TestResult.INCONCLUSIVE])
                    results=self.ValidateEye(CTSCheck,Check,flows,flwID)
                    if len(results)>0:res.extend(results)
                    
                else:res.append([f'PRx did not stabilized to Negotaible Load Power ',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'PRx did not entered in to PT Phase',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not entered in to Nego Phase',Enums.TestResult.INCONCLUSIVE])
        return res
    def check_PM(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']
        # with open("data.json", "w") as file:
        #     json.dump(self.file_list, file, indent=4)
        for pkt in range(self.Flow_limit[0], self.Flow_limit[1]):
            if Check['pkt'] in self.file_list[pkt]['pktType']:
                pm = re.search(r'Active Main Mode:\s*(.*?)\s*\|', self.file_list[pkt]['value'])
                if Check['mode'] in self.file_list[pkt]['value']:
                    res.append([f"Power mode: '{pm.group(1)}' found in packet {self.file_list[pkt]['pktType']} at index {pkt} [Expected: {Check['mode']}]",Enums.TestResult.PASS])
                else:
                    res.append([f"Found Power mode of {self.file_list[pkt]['value']} in the packet {self.file_list[pkt]['pktType']} at index-{pkt} [Expected: {Check['mode']}]", Enums.TestResult.INCONCLUSIVE])
                break
        return res
        


    def ValidateEye(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        results,values=self.EyeTest(Check)
        if values['pkts']>0:

            #  # Update Negotiable Load Power in ECAP Pkt
            if Check.get('PowerCheck',False):
                EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
                ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=self.Flow_limit)
                if len(ECAP)>2:
                    GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                    NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                    NPowerCal = math.floor(((Check['Percentage']/100) * min(15, GPower)) * 10) / 10 
                    res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet at {{{ECAP[2]}}} Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   

                else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])
            res.extend(results)
            # Validate
            if values['Npass_Magnitude']>0:res.append([f'Number of packets which pass the magnitude test is  : {values['Npass_Magnitude']}',Enums.TestResult.PASS])
            if values["Npass_Phase"]>0:res.append([f'Number of packets which pass the Phase test is  : {values['Npass_Phase']}',Enums.TestResult.PASS])
            if Check.get('Ntotal',False):
                
                    res.append([
                        f"Calculated Npass {values['Npass']} and Received Ntotal {values['pkts']} Expected : Npass >=Ntotal-2",
                        Enums.TestResult.PASS if values['Npass'] >= values['pkts']-2 else Enums.TestResult.FAIL
                    ])
            elif Check.get('floor',False):    
                    required = max(int(values['pkts'] * 0.95), 1)
                    percentage = round(values['Npass'] * 100 / values['pkts'], 3) if values['pkts'] else 0
                    res.append([
                        f"Calculated Npass {values['Npass']} and Received Ntotal {values['pkts']}: Pass Percentage:{percentage}%",
                        Enums.TestResult.PASS if values['Npass'] >= required else Enums.TestResult.FAIL
                    ])
            else: res.append([f'Number of packets which pass the magnitude and / or phase test -- Npass is  : {values['Npass']}, Expected :>={Check['Npass']}',Enums.TestResult.PASS if values['Npass'] >= Check['Npass'] else Enums.TestResult.FAIL])
        else:res.append([f'Test did not found sufficient Packets for Measurements',Enums.TestResult.INCONCLUSIVE])
        return res

    def ParityBits(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Pkt= "MPP_Extended_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Identification"
        MPP=self.PktMethod.GetPacketDetails(packet=Pkt, limit=self.Flow_limit)
        if len(MPP)>2:
            Flow2RestrictedBit=self.MPPRestrictedBit(MPP[2])
            if Flow2RestrictedBit:res.append([f'PRx supports MPP Restricted Mode',Enums.TestResult.INCONCLUSIVE])
                
            else:
                res.append([f'PRx did not supports MPP Restricted Mode',Enums.TestResult.PASS])
                pktfound=False
                id=MPP[2]+1
                while id < self.Flow_limit[1]:
                    pkt=self.PktMethod.GetPacketDetails(packet="Get Request", value="PTx Extended Capabilities",limit=[id,self.Flow_limit[1]])
                    if len(pkt)>2:
                        pktfound=True
                        # Check Response
                        Response=self.PktResponse(pkt[2]+1,self.Flow_limit[1])
                        if Response is not None:
                            if Response[0] in ["Extended_Power_Transmitter_Extended_Capabilities", "Power Transmitter Extended Capabilities"]:  res.append([f'TPT sent Response {Response[0]} for PRx GET[ECAP] request Pkt at {{{pkt[2]}}} ',Enums.TestResult.PASS])
                            else: res.append([f'TPT sent Response {Response[0]} for PRx GET[ECAP] request Pkt at {{{pkt[2]}}} ',Enums.TestResult.INCONCLUSIVE])
                        else:
                            # Check are there any packets are not from prx
                            PktorResId=self.findTypeid(limit=[pkt[2]+1,self.Flow_limit[1]],Type="Packet")
                            if PktorResId is not None:
                                res.append([f'TPT did not sent Response  for PRx GET[ECAP] request Pkt at {{{pkt[2]}}} ',Enums.TestResult.INCONCLUSIVE]) 
                            else:break
                        id=pkt[2]+1
                    else:break
                if not pktfound:res.append([f'PRx did not sent GET[ECAP] request Pkt ',Enums.TestResult.INCONCLUSIVE])
                # find End Nego
                SRQ_En=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="End Negotiation", limit=[id,self.Flow_limit[1]])
                if len(SRQ_En)>2: res.append([f'PRx sent SRQ/En packet during the 360 kHz Negotiation phase',Enums.TestResult.FAIL])  
                else:res.append([f'PRx did not sent SRQ/En packet during the 360 kHz Negotiation phase',Enums.TestResult.PASS])                                    
        else:res.append([f'PRx did not sent MPP Extended Identification Packet',Enums.TestResult.INCONCLUSIVE])
        return res
    

    def Misc_Response(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        id=self.Flow_limit[0]
        count=0
        for pkt in Check['Pkts']:
            XcePkt=False
            count+=1
            res.append([f'Sequence : {count}',Enums.TestResult.PASS])
            while id < self.Flow_limit[1]:
                XCE= self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[id,self.Flow_limit[1]])
                if len(XCE)>2:
                    # check response
                    Response=self.PktResponse(XCE[2]+1,self.Flow_limit[1])
                    if Response is None:
                        res.append([f'TPT did not sent  Response for the XCE Packet at {{{XCE[2]}}} in the Power Transfer Phase',Enums.TestResult.INCONCLUSIVE]) 
                        id=Response[2]+1
                    else:
                        if 'ATN' in Response[0]:
                            if 'RESPONSE_TIME' in self.Header['TestcaseID']: res.append([f'TPT sent {Response[0]} Response for the {'First XCE Packet' if count==1 else f'First XCE Packet at {{{XCE[2]}}} after Stabilization '}',Enums.TestResult.PASS])
                            else:res.append([f'TPT sent {Response[0]} Response for the XCE Packet at {{{XCE[2]}}}',Enums.TestResult.PASS])
                            # check Dsr
                            XcePkt=True
                            DSR=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[XCE[2]+1,self.Flow_limit[1]])
                            if len(DSR)>2:
                                Response=self.PktResponse(DSR[2]+1,self.Flow_limit[1])
                                if Response is not None:
                                    if pkt[0] in self.file_list[Response[1]]['pktType'] and pkt[1] in self.file_list[Response[1]]['value']:
                                        res.append([f'TPT sent {pkt[0]}_{pkt[1]} response at {{{Response[1]}}} for the DSR/POLL Packet at {{{DSR[2]}}}',Enums.TestResult.PASS])
                                        # Check Pkt from UUT
                                        x=['Charge Status','ChargeStatus']
                                        if pkt[-1] and not any(
                                            c in self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SupportedOptionalGetRequests']
                                            for c in x
                                        ):
                                        # if pkt[-1]and c for c in x not in self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['SupportedOptionalGetRequests']:
                                            UUTpkt =self.PktMethod.GetPacketDetails(packet="DSR",value='ND',limit=[Response[1],self.Flow_limit[1]])
                                            pkt[2]="DSR_ND"
                                        else:UUTpkt=self.PktMethod.GetPacketDetails(packet=pkt[2],limit=[Response[1],self.Flow_limit[1]])
                                        if len(UUTpkt)>2:
                                            Timing=round((self.file_list[UUTpkt[2]]['startTime']-self.file_list[Response[1]]['stopTime'])*1000,3)
                                            res.append([f'PRx sent {pkt[2]} at {{{UUTpkt[2]}}} within {Timing} mS from the {pkt[0]}_{pkt[1]} , Expected :<={Check['Limit']} mS',Enums.TestResult.PASS if Timing <=Check['Limit'] else Enums.TestResult.FAIL])
                                            id=UUTpkt[2]+1
                                        else:
                                            res.append([f'PRx did not sent {pkt[2]} Packet after {pkt[0]}_{pkt[1]}',Enums.TestResult.FAIL])  
                                            id=Response[1]+1
                                        break
                                    else: res.append([f'TPT sent Response as {self.file_list[Response[1]]['pktType']}_{self.file_list[Response[1]]['value']} for the DSR/POLL Packet {{{DSR[2]}}}',Enums.TestResult.INCONCLUSIVE])   
                                    break
                                else:  res.append([f'TPT did not sent  Response for the DSR/POLL Packet at {{{DSR[2]}}} in the Power Transfer Phase',Enums.TestResult.INCONCLUSIVE])     
                                id=DSR[2]+1
                                break
                            else:  res.append([f'PRx did not sent DSR/Poll after the Sequence XCE-ATN from {{{XCE[2]}}}',Enums.TestResult.INCONCLUSIVE])  
                            break  
                        else:id=Response[1]+1 
                else:break
            if not XcePkt:res.append([f'Test did not Found XCE Packet with Response : ATN ',Enums.TestResult.INCONCLUSIVE])
        return res


    def VerifyPrect_PD(self,CTSCheck,Check,flows,flwID):
        try:
            self.Flow_limit = flows[flwID]['Limit']
            res = []
            EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
            ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=self.Flow_limit)
            if len(ECAP)>2:
                GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                NPowerCal = math.floor(((100/100) * min(15, GPower)) * 10) / 10 
                res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet at {{{ECAP[2]}}} Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
            else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])
            Pkt1 = self.PktMethod.GetPacketDetails(packet="MPP_XCE_Stabilized",limit=self.Flow_limit,Type="TesterMsg")
            if len(Pkt1)>2:
                res.append([f"first MPP_XCE_Stabilized found at {round(Pkt1[0],3)}sec",Enums.TestResult.PASS])
                #Get First PLA
                PLA1= self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[Pkt1[2],self.Flow_limit[1]])
                if len(PLA1)>2:
                    Prect1 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLA1[2],"PRECT")[0]['sDescription'])[0]
                    res.append([f"PLA1 packet found after first MPP_XCE_Stabilized packet at {round(PLA1[0],3)}sec with Prect={Prect1}W",Enums.TestResult.PASS])
                    #Get Second PLA
                    Pkt2 = self.PktMethod.GetPacketDetails(packet="MPP_XCE_Stabilized",limit=[PLA1[2]+1,self.Flow_limit[1]],Type="TesterMsg")
                    if len(Pkt2)>2:
                        res.append([f"Second MPP_XCE_Stabilized found at {round(Pkt2[0],3)}sec",Enums.TestResult.PASS])
                        PLA2= self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[Pkt2[2],self.Flow_limit[1]])
                        if len(PLA2)>2:
                            Prect2 = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLA2[2],"PRECT")[0]['sDescription'])[0]
                            res.append([f"PLA2 packet found after second MPP_XCE_Stabilized packet at {round(PLA2[0],3)}sec with Prect={Prect2}W",Enums.TestResult.PASS])
                            if Prect1 and Prect2:
                                ChkRes = CommonMethods.check_measure([round(Prect1*1.1,2)],Prect2,"LTEQL")
                                print(ChkRes)
                                res.append([f"Verify Condition:Prect2 <= Prect1 * 1.1|{Prect2}W <= {ChkRes[0][0]}W",ChkRes[1]])
                            else:res.append([f"Issue to calculate Prect value from PLA packets",Enums.TestResult.FAIL])
                        else:res.append([f"PLA2 packet not found after Second MPP_XCE_Stabilized packet",Enums.TestResult.FAIL])
                    else:res.append([f"Second MPP_XCE_Stabilized not found",Enums.TestResult.FAIL])
                else:res.append([f"PLA1 packet not found after first MPP_XCE_Stabilized packet",Enums.TestResult.FAIL])
            else:res.append([f"first MPP_XCE_Stabilized not found",Enums.TestResult.FAIL])
            return res
        except Exception as e:
            print(e)

    def PD_PLA_PrectVrect(self,CTSCheck,Check,flows,flwID):
        try:
            res=[]
            self.Flow_limit = flows[flwID]['Limit']
            EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"
            ECAP=self.PktMethod.GetPacketDetails(packet=EcapPkt, Type="Response",limit=self.Flow_limit)
            if len(ECAP)>2:
                GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(ECAP[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                NPowerCal = math.floor(((100/100) * min(15, GPower)) * 10) / 10 
                res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet at {{{ECAP[2]}}} Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
            else: res.append([f'Test did not found ECAP data pkt', Enums.TestResult.INCONCLUSIVE])
            #1. Get the first PLA after Stabilization
            Pkt1 = self.PktMethod.GetPacketDetails(packet="MPP_XCE_Stabilized",limit=self.Flow_limit,Type="TesterMsg")
            if len(Pkt1)>2:
                res.append([f"MPP_XCE_Stabilized found at {round(Pkt1[0],3)}sec",Enums.TestResult.PASS])
                #2.Get the first PLA packet
                PLA1= self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[Pkt1[2],self.Flow_limit[1]])
                if len(PLA1)>2:
                    self.AllChannelData = self.PlotMethod.GetAllChannelData2('2',self.JapiData)
                    PLA1_Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLA1[2],"PRECT")[0]['sDescription'])[0]
                    PLA1_Vrect = self.PktMethod.CalculateVoltTwindow(PLA1[2],self.AllChannelData)
                    res.append([f"First PLA packet found at {round(PLA1[0],3)}sec Measured Prect_P1={round(PLA1_Prect,3)}W and V1={round(PLA1_Vrect[0],3)}V",Enums.TestResult.PASS])
                    #condition 1 : PLA1_Prect > 1W
                    ChkRes = CommonMethods.check_measure([1],PLA1_Prect,"GTEQL")
                    res.append([f"Condition 1:Verify: Prect1>=1W",ChkRes[1]])
                    #3. Get the last PLA packet
                    PLA2 = self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[self.Flow_limit[1],PLA1[2]-1])
                    if len(PLA2)>2:
                        PLA2_Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLA2[2],"PRECT")[0]['sDescription'])[0]
                        PLA2_Vrect = self.PktMethod.CalculateVoltTwindow(PLA2[2],self.AllChannelData)
                        res.append([f"PLA2 packet found at {round(PLA2[0],3)}sec Measured Prect_P2={round(PLA2_Prect,3)}W and V2={round(PLA2_Vrect[0],3)}V",Enums.TestResult.PASS])
                        #condition 2 : P2 <= (P1*V2)/V1
                        # print(PLA2_Prect,round((float(PLA1_Prect)*float(PLA2_Vrect[0]))/float(PLA1_Vrect[0]),2))
                        ChkRes2 = CommonMethods.check_measure([round((float(PLA1_Prect)*float(PLA2_Vrect[0]))/float(PLA1_Vrect[0]),2)],PLA2_Prect,"LTEQL")
                        res.append([f"Condition 1:Verify:  P2 <= (P1*V2)/V1 i.e {ChkRes2[3]} <= {ChkRes2[0][0]}",ChkRes2[1]])
                    else:res.append(["PLA2 packet not found after first PLA",Enums.TestResult.FAIL])
                else:res.append(["PLA1 packet not found after MPP_XCE_Stabilized",Enums.TestResult.FAIL])
            else:res.append([f"MPP_XCE_Stabilized not found for the 360Khz flow",Enums.TestResult.FAIL])
            return res
        except Exception as e:
            traceback.print_exc()

    def ITPT_MAX(self,CTSCheck,Check,flows,flwID):
        try:
            self.Flow_limit = flows[flwID]['Limit']
            res=[]
            templimit = []
            EcapPkt=  "Extended_Power_Transmitter_Extended_Capabilities" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Power Transmitter Extended Capabilities"

            pkt1 = self.PktMethod.GetPacketDetails(packet=EcapPkt,Type="Response",limit=self.Flow_limit)

            if len(pkt1)>2:
                res.append([f"The packet {EcapPkt} found at {round(pkt1[0],3)}sec",Enums.TestResult.PASS])
                GPower=self.BKjsonData['testBkpProjectConfiguration']['EsdfConfigurationModel']['AllESDFFields']['GuaranteedLoadPower']
                NPowerCal = math.floor(((Check['Percentage']/100) * min(15, GPower)) * 10) / 10
                NPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(pkt1[2],'Negotiable_Load_Power')[0]['sRawData']))/10
                res.append([f'TPT set Negotiable Load power to {NPower} W in ECAP Packet ,Expected val :{NPowerCal} W. In SDF Guranteed Load Power was set to {GPower} W ',Enums.TestResult.PASS if NPower== NPowerCal else Enums.TestResult.INCONCLUSIVE])   
            else:res.append([f"The packet {EcapPkt} not found to check the ITPT max value",Enums.TestResult.INCONCLUSIVE])
            
            pkt2 = self.PktMethod.GetPacketDetails(packet="MPP_XCE_Stabilized",limit=self.Flow_limit,Type="TesterMsg")
            if len(pkt2)>2:
                res.append([f" MPP_XCE_Stabilized found at {round(pkt2[0],3)}sec",Enums.TestResult.PASS])
                XCEVlist = []
                cnt=0
                #get first 5 XCEV packets and check the value
                i = pkt2[2]
                while i < self.Flow_limit[1]:
                    Pkt = self.PktMethod.GetPacketDetails(packet="Extended Control Error",limit=[i,self.Flow_limit[1]])
                    if len(Pkt)>2:
                        cnt+=1
                        v = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pkt[2],"Control_Error_Value")[0]['sDescription'])[0]
                        XCEVlist.append(v)
                        if cnt==5:break
                        i = Pkt[2]+1
                    else:break
                if len(XCEVlist)>0:
                    int_values = ','.join(str(int(v)) for v in XCEVlist)
                    if all(abs(v) <= 1 for v in XCEVlist):
                        res.append([f"All 5 XCEV packet values i.e {int_values} Limit :within ±1", Enums.TestResult.PASS])
                    else:
                        res.append([f"All 5 XCEV packet values i.e {int_values} Limit :within ±1", Enums.TestResult.FAIL])
                else:res.append[f"No XCEV packet found after stabilization",Enums.TestResult.INCONCLUSIVE]
            else:res.append([f"MPP_XCE_Stabilized not found to check the ITPT max value",Enums.TestResult.INCONCLUSIVE])
            if len(pkt1)>2 and len(pkt2)>2:
                i = pkt1[2]
                while i < pkt2[2]:
                    pkt3 = self.PktMethod.GetPacketDetails(packet="MPLA_AC_DC_Current",limit=[i,pkt2[2]],Type="TesterMsg")
                    if len(pkt3)>2:
                        ITPT = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(pkt3[2],"I_txrms")[0]['sDescription'])[0]
                        templimit.append([ITPT,round(pkt3[0],3)])
                        i = pkt3[2]+1
                    else:break
                # print(templimit)
                if len(templimit)>0:
                    maxI = max(templimit, key=lambda x: x[0])
                    # print(maxI)
                    ChkRes = CommonMethods.check_measure(Check['expected'],maxI[0],"LT")
                    res.append([f"The MAX ITPT value is {round(maxI[0],3)}mA measured at {round(maxI[1],3)}Sec, Limit {ChkRes[2]}",ChkRes[1]])
                else: res.append([f"No MPLA_AC_DC_Current packets found between {round(pkt1[0],3)}sec to {round(pkt2[0],3)}sec",Enums.TestResult.INCONCLUSIVE])
                PLA1= self.PktMethod.GetPacketDetails(packet="Power Loss Accounting",limit=[pkt2[2]+1,self.Flow_limit[1]])
                if len(PLA1)>2:
                    #find PDelta
                    Prect = GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(PLA1[2],"PRECT")[0]['sDescription'])[0]
                    PDelta = abs(round((Prect-Check['Delta']),3))
                    ChkRes = CommonMethods.check_measure([round(Check['Delta']*0.1,2)],PDelta,"LT")
                    res.append([f"Verify condition : PDelta < 0.1*Pexpected :{PDelta}W < {ChkRes[0][0]}W ",ChkRes[1]])
                else:res.append([f"PLA packet not found after stabilization",Enums.TestResult.FAIL])
            return res
        except Exception as e:
            print(e)
    
    def ValidateNego(self,CTSCheck,Check,flows,flwID):
        res=[]
        pings_360=self.Get360Pings("360")
        if len(pings_360)>=7:
            count=0
            for ping in pings_360:
                res.append([f'Sequence :{count}',Enums.TestResult.PASS])
                self.Flow_limit=ping
                # find Pkt
                pkt1= self.PktMethod.GetPacketDetails(packet="Configuration",limit=self.Flow_limit)
                if len(pkt1)>2:
                    res.append([f'PRx sent Configuration pkt at {{{pkt1[2]}}} ',Enums.TestResult.PASS])
                    pkt2= self.PktMethod.GetPacketDetails(packet="SRQ [0x20]",value="End Negotiation",limit=[pkt1[2]+1,self.Flow_limit[1]])
                    if len(pkt2)>2:
                        r=self.NegoValidate([pkt1[2]+1,pkt2[2]],Check['NegPkts'],Response=False)
                        if len(r)>0:res.extend(r)     
                    else:res.append([f'PRx did not sent Configuration in the Sequence :{count}',Enums.TestResult.INCONCLUSIVE])
                else:res.append([f'PRx did not sent SRQ_End Negotiation in the Sequence :{count}',Enums.TestResult.INCONCLUSIVE])
                count+=1
        else:res.append([f'TPT did not sent Enough Pings for measurements',Enums.TestResult.INCONCLUSIVE])
        return res
    

    def RestrictedMode(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        Pkt= "MPP_Extended_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Identification"
        MPP=self.PktMethod.GetPacketDetails(packet=Pkt, limit=self.Flow_limit)
        if len(MPP)>2:
            Flow2RestrictedBit=self.MPPRestrictedBit(MPP[2])
            if Flow2RestrictedBit:
                res.append([f'PRx set Restricted Bit to One in MPP_Extended_Identification at {{{MPP[2]}}}', Enums.TestResult.PASS])
                Pch,PchPkt=self.PchTime()
                res.append([f'PRx sent Power Control Hold off pkt with Val:{Pch} mS Exp:>=20 mS',Enums.TestResult.PASS if Pch >=20 else Enums.TestResult.FAIL])
                End_Power=self.PktMethod.GetPacketDetails(packet="End Power Transfer", value= "[EPT/rst]",limit=[MPP[2]+1,self.Flow_limit[1]])
                if len(End_Power)>2:
                   res.append([f'PRx sent End Power Tranfer Packet _RST to Switch from Restricted Mode to MPP-Full Mode',Enums.TestResult.PASS])
                else:
                    Renego=self.PktMethod.GetPacketDetails(packet="Renegotiate", limit=[MPP[2]+1,self.Flow_limit[1]])
                    if len(Renego)<2:res.append([f'PRx did not sent Renegotiate Packet to Switch from Restricted Mode to MPP-Full Mode',Enums.TestResult.FAIL])
                    else:
                        # Check pkts Before Renego
                        BeforeRenego=self.Check_CE_PLA(Renego[2]+1,self.Flow_limit[1],"Extended Control Error","Power Loss Accounting") # should not recive those pkts
                        if len(BeforeRenego)>2:res.entend(BeforeRenego)
                        else:res.append([f'PRx sent only Control Error and 8 bit Received Power Packets Before Renegotiation at {{{Renego[2]}}}',Enums.TestResult.PASS])

                        # Check pkts after Renego
                        afterRenego=self.Check_CE_PLA(Renego[2]+1,self.Flow_limit[1],"Control Error","8 bit Received Power")
                        if len(afterRenego)>2:res.entend(afterRenego)
                        else:res.append([f'PRx sent only Extended Control Error and PLA Packets after Renegotiation at {{{Renego[2]}}}',Enums.TestResult.PASS])
            else:res.append([f'PRx did not set the Restricted Bit to 1 in MPP_Extended_Identification PKT at {{{MPP[2]}}} in to 360 Flow',Enums.TestResult.FAIL])  
        else:res.append([f'PRx did not sent MPP-Extended Identification Packet in 360 Flow',Enums.TestResult.INCONCLUSIVE])   
        return res
    
    def ProfileActivation(self,CTSCheck,Check,flows,flwID):
        res1=[]
        res2=[]
        self.Flow_limit = flows[flwID]['Limit']
        flow1,flow2=flows[1]['Limit'],flows[2]['Limit']
        Pkt= "MPP_Extended_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Identification"
        MPP=self.PktMethod.GetPacketDetails(packet=Pkt, limit=flow1)
        if len(MPP)>2:
            Flow1RestrictedBit=self.MPPRestrictedBit(MPP[2])
            if Flow1RestrictedBit:
                res1.append([f'PRx supports Restricted Mode at DP 128kHz',Enums.TestResult.PASS])
                if Check['flow']==2:
                    CFG=self.PktMethod.GetPacketDetails(packet="Configuration", limit=flow2)
                    if len(CFG)>2:
                        # Check pkts After CFG
                        BeforeRenego=self.Check_CE_PLA(CFG[2]+1,self.Flow_limit[1],"Extended Control Error","Power Loss Accounting") # should not recive those pkts
                        if len(BeforeRenego)>2:res2.entend(BeforeRenego)
                        else:res2.append([f'PRx sent only Control Error and 8 bit Received Power Packets after CFG at {{{CFG[2]}}}',Enums.TestResult.PASS])
                    else:res2.append([f'PRx did not sent CFG Packet',Enums.TestResult.INCONCLUSIVE])
            else:
                res1.append([f'PRx did not supports Restricted Mode at DP 128kHz',Enums.TestResult.PASS])
                # TPT to send MPP-Pattern to CFG packet
                id=MPP[2]+1
                if Check['flow']==1:
                    for pkt in Check['Pkts']:
                        Pac=self.PktMethod.GetPacketDetails(packet=pkt[0],value=pkt[1], limit=[id,flow1[1]])
                        if len(Pac)>2:
                            Response=self.PktResponse(Pac[2]+1,flow1[1])
                            if Response is not None:res1.append([f'TPT sent Response {Response[0]} for the {pkt[0]} {"" if pkt[1] is None else pkt[1]} Packet at {{{Pac[2]}}}',Enums.TestResult.PASS])
                            else:res1.append([f'TPT did not sent Response for the {pkt[0]} {"" if pkt[1] is None else pkt[1]} Packet at {{{Pac[2]}}}',Enums.TestResult.FAIL])  
                            id=Pac[2]+1 
                        else:res1.append([f'PRx did not sent {pkt[0]} {"" if pkt[1] is None else pkt[1]} Packet' ,Enums.TestResult.INCONCLUSIVE])

                    # Check EPT pkt
                    End_Power=self.PktMethod.GetPacketDetails(packet="End Power Transfer", value= "[EPT/rep]",limit=[id,flow1[1]])
                    if len(End_Power)>2:
                        res1.append([f'PRx sent End Power Transfer Re-Ping Packet at {{{End_Power[2]}}} to Enter in to 360 Phase',Enums.TestResult.PASS])
                    else:res1.append([f'PRx did not sent End Power Transfer Re-Ping Packet in 128 Flow',Enums.TestResult.INCONCLUSIVE])
                else:
                    # Check Restricted Bit 360 F1ow
                    MPP=self.PktMethod.GetPacketDetails(packet=Pkt, limit=flow2)
                    if len(MPP)>2:
                        RestrictedBit=self.MPPRestrictedBit(MPP[2])
                        if not RestrictedBit:
                            res2.append([f'PRx did not supports Restricted Mode at DP 360kHz',Enums.TestResult.PASS])
                            # check Nego Pkts
                            iid=MPP[2]+1
                            while iid < flow2[1]:
                                if self.file_list[iid]['description']=="Nego" and not self.file_list[iid]['isTesterPkt']:
                                    if any(x in self.file_list[iid]['pktType'] for x in Check['NegPkts']):
                                    # if self.file_list[iid]['pktType'] in Check['NegPkts']:
                                        res2.append([f'PRx sent {self.file_list[iid]['pktType']} Packet at {{{iid}}} in Nego Flow',Enums.TestResult.PASS])
                                    else:
                                        res2.append([f'PRx sent {self.file_list[iid]['pktType']} Packet at {{{iid}}} in Nego Flow which is not in List :{Check['NegPkts']}',Enums.TestResult.FAIL])
                                if self.file_list[iid]['description']=="PT":break 
                                iid+=1
                        else: res2.append([f'PRx set the Restricted Bit to 1 in MPP_Extended_Identification PKT at {{{MPP[2]}}} in to 360 Phase',Enums.TestResult.FAIL])
                    else:res2.append([f'PRx did not sent MPP-Extended Identification Packet in 360 Flow',Enums.TestResult.INCONCLUSIVE])   

        if Check['flow']==1 :return res1
        else: return res2

    def MPLA_PrectCheck(self,CTSCheck,Check,flows,flwID):
        res=[]
        self.Flow_limit = flows[flwID]['Limit']
        # Check Stabilization
        Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=self.Flow_limit)
        res.append([f'PRx {'did not Stabilized to Negotiable Load Power'  if len(Stable)<2 else ''} Stabilized at {{{Stable[2]}}}',Enums.TestResult.PASS if len(Stable)>2 else Enums.TestResult.INCONCLUSIVE ])
        # Check PLA Timing and Prect Delta
        # find First PLA


        id=self.Flow_limit[0]
        Timings=[]
        PrectDelta=[]
        while id < self.Flow_limit[1]:
            FPLA=self.PktMethod.GetexactPacketDetails(packet=Check['Pkt'][0],limit=[id,self.Flow_limit[1]])
            FRP,FPrect=self.FormatPLA(FPLA[2],Check['Pkt'][0])
            # Check Response for PLA
            Response=self.PktResponse(FPLA[2]+1,self.Flow_limit[1])
            if Response is not None :
                if'NAK' in Response[0]:
                    res.append([f'TPT sent {Response[0]} for PLA packet at {{{FPLA[2]}}}',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'TPT did not sent response for PLA packet at {{{FPLA[2]}}}',Enums.TestResult.INCONCLUSIVE])
            
            if len(FPLA)>2:
                SPLA=self.PktMethod.GetexactPacketDetails(packet=Check['Pkt'][0],limit=[FPLA[2]+1,self.Flow_limit[1]])
                if len(SPLA)>2:
                    SRP,SPrect=self.FormatPLA(SPLA[2],Check['Pkt'][0])
                    if SPrect >7.5:
                        Limit=[FPrect-0.95,FPrect+1.05]
                        delta=round((SPrect-FPrect),3)
                        result=True if SPrect >Limit[0] and SPrect < Limit[1] else False
                        if not result:
                            res.append([f' Measured PRECT_delta for PLA between {{{FPLA[2]}}} and PLA at {{{SPLA[2]}}} is {delta} W ,Limit :{Limit}',Enums.TestResult.FAIL])
                        else: PrectDelta.append([round(FPLA[0],3),round(SPLA[0],3),FPLA[2],delta])
                    Timings.append([round(FPLA[0],3),round(SPLA[0],3),FPLA[2],round(( SPLA[0] - FPLA[0]) * 1000, 3)])
                    id=SPLA[2]
                else:break
            else:break
        if Timings:
            min_item = min(Timings, key=lambda x: x[-1])
            max_item = max(Timings, key=lambda x: x[-1])
            res.append([f'Measured Max PLA from {max_item[0]} Sec to {max_item[1]} Sec at {{{max_item[2]}}} is {max_item[-1]} mS --- for {len(Timings)} {Check['Pkt'][0]} Packets, Limit: <=2050 mS', Enums.TestResult.FAIL if  max_item[-1] > 2050 else Enums.TestResult.PASS])
            res.append([f'Measured Min PLA from {min_item[0]} Sec to {min_item[1]} Sec at {{{min_item[2]}}} is {min_item[-1]} mS --- for {len(Timings)} {Check['Pkt'][0]} Packets, Limit: <=2050 mS', Enums.TestResult.FAIL if  min_item[-1] > 2050 else Enums.TestResult.PASS])
        else:
            res.append([f'Test did not found any MPLA Packets',Enums.TestResult.FAIL])

        if PrectDelta:
            min_item = min(PrectDelta, key=lambda x: x[-1])
            max_item = max(PrectDelta, key=lambda x: x[-1])
            res.append([f'Measured Max PRECT_delta from {max_item[0]} Sec to {max_item[1]} Sec at {{{max_item[2]}}} is {max_item[-1]} W',Enums.TestResult.PASS])
            res.append([f'Measured Min PRECT_delta from {min_item[0]} Sec to {min_item[1]} Sec at {{{min_item[2]}}} is {min_item[-1]} W', Enums.TestResult.PASS])

        return res
    
    
    def Cloak_PingExit(self,CTSCheck,Check,flows,flwID):
        res=[]
        cl_reason =0
    
        self.Flow_limit = flows[flwID]['Limit']
        PTPhaseLimit=self.FindPhase(self.Flow_limit[0],"PT")
        if PTPhaseLimit is not None:
            # find DSR /poll
            DSR=self.PktMethod.GetPacketDetails(packet="DSR",value="POLL", limit=[PTPhaseLimit[0],self.Flow_limit[1]])
            if len(DSR)>2:
                Response=self.PktResponse(DSR[2]+1,self.Flow_limit[1])
                cl_reason = self.PktMethod.GetPayloadDetails(Response[1],"Reason")[0]['sDescription'] 
                if Response is not None and 'Coex' in cl_reason:
                    res.append([f'TPT sent {Response[0]} Response with reason:{cl_reason} for the DSR/poll Packet at {{{DSR[2]}}}', Enums.TestResult.PASS])
                    # find Cloak Packet from PRx
                    Cloak=self.PktMethod.GetPacketDetails(packet="Cloak", limit=[Response[1]+1,self.Flow_limit[1]])
                    
                   
                    if len(Cloak)>2:
                        Response=self.PktResponse(Cloak[2]+1,self.Flow_limit[1])
                        if Response is not None:
                           res.append([f'TPT sent {Response[0]} Response for the Cloak Packet at {{{Cloak[2]}}}', Enums.TestResult.PASS if 'ACK' in Response[0] else Enums.TestResult.INCONCLUSIVE]) 
                           id=Response[1]+1
                           # find TCloakDelay
                           DelayTime=round(((30000*1.05 + 50)*1.1*1.05)+1,3)
                           DT=self.PktMethod.GetPacketDetails(packet="Cloak_Ping_Detach",Type="TesterMsg", limit=[id,self.Flow_limit[1]])
                           AT=self.PktMethod.GetPacketDetails(packet="Cloak_Ping_Attach",Type="TesterMsg", limit=[id,self.Flow_limit[1]])
                           if len(DT)>2 and len(AT)>2:DelayTime=round((((round((AT[0]-DT[1])*1000,3))*1.05 + 50)*1.1*1.05)+1,3)
                               
                           # find Cloak Pings
                           count=0
                           DetachTime=0
                           while id < self.Flow_limit[1]:
                                Attach=self.PktMethod.GetPacketDetails(packet="Cloak_Ping_Attach",Type="TesterMsg", limit=[id,self.Flow_limit[1]])
                                if len(Attach)>2:
                                    if count==2:
                                        
                                        Timeduration=round((Attach[0]-DetachTime)*1000,3)
                                        res.append([f'TPT delayed 3rd Cloak Ping by {Timeduration} mS , Exp :{DelayTime-1} mS',Enums.TestResult.PASS if Timeduration > DelayTime-10 else Enums.TestResult.INCONCLUSIVE])
                                        # find Cloak pkt 
                                        Cloak=self.PktMethod.GetPacketDetails(packet="Cloak", limit=[Attach[2]+1,self.Flow_limit[1]])
                                        if len(Cloak)>2:
                                            res.append([f'PRx sent Cloak packet at {{{Cloak[2]}}} for the Cloak ping : {count+1} ',Enums.TestResult.FAIL])
                                        else:res.append([f'PRx did not sent Cloak packet for the Cloak ping : {count+1} ',Enums.TestResult.PASS])
                                        # find SIG packet at next ping
                                        Ping=self.PktMethod.GetPacketDetails(packet='Ping Initiated',value="128",Type="TesterMsg",limit=[Attach[2]+1,len(self.file_list)-1])
                                        if len(Ping)>2:
                                            SS = self.PktMethod.GetPacketDetails(packet='Signal strength',limit=[Ping[2]+1,len(self.file_list)-1])
                                            if len(SS)>2:res.append([f'PRx sent Signal Strength Packet at {{{SS[2]}}} for the Next Digital ping at {{{Ping[2]}}}',Enums.TestResult.PASS])
                                            else:res.append([f'PRx did not sent Signal Strength Packet for the ping at {{{Ping[2]}}}',Enums.TestResult.FAIL])
                                            
                                        else:res.append([f'TPT did not Initiated next ping after Cloak Exit',Enums.TestResult.INCONCLUSIVE])
                                        
                                    Detach=self.PktMethod.GetPacketDetails(packet="Cloak_Ping_Detach",Type="TesterMsg", limit=[Attach[2]+1,self.Flow_limit[1]])
                                    if len(Detach)>2:
                                        count+=1
                                        DetachTime=Detach[1]
                                        # find Cloak pkt 
                                        Cloak=self.PktMethod.GetPacketDetails(packet="Cloak", limit=[Attach[2]+1,Detach[2]])
                                        if len(Cloak)>2:
                                            res.append([f'PRx sent Cloak packet at {{{Cloak[2]}}} for the Cloak ping : {count} ',Enums.TestResult.PASS])
                                        else:res.append([f'PRx did not sent Cloak packet for the Cloak ping : {count} ',Enums.TestResult.FAIL])
                                        id=Detach[2]+1
                                    else:break 
                                else:break    

                        else: res.append([f'TPT did not sent any Response for Cloak Packet at {{{Cloak[2]}}}',Enums.TestResult.INCONCLUSIVE]) 
                    else:res.append([f'PRx did not sent Cloak pkt after the FSK CLOAK at {{{Response[1]}}}',Enums.TestResult.INCONCLUSIVE]) 
                else:res.append([f'TPT did not sent any Response for DSR/Poll at {{{DSR[2]}}}',Enums.TestResult.INCONCLUSIVE])
            else:res.append([f'PRx did not Initiated DSR/Poll Packet',Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not Entered to Power Transfer Phase',Enums.TestResult.INCONCLUSIVE])

        return res

    def MagneticPresenceCheck(self,CTSCheck,Check,flows,flwID):

        res=[]
        if flwID==2: self.Flow_limit = flows[flwID]['Limit']
        else:
            if self.TestData['FileList_Data'][self.Header['TestcaseID']]['flows'][str(flwID)] is not None:
                self.Flow_limit = self.TestData['FileList_Data'][self.Header['TestcaseID']]['flows'][str(flwID)]['Limit']
                self.file_list=self.TestData['FileList_Data'][self.Header['TestcaseID']]['Json']
                self.PktMethod.file_list=self.file_list
            else: return [f'Test Data not Found after removing the Magnetic Cover',Enums.TestResult.INCONCLUSIVE]

        PT=self.PktMethod.GetPacketDetails(packet="Phase_Info",value="Phase Type: PT" if flwID==2 else "Phase Type : PT", Type="TesterMsg",limit=self.Flow_limit)
        if len(PT)>2:
            res.append([f'PRx entered Power Transfer Phase at {{{PT[2]}}}',Enums.TestResult.PASS])
            id=PT[2]+1
            count=0
            CE={'Extended Control Error':[],'Control Error':[]}
            while id <self.Flow_limit[1]:
                if self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    count+=1
                    if 'Control Error' in self.file_list[id]['pktType']:CE[self.file_list[id]['pktType']].append(self.file_list[id]['pktType'])
                id+=1
            if count>=50:
                res.append([f'PRx sent {count} Packets in Power Transfer Phase',Enums.TestResult.PASS])

                if len(CE[Check['CE']])>0:res.append([f'PRx sent {len(CE[Check["CE"]])} {Check["CE"]} Packets in Power Transfer Phase',Enums.TestResult.PASS])
                else:res.append([f'PRx did not sent any {Check["CE"]} Packets in Power Transfer Phase',Enums.TestResult.FAIL])

                if len(CE[Check['CE2']])>0:
                    res.append([f'PRx sent {len(CE[Check["CE2"]])} {Check["CE2"]} Packets in Power Transfer Phase',Enums.TestResult.FAIL])
                else:res.append([f'PRx did not sent any {Check["CE2"]} Packets in Power Transfer Phase',Enums.TestResult.PASS])    

            else:res.append([f'PRx did not sent only {count} Packets in Power Transfer Phase , Exp :50',Enums.TestResult.INCONCLUSIVE])
   
        else:res.append([f'PRx did not Entered to Power Transfer Phase',Enums.TestResult.INCONCLUSIVE])

        return res


    #----------------------------------------------------------------------------------- Support Functions -------------------------------------------------------------------------------------#
    
    def Find_PLA_ATN(self,id,Check):
        while id < self.Flow_limit[1]:
            PLA=self.PktMethod.GetPacketDetails(packet=Check['PowerPkt'], limit=[id,self.Flow_limit[1]])
            if len(PLA)>2:
                Response=self.PktResponse(PLA[2]+1,self.Flow_limit[1])
                if Response is not None:
                    if 'ATN' in Response[0]:return PLA[2]
                id=PLA[2]+1
            else:return self.Flow_limit[1]

    def csv_to_json(self,csv_filepath):
        
        output = {}
        with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
        # Data rows start from row index 3 (0-indexed)
        for row in rows[3:]:
            if not any(row):  # Skip empty rows
                continue
            record = {
                "Timestamp": float(row[1]),
                "Packet": row[2],
                "Magnitude Results": {
                    "Amplitude": {
                        "Value": float(row[3]),
                        "Limit": row[4].strip("[] ").strip().replace("]",'')
                    },
                    "Modulation Index": {
                        "Value": float(row[5]),
                        "Limit": row[6].strip("[] ").strip().replace("]",'') if row[6] not in ('', '-1') else -1
                    },
                    "SNR": {
                        "Value": float(row[7]),
                        "Limit": row[8].strip("[] ").strip().replace("]",'')
                    },
                    "Half bit period": {
                        "Value": float(row[9]),
                        "Limit": row[10].strip("[] ").strip().replace("]",'')
                    },
                    "Eye width": {
                        "Value": float(row[11]),
                        "Limit": row[12].strip("[] ").strip().replace("]",'')
                    },
                    "Fclk": {
                        "Value": float(row[13]),
                        "Limit": row[14].strip("[] ").strip().replace("]",'')
                    },
                    "Yth": float(row[15]) if row[15] else None,
                    "InitialYth": float(row[16]) if row[16] else None
                },
                "Phase Results": {
                    "Amplitude": {
                        "Value": float(row[17]) if len(row) > 17 and row[17] else None,
                        "Limit": row[18].strip("[] ").strip().replace("]",'') if len(row) > 18 and row[18] else None
                    },
                    "SNR": {
                        "Value": float(row[19]) if len(row) > 19 and row[19] else None,
                        "Limit": row[20].strip("[] ").strip().replace("]",'') if len(row) > 20 and row[20] else None
                    },
                    "Half bit period": {
                        "Value": float(row[21]) if len(row) > 21 and row[21] else None,
                        "Limit": row[22].strip("[] ").strip().replace("]",'') if len(row) > 22 and row[22] else None
                    },
                    "Eye width": {
                        "Value": float(row[23]) if len(row) > 23 and row[23] else None,
                        "Limit": row[24].strip("[] ").strip().replace("]",'') if len(row) > 24 and row[24] else None
                    },
                    "Fclk": {
                        "Value": float(row[25]) if len(row) > 25 and row[25] else None,
                        "Limit": row[26].strip("[] ").strip().replace("]",'') if len(row) > 26 and row[26] else None
                    },
                    "Yth": float(row[27]) if len(row) > 27 and row[27] else None,
                    "InitialYth": float(row[28]) if len(row) > 28 and row[28] else None
                }
            }

            output[int(row[0])] = record

        return output
    

    def EyeTest(self,Check):
        res=[]
        values={
            "Npass_Magnitude":0,
            "Npass_Phase":0,
            "Npass":0,
            "pkts":0
        }
        PathList = self.Header['CapturePath'].split('\\')
        EyeInfoPath = CommonMethods.find_file('/'.join(PathList[0:len(PathList)-1]),'AnalysisData_EYE.csv')
        Eyeresults=self.csv_to_json(EyeInfoPath)
        # with open('Eye.json', 'w') as json_file:
        #     json.dump(Eyeresults, json_file, indent=4)
        for pktcount in Eyeresults:
            values['pkts']+=1    
            # pkts+=1
            res.append([f'PRx sent {Eyeresults[pktcount]['Packet']} at { Eyeresults[pktcount]['Timestamp']} Sec', Enums.TestResult.PASS])
            dum1=[]
            MagnitudeResult=True
            for key in Check['Magnitude']:
                result=False
                if  Eyeresults[pktcount]['Magnitude Results'][key]['Value'] is not None:
                    match Check['Magnitude'][key][0]:
                        case "GTE":result= True if Eyeresults[pktcount]['Magnitude Results'][key]['Value'] >= Check['Magnitude'][key][1] else False
                        case "Between":result= True if Eyeresults[pktcount]['Magnitude Results'][key]['Value'] >= Check['Magnitude'][key][1] and   Eyeresults[pktcount]['Magnitude Results'][key]['Value'] <=Check['Magnitude'][key][2] else False
                    if key =="Amplitude" and Check.get('Modulation',False)and not result:
                        result= True if Eyeresults[pktcount]['Magnitude Results']["Modulation Index"]['Value'] >= 3 else False
                        dum1.append([f'Measured Magnitude : Modulation Index Measurement is { Eyeresults[pktcount]['Magnitude Results']["Modulation Index"]['Value']} Limit:{Eyeresults[pktcount]['Magnitude Results']["Modulation Index"]['Limit']} ',Enums.TestResult.PASS if result else Enums.TestResult.FAIL])
                    else:dum1.append([f'Measured Magnitude :{key} Measurement is { Eyeresults[pktcount]['Magnitude Results'][key]['Value']} Limit:{Eyeresults[pktcount]['Magnitude Results'][key]['Limit']} ',Enums.TestResult.PASS if result else Enums.TestResult.FAIL])

                    if not result:MagnitudeResult=False
                else:
                    dum1.append([f'Measured Magnitude :{key} is None',Enums.TestResult.INCONCLUSIVE])
                    MagnitudeResult=False
            if not MagnitudeResult:
                dum2=[]
                PhaseResult=True
                for key in Check['Phase']:
                    result=False
                    if  Eyeresults[pktcount]['Phase Results'][key]['Value'] is not None:
                        match Check['Phase'][key][0]:
                            case "GTE":result= True if Eyeresults[pktcount]['Phase Results'][key]['Value'] >= Check['Phase'][key][1] else False
                            case "Between":result= True if Eyeresults[pktcount]['Phase Results'][key]['Value'] >= Check['Phase'][key][1] and   Eyeresults[pktcount]['Phase Results'][key]['Value'] <=Check['Phase'][key][2] else False

                        if not result:PhaseResult=False
                        dum2.append([f'Measured Phase :{key} Measurement is {Eyeresults[pktcount]['Phase Results'][key]['Value']} Limit:{Eyeresults[pktcount]['Phase Results'][key]['Limit']} ',Enums.TestResult.PASS if result else Enums.TestResult.FAIL])
                    else: 
                        dum2.append([f'Measured Phase :{key} is None',Enums.TestResult.INCONCLUSIVE])
                        PhaseResult=False    

                if len(dum2)>0:  res.extend(dum2)
              
                if not PhaseResult:
                     if len(dum1)>0:res.extend(dum1)   

                if PhaseResult:
                    values['Npass']+=1
                    values['Npass_Phase']+=1
                    # Npass+=1
                    # Npass_Phase+=1
    
            else:
                if len(dum1)>0:
                    values['Npass']+=1
                    values['Npass_Magnitude']+=1
                    # Npass_Magnitude+=1
                    # Npass+=1
                    res.extend(dum1)   

        return res,values
    
    def CloakPingDelay(self,limit):
        val=0
        id=limit[0]
        while id < limit[1]:
            if  'SRQ [0x20]' in self.file_list[id]['pktType'] and 'Cloak Ping Delay High' in self.file_list[id]['value']:
                cloak_high_value = float((self.PktMethod.GetPayloadDetails(id, 'Cloak_Ping_Delay_Value_High')[0]['sDescription']).split(":")[1].replace("S", ""))*1000
                val+=cloak_high_value
            elif 'SRQ [0x20]' in self.file_list[id]['pktType'] and 'Cloak Ping Delay' in self.file_list[id]['value']:
                value_low = float(self.file_list[id]['value'].split(":")[1].replace('}','').replace('S',''))*1000
                val+=value_low
                break
            id+=1

        return val
    
    def MPPRestrictedBit(self,id):
        RestrictedBit=self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(id,'Restricted')[0]['sRawData'])
        if RestrictedBit==1:return True
        else:False

    def NegoValidate(self,limit,pkts,Inconclusive=True,Response=True):
        res=[]
        id=limit[0]
        while id <= limit[1]:
            if not self.file_list[id]['isTesterPkt']  and not self.file_list[id]['isFWTestermessage']  :
                pktfound=False
                for pkt in pkts:
                    if pkt[0] in self.file_list[id]['pktType'] and True if pkt[1] is None else pkt[1] in self.file_list[id]['value']:
                        pktfound=True
                        PktName=pkt[0]+" "+pkt[1] if pkt[1] is not None else pkt[0]
                        if Response:
                            # Check Response
                            Response=self.PktResponse(id+1,self.Flow_limit[1])
                            if Response is not None:
                                res.append([f'TPT sent {Response[0]} at {{{Response[1]}}} for PRx - {PktName} Packet at {{{id}}}',Enums.TestResult.PASS if pkt[2] in Response[0] else Enums.TestResult.INCONCLUSIVE])
                            else:res.append([f'TPT did not sent Response for the Pkt {PktName} at {{{id}}}',Enums.TestResult.INCONCLUSIVE])
                        else:res.append([f'PRx sent the  {PktName} at {{{id}}}',Enums.TestResult.PASS])
                        break
                if not pktfound: res.append([f' PRx sent the Pkt {self.file_list[id]['pktType']} {self.file_list[id]['value']} at {{{id}}} which is not a Nego Phase Pkt',Enums.TestResult.INCONCLUSIVE if Inconclusive else Enums.TestResult.FAIL])      
            id+=1
        return res

        
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

    def PchTime(self,Neg=False):
        pchtime=5
        PchPkt=False
        pchcount,Pchval=self.Pch()
        if pchcount>0:
            pchtime=Pchval[pchcount-1]
            PchPkt=True
        if Neg:
            id=self.Flow_limit[0]
            while id < self.Flow_limit[1]:
                Pch=self.PktMethod.GetPacketDetails(packet="SRQ [0x20] ",value="Power Control Hold Off",limit=[id,self.Flow_limit[1]])
                if len(Pch)>2:
                    pchtime=GeneralMethods.GetFloatFromStr(self.PktMethod.GetPayloadDetails(Pch[2],"Power_Control_Hold_Off_Time")[0]['sRawData'])[0]
                    id=Pch[2]+1
                    PchPkt=True
                else:break

        return pchtime,PchPkt

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
                    status = ( Enums.TestResult.PASS if result else (  Enums.TestResult.INCONCLUSIVE if PayLoads[Pd_id].get("Inconclusive_Check", False) else Enums.TestResult.FAIL ) )
                    if (not PayLoads[Pd_id].get("Result_check",True) and not result) or PayLoads[Pd_id].get("Result_check",True):
                        desp=CommonMethods.GetCompDes(PayLoads[Pd_id].get("Exp"),PayLoads[Pd_id].get("comp"))
                        # res.append( [f'{'PRx'if Receiver else 'PTx'} sent the {PayLoads[Pd_id].get("Name")} Field with Val {actual_val}  for the  {PacketName} datapacket at Id @{Index}, Exp:{PayLoads[Pd_id].get("Exp")},Comp :{PayLoads[Pd_id].get("comp")}.', status])
                        res.append( [f'{'PRx'if Receiver else 'PTx'} sent the {PayLoads[Pd_id].get("Name")} Field with Val {actual_val}  for the  {PacketName} data packet , Exp:{desp}', status])
                    Check=True
            if not Check:res.append([f'{'PRx'if Receiver else 'PTx'} did not sent Expected {PayLoads[Pd_id].get("Name")} in the {PacketName} Data Packet  at {{{Index}}}, Exp:{PayLoads[Pd_id].get("Exp")} , Comp :{PayLoads[Pd_id].get("comp")}.',Enums.TestResult.FAIL])   
            Pd_id+=1
        return res

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
      
    
    def Get360Pings(self,value):
        pings=[]
        id=0
        while id < len(self.file_list)-1:
            PD = self.PktMethod.GetPacketDetails(packet='Ping Initiated',value=value,Type="TesterMsg",limit=[id,len(self.file_list)-1])
            if len(PD)>2:
                SD= self.PktMethod.GetPacketDetails(packet='Shutdown',Type="TesterMsg",limit=[PD[2],len(self.file_list)-1])
                if len(SD)>2:
                    pings.append([PD[2],SD[2]])
                    id=SD[2]+1
                else:
                    pings.append([PD[2],len(self.file_list)-1])
                    break      
            else:break
        return pings
       
    def CheckPkts(self,start,end,pkts):
        res=[]
        for pkt in pkts:
            PktName=pkt[0]+""if pkt[1] is None else pkt[0]+"_"+pkt[1]
            pktfound=False
            id=start
            while id < end:
              
                if (pkt[0] in self.file_list[id]['pktType'] and True if pkt[1] is None else pkt[1] in self.file_list[id]['value']) and not self.file_list[id]['isTesterPkt']:
                    pktfound=True
                    res.append([f"{PktName} Pkt is found at {{{id}}}",Enums.TestResult.PASS])
                    #  #Check payload  if required
                    if pkt[2]:
                        PL=self.Payload_Details(PacketName=PktName,Index=id,PayLoads=pkt[3])
                        if len(PL)>0:res.extend(PL)
                id+=1
            if not pktfound:res.append([f"{PktName} pkt did not found",Enums.TestResult.FAIL])
        return res
    
    def Check_CE_PLA(self,start,end,CE,PLA):
        res=[]
        id=start
        while id < end:
            if self.file_list[start]['pktType']==CE  or self.file_list[start]['pktType']==PLA:
                res.append([f'PRx sent {self.file_list[start]['pktType']} at {{{start}}}',Enums.TestResult.FAIL])
            id+=1
        return res

    def Get_Alpha(self,id,pkt):
        CoilVals={}
        if pkt in ["Power_Loss_Accounting_Parameters",'Power Loss Accounting Parameters']:
           CoilVals["g_Coil_Tx"]=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(id,'g_coil_T')[0]['sRawData']))/10000
           CoilVals["Alpha_FM_DC"]=float(self.PktMethod.GetPayloadDetails(id,'Alpha_FM_DC')[0]['sDescription'].split("(")[1].replace(")",""))
           CoilVals["Alpha_FM"]=float(self.PktMethod.GetPayloadDetails(id,'Alpha FM:')[0]['sDescription'].split("(")[1].replace(")",""))

        else:
            vals=self.file_list[id]['value'].removeprefix("-").replace(" ","").replace("{","").replace("}","").split('|')
            for val in vals:CoilVals[val.split(":")[0]]= float(val.split(":")[1])
        return CoilVals
        

    def PrectValues(self,limit):
        Prect=[]
        id=limit[0]
        while id <limit[1]:
            if "CAL_CAPTURE [0x96]" in self.file_list[id]['pktType']:
                Power=float(self.file_list[id]['value'].split("|")[1].split(":")[1].replace("W",""))
                Prect.append(Power)
            id+=1
        return Prect
    
    def PLA_RRP_Prect(self,Pkt,limit,Target=None):
        ReceivedPowers=[]
        PrectPowers=[]
        Count=0
        id=limit[0]
        while id <limit[1]:
            if Pkt in self.file_list[id]['pktType']:
                ReceivedPower,PRECT =self.FormatPLA(id,Pkt)
                ReceivedPowers.append(ReceivedPower)
                PrectPowers.append(PRECT)
                Count+=1
                if Target is not None and Count>=Target:break
            id+=1
        return ReceivedPowers,PrectPowers
               

    def FormatPLA(self,id,Pkt):
        ReceivedPower=PRECT=None
        if Pkt=="Power Loss Accounting":
            ReceivedPower=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(id,'Received_Power_Value')[0]['sRawData']))/1000
            PRECT=(self.PktMethod.hex_to_decimal(self.PktMethod.GetPayloadDetails(id,'PRECT')[0]['sRawData']))/1000
        else:
            ReceivedPower=float(self.file_list[id]['value'].split("RP:")[1].split("|")[0].replace("W",""))
            PRECT=float(self.file_list[id]['value'].split("|")[1].split(":")[1].replace("W",""))
          
        return ReceivedPower,PRECT    


    
    def CheckResponseForPkts(self,limit,pkts=[]):
        res=[]
        for pkt in pkts:
            id=limit[0]
            while id < limit[1]:
                if pkt[0] in self.file_list[id]['pktType'] and True if pkt[1] is None else pkt[1] in self.file_list[id]['value']:
                    #Check Response
                    Response=self.PktResponse(id+1,self.Flow_limit[1])
                    if Response is not None:
                        res.append([f"{ pkt[0]} {"" if pkt[1] is None else pkt[1]} is found at {{{id}}} with Response as {Response[0]}",Enums.TestResult.PASS if pkt[2] in Response[0] else Enums.TestResult.FAIL])
                    else:res.append([f"{ pkt[0]} {"" if pkt[1] is None else pkt[1]} is found at {{{id}}} with No Response ",Enums.TestResult.FAIL])
                id+=1
        return res

    def PLA2_Timing(self,Pkt,limit,Target=None):

        Timings=[]
        PktsCount=0
        id=limit[0]
        while id < limit[1]:
            if  Pkt in self.file_list[id]['pktType'] :
                pkt2= self.PktMethod.GetPacketDetails(packet=Pkt,limit=[id+1,limit[1]])
                if len(pkt2)>2:
                    PktsCount+=1
                    Timings.append([round((self.file_list[pkt2[2]]['startTime']-self.file_list[id]['startTime'])*1000,2),id,pkt2[2]])
                    if Target is not None and PktsCount>=Target:break
                    id=pkt2[2]
                else:break  
            else:id+=1
        return Timings


    def PLA2_Fast(self,Pkt,limit,TimeLimit=[],Percentage=None,Target=None):

        res=[]
        TimingsId=self.PLA2_Timing(Pkt,limit,Target=None)
        FailCount=0
        Timings=[]
        for Time in TimingsId:
            Timings.append(Time[0])
            if TimeLimit[0]=="GTE":
                if Time[0] < TimeLimit[1]:
                    if Percentage is None:res.append([f'Measured Tpla_fast from {Pkt} at id{Time[1]} to {Pkt} at id{Time[2]}is {Time[0]} mS Limit : >={TimeLimit[1] } mS', Enums.TestResult.FAIL])
                    FailCount+=1
            if TimeLimit[0]=="LTE":
                if Time[0] > TimeLimit[1]:
                    if Percentage is None:res.append([f'Measured Tpla_fast from {Pkt} at id{Time[1]} to {Pkt} at id{Time[2]}is {Time[0]} mS Limit : <={TimeLimit[1] } mS', Enums.TestResult.FAIL])
                    FailCount+=1
                
        if Percentage is not None:
            if FailCount >  int((Percentage/100) * len(Timings)):
                res.append([f'Measured  Max Tpla_fast is {max(Timings)} mS ,Min Tpla_fast is {min(Timings)} mS  for {len(Timings)} Packets ,Limit :{TimeLimit[0]} {TimeLimit[1] } mS', Enums.TestResult.FAIL])
                res.append([f'More than {Percentage}% of the Intervals met the fail criteria', Enums.TestResult.FAIL])
            else:res.append([f'Measured  Max Tpla_fast is {max(Timings)} mS ,Min Tpla_fast is {min(Timings)} mS for {len(Timings)} Packets ,Limit :{TimeLimit[0]} {TimeLimit[1] } mS', Enums.TestResult.PASS])
        else: res.append([f'Measured  Max Tpla_fast is {max(Timings)} mS ,Min Tpla_fast is {min(Timings)} mS for {len(Timings)} Packets ,Limit : {TimeLimit[0]} {TimeLimit[1] } mS', Enums.TestResult.PASS])
           
        return res
    
    def PLA_MSR(self,NegotiablePower,Check,limit,NegotiablePercentage=10):

        res=[]
        PowerVals=[]
        Stable=self.PktMethod.GetPacketDetails(packet="Stabilized",Type="TesterMsg",limit=limit)
        if len(Stable)>2:                                           
            # Collect the First PLA Prect Val
            FirstPLA=self.PktMethod.GetPacketDetails(packet=Check['Pkt'][0],limit=[Stable[2]+1,limit[1]])
            if len(FirstPLA)>2:
                RRP,Power=self.FormatPLA(FirstPLA[2],Check['Pkt'][0])
                res.append([f"Measured Prect_Power value in {Check['Pkt'][0]} pkt after Stabilization is {Power} W  at {{{FirstPLA[2]}}}, Expected Range :[{round((NegotiablePower-(NegotiablePercentage/100)*NegotiablePower),2)},{round((NegotiablePower+(NegotiablePercentage/100)*NegotiablePower),2)}]", Enums.TestResult.INCONCLUSIVE if Power > (NegotiablePower+(NegotiablePercentage/100)*NegotiablePower) or Power < (NegotiablePower-(NegotiablePercentage/100)*NegotiablePower) else Enums.TestResult.PASS])
                id=FirstPLA[2]+1
                Count=0
                while id <limit[1]:
                    if Check['Pkt'][0] in self.file_list[id]['pktType'] :
                        ReceivedPower,PrectPower=self.FormatPLA(id,Check['Pkt'][0])
                        Vals=[id,ReceivedPower,PrectPower]
                        id=id+1
                        while id < limit[1]:
                            if "MPLA_Vin_Ppt" in self.file_list[id]['pktType']:
                                TransmitterPower=float(self.file_list[id]['pktType'].split("|")[-1].replace("W;",""))
                                Vals.append(TransmitterPower)
                                PowerVals.append(Vals)
                                id+=1
                                break
                            id+=1
                        Count+=1
                    if Count>=Check['PktsCount']:break
                    if "MSR [0x13]" in  self.file_list[id]['pktType'] and  not self.file_list[id]['isTesterPkt']:
                        return self.PLA_MSR(NegotiablePower,Check,limit=[id+1,limit[1]],NegotiablePercentage=NegotiablePercentage)
                    id+=1
            else:
                res.append([f"PRx did not sent the {Check['Pkt'][0]} after Stabilization",Enums.TestResult.INCONCLUSIVE])
        else:res.append([f'PRx did not stabilized to Negotiable Load Power',Enums.TestResult.INCONCLUSIVE])

        return res,PowerVals
    
    def PFOMeasures(self,Check,PowerVals):
        results=[]
        PowerLevls={}
        for Level in Check['PFORange'].keys():
            if Level not in PowerLevls:PowerLevls[Level]=[]
            AveragePFO=[]
            for Power in PowerVals: #Power=[id,RecivedPower,PRect,Transmitter power]                       
                match Check['PFORange'][Level]['PowerVal'][0]:
                    case "GT":
                        if Power[2] > Check['PFORange'][Level]['PowerVal'][1]:
                            PowerLevls[Level].append(Power) 
                            AveragePFO.append(round((Power[-1]-Power[1])*1000,3))         
                    case "LTE":
                        if Power[2] <= Check['PFORange'][Level]['PowerVal'][1]: 
                            PowerLevls[Level].append(Power)
                            AveragePFO.append(round((Power[-1]-Power[1])*1000,3))
                           
            if len(PowerLevls[Level])>0:
                PL= f' > {Check['PFORange'][Level]['PowerVal'][1]} W' if Check['PFORange'][Level]['PowerVal'][0] =='GT'else f' <= {Check['PFORange'][Level]['PowerVal'][1]} W'
                MaxPFO=max(AveragePFO)
                MinPFO=min(AveragePFO)
                pkts=len(AveragePFO)
                count=0
                for Power in PowerLevls[Level]:
                    PFO=round((Power[-1]-Power[1])*1000,3)
                    if PFO < Check['PFORange'][Level]['2'][0] or PFO>=Check['PFORange'][Level]['2'][1]:
                        count+=1
                        if count >1:
                            results.append([f'Calculated PFO Value is {PFO} mW at {{{Power[0]}}}  is in  out of Range Expected range :{ Check['PFORange'][Level]['2']},Power level : {PL}',Enums.TestResult.FAIL])
               
                results.append([f'Calculated Max PFO Value is {MaxPFO} mW and Min PFO Value is {MinPFO} mW --- for the {pkts} {Check['Pkt'][0]} Packets, Expected range :{ Check['PFORange'][Level]['2']} , Power level : {PL}' ,Enums.TestResult.PASS])
                AveragePFO=round((sum(AveragePFO)/len(AveragePFO)),3)
                self.TestData['TestResults'][self.Header['TestcaseID']]=AveragePFO # Store the Average PFO value in Json
                self.TestResultsjson.update_file(self.TestData)
                results.append([f'Calculated Average PFO value for the {pkts} {Check['Pkt'][0]} Packets is {AveragePFO} mW , Expected range :{ Check['PFORange'][Level]['1']},Power level : {PL}',Enums.TestResult.FAIL if AveragePFO < Check['PFORange'][Level]['1'][0] or AveragePFO >=Check['PFORange'][Level]['1'][1] else 'pass'])
        return results 



    def Group_PRECT(self,PrectVals):
        Levels={"L1":[],"L2":[],"L3":[]}
        for val in PrectVals:
            if 8.0 <= val < 11.0:
                Levels['L1'].append(val)
            elif 11.0 <= val < 13.0:
                Levels['L2'].append(val)
            elif 13.0 <= val < 15.5:
                Levels['L3'].append(val)
        return Levels
    
    def DplossValues(self,limit):
        values=[]
        id=limit[0]
        while id < limit[1]:
            if 'DeltaPLoss' in self.file_list[id]['pktType']:
                values.append(float(self.file_list[id]['pktType'].split("|")[1].replace(";","")))
            id+=1
        return values


    #-------------------------------------------------------------------------------------------------------------- Ranjith -------------------------------------------------------------------------------#

    def cloak_TC_Natural(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']
        #check sequence entered the PT phase
        pt_pass = False
        cl_pass = False
        check_clk_list = []
        check_clk = False
        
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                for cl in range(pt+1, self.Flow_limit[1]):
                    if 'Cloak Phase' in self.file_list[cl]['description']:      
                        cl_pass = True
                        break
                break
        if pt_pass and cl_pass:
            #check cloak_low and high in SRQ
            cloak_high = False
            cloak_low = False
            value_low = None
            cloak_high_value = None
            t_cloak = Check['t_cloak']  #default value if cloak_l / h not presents in sequence
            for clk_ping_delay in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'SRQ [0x20] ' in self.file_list[clk_ping_delay]['pktType'] and 'Cloak Ping Delay High' in self.file_list[clk_ping_delay]['value']:
                    cloak_high = True
                    cloak_high_value = self.PktMethod.GetPayloadDetails(clk_ping_delay, 'Cloak_Ping_Delay_Value_High')[0]['sDescription']
                    print(cloak_high_value)
                    cloak_high_value = float(cloak_high_value.split(":")[1].strip().replace("S", ""))
                    cloak_high_value = cloak_high_value * 1000
                    print(cloak_high_value)
                    break
            for clk_ping_d_low in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'SRQ [0x20] ' in self.file_list[clk_ping_d_low]['pktType'] and 'Cloak Ping Delay' in self.file_list[clk_ping_d_low]['value']:
                    cloak_low = True
                    value_low = self.file_list[clk_ping_d_low]['value']
                    value_low = float(re.search(r'[\d.]+', value_low).group()) * 1000
                    print(value_low)
                    break
            if cloak_high and cloak_low:
                t_cloak = cloak_high_value + value_low
            print(t_cloak)
            #check Prx triggers the Cloak_phase
            cloak_found = False
            for clk in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'Cloak' in self.file_list[clk]['pktType'] and not self.file_list[clk]['isTesterPkt']:
                    cloak_found = True
                    res.append([f"Cloak by Prx was initiated at index-{self.file_list[clk]['rowIndex']}", Enums.TestResult.PASS])
                    reason = self.PktMethod.GetPayloadDetails(clk, 'Reason')[0]['sDescription']
                    if Check['reason'] in reason:
                        res.append([f"Cloak_Reason: {Check['reason']} was observed", Enums.TestResult.PASS])
                    else:
                        res.append([f"Cloak_Reason: {Check['reason']} was not observed", Enums.TestResult.FAIL])
                    clk += 1
                    #set the new_limit for cloak check
                    clk_limit = []
                    start = 0
                    end = 0
                    for limit in range(clk, self.Flow_limit[1]+1):
                        if 'Phase_Info' in  self.file_list[limit]['pktType'] and 'Cloak' in self.file_list[limit]['value']:
                            start = limit
                            limit += 1
                            for limit_1 in range(limit, self.Flow_limit[1]+1):
                                if 'Phase_Info' in  self.file_list[limit_1]['pktType'] and 'Reset' in self.file_list[limit_1]['value']:
                                    end = limit_1
                            break
                    clk_limit = [start, end+1]
                    print(clk_limit)
                    break
            #check report packet and their response 
            report_ID = False
            for rep in range(clk_limit[0], clk_limit[1]):
                if 'Report' in self.file_list[rep]['pktType'] and not self.file_list[rep]['isTesterPkt']:
                    prx_id = self.PktMethod.GetPayloadDetails(rep, 'Report_ID')[0]['sDescription']
                    if 'PRx Identification' in prx_id:
                        report_ID = True
                        #response
                        response_ack = self.GetPacketResponse3(rep, [rep,clk_limit[1]])
                        if self.file_list[response_ack]['pktType'] == 'ACK':           
                            res.append([f"Report packet with PRx Identification found at index-{self.file_list[rep]['rowIndex']}", Enums.TestResult.PASS])
                            res.append([f"TPT send ACK response for the Report packet at index-{self.file_list[response_ack]['rowIndex']}", Enums.TestResult.PASS])
                            #Get[Ptx XID] packet and TPT respond with XID
                            check_ptx_xid = False
                            check_response_xid = False
                            response_xid = 0
                            # print(prx_id, report_ID)
                            if prx_id and report_ID:
                                # print("eneterd get request")
                                for ptx_xid in range(response_ack+1, clk_limit[1]):
                                    if 'Get Request' in self.file_list[ptx_xid]['pktType'] and not self.file_list[ptx_xid]['isTesterPkt'] and 'PTx Extended Identification' in self.file_list[ptx_xid]['value']:
                                        check_ptx_xid = True
                                        res.append([f"GET[PTx XID] request was found at index-{self.file_list[ptx_xid]['rowIndex']}", Enums.TestResult.PASS])
                                        #response
                                        response_xid = self.GetPacketResponse3(ptx_xid, [ptx_xid,clk_limit[1]])
                                        EPTI=  "Extended_Power_Transmitter_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Power Transmitter Identification"

                                        if self.file_list[response_xid]['pktType'] == EPTI and self.file_list[response_xid]['isTesterPkt']: 
                                            check_response_xid = True
                                            res.append([f"TPT responded with XID packet for the request GET[PTx XID] index-{self.file_list[response_xid]['rowIndex']}", Enums.TestResult.PASS])
                                        break
                            if not check_ptx_xid:
                                res.append([f"GET[PTx XID] request was not found at Index- [{response_ack+1, clk_limit[1]}]", Enums.TestResult.FAIL])
                            if not check_response_xid:
                                res.append([f"TPT not responded with XID packet for the request GET[PTx XID", Enums.TestResult.FAIL])
                            
                            #check PT phase after the sequence
                            # print(check_ptx_xid , response_xid)
                            if check_ptx_xid and response_xid != 0:
                                # print("eneterrd _check pt")
                                PT_phase_check = False
                                for pt in range(response_xid+1, clk_limit[1]):
                                    if ('PT' in self.file_list[pt]['description'] and ('Extended Control Error' in self.file_list[pt]['pktType'] or 'Power Loss Accounting' in self.file_list[pt]['pktType'])):
                                        PT_phase_check = True
                                        res.append([f"Sequence entered into PT phase again, Index-[{pt, clk_limit[1]}]", Enums.TestResult.PASS])
                                        break
                                if not PT_phase_check:
                                    res.append([f"Sequence not enetered into the PT phase after the cloak exit. Index- [{response_xid+1, clk_limit[1]}]", Enums.TestResult.FAIL])                     
                    break
            if not report_ID:
                res.append([f"Report[Prx ID] packet was not observed at the cloak phase index- {clk_limit}", Enums.TestResult.FAIL])
            
        elif not pt_pass:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"The packet sequence doesn't entered Cloak phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def cloak_Tc(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']
        #check wheather entered PT phase
        #check sequence entered the PT phase
        pt_pass = False
        cl_pass = False
        check_clk_list = []
        check_clk = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                for cl in range(pt+1, self.Flow_limit[1]):
                    if 'Cloak Phase' in self.file_list[cl]['description']:      
                        cl_pass = True
                        break
                break
        print(pt_pass, cl_pass)
        if pt_pass and cl_pass:
            #check cloak_low and high in SRQ
            cloak_high = False
            cloak_low = False
            value_low = None
            cloak_high_value = None
            t_cloak = Check['t_cloak']  #default value if cloak_l / h not presents in sequence
            for clk_ping_delay in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'SRQ [0x20] ' in self.file_list[clk_ping_delay]['pktType'] and 'Cloak Ping Delay High' in self.file_list[clk_ping_delay]['value']:
                    cloak_high = True
                    cloak_high_value = self.PktMethod.GetPayloadDetails(clk_ping_delay, 'Cloak_Ping_Delay_Value_High')[0]['sDescription']
                    print(cloak_high_value)
                    cloak_high_value = float(cloak_high_value.split(":")[1].strip().replace("S", ""))
                    cloak_high_value = cloak_high_value * 1000
                    print(cloak_high_value)
                    break
            for clk_ping_d_low in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'SRQ [0x20] ' in self.file_list[clk_ping_d_low]['pktType'] and 'Cloak Ping Delay' in self.file_list[clk_ping_d_low]['value']:
                    cloak_low = True
                    value_low = self.file_list[clk_ping_d_low]['value']
                    value_low = float(re.search(r'[\d.]+', value_low).group()) * 1000
                    print(value_low)
                    break
            if cloak_high and cloak_low:
                t_cloak = cloak_high_value + value_low
            print(t_cloak)
            #check Prx triggers the Cloak_phase
            cloak_found = False
            for clk in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'Cloak' in self.file_list[clk]['pktType'] and not self.file_list[clk]['isTesterPkt']:
                    cloak_found = True
                    res.append([f"Cloak by Prx was initiated at index-{self.file_list[clk]['rowIndex']}", Enums.TestResult.PASS])
                    reason = self.PktMethod.GetPayloadDetails(clk, 'Reason')[0]['sDescription']
                    if Check['reason'] in reason:
                        res.append([f"Cloak_Reason: {reason} was observed", Enums.TestResult.PASS])
                    else:
                        res.append([f"Cloak_Reason: {reason} was not observed", Enums.TestResult.FAIL])
                    clk += 1
                    #set the new_limit for cloak check
                    clk_limit = []
                    start = 0
                    end = 0
                    for limit in range(clk, self.Flow_limit[1]+1):
                        if 'Phase_Info' in  self.file_list[limit]['pktType'] and 'Cloak' in self.file_list[limit]['value']:
                            start = limit
                            limit += 1
                            for limit_1 in range(limit, self.Flow_limit[1]+1):
                                if 'Phase_Info' in self.file_list[limit_1]['pktType'] and 'Reset' in self.file_list[limit_1]['value']:
                                    end = limit_1
                            break
                    clk_limit = [start, end+1]
                    print(clk_limit)
                    if len(clk_limit) == 2:
                        #check Atleast 3 cycle of cloak packets in cloak pings by Prx
                        cloak_count = 0
                        assertions_details = []
                        attach = 0
                        detach = 0
                        cloak = 0
                        exp_pings = False
                        id = clk_limit[0]
                        while id <= clk_limit[1]:
                            check_clk = False
                            if 'Cloak_Ping_Attach' in self.file_list[id]['pktType'] and self.file_list[id]['isTesterPkt']:
                                attach = id
                                id+= 1
                                id_1 = id
                                while id_1 <= clk_limit[1]:
                                    if 'Cloak_Ping_Detach' in self.file_list[id_1]['pktType'] and self.file_list[id_1]['isTesterPkt']:
                                        detach = id_1 
                                        #Get cloak packets during the interval
                                        for clk_1 in range(attach, detach):
                                            if 'Cloak' in self.file_list[clk_1]['pktType'] and not  self.file_list[clk_1]['isTesterPkt']:
                                                check_clk = True
                                                check_clk_list.append(clk_1)
                                                response = self.GetPacketResponse3(clk_1, [clk_1, clk_limit[1]])
                                                if self.file_list[response]['pktType'] == 'ACK':
                                                    cloak = response
                                                break
                                        assertions_details.append([[attach, detach], cloak])
                                        break
                                    elif 'Cloak_Ping_Attach' in self.file_list[id_1]['pktType'] and self.file_list[id_1]['isTesterPkt']:
                                        break
                                    id_1 +=1                                
                            id += 1
                        print(assertions_details)
                        if len(assertions_details) >= 3:
                            exp_pings = True
                    else: res.append([f"Cloak phase expected pings are not observed", Enums.TestResult.INCONCLUSIVE])
                    break
            if exp_pings:                       
                value = []
                attach_time = []
                #Measure t_cloak
                ck = 0
                while ck <= len(assertions_details)-1:
                    value.append(self.file_list[assertions_details[ck][1]]['stopTime'])
                    ck+=1
                #get the attach time from the limit 
                print(value)
                for attach in range(1, len(assertions_details)):
                    attach_time.append(self.file_list[assertions_details[attach][0][0]]['startTime'])
                    # print(self.file_list[assertions_details[attach][0][0]]['rowIndex'],attach_time)
                # print(attach_time)
                result_ms = [round((b - a) * 1000, 3) for a, b in zip(value, attach_time)]  #measurement for t_cloak
                print(result_ms)
                limit_range = [0.95*t_cloak, 1.05*t_cloak]
                # print(limit_range)
                t_cloak_check = []
                t_clk = True
                for i, val in enumerate(result_ms):
                    if not (limit_range[0] <= val <= limit_range[1]):
                        start_idx = assertions_details[i][0][1]
                        stop_idx = assertions_details[i+1][0][0]
                        print(f"Out of range: {val} ms")
                        print(f"Start index: {start_idx}, Stop index: {stop_idx}")
                        res.append([f"Measured t_cloak : {val} ms was not within the range at [Start index: {start_idx}, Stop index: {stop_idx}] Expected Range:{limit_range}", Enums.TestResult.FAIL])
                        t_clk = False
                        t_cloak_check.append(t_clk)
                    else: 
                        t_clk = True
                        t_cloak_check.append(t_clk)

                if all(t_cloak_check):
                    res.append([f"All t_cloak measured are proper or within the range, Expected range: Expected Range:{limit_range}", Enums.TestResult.PASS])

                #check 3 cyle of cloak initiated and also check the reasons 
                # print(check_clk_list)
                if Check['cloak_cycle'] is not None:
                    if len(check_clk_list) >= Check['cloak_cycle']:
                        res.append([f"{Check['cloak_cycle']}x ASK cloak packets have recieved", Enums.TestResult.PASS])
                    else: res.append([f"{Check['cloak_cycle']}x ASK cloak packets have recieved", Enums.TestResult.FAIL])

                #t_wake measurement
                if Check['t_wake']:
                    cloak_count_1 = 1
                    if len(check_clk_list) >= 3:
                        for s, e in zip(assertions_details,check_clk_list):
                            # print(s[0][0], e)
                            t_wake = round((self.file_list[e]['startTime'] - self.file_list[s[0][0]]['startTime']) * 1000,3)
                            print(t_wake)
                            if (19 <= t_wake <= 64):
                                res.append([f"Cloak_{cloak_count_1} - Measured t_wake: {t_wake}ms which is  within the range. Expected : 19ms <= t_wake <= 64ms", Enums.TestResult.PASS])
                            else: res.append([f"Cloak_{cloak_count_1} - Measured t_wake: {t_wake}ms  which is not within the range. Expected : 19ms <= t_wake <= 64ms", Enums.TestResult.FAIL])
                            cloak_count_1 += 1
                
                #check reason for the cloak packet
                reason_cloak_1 = []
                reason_cloak_check = False
                for res_1 in range(0, len(check_clk_list)-1):
                    reason_response = self.PktMethod.GetPayloadDetails(check_clk_list[res_1], 'Reason')[0]['sDescription']
                    # print(reason_response)
                    if Check['reason'] in reason:
                        reason_cloak_check = True
                        reason_cloak_1.append(reason_cloak_check)
                        # res.append([f"Cloak_Reason: {Check['reason']} was observed", Enums.TestResult.PASS])
                    else:
                        reason_cloak_check = False
                        reason_cloak_1.append(reason_cloak_check)
                        # print(reason_response)
                        res.append([f"Cloak_Reason: {Check['reason']} was not observed at packet index: {check_clk_list[res_1]}", Enums.TestResult.FAIL])
                if all(reason_cloak_1):
                    res.append([f"All observed cloak reason are {Check['reason']}", Enums.TestResult.PASS])
                

                #check report sequence check  - 11.4.3 test case validation
                report_ID = False
                reportid =[]
                report_count = 1
                t_response = []
                if Check['report_check']:
                    for rep in range(clk_limit[0], clk_limit[1]):
                        report_ID = False
                        #check first report packet
                        if 'Report' in self.file_list[rep]['pktType'] and not self.file_list[rep]['isTesterPkt']:
                            print("Enetred_report")
                            prx_id = self.PktMethod.GetPayloadDetails(rep, 'Report_ID')[0]['sDescription']
                            print(prx_id)
                            if 'PRx Identification' in prx_id:
                                if report_count == 1:
                                    res.append([f"1st Report PRx ID packet was observed at index-{self.file_list[rep]['rowIndex']}", Enums.TestResult.PASS])
                                else:
                                    res.append([f"2nd Report PRx ID packet was observed at index-{self.file_list[rep]['rowIndex']}", Enums.TestResult.PASS])
                                report_ID = True
                                reportid.append(report_ID)
                                t_response.append(rep)
                                #check response
                                response_ack_1 = self.GetPacketResponse3(rep, [rep,rep+2]) 
                                if response_ack_1 == None:
                                    response_ack_1 = 0
                                print(f"count{report_count}, {response_ack_1}")                               
                                if report_count == 1 and response_ack_1 == 0:
                                    res.append([f"TPT muted the reply for the 1st PRx ID report packet", Enums.TestResult.PASS])
                                elif report_count == 1 and response_ack_1 != 0:
                                    res.append([f"TPT not muted the reply for the 1st PRx ID report packet", Enums.TestResult.FAIL])
                                elif report_count == 2 and response_ack_1 > 0 and self.file_list[response_ack_1]['pktType'] == 'ACK':
                                    res.append([f"TPT reply with ACK response for the PRx ID report packet. Index - {response_ack_1}", Enums.TestResult.PASS])
                                elif report_count == 2 and response_ack_1 == 0:
                                    res.append([f"TPT not reply with ACK response for the PRx ID report packet", Enums.TestResult.FAIL])
                            report_count += 1
                    if not all(reportid) and reportid <= 1:
                        res.append([f"Expected retry of Report PRx ID packet was not observed. Index - {clk_limit}", Enums.TestResult.INCONCLUSIVE])
                    
                    #t_responsetimeout measurement
                    if len(t_response) == 2 and all(reportid):
                        t_response_timeout = 0                      
                        t_response_timeout = round((self.file_list[t_response[1]]['startTime'] - self.file_list[t_response[0]]['stopTime']) * 1000,3)
                        print(t_response_timeout)
                        if t_response_timeout >= 15:
                            res.append([f"Observed t_response : {t_response_timeout}ms, when PTx did not respond to the 1st report packet, Limit = >= 15ms", Enums.TestResult.PASS])
                        else: res.append([f"Observed t_response : {t_response_timeout}ms, when PTx did not respond to the 1st report packet, Limit = >= 15ms", Enums.TestResult.FAIL])     
                
            else: res.append(["Expected count of cloak pings were not initiated", Enums.TestResult.INCONCLUSIVE])

        elif not pt_pass:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"The packet sequence doesn't entered Cloak phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def cloak_TC_tx_init(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']
        #check wheather entered PT phase
        #check sequence entered the PT phase
        pt_pass = False
        cl_pass = False
        check_clk_list = []
        check_clk = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                for cl in range(pt+1, self.Flow_limit[1]):
                    if 'Cloak Phase' in self.file_list[cl]['description']:      
                        cl_pass = True
                        break
                break
        print(pt_pass, cl_pass)
        response_atn = 0
        response_atn_check = False
        response_dsr_check = False
        ptx_cloak_check = False
        prx_cloak_check = False
        cloak_response_check = False
        t_ptx_cloak = []
        new_limit = []
        start = 0
        end =0
        if pt_pass:   
            # check clk phase first attach ping
            for ping in range(self.Flow_limit[0], self.Flow_limit[1]-1):
                if 'Phase_Info' in  self.file_list[ping]['pktType'] and 'Cloak' in self.file_list[ping]['value']:
                    start = ping
                    break
            print(start)
            # check which XCE packet have ATN
            for xce in range(self.Flow_limit[0], start):
                if 'Extended Control Error' in self.file_list[xce]['pktType'] and not self.file_list[xce]['isTesterPkt']:
                    response_atn = self.GetPacketResponse3(xce, [xce, start])
                    if response_atn is None:
                        response_atn = 0
                    #check ATN response
                    if response_atn != 0 and self.file_list[response_atn]['pktType'] == 'ATN':
                        print(response_atn)
                        res.append([f"XCE packet with ATN response observed at index -[{response_atn}]", Enums.TestResult.PASS])
                        response_atn_check = True
            # res.append(msg) #for xce with ATN response
            #Check DSR packet
            for dsr in range(response_atn, start):
                if 'DSR' in self.file_list[dsr]['pktType'] and 'POLL' in self.file_list[dsr]['value'] and not self.file_list[dsr]['isTesterPkt']:
                    response_dsr_check = True
                    res.append([f"DSR packet was found at index -[{dsr}]", Enums.TestResult.PASS])
                    #check PTx cloak packet
                    for clk in range(dsr, start):
                        if 'Cloak' in self.file_list[clk]['pktType'] and self.file_list[clk]['isTesterPkt']:
                            ptx_cloak_check = True
                            clk_reason = self.PktMethod.GetPayloadDetails(clk, 'Reason')[0]['sDescription']
                            if Check['reason'] in clk_reason:
                                res.append([f"Cloak by TPT was initiated at index -[{clk}]", Enums.TestResult.PASS])
                                res.append([f"Cloak_Reason: {clk_reason} was observed", Enums.TestResult.PASS])
                                t_ptx_cloak.append(clk)
                            #check PRx cloak packet
                            prx_cloak = self.GetPacketResponse3(clk, [clk, start], uut = True)
                            print(prx_cloak, "prx_cloak")
                            if self.file_list[prx_cloak]['pktType'] == 'Cloak' and not self.file_list[prx_cloak]['isTesterPkt']:
                                prx_cloak_check = True
                                res.append([f"Cloak by Prx was observed at index -[{prx_cloak}]", Enums.TestResult.PASS])
                                t_ptx_cloak.append(prx_cloak)
                                #check cloak response ACK
                                cloak_response = self.GetPacketResponse3(prx_cloak, [prx_cloak, self.Flow_limit[1]])  
                                if self.file_list[cloak_response]['pktType'] == 'ACK' and self.file_list[cloak_response]['isTesterPkt']: 
                                    cloak_response_check = True
                                    res.append([f"ACK response was observed for PRx cloak packet at index -[{cloak_response}]", Enums.TestResult.PASS])
                            break
                    break

            #check t_ptx_cloak measurement
            if ptx_cloak_check and prx_cloak_check and len(t_ptx_cloak) == 2 and Check['t_ptx_cloak']:
                t_ptx_cloak_value =  round((self.file_list[t_ptx_cloak[1]]['startTime'] - self.file_list[t_ptx_cloak[0]]['stopTime']) * 1000,3)
                if t_ptx_cloak_value <= Check['t_ptxcloak']:
                    res.append([f"Measured t_ptx_cloak: {t_ptx_cloak_value}ms, Limit: t_ptx_cloak <= {Check['t_ptxcloak']}ms", Enums.TestResult.PASS])
                else: res.append([f"Measured t_ptx_cloak: {t_ptx_cloak_value}ms, Limit: t_ptx_cloak <= {Check['t_ptxcloak']}ms", Enums.TestResult.FAIL])
            
            if not response_atn_check:
                res.append([f"ATN response was not observed for any XCE packet", Enums.TestResult.INCONCLUSIVE])
            if not response_dsr_check:
                res.append([f"DSR packet response was not observed", Enums.TestResult.INCONCLUSIVE])
            if not ptx_cloak_check:
                res.append([f"Ptx cloak packet was not observed", Enums.TestResult.INCONCLUSIVE])
            if not prx_cloak_check:
                res.append([f"Prx cloak packet was not observed", Enums.TestResult.INCONCLUSIVE])
            if not cloak_response_check:
                res.append([f"ACK response was not observed for the PRx cloak packet", Enums.TestResult.INCONCLUSIVE])
            
            if Check['ptx_cloak'] and cloak_response_check and prx_cloak_check:
                #store end limit
                for limit_1 in range(start, self.Flow_limit[1]):
                    if 'Cloak_Ping_Detach' in self.file_list[limit_1]['pktType'] and self.file_list[limit_1]['isTesterPkt']:
                        end = limit_1

                new_limit = [start, end]
                print(new_limit)
                clk_list = []
                clk_list_res = []
                response_clk = False
                cloak_count = 1
                #check cloak cycles 
                for cl in range(new_limit[0], new_limit[1]-1):
                    if 'Cloak' in self.file_list[cl]['pktType'] and not self.file_list[cl]['isTesterPkt']:
                        clk_list.append(cl)
                        # res.append([f"Cloak-{cloak_count} packet found at {round(self.file_list[cl]['startTime'], 3)} sec", Enums.TestResult.PASS])
                        #check response
                        cloak_response = self.GetPacketResponse3(cl, [cl, new_limit[1]])
                        if self.file_list[cloak_response]['pktType'] == 'ACK':
                            response_clk = True
                            clk_list_res.append(response_clk)
                            response_clk = False
                        cloak_count += 1
                print(clk_list)
                print(clk_list_res)
                if len(clk_list) >= 3 and len(clk_list_res) == len(clk_list):
                    res.append([f"{cloak_count}x cloak cycle was observed. Minimum 3x cloak cycle is expected", Enums.TestResult.PASS])
                elif len(clk_list) >= 3 and len(clk_list_res) != len(clk_list):
                    res.append([f"Cloak response missing for the cloak packet", Enums.TestResult.INCONCLUSIVE])
                else: res.append([f"{cloak_count}x cloak cycle was observed. Minimum 3x cloak cycle is expected", Enums.TestResult.FAIL])

                #next new limit for exit handshake sequence
                for limit_2 in range(end, self.Flow_limit[1]):
                    if 'Phase_Info' in self.file_list[limit_2]['pktType'] and 'Reset' in self.file_list[limit_2]['value']:
                        end_1 = limit_1
                #check cloak exit handshake 
                cloak_with_atn = False
                clk_atn = 0
                for ex in range(end, end_1):
                    if 'Cloak' in self.file_list[ex]['pktType'] and not self.file_list[ex]['isTesterPkt']:
                        clk_atn = self.GetPacketResponse3(ex, [ex, end_1])
                        if self.file_list[clk_atn]['pktType'] == 'ATN':
                            cloak_with_atn = True
                if cloak_with_atn:
                    report_ID = False
                    response_ack = 0
                    res.append([f"Cloak with ATN response was observed at index -[{clk_atn}]", Enums.TestResult.PASS])
                    #check report ID
                    for rep in range(clk_atn , end_1):
                        if 'Report' in self.file_list[rep]['pktType'] and not self.file_list[rep]['isTesterPkt']:
                            prx_id = self.PktMethod.GetPayloadDetails(rep, 'Report_ID')[0]['sDescription']
                            if 'PRx Identification' in prx_id:
                                report_ID = True
                                #response
                                response_ack = self.GetPacketResponse3(rep, [rep,end_1])
                                if self.file_list[response_ack]['pktType'] == 'ACK':           
                                    res.append([f"Report packet with PRx Identification found at index -[{rep}]", Enums.TestResult.PASS])
                                    res.append([f"TPT send ACK response for the Report packet at index -[{response_ack}]", Enums.TestResult.PASS])
                    #Get[Ptx XID] packet and TPT respond with XID
                    check_ptx_xid = False
                    check_response_xid = False
                    response_xid = 0
                    for ptx_xid in range(response_ack+1, end_1):
                        if 'Get Request' in self.file_list[ptx_xid]['pktType'] and not self.file_list[ptx_xid]['isTesterPkt'] and 'PTx Extended Identification' in self.file_list[ptx_xid]['value']:
                            check_ptx_xid = True
                            res.append([f"GET[PTx XID] request was found at index -[{ptx_xid}]", Enums.TestResult.PASS])
                            #response
                            response_xid = self.GetPacketResponse3(ptx_xid, [ptx_xid,end_1])
                            EPTI=  "Extended_Power_Transmitter_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Power Transmitter Identification"

                            if self.file_list[response_xid]['pktType'] == EPTI and self.file_list[response_xid]['isTesterPkt']: 
                                check_response_xid = True
                                res.append([f"TPT responded with PTx_XID packet for the request GET[PTx XID] at index -[{response_xid}]", Enums.TestResult.PASS])
                            break
                    if not check_ptx_xid:
                        res.append([f"GET[PTx XID] request was not found at Index- [{response_ack+1, self.Flow_limit[1]}]", Enums.TestResult.FAIL])
                    if not check_response_xid:
                        res.append([f"TPT not responded with PTx_XID packet for the request GET[PTx XID]", Enums.TestResult.FAIL])
                    
                    #check PT phase after the exit handshake in cloak phase                
                    if check_ptx_xid and response_xid != 0:
                        # print("eneterrd _check pt")
                        PT_phase_check = False
                        for pt_phase in range(response_xid, self.Flow_limit[1]):
                            if ('PT' in self.file_list[pt_phase]['description'] and ('Extended Control Error' in self.file_list[pt_phase]['pktType'] or 'Power Loss Accounting' in self.file_list[pt_phase]['pktType'])):
                                PT_phase_check = True
                                res.append([f"Sequence entered into PT phase again, Index-[{pt_phase, self.Flow_limit[1]}]", Enums.TestResult.PASS])
                                break
                        if not PT_phase_check:
                            res.append([f"Sequence not enetered into the PT phase after the cloak exit. Index- [{response_xid+1, self.Flow_limit[1]}]", Enums.TestResult.FAIL])   
                                      
                else: res.append([f"Cloak with ATN response was not observed", Enums.TestResult.INCONCLUSIVE])
           
        elif not pt_pass:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def ping_retry(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']
        value = None
        pt_pass = False
        cl_pass = False
        # with open("data.json", "w") as file:
        #     json.dump(self.file_list, file, indent=4)
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                for cl in range(pt+1, self.Flow_limit[1]):
                    if 'Cloak Phase' in self.file_list[cl]['description']:      
                        cl_pass = True
                        break
                break
        # print(pt_pass, cl_pass)
        if pt_pass and cl_pass:
            #check the SRQ-Detect ping packet
            srq_detect = False
            cloak_detect_value = False
            for det_pg in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'SRQ [0x20] ' in self.file_list[det_pg]['pktType'] and 'Cloak Detect Ping' in self.file_list[det_pg]['value']:
                    srq_detect = True
                    match = re.search(r'\d+(\.\d+)?', self.file_list[det_pg]['value'])  # extract the first number (int or float) from the string
                    if match:
                        value = float(match.group()) 
                        res.append([f"Cloak Detect Ping with value {value} ms was observed at Index-{det_pg}", Enums.TestResult.PASS])
                    if value != 0 or value != 0.0:
                        cloak_detect_value = True
                        res.append([f"SRQ-Detect ping packet was observed at index-{self.file_list[det_pg]['rowIndex']}", Enums.TestResult.PASS])
                    #check response for the detect ping
                    response_detect = self.GetPacketResponse3(det_pg, [det_pg, self.Flow_limit[1]])
                    if response_detect != 0 and self.file_list[response_detect]['pktType'] == 'ACK':
                        res.append([f"ACK response was observed for the SRQ-Detect ping packet at index-{self.file_list[response_detect]['rowIndex']}", Enums.TestResult.PASS])
                    else: res.append([f"ACK response was not observed for the SRQ-Detect ping packet", Enums.TestResult.FAIL])
                    break
            if cloak_detect_value:
                #proceed next step
                #check the stable and update the new limit after the stable
                new_limit = []
                coun = 1
                xce_stable = []
                xce_values = []
                xce_stable_check = ['-3', '-2', '-1', '0', '1', '2', '3']
                
                        
                for st in range(response_detect, self.Flow_limit[1]):
                    if 'MPP_XCE_Stabilized' in self.file_list[st]['pktType']:
                        new_l = st
                        new_limit = [new_l, self.Flow_limit[1]]
                        # print(self.Flow_limit[1], st)
                        for st_1 in range(self.Flow_limit[0], st):
                            # print(st_1)
                            if 'Extended Control Error' in self.file_list[st_1]['pktType'] and not self.file_list[st_1]['isTesterPkt']:
                                xce_values.append(self.file_list[st_1]['value'])
                        break
                
                print(xce_values)
                xce_values = xce_values[::-1]
                xce_values = xce_values[:5]
                XCEV = any(item in xce_stable_check for item in xce_values)
                print(XCEV)
                if XCEV:
                    res.append([f"Stable was observed for the XCEV packets with {xce_values} before the MPP_XCE_Stabilized. Expected: XCEV +- 3", Enums.TestResult.PASS])   
                else: res.append([f"Stable was not observed for the XCEV packet with value in {xce_values} before the MPP_XCE_Stabilized. Expected: XCEV +- 3", Enums.TestResult.FAIL])
                
                print(new_limit)
                #check ATN response for the XCE packet after the stable
                check_atn = False
                for xce in range(new_limit[0], new_limit[1]):
                    if 'Extended Control Error' in self.file_list[xce]['pktType'] and not self.file_list[xce]['isTesterPkt']:
                        response_atn = self.GetPacketResponse3(xce, [xce, new_limit[1]])
                        if response_atn != 0 and self.file_list[response_atn]['pktType'] == 'ATN':
                            check_atn = True
                            res.append([f"ATN response was observed for the XCE packet at index-{self.file_list[response_atn]['rowIndex']}", Enums.TestResult.PASS])
                            break
                # print(check_atn)
                if check_atn:
                    #check DSR POLL response after ATN packet
                    check_dsr = False
                    for dsr in range(response_atn, new_limit[1]):
                        if 'DSR' in self.file_list[dsr]['pktType'] and 'POLL' in self.file_list[dsr]['value'] and not self.file_list[dsr]['isTesterPkt']:
                            check_dsr = True
                            res.append([f"DSR-POLL packet was observed at index-{self.file_list[dsr]['rowIndex']}", Enums.TestResult.PASS])
                            break
                if not check_atn:
                    res.append([f"ATN response was not observed for any XCE packet after the stable", Enums.TestResult.INCONCLUSIVE])
                if not check_dsr:
                    res.append([f"DSR-POLL packet was not observed for the ATN packet", Enums.TestResult.INCONCLUSIVE])
                
                #check the Prx cloak packet after the DSR POLL
                check_cloak_prx = False
                check_cloak_ptx = False
                cloak_ack_check = False
                cloak_1 = 0
                for clk in range(dsr, new_limit[1]):
                    if 'Cloak' in self.file_list[clk]['pktType'] and self.file_list[clk]['isTesterPkt']:
                        reason = self.PktMethod.GetPayloadDetails(clk, 'Reason')[0]['sDescription']
                        if Check['reason'] in reason:
                            check_cloak_prx = True
                            res.append([f"Cloak by Prx was initiated at index-{self.file_list[clk]['rowIndex']} sec with reason {reason}", Enums.TestResult.PASS])  
                            cloak_respons_by_ptx = self.GetPacketResponse3(clk, [clk, new_limit[1]], uut = True)  
                            if self.file_list[cloak_respons_by_ptx]['pktType'] == 'Cloak' and not self.file_list[cloak_respons_by_ptx]['isTesterPkt']:   
                                check_cloak_ptx = True
                                res.append([f"Cloak by PTx was observed at index-{self.file_list[cloak_respons_by_ptx]['rowIndex']}in response to Prx cloak", Enums.TestResult.PASS])    
                            cloak_ack = self.GetPacketResponse3(cloak_respons_by_ptx, [cloak_respons_by_ptx, new_limit[1]])
                            if self.file_list[cloak_ack]['pktType'] == 'ACK' and self.file_list[cloak_ack]['isTesterPkt']:
                                cloak_ack_check = True
                                cloak_1 = cloak_ack
                                res.append([f"ACK response was observed for the PTx cloak packet at {self.file_list[cloak_ack]['rowIndex']}", Enums.TestResult.PASS])         
                        break
                if not check_cloak_prx:
                    res.append([f"Cloak by Prx was not initiated after the DSR-POLL packet", Enums.TestResult.INCONCLUSIVE])
                if not check_cloak_ptx:
                    res.append([f"Cloak by PTx was not observed in response to Prx cloak", Enums.TestResult.INCONCLUSIVE])
                if not cloak_ack_check:
                    res.append([f"ACK response was not observed for the PTx cloak packet", Enums.TestResult.INCONCLUSIVE])

                if check_cloak_prx and check_cloak_ptx and cloak_ack_check:
                    #get cloak seq limit 
                    new_limit_1 = []
                    lim_1 = 0
                    for limit in range(cloak_ack, new_limit[1]):
                        if 'Phase_Info' in self.file_list[limit]['pktType'] and 'Cloak' in self.file_list[limit]['value']:
                            lim_1 = limit
                            for limit_1 in range(lim_1, new_limit[1]):
                                if 'Phase_Info' in self.file_list[limit_1]['pktType'] and 'Reset' in self.file_list[limit_1]['value']:
                                    new_limit_1 = [lim_1, limit_1]
                                    break
                            break
                    print(new_limit_1)
                    if len(new_limit_1) == 2:
                        assertions_details = []
                        check_clk_list = []
                        id = new_limit_1[0]               
                        while id <= new_limit_1[1]:
                            check_clk = False
                            if 'Cloak_Ping_Attach' in self.file_list[id]['pktType'] and self.file_list[id]['isTesterPkt']:
                                attach = id
                                id+= 1
                                id_1 = id
                                while id_1 <= new_limit_1[1]:
                                    if 'Cloak_Ping_Detach' in self.file_list[id_1]['pktType'] and self.file_list[id_1]['isTesterPkt']:
                                        detach = id_1 
                                        #Get cloak packets during the interval
                                        for clk_1 in range(attach, detach):
                                            if 'Cloak' in self.file_list[clk_1]['pktType'] and not  self.file_list[clk_1]['isTesterPkt']:
                                                check_clk = True
                                                check_clk_list.append(clk_1)
                                                response = self.GetPacketResponse3(clk_1, [clk_1, new_limit_1[1]])
                                                if self.file_list[response]['pktType'] == 'ACK':
                                                    cloak = clk_1
                                                break
                                        assertions_details.append([[attach, detach], cloak])
                                        break
                                    elif 'Cloak_Ping_Attach' in self.file_list[id_1]['pktType'] and self.file_list[id_1]['isTesterPkt']:
                                        break
                                    id_1 +=1                                
                            id += 1
                        # print(assertions_details)
                        #check 3x cloak ping cycle
                        if len(assertions_details) >= 3:
                            limit_4 = 0
                            res.append([f"{Check['cloak_cycle']}x cloak ping cycle was observed during the cloak phase, Cloak packet indexes - {check_clk_list}", Enums.TestResult.PASS])                         
                            # print(clk_detect_timeout_range)                            
                            print("clk_pings", assertions_details)
                            #take all short pings between the cloak initiated
                            shrt_pings = {}
                            shrt_pings_lst = []
                            for cl in assertions_details:
                                shrt_pings = {'attach': [], 'detach': []}
                                i = cloak_1
                                while i <= cl[1]-1:
                                    if 'Cloak_Detect_Ping_Attach' in self.file_list[i]['pktType'] and self.file_list[i]['isTesterPkt']:
                                        shrt_pings['attach'].append(i)
                                    elif 'Cloak_Detect_Ping_Detach' in self.file_list[i]['pktType'] and self.file_list[i]['isTesterPkt']:
                                        shrt_pings['detach'].append(i)         
                                    i+=1
                                shrt_pings_lst.append(shrt_pings)
                                cloak_1 = cl[1]                            
                            print(shrt_pings_lst)
                            shortpings = [[[att, det] for att, det in zip(d['attach'], d['detach'])]for d in shrt_pings_lst]
                            print(shortpings)
                            pings = []
                            #short pings measurement
                            for idx, (shrt, clk_2) in enumerate(zip(shortpings, assertions_details)):   
                                pings.append(shrt[0])
                                res.append([f"Received Short pings at indexes : {shrt[0]} for ASK cloak sequence:{idx+1}, Cloak index: {clk_2[1]}",Enums.TestResult.PASS])
                                                    
                            if len(pings) == len(assertions_details):
                                #measurement for t_d_active                            
                                for tact in pings:
                                    t_dactive = round((self.file_list[tact[1]]['startTime'] - self.file_list[tact[0]]['startTime']) * 1000,1)
                                    if Check['t_dactive'] == t_dactive:
                                        res.append([f"t_dactive measured between Cloak Detect Ping attach and detach is {t_dactive} ms which is equal to expected value {Check['t_dactive']} ms - measured index: [{tact}]", Enums.TestResult.PASS])
                                    else: res.append([f"t_dactive measured between Cloak Detect Ping attach and detach is {t_dactive} ms which is not equal to expected value {Check['t_dactive']} ms - measured index: [{tact}]", Enums.TestResult.FAIL])
                                #TPT goes to ping phase
                                check_ping_attach = False
                                sig = assertions_details[-1][1]
                                for att in range(sig, self.Flow_limit[1]):
                                    if 'Cloak_Ping_Attach' in self.file_list[att]['pktType'] and self.file_list[att]['isTesterPkt']:
                                        limit_4 = att
                                        check_ping_attach = True
                                        res.append([f"Cloak_Ping_Attach assertion observed at index: {self.file_list[att]['rowIndex']}", Enums.TestResult.PASS])
                                        break
                                if check_ping_attach:
                                    check_ping_phase = False
                                    for ping_ph in range(limit_4, new_limit_1[1]):
                                        if 'Signal strength' in self.file_list[ping_ph]['pktType'] and 'Cloak' in self.file_list[ping_ph]['description']:
                                            res.append([f"Prx Doesn't send ASK Cloak packets", Enums.TestResult.PASS])
                                            res.append([f"TPT entered into Ping phase at index-{self.file_list[ping_ph]['rowIndex']}", Enums.TestResult.PASS])
                                            check_ping_phase = True
                                            break
                                    if not check_ping_phase:
                                        res.append([f"TPT did not enter into Ping phase after the N cloak cycles", Enums.TestResult.FAIL])
                                else:
                                    res.append([f"Cloak_Ping_Attach assertion not observed", Enums.TestResult.INCONCLUSIVE])
                                
                            else: res.append([f"Expected Short pings not observed", Enums.TestResult.INCONCLUSIVE])
                        else: res.append([f"{Check['cloak_cycle']}x cloak ping cycle was observed during the cloak phase", Enums.TestResult.INCONCLUSIVE])

            else:
                res.append([f"Cloak Detect Ping value was 0 or not observed, expected non zero value", Enums.TestResult.INCONCLUSIVE])

        elif not pt_pass:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"The packet sequence doesn't entered Cloak phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def clk_Response(self,CTSCheck,Check,flows,flwID):
        # with open('QI.json', 'w') as json_file:
        #     json.dump(self.file_list, json_file, indent=4)
        res = []
        self.Flow_limit = flows[flwID]['Limit']
        value = None
        pt_pass = False
        cl_pass = False
        
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                for cl in range(pt+1, self.Flow_limit[1]):
                    if 'Cloak Phase' in self.file_list[cl]['description']:      
                        cl_pass = True
                        break
                break
        print(pt_pass, cl_pass)
        if pt_pass and cl_pass:
            #check ATN and DSR response for the XCE packet
            check_atn = False
            check_dsr = False
            prx_cloak_1 = False
            ptx_cloak = False
            prx_cloak_response = False
            cloak_ack = 0
            for xce in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'Extended Control Error' in self.file_list[xce]['pktType'] and not self.file_list[xce]['isTesterPkt']:
                    response_atn = self.GetPacketResponse3(xce, [xce, self.Flow_limit[1]])
                    if response_atn != 0 and self.file_list[response_atn]['pktType'] == 'ATN':
                        check_atn = True
                        res.append([f"ATN response was observed for the XCE packet at index-{self.file_list[response_atn]['rowIndex']}", Enums.TestResult.PASS])
                        #check DSR POLL response after ATN packet
                        for dsr in range(response_atn, self.Flow_limit[1]):
                            if 'DSR' in self.file_list[dsr]['pktType'] and 'POLL' in self.file_list[dsr]['value'] and not self.file_list[dsr]['isTesterPkt']:
                                check_dsr = True
                                res.append([f"DSR-POLL packet was observed at index-{self.file_list[dsr]['rowIndex']}", Enums.TestResult.PASS])
                                # check cloak initiate
                                cloak_response = self.GetPacketResponse3(dsr, [dsr, self.Flow_limit[1]])
                                if self.file_list[cloak_response]['pktType'] == 'Cloak' and self.file_list[cloak_response]['isTesterPkt']:
                                    ptx_cloak = True
                                    reason = self.PktMethod.GetPayloadDetails(cloak_response, 'Reason')[0]['sDescription']
                                    if Check['reason'] in reason:
                                        res.append([f"Cloak with Reason:{reason} by TPT was initiated at index-{self.file_list[cloak_response]['rowIndex']} in response to DSR-POLL packet", Enums.TestResult.PASS])
                                prx_cloak = self.GetPacketResponse3(cloak_response, [cloak_response, self.Flow_limit[1]], uut = True)
                                if self.file_list[prx_cloak]['pktType'] == 'Cloak' and not self.file_list[prx_cloak]['isTesterPkt']:
                                    prx_cloak_1 = True
                                    res.append([f"Cloak by Prx was observed at index-{self.file_list[prx_cloak]['rowIndex']} in response to TPT cloak", Enums.TestResult.PASS])
                                prx_clk_response = self.GetPacketResponse3(prx_cloak, [prx_cloak, self.Flow_limit[1]])
                                print(prx_clk_response)
                                if self.file_list[prx_clk_response]['pktType'] == 'ACK' and self.file_list[prx_clk_response]['isTesterPkt']:
                                    prx_cloak_response = True
                                    cloak_ack = prx_clk_response
                                    res.append([f"ACK response was observed for the PRx cloak packet at index-{self.file_list[prx_clk_response]['rowIndex']}", Enums.TestResult.PASS])
                                break
                        break
            if not check_atn:
                res.append([f"ATN response was not observed for any XCE packet", Enums.TestResult.INCONCLUSIVE])
            if not check_dsr:
                res.append([f"DSR-POLL packet was not observed for the ATN packet", Enums.TestResult.INCONCLUSIVE])
            if not ptx_cloak:
                res.append([f"Cloak by TPT was not initiated in response to DSR-POLL packet", Enums.TestResult.INCONCLUSIVE])
            if not prx_cloak_1:
                res.append([f"Cloak by Prx was not observed in response to TPT cloak", Enums.TestResult.INCONCLUSIVE])
            if not prx_cloak_response:
                res.append([f"ACK response was not observed for the PRx cloak packet", Enums.TestResult.INCONCLUSIVE])

            if check_atn and check_dsr and ptx_cloak and prx_cloak and prx_cloak_response:
                #get cloak seq limit 
                new_limit_1 = []
                lim_1 = 0
                for limit in range(cloak_ack, self.Flow_limit[1]):
                    if 'Phase_Info' in self.file_list[limit]['pktType'] and 'Cloak' in self.file_list[limit]['value']:
                        lim_1 = limit
                        for limit_1 in range(lim_1, self.Flow_limit[1]):
                            if 'Phase_Info' in self.file_list[limit_1]['pktType'] and 'Reset' in self.file_list[limit_1]['value']:
                                new_limit_1 = [lim_1, limit_1]
                                break
                        break
                print(new_limit_1)
                if len(new_limit_1) == 2:
                    assertions_details = []
                    check_clk_list = []
                    id = new_limit_1[0] 
                    last_clk = 0              
                    while id <= new_limit_1[1]:
                        check_clk = False

                        if 'Cloak_Ping_Attach' in self.file_list[id]['pktType'] and self.file_list[id]['isTesterPkt']:
                            attach = id
                            id+= 1
                            id_1 = id
                            while id_1 <= new_limit_1[1]:
                                if 'Cloak_Ping_Detach' in self.file_list[id_1]['pktType'] and self.file_list[id_1]['isTesterPkt']:
                                    detach = id_1 
                                    #Get cloak packets during the interval
                                    for clk_1 in range(attach, detach):
                                        if 'Cloak' in self.file_list[clk_1]['pktType'] and not  self.file_list[clk_1]['isTesterPkt']:
                                            check_clk = True                                           
                                            response = self.GetPacketResponse3(clk_1, [clk_1, new_limit_1[1]])
                                            if self.file_list[response]['pktType'] == 'ACK':
                                                cloak = response
                                                check_clk_list.append(clk_1)
                                                last_clk = clk_1
                                            break
                                    assertions_details.append([[attach, detach], cloak])
                                    break
                                elif 'Cloak_Ping_Attach' in self.file_list[id_1]['pktType'] and self.file_list[id_1]['isTesterPkt']:
                                    break
                                id_1 +=1                                
                        id += 1
                    print(assertions_details)
                    print(check_clk_list)
                    #check 3x cloak ping cycle
                    if len(check_clk_list) >= 3:
                        new_limit_2 = [last_clk, new_limit_1[1]]
                        check_cloak_with_atn = False
                        check_report_with_prx_id = False
                        check_nak = False
                        nak_res = 0
                        xid_index = 0
                        value_before_cloak = 0
                        value_after_cloak = 0
                        check_get_ptx_xid = False
                        check_response_xid = False  
                        res.append([f"{Check['cloak_cycle']}x cloak ping cycle was observed during the cloak phase, Cloak packet indexes - {check_clk_list}", Enums.TestResult.PASS])
                        #check ATN response for next cloak packet    
                        for atn_1 in range(last_clk, new_limit_1[1]):
                            if 'Cloak' in self.file_list[atn_1]['pktType'] and not self.file_list[atn_1]['isTesterPkt']:
                                response_atn = self.GetPacketResponse3(atn_1, [atn_1, new_limit_1[1]])
                                if response_atn != 0 and self.file_list[response_atn]['pktType'] == 'ATN':
                                    res.append([f"ATN response was observed for the cloak packet at index-{self.file_list[response_atn]['rowIndex']}", Enums.TestResult.PASS])
                                    check_cloak_with_atn = True
                                    print("report limit", response_atn, new_limit_1[1])
                                    for report in range(response_atn, new_limit_1[1]):
                                        if 'Report' in self.file_list[report]['pktType'] and not self.file_list[report]['isTesterPkt']:
                                            report_ID = self.PktMethod.GetPayloadDetails(report, 'Report_ID')[0]['sDescription']
                                            if 'Receiver Identification' in report_ID or 'PRx Identification' in report_ID:
                                                check_report_with_prx_id = True
                                                res.append([f"Report packet with PRx Identification found at index-{self.file_list[report]['rowIndex']}", Enums.TestResult.PASS])
                                                nak_res = self.GetPacketResponse3(report, [report, new_limit_1[1]])
                                                print(nak_res+1, new_limit_1[1])
                                                if Check['response'] == 'NAK':
                                                    if self.file_list[nak_res]['pktType'] == 'NAK' and self.file_list[nak_res]['isTesterPkt']:
                                                        res.append([f"TPT responded with NAK for the report packet at {self.file_list[nak_res]['rowIndex']}", Enums.TestResult.PASS])
                                                        check_nak = True
                                                        #check PRx doesn't send ASK Cloak
                                                    clk_aft = False
                                                    for check_clk in range(nak_res+1, new_limit_1[1]):
                                                        if self.file_list[check_clk]['pktType'] == 'Cloak':
                                                            res.append([f"PRx sends ASK Cloak after unexpected response", Enums.TestResult.FAIL])
                                                            clk_aft = True
                                                            break
                                                    if not clk_aft:
                                                        res.append([f"PRx doesn't send ASK Cloak after unexpected response", Enums.TestResult.PASS])
                                                    chk_png = False
                                                    print(nak_res+1, self.Flow_limit[1])
                                                    id = nak_res+1
                                                    while id < self.Flow_limit[1]+30:
                                                        if 'Signal strength' in self.file_list[id]['pktType']:
                                                            res.append([f"TPT entered into Ping phase[{self.file_list[id]['pktType']}] at index-{self.file_list[id]['rowIndex']} after the unexpected response for the report packet", Enums.TestResult.PASS])
                                                            chk_png = True
                                                            id = self.Flow_limit[1]+30
                                                            break
                                                        id += 1
                                                          
                                                    if not chk_png:
                                                        res.append([f"TPT did not enter into Ping phase after the unexpected response for the report packet", Enums.TestResult.FAIL])                                                      
                                                    break
                                                if Check['response'] == 'ACK':
                                                    if self.file_list[nak_res]['pktType'] == 'ACK' and self.file_list[nak_res]['isTesterPkt']:
                                                        res.append([f"TPT responded with ACK for the report packet at index-{self.file_list[nak_res]['rowIndex']}", Enums.TestResult.PASS])
                                                        #check get(XID) and response after ACK
                                                        check_get_ptx_xid = False
                                                        check_response_xid = False
                                                        for get_re in range(nak_res, self.Flow_limit[1]):
                                                            if 'Get Request' in self.file_list[get_re]['pktType'] and not self.file_list[get_re]['isTesterPkt'] and 'PTx Extended Identification' in self.file_list[get_re]['value']:
                                                                res.append([f"GET[PTx XID] request was found at index-{self.file_list[get_re]['rowIndex']}", Enums.TestResult.PASS])
                                                                check_get_ptx_xid = True
                                                                #response
                                                                response_xid = self.GetPacketResponse3(get_re, [get_re,new_limit_1[1]])
                                                                EPTI=  "Extended_Power_Transmitter_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Power Transmitter Identification"

                                                                if self.file_list[response_xid]['pktType'] == EPTI and self.file_list[response_xid]['isTesterPkt']:
                                                                    res.append([f"TPT responded with XID packet for the request GET[PTx XID] at index-{self.file_list[response_xid]['rowIndex']}", Enums.TestResult.PASS])
                                                                    check_response_xid = True
                                                                    xid_index = response_xid
                                                                break 
                                                                      
                                                        break
                                                break
                                            break
                                    break
                        if not check_cloak_with_atn:
                            res.append([f"ATN response was not observed for any cloak packet after the {Check['cloak_cycle']}x cloak ping cycles", Enums.TestResult.INCONCLUSIVE])
                        if not check_report_with_prx_id:
                            res.append([f"Report packet with PRx Identification was not found after the ATN response for cloak packet", Enums.TestResult.INCONCLUSIVE])
                        if not check_nak and Check['response'] == 'NAK':
                            res.append([f"TPT did not respond with NAK for the report packet with PRx Identification", Enums.TestResult.INCONCLUSIVE])
                        if not check_get_ptx_xid and Check['response'] == 'ACK':
                            res.append([f"GET[PTx XID] request was not found after the ACK response for the report packet with PRx Identification", Enums.TestResult.INCONCLUSIVE])
                        if not check_response_xid and Check['response'] == 'ACK':
                            res.append([f"TPT did not respond with XID packet for the request GET[PTx XID]", Enums.TestResult.INCONCLUSIVE])
                        if check_cloak_with_atn and check_report_with_prx_id and check_nak and Check['reason'] == 'NAK':
                            # check the sequence entered ping phase again
                            check_ping_phase = False
                            for ping_ph in range(nak_res, new_limit_1[1]):
                                if 'Signal strength' in self.file_list[ping_ph]['pktType'] and 'Cloak' in self.file_list[ping_ph]['description']:
                                    res.append([f"TPT entered into Ping phase at index-{self.file_list[ping_ph]['rowIndex']}, after the NAK response for the report packet", Enums.TestResult.PASS])
                                    check_ping_phase = True                   
                            if not check_ping_phase:
                                res.append([f"TPT did not enter into Ping phase after the NAK response for the report packet", Enums.TestResult.FAIL])
                        if check_cloak_with_atn and check_report_with_prx_id and check_get_ptx_xid and check_response_xid and Check['response'] == 'ACK':
                            #check random identifier and check before cloak xid and not got xid
                            for check_xid in range(self.Flow_limit[0], new_limit_1[1]):
                                EPTI=  "Extended_Power_Transmitter_Identification" if self.Certification in [ "2.0.1",  "2.1.0", "2.2.1", "2.3.0","2.0.0"] else "Extended Power Transmitter Identification"

                                if EPTI in self.file_list[check_xid]['pktType'] and self.file_list[check_xid]['isTesterPkt']:           
                                    value_before_cloak = self.PktMethod.GetPayloadDetails(check_xid, 'Device_Identifier')[0]['sDescription']
                                    value_before_cloak = re.search(r"\d+", value_before_cloak).group()                  
                                    # else: res.append([f"TPT did not respond with XID packet for the request GET[PTx XID] before the cloak phase", Enums.TestResult.FAIL])
                                    break
                            value_after_cloak = self.PktMethod.GetPayloadDetails(xid_index, 'Device_Identifier')[0]['sDescription']
                            value_after_cloak = number = re.search(r"\d+", value_after_cloak).group()
                            print(value_before_cloak, value_after_cloak)
                            if value_before_cloak != value_after_cloak:
                                res.append([f"Device Identifier value in XID response packet is different before and after the cloak phase, value before cloak: {value_before_cloak}, value after cloak: {value_after_cloak}", Enums.TestResult.PASS])
                                #check the digital ping reset after random identifier mismatched XID response
                                check_digital_ping = False
                                print(response_xid, len(self.file_list))
                                for dig_ping in range(response_xid, len(self.file_list)):
                                    if 'Signal strength' in self.file_list[dig_ping]['pktType'] and not self.file_list[dig_ping]['isTesterPkt']:
                                        res.append([f"Digital Ping packet was observed at {self.file_list[dig_ping]['rowIndex']} sec after the XID response with mismatched identifier", Enums.TestResult.PASS])
                                        check_digital_ping = True
                                        break
                                if not check_digital_ping:
                                    res.append([f"Digital Ping packet was not observed after the XID response with mismatched identifier", Enums.TestResult.FAIL])
                            else: res.append([f"Device Identifier value in XID response packet is same before and after the cloak phase, value before cloak: {value_before_cloak}, value after cloak: {value_after_cloak}", Enums.TestResult.INCONCLUSIVE])
                    else: res.append([f"{Check['cloak_cycle']}x cloak ping cycle was observed during the cloak phase, Cloak packet indexes - {check_clk_list}", Enums.TestResult.FAIL])
                   
        elif not pt_pass:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        else: res.append([f"The packet sequence doesn't entered Cloak phase", Enums.TestResult.INCONCLUSIVE])
        return res
            
        
    def EDS_check_1(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']                   
        #check EDS packet before initiating the Auth sequence
        eds_initiated = False
        for eds in range(self.Flow_limit[0], self.Flow_limit[1]):
            if 'Enabled Data Streams' in self.file_list[eds]['pktType'] and not self.file_list[eds]['isTesterPkt']:
                eds_initiated = True
                res.append([f"Prx Requested Enabled Data Streams packet at {round(self.file_list[eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
                response_eds = self.GetPacketResponse3(eds, [eds,self.Flow_limit[1]])
                if self.file_list[response_eds]['pktType'] == 'Enabled Data Streams':
                    res.append([f"PTx responded with Enabled Data Streams packet for EDS packet request from Prx at {round(self.file_list[response_eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
        if not eds_initiated:
            pass  #if requires can edit later
        #check sequence entered the PT phase
        pt_pass = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                break
        if pt_pass:
            t_dts_data = {}
            temp_limit = []
            temp_limit_1 = []
            check_SADC_open_tester = False
            check_SADC_close_tester = False
            check_SADC_open_dut = False
            chdck_SADC_close_dut = False
            temppkt_1_bit = None
            temppkt_2_bit = None
            open_pkt = None
            close_pkt = None
            val = ''
            val_1 = ''
            seq_check = False
            check_CRC = False
            seq_count = 1
            # temp_ids = []
            auth_count = 1
            sequence = self.eds_default(self.Flow_limit)
            print(len(sequence))
            if len(sequence) >= 1:
                res.append([f"{len(sequence)} Auth sequences were found & indexes are {sequence}", Enums.TestResult.PASS])
                for seq in sequence:
                    check_res_open = False
                    check_res_close = False
                    check_res_open_1 = False
                    check_res_close_1 = False
                    res.append([f"Sequence {seq_count} -> index of {seq}", Enums.TestResult.PASS])

                    t_dts_data.setdefault(f"sequence{seq_count}", [])
                    sadc_open_found = False
                    id = seq[0]
                    while id < seq[1]:
                        if ("SADC" in self.file_list[id]['pktType'] and "Open" in self.file_list[id]['value'] and not self.file_list[id]['isTesterPkt']):
                            temppkt_1_bit = self.file_list[id]['value']
                            sadc_open_found = True
                            res.append([f"{self.file_list[id]['pktType']}{self.file_list[id]['value']} packet found at index-{self.file_list[id]['rowIndex']}",
                                Enums.TestResult.PASS])
                            seq_key = f"sequence{seq_count}"
                            if seq_key not in t_dts_data:
                                t_dts_data[seq_key] = []

                            t_dts_data[seq_key].append({"pkt": "SADC", "start_time": self.file_list[id]['startTime'], "index": id})
                            print("Bit", temppkt_1_bit)
                            
                            # if id < seq[1] and "SDSR" in self.file_list[id]['pktType'] and self.file_list[id]['isTesterPkt']:
                            #     res.append([f"SDSR {self.file_list[id]['value']} response packet found at {round(self.file_list[id]['startTime'], 3)}sec", Enums.TestResult.PASS])

                            #     id += 1
                            #check SADC open response packet
                            che = 0
                            for op in range(id, seq[1]+1):
                                if 'SADT' in self.file_list[op]['pktType'] and not self.file_list[id]['isTesterPkt']:
                                    #internal limit will SADT end
                                    che = op
                                    break
                            print("check",op)
                            print("ids", id, che+1)
                            for res_1 in range(id, che+1):
                                if 'SDSR' in self.file_list[res_1]['pktType'] and 'ACK' in self.file_list[res_1]['value'] and self.file_list[res_1]['isTesterPkt']:
                                    check_res_open = True
                                    # print("Check",res_1)
                                    res.append([f"SDSR- ACK response was found for SADC-Open packet at index-{self.file_list[res_1]['rowIndex']}", Enums.TestResult.PASS])
                                    id = res_1+1
                                    break
                            if not check_res_open:
                                res.append([f"SDSR response was not found for SADC-Open packet", Enums.TestResult.INCONCLUSIVE])
                            sadc_close_found = False
                            uid = id + 1
                            while uid < seq[1]:
                                if ("SADC" in self.file_list[uid]['pktType'] and "Close" in self.file_list[uid]['value'] and not self.file_list[uid]['isTesterPkt']):
                                    t_dts_data[seq_key].append({"pkt": "SADC", "start_time": self.file_list[uid]['startTime'], "index": uid})
                                    sadc_close_found = True  # fall back logic flag
                                    temp_limit = [id, uid]
                                    bytes_value = re.search(r'\d+', temppkt_1_bit).group()
                                    temp_bytes = 0
                                    odd_even = []
                                    uuid = temp_limit[0]
                                    while uuid <= temp_limit[1] + 1:
                                        if ("SADT" in self.file_list[uuid]['pktType'] and not self.file_list[uuid]['isTesterPkt']):
                                            val_1 = self.file_list[uuid]['pktType']
                                            ev_od = re.search(r'/(\d+[eo])', val_1)  # extracting the even odd packets from SADT
                                            if ev_od:
                                                odd_even.append(ev_od.group(1))

                                            print("val_1:", val_1)
                                            seq_key = f"sequence{seq_count}"

                                            if seq_key not in t_dts_data:
                                                t_dts_data[seq_key] = []

                                            t_dts_data[seq_key].append({"pkt": "SADT", "start_time": self.file_list[uuid]['startTime'], "index": uuid})
                                            match = re.search(r'\d+', val_1)
                                            number = int(match.group()) if match else None
                                            temp_bytes += number
                                        uuid += 1
                                    print(temp_limit)
                                    print("temp_bytes:", temp_bytes, "bytes_value:", bytes_value)
                                    print("odd_even values", odd_even)
                                    # result of odd and even count
                                    even_count = 0
                                    odd_count = 0
                                    for v in odd_even:
                                        if v.endswith('e'):
                                            even_count += 1
                                        elif v.endswith('o'):
                                            odd_count += 1
                                    msg = f"Received {f'{even_count} even_packets' if even_count else ''}{' and ' if even_count and odd_count else ''}{f'{odd_count} odd_packets' if odd_count else ''}"
                                    res.append([msg + 'SADT sequences', Enums.TestResult.PASS])

                                    print("Even received:", even_count)
                                    print("Odd received:", odd_count)
                                    if temp_bytes == int(bytes_value):
                                        res.append([f"Transferred bytes {temp_bytes} observed from SADT packets.{odd_even}", Enums.TestResult.PASS])
                                        res.append([
                                            f"{self.file_list[temp_limit[1]]['pktType']}-{self.file_list[temp_limit[1]]['value']} packet by DUT was found at index-{self.file_list[temp_limit[1]]['rowIndex']}",
                                            Enums.TestResult.PASS])

                                        res_check = temp_limit[1]
                                        print("temp_res", res_check)
                                        #for SADC close packet response                                                            
                                        for cl in range(temp_limit[1], seq[1]):
                                            if 'ATN' in self.file_list[cl]['pktType'] and self.file_list[cl]['isTesterPkt']:
                                                print("atn_index", cl)
                                                #check SDSR ack response for the SADC close with internal limit
                                                for res_2 in range(temp_limit[1], cl):
                                                    if 'SDSR' in self.file_list[res_2]['pktType'] and 'ACK' in self.file_list[res_2]['value'] and self.file_list[res_2]['isTesterPkt']:
                                                        check_res_close = True
                                                        # print("Check",res_1)
                                                        res.append([f"SDSR- ACK response was found for SADC-Close packet at index-{self.file_list[res_2]['rowIndex']}", Enums.TestResult.PASS])
                                                        break                        
                                                break
                                        if not check_res_close:
                                            res.append([f"SDSR response was not found for the SADC-close packet", Enums.TestResult.INCONCLUSIVE])
                                        
                                    else:
                                        res.append([
                                            f"Total transferred bytes are {temp_bytes} which is not matched with the bytes mentioned in SADC packet[Transfer size in bytes], which is expected",
                                            Enums.TestResult.FAIL])
                                    uuid_1 = uid + 1
                                    dsr_found = False
                                    atn_found = False

                                    for uid_1 in range(uuid_1, seq[1]):
                                        # check ATN
                                        temp_pkt_1 = self.PktMethod.GetPacketDetails(packet="ATN", limit=[uid_1, seq[1]], Type="Response")
                                        if len(temp_pkt_1) > 2:
                                            atn_found = True
                                            uid_1 += 1
                                            temp_pkt_2 = self.PktMethod.GetPacketDetails(packet="DSR", limit=[uid_1, seq[1]], Type="Packet")
                                            if len(temp_pkt_2) > 2:
                                                dsr_found = True
                                                res.append([
                                                    f"ATN packet found for the packet {self.file_list[temp_pkt_1[2] - 1]['pktType']} at index-{self.file_list[temp_pkt_1[2]]['rowIndex']} followed by DSR/POLL Request to Send packet at index-{self.file_list[temp_pkt_2[2]]['rowIndex']}",
                                                    Enums.TestResult.PASS])
                                                print(temp_pkt_1, temp_pkt_2)
                                                temp_id = uid_1 + 1
                                                break
                                        uid = uid_1
                                    sadc_open_tester_found = False
                                    for temp in range(temp_id, seq[1] + 1):
                                        if 'SADC' in self.file_list[temp]['pktType'] and 'Open' in self.file_list[temp]['value'] and self.file_list[temp]['isTesterPkt'] and not self.file_list[temp][
                                            'isFWTestermessage']:
                                            # print("SADC Open packet found at index:", temp)
                                            sadc_open_tester_found = True

                                            temppkt_2_bit = self.file_list[temp]['value']
                                            temppkt_2_bit = re.search(r'\d+', temppkt_2_bit).group()
                                            # print("Bit", temppkt_2_bit)
                                            res.append([f"{self.file_list[temp]['pktType']}{self.file_list[temp]['value']} by tester packet found at "
                                                                                        f"index-{self.file_list[temp]['rowIndex']}", Enums.TestResult.PASS])
                                            open_pkt = temp  # getting internal limit
                                            temp_pkt_3 = [0,0,0] #dummy list
                                            # print(temp_pkt_3)
                                            if len(temp_pkt_3) >= 2:
                                                # res.append(
                                                #     [f"{self.file_list[temp_pkt_3[2]]['pktType']}-{self.file_list[temp_pkt_3[2]]['value']} resposne was observed for the SADC packet",
                                                #      Enums.TestResult.PASS])
                                                print("check_last ids", open_pkt, seq[1])
                                                for op_1 in range(open_pkt, seq[1]):
                                                    if 'SADT' in self.file_list[op_1]['pktType'] and self.file_list[op_1]['isTesterPkt']:
                                                        # print("check_last_ids_1", open_pkt, op_1+1)
                                                        for res_3 in range(open_pkt, op_1+1):                       
                                                            if 'SDSR' in self.file_list[res_3]['pktType'] and not self.file_list[res_3]['isTesterPkt']:
                                                                check_res_open_1 = True
                                                                res.append([f"SDSR- ACK response was found for SADC-Open packet by Prx at index-{self.file_list[res_3]['rowIndex']}", Enums.TestResult.PASS])
                                                                break
                                                        break
                                                if not check_res_open_1:
                                                    res.append([f"SDSR response was not found for SADC-Open packet by Prx", Enums.TestResult.INCONCLUSIVE])
                                                temp += 1
                                                # print(temp, seq[1])
                                                sadc_close_tester_found = False
                                                u = temp
                                                err_crc_check = False
                                                while u < seq[1] + 1:
                                                    if 'SADC' in self.file_list[u]['pktType'] and 'Close' in self.file_list[u]['value'] and self.file_list[u]['isTesterPkt'] and not self.file_list[u][
                                                        'isFWTestermessage']:
                                                        sadc_close_tester_found = True
                                                        temp = u
                                                        close_pkt = temp
                                                        # print("SADC Close[tester pkt] packet found at index:", u)
                                                        break
                                                    u += 1
                                                temp_ids = [open_pkt, close_pkt]  # sadt check internal limit

                                                # test case MPP_PRX_CPX_XDATAS_ERROR_SDSR check
                                                check_DSR = []
                                                resend_DSR = False
                                                if Check['check_DSR'] is not None and not seq_check:
                                                    seq_check = True
                                                    # print("entering check_DSR")
                                                    for j in range(open_pkt, close_pkt):
                                                        check_DSR.append([self.file_list[j]['pktType'], j])
                                                    # Find first SADT packet
                                                    sadt_index = next((i for i, v in enumerate(check_DSR) if v[0].strip().startswith("SADT")), None)
                                                    if sadt_index is not None:
                                                        result_found = False
                                                        # Scan packets after first SADT
                                                        for pkt, idx in check_DSR[sadt_index + 1:]:
                                                            pkt = pkt.strip()
                                                            # If DSR appears first → PASS
                                                            if pkt == "DSR":
                                                                res.append([f'DSR/POLL packet sent by DUT after first SADT sequence at packet index {idx} [Index{temp_ids}]',
                                                                    Enums.TestResult.PASS])
                                                                result_found = True
                                                                break
                                                            # If another SADT appears before DSR → FAIL
                                                            elif pkt.startswith("SADT"):
                                                                res.append([f'Second SADT packet found at index {idx} before DSR [Index{temp_ids}]', Enums.TestResult.FAIL])
                                                                result_found = True
                                                                break
                                                        # If neither found
                                                        if not result_found:
                                                            res.append([f'DSR packet not found after first SADT sequence [Index{temp_ids}]', Enums.TestResult.FAIL])
                                                    else:
                                                        res.append([f'First SADT packet not found [Index{temp_ids}]', Enums.TestResult.INCONCLUSIVE])
                                                respons = temp_ids[0]
                                                temp_bytes_1 = 0
                                                bytes_value_1 = re.search(r'\d+', temppkt_2_bit).group()
                                                odd_even_1 = []
                                                while respons < temp_ids[1] + 1:
                                                    if 'SADT' in self.file_list[respons]['pktType'] and self.file_list[respons]['isTesterPkt']:
                                                        # print("Enetered")

                                                        val_2 = self.file_list[respons]['pktType']
                                                        ev_od_1 = re.search(r'/(\d+[eo])', val_2)  # extracting the even odd packets from SADT
                                                        if ev_od_1:
                                                            odd_even_1.append(ev_od_1.group(1))
                                                        respons += 1

                                                        # print("val_2:", val_2)
                                                        match = re.search(r'\d+', val_2)
                                                        number = int(match.group()) if match else None
                                                        temp_bytes_1 += number
                                                        uid = respons
                                                    respons += 1
                                                # result of odd and even count
                                                even_count_1 = 0
                                                odd_count_1 = 0
                                                for v_1 in odd_even_1:
                                                    if v_1.endswith('e'):
                                                        even_count_1 += 1
                                                    elif v_1.endswith('o'):
                                                        odd_count_1 += 1
                                                msg = f"Received {f'{even_count_1} even_packets' if even_count_1 else ''}{' and ' if even_count_1 and odd_count_1 else ''}{f'{odd_count_1} odd_packets' if odd_count_1 else ''}"
                                                res.append([msg + 'SADT sequences', Enums.TestResult.PASS])

                                                # print("Even received:", even_count)
                                                # print("Odd received:", odd_count)
                                                # print("temp_bytes_1:", temp_bytes_1, "bytes_value_1:", bytes_value_1)
                                                if temp_bytes_1 == int(bytes_value_1):
                                                    res.append([f"Transferred bytes {temp_bytes_1} observed from SADT packets.{odd_even_1}", Enums.TestResult.PASS])
                                                    res.append([
                                                        f"{self.file_list[temp_ids[1]]['pktType']} {self.file_list[temp_ids[1]]['value']} packet by Tester was found at index-{self.file_list[temp_ids[1]]['rowIndex']}",
                                                        Enums.TestResult.PASS])
                                                    #check sdsr response for SADC close
                                                    
                                                    for cl_2 in range(temp_ids[1], temp_ids[1]+8):
                                                        if 'SDSR' in self.file_list[cl_2]['pktType'] and 'ACK' in self.file_list[cl_2]['value'] and not self.file_list[cl_2]['isTesterPkt']:
                                                            res.append([f"SDSR- ACK response was found for SADC-Close packet at index-{self.file_list[cl_2]['rowIndex']}", Enums.TestResult.PASS])
                                                            check_res_close_1 = True
                                                            break
                                                    if not check_res_close_1:
                                                        res.append([f"SDSR response was not found for SADC-Close packet", Enums.TestResult.INCONCLUSIVE])
                                                    
                                                    
                                                            
                                                else:
                                                    res.append([
                                                        f"Total transferred bytes are {temp_bytes_1} which is not matched with the bytes mentioned in SADC packet[Transfer size in bytes], which is not expected",
                                                        Enums.TestResult.FAIL])
                                            uid = temp
                                    break
                                uid += 1
                            id = uid + 1
                        id += 1
                    seq_count += 1
                    # fallback logic
                    if not sadc_open_found:
                        res.append([f"SADC_open by PRx was not found", Enums.TestResult.INCONCLUSIVE])
                    if not sadc_close_found:
                        res.append([f"SADC_close by PRx was not found", Enums.TestResult.INCONCLUSIVE])
                    if not atn_found:
                        res.append([f"ATN response was not found", Enums.TestResult.INCONCLUSIVE])
                    if not dsr_found:
                        res.append([f"DSR packet was not found", Enums.TestResult.INCONCLUSIVE])
                    if not sadc_open_tester_found:
                        res.append([f"SADC_open by Tester was not found", Enums.TestResult.INCONCLUSIVE])
                    if not sadc_close_tester_found:
                        res.append([f"SADC_close by Tester was not found", Enums.TestResult.INCONCLUSIVE])
                # check tdts timings
                if Check['tdts'] is not None:
                    occ = {"SADC-SADT": 0, "SADT-SADT": 0, "SADT-SADC": 0}
                    grouped_results = {"SADC-SADT": [], "SADT-SADT": [], "SADT-SADC": []}
                    for seq_name, packets in t_dts_data.items():
                        packets.sort(key=lambda x: x["start_time"])
                        for i in range(len(packets) - 1):
                            p1 = packets[i]["pkt"]
                            p2 = packets[i + 1]["pkt"]
                            idx1 = packets[i]["index"]
                            idx2 = packets[i + 1]["index"]
                            t1 = packets[i]["start_time"]
                            t2 = packets[i + 1]["start_time"]
                            tdts = round((t2 - t1) * 1000, 3)
                            pair = f"{p1}-{p2}"
                            if pair in occ:
                                occ[pair] += 1
                                status = Enums.TestResult.PASS if tdts <= 5000 else Enums.TestResult.FAIL
                                line = f"Measured tdts: {tdts}ms between {p1}[{idx1}] and {p2}[{idx2}].Total occurence:{occ[pair]} Status:{status} - Expected Range tdts <= 5000ms"
                                grouped_results[pair].append((line, status))
                    order = ["SADC-SADT", "SADT-SADT", "SADT-SADC"]

                    for pair in order:
                        for line, status in grouped_results[pair]:
                            if status == Enums.TestResult.PASS:
                                res.append([line, Enums.TestResult.PASS])
                            else:
                                res.append([line, Enums.TestResult.FAIL])  # print(line)
            elif len(sequence) == 0:
                sadc_1_check = False
                #check the auth sequence whether its there - TPR as DUT
                for check1 in range(self.Flow_limit[0], self.Flow_limit[1]):
                    if 'SADC' in self.file_list[check1]['pktType'] and 'Open' in self.file_list[check1]['value'] and not self.file_list[check1]['isTesterPkt']:
                        for check_2 in range(check1+1, self.Flow_limit[1]+1):
                            if 'SADC' in self.file_list[check_2]['pktType'] and 'Close' in self.file_list[check_2]['value'] and not self.file_list[check_2]['isTesterPkt']:
                                sadc_1_check = True
                        break
                # print("sadc_1_check", sadc_1_check)
                if sadc_1_check:
                    check_sadc_open = False
                    check_sadc_close = False
                    limit = 0
                    for sadc_op in range(self.Flow_limit[0], self.Flow_limit[1]+1):
                        if 'SADC' in self.file_list[sadc_op]['pktType'] and 'Open' in self.file_list[sadc_op]['value'] and not self.file_list[sadc_op]['isTesterPkt']:
                            check_sadc_open = True
                            for sadc_cl in range(sadc_op, self.Flow_limit[1]+1):
                                if 'SADC' in self.file_list[sadc_cl]['pktType'] and 'Close' in self.file_list[sadc_cl]['value'] and not self.file_list[sadc_cl]['isTesterPkt']:
                                    check_sadc_close = True
                                    limit = sadc_cl
                                    break
                            break
                    #new_limit [sadc_cl , self.Flow_limit[1]]
                    #check ATN and DSR poll
                    if check_sadc_open and check_sadc_close:
                        atn_check = False
                        dsr_check = False
                        for atn in range(limit, self.Flow_limit[1]+1):
                            if 'ATN' in self.file_list[atn]['pktType'] and self.file_list[atn]['isTesterPkt']:
                                atn_check = True
                                res.append([f"ATN resposne was observed at {round(self.file_list[atn]['startTime'], 3)}sec", Enums.TestResult.PASS])
                                for dsr in range(atn, self.Flow_limit[1]):
                                    if 'DSR' in self.file_list[dsr]['pktType'] and not self.file_list[dsr]['isTesterPkt']:
                                        dsr_check = True
                                        res.append([f"DSR-POLL packet was observed at {round(self.file_list[dsr]['startTime'], 3)}sec", Enums.TestResult.PASS])
                                        limit = dsr
                                        break
                                break
                        if not atn_check:
                            res.append([f"ATN resposne was not observed", Enums.TestResult.INCONCLUSIVE])
                        if not dsr_check:
                            res.append([f"DSR resposne was not observed", Enums.TestResult.INCONCLUSIVE])
                        if atn_check and dsr_check:
                            inte_limit = []
                            #check_ the internal flow
                            for op in range(limit, self.Flow_limit[1]):
                                if 'SADC' in self.file_list[op]['pktType'] and 'Open' in self.file_list[op]['value'] and self.file_list[op]['isTesterPkt']:
                                    # print("Internal limit found at index:", op)
                                    inte_limit = [op, self.Flow_limit[1]]
                                    break
                            if len(inte_limit) == 2:
                                count = 1
                                in_index = 0
                                lim = 0
                                sdsr=0
                                dsr_retry =0
                                dsr_retry_check = False
                                sadt_1_check = False
                                sadt_2_check = True
                                for sadt1 in range(1, 3):
                                    if count == 1:
                                        for ch in range(inte_limit[0], inte_limit[1]):
                                            if 'SADT' in self.file_list[ch]['pktType'] and self.file_list[ch]['isTesterPkt']:
                                                in_index = ch
                                                for ch_1 in range(ch+1, inte_limit[1]):
                                                    if 'SADT' in self.file_list[ch_1]['pktType'] and self.file_list[ch_1]['isTesterPkt']:
                                                        lim = ch_1
                                                        break
                                                for response in range(in_index, lim):
                                                    if 'SDSR' in self.file_list[response]['pktType'] and 'ACK' in self.file_list[response]['value']:
                                                        res.append([f"SADT 1st packet with SDSR response was observed at index-{self.file_list[response]['rowIndex']}", Enums.TestResult.PASS])
                                                        sadt_1_check = True
                                                        sdsr = response
                                                        break
                                                break
                                    if count == 2:
                                        for ch_2 in range(lim+1, inte_limit[1]):
                                            if 'SADT' in self.file_list[ch_2]['pktType'] and self.file_list[ch_2]['isTesterPkt']:
                                                dsr_retry = ch_2
                                                # print ("limit", ch_2, inte_limit[1])
                                                for response_1 in range(sdsr+1,ch_2-1):
                                                    if 'SDSR' in self.file_list[response_1]['pktType'] and 'ACK' in self.file_list[response_1]['value']:
                                                        res.append([f"2nd SADT packet was observed at index-{self.file_list[response_1]['rowIndex']}", Enums.TestResult.INCONCLUSIVE])
                                                        sadt_2_check = False
                                                        break
                                                if not sadt_2_check: res.append([f"2nd SADT packet muted after 1st SADT sequence", Enums.TestResult.PASS])
                                                break
                                    count += 1
                                # print("limittt", lim, dsr_retry)
                                for dsr_retry in range(sdsr, lim+1):
                                    if 'DSR' in self.file_list[dsr_retry]['pktType'] and not self.file_list[dsr_retry]['isTesterPkt'] and '{POLL}' in self.file_list[dsr_retry]['value']:
                                        res.append([f"DSR/POLL retry packet was observed at {round(self.file_list[dsr_retry]['startTime'], 3)}sec", Enums.TestResult.PASS])
                                        dsr_retry_check = True
                                        break
                                
                                if not sadt_1_check: res.append([f"1st SADT packet not observed with SDSR response", Enums.TestResult.INCONCLUSIVE])           
                                if not dsr_retry_check: res.append([f"DSR/POLL retry packet was not observed after the 2nd SADT packet", Enums.TestResult.INCONCLUSIVE])


                                    
                            else: res.append([f"Auth sequence by PTx not initiated", Enums.TestResult.INCONCLUSIVE])

                                
                else: res.append([f"No Auth count sequence found, which is not expected, at least 1 sequence should initiate", Enums.TestResult.FAIL])


            else:
                res.append([f"No Auth count sequence found, which is not expected, at least 1 sequence should initiate", Enums.TestResult.FAIL])
            # print(t_dts_data)
        else:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def EDS_check_3(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']         
        #check EDS packet before initiating the Auth sequence
        eds_initiated = False
        for eds in range(self.Flow_limit[0], self.Flow_limit[1]):
            if 'Enabled Data Streams' in self.file_list[eds]['pktType'] and not self.file_list[eds]['isTesterPkt']:
                eds_initiated = True
                res.append([f"Prx Requested Enabled Data Streams packet at {round(self.file_list[eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
                response_eds = self.GetPacketResponse3(eds, [eds,self.Flow_limit[1]])
                if self.file_list[response_eds]['pktType'] == 'Enabled Data Streams':
                    res.append([f"PTx responded with Enabled Data Streams packet for EDS packet request from Prx at {round(self.file_list[response_eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
        if not eds_initiated:
            pass  #if requires can edit later
        #check sequence entered the PT phase
        pt_pass = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                break
        if pt_pass:
            check_sadc_open = False
            sequence = self.eds_default(self.Flow_limit)
            # print(sequence)
            temp_ids = []
            seq_count = 1
            open_pkt = 0
            close_pkt = 0
            ack_observed = False
            err_crc = False
            atn_check = False
            dsr_check = False
            retry_sequence = 0
            if len(sequence) >= 2:
                for seq in sequence:
                    # check ATN and DSR packet
                    for ids in range(seq[0], seq[1]):
                        if 'ATN' in self.file_list[ids]['pktType'] and self.file_list[ids]['isTesterPkt']:
                            atn_check = True
                            chh = ids
                            res.append([f"ATN response packet found at index-{self.file_list[ids]['rowIndex']}", Enums.TestResult.PASS])
                            break
                    if atn_check:
                        for idd in range(chh, seq[1]):
                            if 'DSR' in self.file_list[idd]['pktType'] and not self.file_list[idd]['isTesterPkt'] and '{POLL}' in self.file_list[idd]['value']:
                                dsr_check = True
                                res.append([f"DSR/POLL packet found at index-{self.file_list[idd]['rowIndex']}", Enums.TestResult.PASS])
                                break
                    if not atn_check:
                        res.append([f"ATN response packet not found", Enums.TestResult.FAIL])
                    if not dsr_check:
                        res.append([f"DSR/POLL packet not found", Enums.TestResult.FAIL])
                    if atn_check and dsr_check:
                        # reset flags for each sequence
                        ack_observed = False
                        err_crc = False
                        for id in range(seq[0], self.Flow_limit[1]):
                            if seq_count == 1:
                                if 'SDSR' in self.file_list[id]['pktType'] and 'ACK' in self.file_list[id]['value']:
                                    res.append([
                                        f"SDSR{self.file_list[id]['value']} response packet found for the Auth sequence {seq_count} SADC packet at index-{self.file_list[id]['rowIndex']}",
                                        Enums.TestResult.PASS])
                                    ack_observed = True
                                    break
                            elif seq_count == 2:
                                if 'SDSR' in self.file_list[id]['pktType'] and 'ERR_CRC' in self.file_list[id]['value']:
                                    res.append([
                                        f"SDSR{self.file_list[id]['value']} response packet found for the Auth sequence {seq_count} SADC packet at index-{self.file_list[id]['rowIndex']}",
                                        Enums.TestResult.PASS])
                                    err_crc = True
                                    retry_sequence = id
                                    break
                        # ---- Failure handling ----
                        if seq_count == 1 and not ack_observed:
                            res.append([f"SDSR ACK response packet not found for the Auth sequence {seq_count} SADC packet [Index{temp_ids}]", Enums.TestResult.FAIL])
                        elif seq_count == 2 and not err_crc:
                            res.append([f"SDSR ERR_CRC response packet not found for the Auth sequence {seq_count} SADC packet [Index{temp_ids}]", Enums.TestResult.FAIL])
                        seq_count += 1
                if retry_sequence != 0:
                    sadc_close_check = False
                    sadc_open_check = False

                    for ii in range(retry_sequence, self.Flow_limit[1]):
                        if self.file_list[ii]['pktType'] == 'SADC' and 'Open' in self.file_list[ii]['value']:
                            sadc_open_check = True
                            retry_open = ii
                            break
                    for jj in range(retry_open, self.Flow_limit[1]):
                        if self.file_list[jj]['pktType'] == 'SADC' and 'Close' in self.file_list[jj]['value']:
                            sadc_close_check = True
                            retry_close = jj
                            break
                    if sadc_open_check and sadc_close_check:
                        res.append([f"Retried Auth sequence after the ERR_CRC response found at the index [{retry_open, retry_close}]", Enums.TestResult.PASS])
                    else:
                        res.append([f"Retried Auth sequence after the ERR_CRC response not found", Enums.TestResult.INCONCLUSIVE])
        else:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def EDS_check_2(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit']         
        #check EDS packet before initiating the Auth sequence
        eds_initiated = False
        for eds in range(self.Flow_limit[0], self.Flow_limit[1]):
            if 'Enabled Data Streams' in self.file_list[eds]['pktType'] and not self.file_list[eds]['isTesterPkt']:
                eds_initiated = True
                res.append([f"Prx Requested Enabled Data Streams packet at index-{self.file_list[eds]['rowIndex']}", Enums.TestResult.PASS])
                response_eds = self.GetPacketResponse3(eds, [eds,self.Flow_limit[1]])
                if self.file_list[response_eds]['pktType'] == 'Enabled Data Streams':
                    res.append([f"PTx responded with Enabled Data Streams packet for EDS packet request from Prx at index-{self.file_list[response_eds]['rowIndex']}", Enums.TestResult.PASS])
        if not eds_initiated:
            pass  #if requires can edit later
        #check sequence entered the PT phase                    
        pt_pass = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                break
        if pt_pass:
            
            # check custom_limit
            temp_id_1 = 0
            temp_id = 0
            sdsr_check = False
            sadc_check = False
            sadc_check_1 = False
            sadc_close = False
            if Check['check_SDSR'] is not None:
                for id in range(self.Flow_limit[0], self.Flow_limit[1]):
                    # print(id)
                    if self.file_list[id]['pktType'] == 'SADC' and 'Open' in self.file_list[id]['value']:
                        sadc_check = True
                        res.append([f"SADC{self.file_list[id]['value']} packet by DUT found at index-{self.file_list[id]['rowIndex']}", Enums.TestResult.PASS])
                        id += 1
                        if self.file_list[id]['pktType'] == 'SDSR' and Check['check_SDSR'] in self.file_list[id]['value']:
                            res.append([f"SDSR{self.file_list[id]['value']} packet by tester found at index-{self.file_list[id]['rowIndex']}", Enums.TestResult.PASS])
                            sdsr_check = True
                            temp_id = id + 1
                            break
                for id_1 in range(temp_id, self.Flow_limit[1]):
                    if self.file_list[id_1]['pktType'] == 'SADC' and 'Close' in self.file_list[id_1]['value']:
                        temp_id_1 = id_1
                        sadc_close = True
                        break
                new_limit = [temp_id, temp_id_1]
                # print(new_limit)
                if sadc_check and sadc_close and sdsr_check:
                    for check in range(new_limit[0], new_limit[1]):
                        if self.file_list[check]['pktType'] == 'SADC' and 'Open' in self.file_list[check]['value']:
                            sadc_check_1 = True
                            res.append([f"SADC{self.file_list[check]['value']} packet retried by DUT found at index-{self.file_list[check]['rowIndex']}",
                                Enums.TestResult.PASS])
                            break
                if not sdsr_check:
                    res.append([f"SDSR {Check['check_SDSR']} packet by tester not found", Enums.TestResult.FAIL])
                if not sadc_check:
                    res.append([f"SADC Open packet by DUT not found", Enums.TestResult.FAIL])
                if not sadc_check_1:
                    res.append([f"retried SADC Open packet by DUT not found", Enums.TestResult.FAIL])
                if not sadc_close:
                    res.append([f"SADC close packet by DUT not found", Enums.TestResult.FAIL])
            else:
                temp_ids = []
                temp = 0
                for id in range(self.Flow_limit[0], self.Flow_limit[1]):
                    # print(id)
                    if self.file_list[id]['pktType'] == 'SADC' and 'Open' in self.file_list[id]['value']:
                        sadc_check = True
                        temp = id
                        break
                for ids in range(temp, self.Flow_limit[1]):
                    if self.file_list[ids]['pktType'] == 'SADC' and 'Close' in self.file_list[ids]['value']:
                        temp_ids = [temp, ids]
                        sadc_close = True
                        break
                # print("Teamp_ids", temp_ids)
                nak_check = False
                if sadc_check and sadc_close:
                    for fsk in range(temp_ids[0], temp_ids[1]):
                        if 'SADT' in self.file_list[fsk]['pktType']:
                            response = self.GetPacketResponse3(fsk, [fsk, self.Flow_limit[1]])
                            # print(response)
                            if self.file_list[response]['pktType'] == Check['response']:
                                res.append([f"NAK response observed for the SADT packet at index-{self.file_list[response]['rowIndex']}", Enums.TestResult.PASS])
                                nak_check = True
                            elif self.file_list[response]['pktType'] != Check['response'] and nak_check:
                                res.append([
                                    f"{self.file_list[response]['pktType']} Resposne observed for the retried SADT packet at index-{self.file_list[response]['rowIndex']}", Enums.TestResult.PASS])
                            else:
                                res.append([f"NAK response was not observed for the SADT packet", Enums.TestResult.FAIL])
                if not sadc_check:
                    res.append([f"SADC Open packet by DUT not found", Enums.TestResult.FAIL])
                if not sadc_close:
                    res.append([f"SADC close packet by DUT not found", Enums.TestResult.FAIL])
        else:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def EDS_cloak(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit'] 
        #check EDS packet before initiating the Auth sequence
        eds_initiated = False
        for eds in range(self.Flow_limit[0], self.Flow_limit[1]):
            if 'Enabled Data Streams' in self.file_list[eds]['pktType'] and not self.file_list[eds]['isTesterPkt']:
                eds_initiated = True
                res.append([f"Prx Requested Enabled Data Streams packet at {round(self.file_list[eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
                response_eds = self.GetPacketResponse3(eds, [eds,self.Flow_limit[1]])
                if self.file_list[response_eds]['pktType'] == 'Enabled Data Streams':
                    res.append([f"PTx responded with Enabled Data Streams packet for EDS packet request from Prx at {round(self.file_list[response_eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
        if not eds_initiated:
            pass  #if requires can edit later
        #check sequence entered the PT phase            
        pt_pass = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                break
        if pt_pass:
            
            #check SADC and SADT_1 presents
            sadc_open_check = False
            sadt_check = False
            temp_id = 0
            cloak_cycle_count_check = False
            for id in range(self.Flow_limit[0], self.Flow_limit[1]):
                if 'SADC' in self.file_list[id]['pktType'] and 'Open' in self.file_list[id]['value'] and not self.file_list[id]['isTesterPkt']:
                    sadc_open_check = True
                    res.append([f"SADC Open packet by DUT found at index-{self.file_list[id]['rowIndex']}", Enums.TestResult.PASS])
                    id += 1
                    for sadt in range(id, self.Flow_limit[1]):
                        #check one SADT packet should come [SADT_1]
                        if 'SADT' in self.file_list[sadt]['pktType'] and not self.file_list[sadt]['isTesterPkt']:
                            res.append([f"SADT_1 packet by DUT found at index-{self.file_list[sadt]['rowIndex']}", Enums.TestResult.PASS])
                            sadt_check = True
                            temp_id = sadt+1
                            break
                    break
            #check ATN for 1st XCE packet
            xce_1_found = False
            atn_check = False
            if sadc_open_check and sadt_check:
                for xce in range(temp_id, self.Flow_limit[1]):
                    if 'Extended Control Error' in self.file_list[xce]['pktType']:
                        xce_1_found = True
                        res.append([f"XCE first packet found at index-{self.file_list[xce]['rowIndex']}", Enums.TestResult.PASS])
                        xce += 1
                        response = self.GetPacketResponse3(xce, [xce, self.Flow_limit[1]])
                        if self.file_list[response]['pktType'] == 'ATN':
                            atn_check = True
                            res.append([f"ATN response found for the first XCE packet at index-{self.file_list[response]['rowIndex']}", Enums.TestResult.PASS])
                            temp_id = response + 1
                            break
                        break
            #check cloak initiated
            dsr_check = False
            ptx_cloak = False
            prx_cloak = False
            # ptx_cloak_index = 0
            if xce_1_found and atn_check:
                for clk in range(temp_id, self.Flow_limit[1]):
                    if 'DSR' in self.file_list[clk]['pktType'] and '{POLL}' in self.file_list[clk]['value']:
                        dsr_check = True
                        res.append([f"DSR/POLL packet found at index-{self.file_list[clk]['rowIndex']}", Enums.TestResult.PASS])
                        clk += 1
                        for cloak in range(clk, self.Flow_limit[1]):
                            if 'Cloak' in self.file_list[cloak]['pktType'] and self.file_list[cloak]['isTesterPkt']:
                                ptx_cloak = True
                                res.append([f"Cloak packet by Ptx found at index-{self.file_list[cloak]['rowIndex']}", Enums.TestResult.PASS])
                                #check payload coex mitigration in ptx cloak
                                if self.file_list[cloak]['header_Payload']['childelement'][0]['childelement'][1]['sDescription'] == 'Coex Mitigation':
                                    res.append([f"Cloak packet reason: Coex Mitigation found", Enums.TestResult.PASS])
                                else:
                                    res.append([f"Cloak packet reason: Coex Mitigation not found", Enums.TestResult.FAIL])
                                cloak+=1
                                for cloak_prx in range(cloak, self.Flow_limit[1]):
                                    if 'Cloak' in self.file_list[cloak]['pktType'] and not self.file_list[cloak]['isTesterPkt']:
                                        prx_cloak = True
                                        temp_id = cloak_prx + 1
                                        res.append([f"Cloak packet by Prx found at {round(self.file_list[cloak_prx]['startTime'], 3)} sec", Enums.TestResult.PASS])
                                        break
                                break
                        break
            #check 2-cycle of cloak initiated
            if dsr_check and ptx_cloak and prx_cloak:
                temp_ids = []
                temp_id_1 = 0
                for ping in range(temp_id, self.Flow_limit[1]):
                    if 'Phase_Info' in self.file_list[ping]['pktType'] and 'Cloak' in self.file_list[ping]['value']:
                        temp_id = ping
                        break
                for ping_1 in range(temp_id, self.Flow_limit[1]+2):
                    if 'Phase_Info' in self.file_list[ping_1]['pktType'] and 'Reset' in self.file_list[ping_1]['value']:
                        temp_id_1 = ping_1
                temp_ids = [temp_id, temp_id_1]    #temp limit for check cloak sequence
                # print(temp_ids)
                if temp_ids:
                    cloak_cycle_count = []
                    for clk in range(temp_ids[0], temp_ids[1]):  #check cloak cycles
                        if 'Cloak' in self.file_list[clk]['pktType'] and not self.file_list[clk]['isTesterPkt']:
                            cloak_cycle_count.append(self.file_list[clk]['pktType'])
                            res.append([f"Cloak packet by tester initiated at index-{self.file_list[clk]['rowIndex']}" , Enums.TestResult.PASS])
                    if len(cloak_cycle_count) >= 2:
                        cloak_cycle_count_check = True
                        res.append([f"Total {len(cloak_cycle_count)} cloak cycle count was observed.", Enums.TestResult.PASS])
                    else: res.append([f"Expected cloak cycle count was not observed in the cloak sequence", Enums.TestResult.FAIL])
                else:
                    res.append([f"Cloak ping detect attach / Detach was not completed properly", Enums.TestResult.INCONCLUSIVE])
            #check whether waited for 1 minute otherwise check auth sequence again initiated
            if cloak_cycle_count_check:
                #check the total timing
                # print(self.file_list[self.Flow_limit[1]]['startTime'])
                # print(self.file_list[temp_ids[1]]['startTime'])
                timing = round((self.file_list[temp_ids[1]]['startTime'] - self.file_list[temp_ids[0]]['startTime']) * 1000, 3)
                # print("Timing", timing)
                minutes = timing / (1000 * 60)
                data_stream = False
                data_stream_index = 0
                if minutes >= 1.0:
                    #check whether auth sequence initiated
                    for auth in range(temp_ids[1], self.Flow_limit[1]):
                        if 'SADC' in self.file_list[auth]['pktType'] and not self.file_list[auth]['isTesterPkt']:
                            data_stream = True
                            data_stream_index = auth
                            break
                else:
                    res.append([f"Streamer not waited for 1 minute of duration - Observed duration: {minutes}", Enums.TestResult.INCONCLUSIVE])
                if not data_stream:
                    res.append([f"data stream was not started by PRX & limit: [{temp_ids[1], self.Flow_limit[1]}]", Enums.TestResult.PASS])
                else:
                    #if data stream is there need to complete it
                    res.append([f"data stream was started by PRX at index-{self.file_list[data_stream_index]['rowIndex']}", Enums.TestResult.PASS])
                    #logic for complete the sequence of auth sequence initiated

            #fallback logic if not got expected
            if not sadc_open_check:
                res.append([f"SADC Open packet by DUT not found", Enums.TestResult.INCONCLUSIVE])
            if not sadt_check:
                res.append([f"SADT_1 packet by DUT not found", Enums.TestResult.FAIL])
            if not xce_1_found:
                res.append([f"XCE packet by DUT not found", Enums.TestResult.FAIL])
            if not atn_check:
                res.append([f"ATN response not found", Enums.TestResult.FAIL])
            if not dsr_check:
                res.append([f"DSR/POLL packet not found", Enums.TestResult.FAIL])
            if not ptx_cloak:
                res.append([f"Cloak by Ptx was not initiated", Enums.TestResult.FAIL])
            if not prx_cloak:
                res.append([f"Cloak by Prx was not initiated", Enums.TestResult.FAIL])
        else: res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def EDS_stream(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit'] 
        #check EDS packet before initiating the Auth sequence
        eds_initiated = False
        for eds in range(self.Flow_limit[0], self.Flow_limit[1]):
            if 'Enabled Data Streams' in self.file_list[eds]['pktType'] and not self.file_list[eds]['isTesterPkt']:
                eds_initiated = True
                res.append([f"Prx Requested Enabled Data Streams packet at {round(self.file_list[eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
                response_eds = self.GetPacketResponse3(eds, [eds,self.Flow_limit[1]])
                if self.file_list[response_eds]['pktType'] == 'Enabled Data Streams':
                    res.append([f"PTx responded with Enabled Data Streams packet for EDS packet request from Prx at {round(self.file_list[response_eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
        if not eds_initiated:
            pass  #if requires can edit later
        #check sequence entered the PT phase                         
        pt_pass = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                break
        if pt_pass:
            
            # TPT to respond to all the authentication request from PRX
            SADC_open_check = False
            SDSR_open_check = False
            SADC_close_check = False
            SDSR_close_check = False
            atn_check = False
            dsr_check = False
            SADT_check = False
            SADT_response = False
            # epp_supported = False
            # crc_proper = False
            crc_indexes = 0
            epp_list = []
            crc_list = []
            temp_id = 0
            temp_id_1 = 0
            dsr = 0
            timing_check = False
            minutes = None
            for sadc in range(self.Flow_limit[0], self.Flow_limit[1]+1):
                if 'SADC' in self.file_list[sadc]['pktType'] and 'Open' in self.file_list[sadc]['value'] and not self.file_list[sadc]['isTesterPkt']:
                    SADC_open_check = True
                    temp_id = sadc
                    #check response for the SADC open packet
                    response = self.GetPacketResponse3(sadc, [temp_id,self.Flow_limit[1]])
                    # print("response",self.file_list[response]['pktType'])
                    if self.file_list[response]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response]['value']:
                        SDSR_open_check = True
                    for sadc_close in range(temp_id, self.Flow_limit[1]):
                        if 'SADC' in self.file_list[sadc_close]['pktType'] and 'Close' in self.file_list[sadc_close]['value'] and not self.file_list[sadc_close]['isTesterPkt']:
                            SADC_close_check = True
                            temp_id_1 = sadc_close
                            # check response for the SADC close packet
                            response = self.GetPacketResponse3(sadc_close, [temp_id_1,self.Flow_limit[1]])
                            if self.file_list[response]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response]['value']:
                                SDSR_close_check = True
                            break
                    break
            # print(SADC_open_check, SDSR_open_check, SADC_close_check, SADC_close_check)
            if SADC_open_check and SDSR_open_check and SADC_close_check and SDSR_close_check:
                #check SADT and their response
                for sadt in range(temp_id, temp_id_1):
                    if 'SADT' in self.file_list[sadt]['pktType']:
                        SADT_check = True
                        response = self.GetPacketResponse3(sadt, [sadt,self.Flow_limit[1]])
                        if self.file_list[response]['pktType'] == 'ACK' or self.file_list[response]['pktType'] == 'NAK':
                            SADT_response = True
                if not SADT_check:
                    res.append([f"SADT packet was not found", Enums.TestResult.INCONCLUSIVE])
                if not SADT_response:
                    res.append([f"TPT not responds to all SADT packets", Enums.TestResult.FAIL])
            # print(SADC_open_check,SDSR_open_check,SADC_close_check,SDSR_close_check,SADT_check,SADT_response)
            if SADC_open_check and SDSR_open_check and SADC_close_check and SDSR_close_check and SADT_check and SADT_response:
                res.append([f"TPT responds to all Authentication request from PRx packets", Enums.TestResult.PASS])
            else: res.append([f"TPT not responds to all Authentication request from PRx packets", Enums.TestResult.FAIL])

            #check ATN and DSR packet
            if SADT_check and SADT_response:
                for atn in range(temp_id_1+1 , self.Flow_limit[1]):
                    if 'ATN' in self.file_list[atn]['pktType']:
                        atn_check = True
                        res.append([f"ATN response was found at index-{self.file_list[atn]['rowIndex']}", Enums.TestResult.PASS])
                        for dsr in range(temp_id_1, self.Flow_limit[1]):
                            if 'DSR' in self.file_list[dsr]['pktType'] and '{POLL}' in self.file_list[dsr]['value']:
                                dsr_check = True
                                res.append([f"DSR/POLL packet was found at index-{self.file_list[dsr]['rowIndex']}", Enums.TestResult.PASS])
                                temp_id = dsr
                                break
                        break

                if not atn_check:
                    res.append([f"ATN response was not initiated for the XCE packet", Enums.TestResult.FAIL])
                if not dsr_check:
                    res.append([f"DSR/POLL packet was not initiated", Enums.TestResult.FAIL])

            #validation for 11.5.9 test case
            if atn_check and dsr_check and Check['timing_check_1min'] is None and Check['checking_even_data_stream'] is not None:
                #check open and close limit
                open_1 = None
                SADC_open_check_1 = False
                SADC_close_check_1 = False
                sdsr_open_check = False
                sdsr_close_check = False
                response_1 = 0
                response_2 = 0
                new_limit_1 = []
                index_sdsr = 0
                for open_1 in range(dsr+1, self.Flow_limit[1]):
                    #sadc_open
                    if 'SADC' in self.file_list[open_1]['pktType'] and 'Open' in self.file_list[open_1]['value'] and self.file_list[open_1]['isTesterPkt']:
                        SADC_open_check_1 = True
                        #check the response for that packet
                        for op in range(open_1, self.Flow_limit[1]):
                            if 'SADC' in self.file_list[op]['pktType'] and 'Close' in self.file_list[op]['value'] and self.file_list[op]['isTesterPkt']:
                                for op1 in range(open_1, op):
                                    if 'SDSR' in self.file_list[op1]['pktType'] and 'ACK' in self.file_list[op1]['value']:
                                        response_1 = op1
                                        break
                                break
                        # response_1 = self.GetPacketResponse3(open_1, [open_1,self.Flow_limit[1]], uut = True)
                        # print(response_1, self.file_list[response_1]['pktType'])
                        if self.file_list[response_1]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response_1]['value']:
                            sdsr_open_check = True
                            
                        else: res.append([f"SDSR-ACK response not observed for the SADC-Open packet", Enums.TestResult.FAIL])
                        #sadc_close              
                        for close_1 in range(response_1, self.Flow_limit[1]):
                            if 'SADC' in self.file_list[close_1]['pktType'] and 'Close' in self.file_list[close_1]['value'] and self.file_list[close_1]['isTesterPkt']:
                                SADC_close_check_1 = True
                                #check the response for that packet
                                for cl in range(close_1, self.Flow_limit[1]):
                                    if 'SDSR' in self.file_list[cl]['pktType'] and 'ACK' in self.file_list[cl]['value']:
                                        response_2 = cl
                                        break
                                # response_2 = self.GetPacketResponse3(close_1, [close_1,self.Flow_limit[1]], uut = True)
                                # print(response_2, self.file_list[response_2]['pktType'])
                                if self.file_list[response_2]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response_2]['value']:
                                    sdsr_close_check = True
                                    index_sdsr = response_2
                                elif self.file_list[response_2]['pktType'] == 'SDSR' and 'ERR_CRC' in self.file_list[response_2]['value']:
                                    sdsr_close_check = False
                                    index_sdsr = response_2
                                else: res.append([f"SDSR-ACK response not observed for the SADC-Close packet", Enums.TestResult.FAIL])
                                break
                        break
                if not SADC_open_check_1:
                    res.append([f"SADC-Open by Prx was not found", Enums.TestResult.INCONCLUSIVE])
                if not SADC_close_check_1:
                    res.append([f"SADC-Close by Prx was not found", Enums.TestResult.INCONCLUSIVE])
                # print(SADC_open_check_1, SADC_close_check_1)
                #check continuos 3x same pattern
                if SADC_open_check_1 and SADC_close_check_1:
                    sadt_list = []
                    new_limit_1 = [response_1, response_2]
                    for i in range(response_1, response_2 + 1):
                        pkt = self.file_list[i].get('pktType', '')
                        if 'SADT' in pkt:
                            sadt_list.append([pkt, i])
                    # print(sadt_list)
                    even_pattern_found = False
                    found_index = 0
                    for i in range(len(sadt_list) - 2):
                        if (sadt_list[i][0].endswith('e') and sadt_list[i+1][0].endswith('e') and sadt_list[i+2][0].endswith('e')):                                                                                                                               
                            # print(sadt_list[i][1])  
                            found_index = sadt_list[i][1]
                            even_pattern_found = True
                            break
                    if even_pattern_found:
                        res.append([f"Repeating SADT/even packet 3x on the same stream was found. indexes-[{found_index, found_index+2, found_index+4}]", Enums.TestResult.PASS])
                        #check response for SADC_Close
                        if sdsr_close_check:
                            res.append([f"SDSR-ACK response was observed for SADC-Close packet at index-{self.file_list[index_sdsr]['rowIndex']}", Enums.TestResult.PASS])
                        elif not sdsr_close_check:
                            res.append([f"SDSR-ACK response was not observed for SADC-Close packet, Observed packet: {self.file_list[index_sdsr]['pktType']}", Enums.TestResult.FAIL])
                    else: res.append([f"Repeating SADT/even packet 3x on the same stream was not found.", Enums.TestResult.FAIL])
            
            #validation for 11.5.10 test case
            if atn_check and dsr_check and Check['timing_check_1min'] is None and Check['checking_even_data_stream'] is None:
                #Get the limit for checking 
                open_pkt= 0
                close_pkt=0
                new_limit_2 = []
                for open_2 in range(dsr+1, self.Flow_limit[1]):
                    #sadc_open
                    if 'SADC' in self.file_list[open_2]['pktType'] and 'Open' in self.file_list[open_2]['value'] and self.file_list[open_2]['isTesterPkt']:
                        SADC_open_check_2 = True
                        open_pkt = open_2
                        #sadc_close              
                        for close_2 in range(open_2+1, self.Flow_limit[1]):
                            if 'SADC' in self.file_list[close_2]['pktType'] and 'Close' in self.file_list[close_2]['value'] and self.file_list[close_2]['isTesterPkt']:
                                SADC_close_check_2 = True
                                close_pkt = close_2                                     
                        if Check['open']:  
                            break
                #set before checking into loop for TC1 and TC2
                new_limit_2 = [open_pkt, close_pkt]
                # print(new_limit_2)
                #verify the repeated SADC packets
                if Check['open']:
                    chk_1 = 'Open'
                else:
                    chk_1 = 'Close'
                count = 0
                for rep in range(new_limit_2[0], self.Flow_limit[1]):                              
                    if 'SADC' in self.file_list[rep]['pktType'] and chk_1 in self.file_list[rep]['value'] and self.file_list[rep]['isTesterPkt']:
                        count += 1
                        if count == 1:
                            res.append([f"SADC-{chk_1} packet was found at index-{self.file_list[rep]['rowIndex']}", Enums.TestResult.PASS])
                        elif count == 2: res.append([f"Repeat SADC-{chk_1} packet was found at index-{self.file_list[rep]['rowIndex']}", Enums.TestResult.PASS])
                        else: pass
                        #check response
                        for ress in range(rep, self.Flow_limit[1]):
                            if 'SDSR' in self.file_list[ress]['pktType']:
                                response_1 = ress
                                break
                            
                        # print(response_1)                           
                        value = self.file_list[response_1]['pktType']
                        if self.file_list[response_1]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response_1]['value']:
                            if count == 1:
                                res.append([f"SDSR_ACK response was found for the SADC-{chk_1} packet at index-{self.file_list[response_1]['rowIndex']}", Enums.TestResult.PASS])
                            elif count == 2:
                                res.append([f"Repeat sequence- SDSR_ACK response was found for the SADC-{chk_1} packet at index-{self.file_list[response_1]['rowIndex']}", Enums.TestResult.PASS])
                        else: 
                            if count == 1:
                                res.append([f"SDSR_ACK response was not found for the SADC-{chk_1} packet", Enums.TestResult.FAIL])
                            elif count == 2:
                                res.append([f"Repeated sequence - SDSR_ACK response was not found for the SADC-{chk_1} packet", Enums.TestResult.FAIL])
                if count == 0:
                    res.append([f"SADC-{chk_1} packet was not found in the packet sequence", Enums.TestResult.INCONCLUSIVE])
                                                                                                                    
            #check 1 minute timing after the DSR packet
            if atn_check and dsr_check and Check['timing_check_1min'] is not None:
                # timing_check = False
                timing = round((self.file_list[self.Flow_limit[1]]['startTime'] - self.file_list[temp_id+1]['startTime']) * 1000, 3)
                minutes = timing / (1000 * 60)
                minutes = round(minutes)
                # print("minutes", minutes)
                if minutes >= 1:
                    timing_check = True

            #check EPP version auth not initiated
            epp_supported = None
            crc_proper = None
            if timing_check and Check['timing_check_1min'] is not None:
                packet_indexes = []
                if Check['check_epp']:
                    chk = 'Open'
                else:
                    chk = 'Close'
                for check in range(temp_id, self.Flow_limit[1]):
                    epp_supported = False
                    crc_proper = False
                    if 'SADC' in self.file_list[check]['pktType'] and chk in self.file_list[check]['value'] and not self.file_list[check]['isTesterPkt']:
                        if chk == 'Open':
                            value = self.PktMethod.GetPayloadDetails(check, 'Stream_Number')[0]['sDescription']
                        elif chk == 'Close':
                            response = self.GetPacketResponse3(check, [check,self.Flow_limit[1]])
                            # print(response)
                            value = self.file_list[response]['value']
                            response = self.file_list[response]['pktType']
                        # print(value)
                        if 'Qi Authentication' in value and Check['check_epp']:
                            epp_supported = True
                            epp_list.append(epp_supported)
                            epp_supported = False
                        elif 'ACK' in value and Check['check_CRC'] and response == 'SDSR':
                            crc_proper = True
                            crc_list.append(crc_proper)
                            crc_indexes = check
                            packet_indexes.append(check)
                            if not crc_proper:  #Will provide in loop result to get the non-proper index for user
                                res.append([f"checked CRC was not proper from SADC close packet at {crc_indexes}",Enums.TestResult.FAIL])
                            crc_proper = False
                # print(epp_list)
                # print(crc_list)
                if Check['check_epp']:
                    if all(epp_list):
                        res.append([f"QI EPP are not Supported [Index - {temp_id, self.Flow_limit[1]}", Enums.TestResult.PASS])
                    else: res.append([f"QI EPP are Supported [Index - {temp_id, self.Flow_limit[1]}", Enums.TestResult.FAIL])
                elif Check['check_CRC']:
                    if all(crc_list):
                        res.append([f"All measured CRC was proper by sending SDSR-ACK packet",Enums.TestResult.PASS])
                    else: res.append([f"All measured CRC was not proper by not sending SDSR-ACK packet, [Index - {temp_id, self.Flow_limit[1]}",Enums.TestResult.FAIL])


            #fallback for <1minute of execution
            elif Check['timing_check_1min'] is not None and not timing:
                res.append([f"Streamer not waited for 1 minute of duration - Observed duration: {minutes}", Enums.TestResult.INCONCLUSIVE])

            if not SADC_open_check:
                res.append([f"SADC_Open Packet by PRx was not found", Enums.TestResult.INCONCLUSIVE])
            if not SDSR_open_check:
                res.append([f"SDSR response for SADC open Packet was not found", Enums.TestResult.FAIL])
            if not SADC_close_check:
                res.append([f"SADC_close Packet by PRx was not found", Enums.TestResult.INCONCLUSIVE])
            if not SDSR_close_check:
                res.append([f"SDSR response for SADC close Packet was not found", Enums.TestResult.FAIL])

        else: res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res
    
    def EDS_crc_handling(self,CTSCheck,Check,flows,flwID):
        res = []
        self.Flow_limit = flows[flwID]['Limit'] 
        #check EDS packet before initiating the Auth sequence
        eds_initiated = False
        for eds in range(self.Flow_limit[0], self.Flow_limit[1]):
            if 'Enabled Data Streams' in self.file_list[eds]['pktType'] and not self.file_list[eds]['isTesterPkt']:
                eds_initiated = True
                res.append([f"Prx Requested Enabled Data Streams packet at {round(self.file_list[eds]['startTime'], 3)}sec", Enums.TestResult.PASS])
                response_eds = self.GetPacketResponse3(eds, [eds,self.Flow_limit[1]])
                if self.file_list[response_eds]['pktType'] == 'Enabled Data Streams':
                    res.append([f"PTx responded with Enabled Data Streams packet for EDS packet request from Prx at index-{self.file_list[response_eds]['rowIndex']}", Enums.TestResult.PASS])
        if not eds_initiated:
            pass  #if requires can edit later
        #check sequence entered the PT phase          
        pt_pass = False
        for pt in range(self.Flow_limit[0], self.Flow_limit[1] + 1):
            if 'PT' in self.file_list[pt]['description']:
                pt_pass = True
                break
        if pt_pass:
            
            # TPT to respond to all the authentication request from PRX
            SADC_open_check = False
            SDSR_open_check = False
            SADC_close_check = False
            SDSR_close_check = False
            SADT_check = False
            SADT_response = False
            sadt_responses = []
            temp_id = 0
            temp_id_1 = 0
            err_crc = 0
            for sadc in range(self.Flow_limit[0], self.Flow_limit[1]+1):
                if 'SADC' in self.file_list[sadc]['pktType'] and 'Open' in self.file_list[sadc]['value'] and not self.file_list[sadc]['isTesterPkt']:
                    SADC_open_check = True
                    temp_id = sadc
                    #check response for the SADC open packet
                    response = self.GetPacketResponse3(sadc, [temp_id,self.Flow_limit[1]])
                    # print("response",self.file_list[response]['pktType'])
                    if self.file_list[response]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response]['value']:
                        SDSR_open_check = True
                        temp_id = response + 1
                    for sadc_close in range(temp_id, self.Flow_limit[1]):
                            if 'SADC' in self.file_list[sadc_close]['pktType'] and 'Close' in self.file_list[sadc_close]['value'] and not self.file_list[sadc_close]['isTesterPkt']:
                                SADC_close_check = True
                                temp_id_1 = sadc_close
                                # check response for the SADC close packet
                                response = self.GetPacketResponse3(sadc_close, [temp_id_1,self.Flow_limit[1]])
                                if self.file_list[response]['pktType'] == 'SDSR' and 'ERR_CRC' in self.file_list[response]['value']:
                                    SDSR_close_check = True
                                    err_crc = response
                                break
                    if SADC_open_check and SDSR_open_check and SDSR_close_check and SADC_close_check:
                        #check SADT and their response
                        for sadt in range(temp_id, temp_id_1+1):
                            if 'SADT' in self.file_list[sadt]['pktType']:
                                response = self.GetPacketResponse3(sadt, [sadt,self.Flow_limit[1]])
                                # print(self.file_list[response]['pktType'])
                                if self.file_list[response]['pktType'] == 'ACK':                                                 
                                    SADT_response = True
                                    sadt_responses.append(SADT_response)
                                else: res.append([f"Expected response was not observed for the SADT packet [index-{response}]", Enums.TestResult.FAIL])                                                      
                    break
            #Fall back logic for the expected sequence observed with proper response
            if SADC_open_check and SDSR_open_check and SADC_close_check and SDSR_close_check and SADT_response and all(sadt_responses):
                res.append([f"Prx Auth sequence observed with SDSR-ERR_CRC response at index- [{err_crc}] for the SADC close packet", Enums.TestResult.PASS])
            elif SADC_open_check and SDSR_open_check and SADC_close_check and SDSR_close_check and SADT_response and not all(sadt_responses):
                res.append([f"All SADT responses were not proper, or the expected responses were not received.", Enums.TestResult.FAIL])
            else: res.append([f"Prx Auth sequence with SDSR-ERR_CRC response for the SADC close packet was not observed", Enums.TestResult.FAIL])
            
            if not SADC_open_check:
                res.append([f"SADC_Open Packet by PRx was not found", Enums.TestResult.INCONCLUSIVE])
            if not SDSR_open_check:
                res.append([f"SDSR response for SADC open Packet was not found", Enums.TestResult.FAIL])
            if not SADC_close_check:
                res.append([f"SADC_close Packet by PRx was not found", Enums.TestResult.INCONCLUSIVE])
            if not SDSR_close_check:
                res.append([f"Expected response of SDSR response for SADC close Packet was not found", Enums.TestResult.FAIL])
            
            # print(sadt_responses)
            # print(SADC_open_check, SDSR_open_check, SADC_close_check, SDSR_close_check, SADT_response)
            #check retry sequence of auth from Prx
            if SDSR_close_check:
                temp_id_2 = 0
                retry_auth_check_open = False
                retry_auth_check_close = False
                SDSR_close_check_retry = False
                retry_auth_sdsr_open = False
                retry_auth_sdsr_close = False
                sadt_responses_1 = []
                sadt_res_1 = False
                for sadc_1 in range(temp_id_1, self.Flow_limit[1]+1):
                    if 'SADC' in self.file_list[sadc_1]['pktType'] and 'Open' in self.file_list[sadc_1]['value'] and not self.file_list[sadc_1]['isTesterPkt']:
                        retry_auth_check_open = True
                        temp_id = sadc_1
                        temp_id_2 = sadc_1
                        #check response for the SADC open packet
                        response = self.GetPacketResponse3(sadc_1, [temp_id,self.Flow_limit[1]])
                        # print("response",self.file_list[response]['pktType'])
                        if self.file_list[response]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response]['value']:
                            retry_auth_sdsr_open = True
                            temp_id = response + 1
                        for sadc_close_1 in range(temp_id, self.Flow_limit[1]):
                                if 'SADC' in self.file_list[sadc_close_1]['pktType'] and 'Close' in self.file_list[sadc_close_1]['value'] and not self.file_list[sadc_close_1]['isTesterPkt']:
                                    retry_auth_check_close = True
                                    temp_id_1 = sadc_close_1
                                    # check response for the SADC close packet
                                    response = self.GetPacketResponse3(sadc_close, [temp_id_1,self.Flow_limit[1]])
                                    if self.file_list[response]['pktType'] == 'SDSR' and 'ACK' in self.file_list[response]['value']:
                                        retry_auth_sdsr_close = True
                                    break
                        # print(retry_auth_check_open, retry_auth_check_close, retry_auth_sdsr_open, retry_auth_sdsr_close)
                        if retry_auth_check_open and retry_auth_check_close:
                            for check_1 in range(temp_id_2, temp_id_1):
                                if 'SADT' in self.file_list[check_1]['pktType']:
                                    response = self.GetPacketResponse3(check_1, [check_1,self.Flow_limit[1]])
                                    if self.file_list[response]['pktType'] == 'ACK':
                                        sadt_responses_1.append(True)
                                        sadt_res_1 = True 
                                
                        break
                # print(temp_id_2, temp_id_1)
                # print(retry_auth_check_open, retry_auth_check_close, sadt_responses_1)
                if retry_auth_check_open and retry_auth_check_close:
                    res.append([f"Retry auth sequence was observed with SADC open at index {temp_id_2} and SADC close at index {temp_id_1}", Enums.TestResult.PASS])
                else: res.append([f"Retry auth sequence was not observed properly", Enums.TestResult.FAIL])
                                            
                #retry auth fall back logic
                if retry_auth_check_open and retry_auth_check_close and retry_auth_sdsr_open and retry_auth_sdsr_close and all(sadt_responses_1):
                    res.append([f"Retry auth sequence was observed with proper response for the SADT packets", Enums.TestResult.PASS])
                elif retry_auth_check_open and retry_auth_check_close and retry_auth_sdsr_open and retry_auth_sdsr_close and not all(sadt_responses_1):
                    res.append([f"Retry auth sequence was observed but SADT responses were not proper, or the expected responses were not received.", Enums.TestResult.FAIL])
                else: res.append([f"Retry auth sequence with proper response was not observed", Enums.TestResult.FAIL])
                                                                                                                            
        else:
            res.append([f"The packet sequence doesn't entered PT phase", Enums.TestResult.INCONCLUSIVE])
        return res


    #-------------------------------------------------------------------------------------------------------------- Ranjith (Support Functions) -------------------------------------------------------------------------------#      

    def eds_default(self, limit):
        temp_seq = []
        id = limit[0]
        while id < limit[1]:
            if "SADC" in self.file_list[id]['pktType'] and "Open" in self.file_list[id]['value'] and not self.file_list[id]['isTesterPkt']:
                uid = id + 1
                while uid < limit[1]:
                    if "SADC" in self.file_list[uid]['pktType'] and "Close" in self.file_list[uid]['value'] and self.file_list[uid]['isTesterPkt']:
                        temp_seq.append([id, uid])
                        break
                    uid += 1
                id = uid + 1
            id += 1
        return temp_seq
    
    def GetPacketResponse3(self, index, limit, uut = False):
        # print(limit)
        uut_check = uut
        if uut_check == True:
            # print(limit)
            id = limit[0]
            # print(self.GetPacketType(id),id)
            while id < limit[1]:
                if self.PktMethod.GetPacketType(id) == "Packet":
                    return id
                elif self.PktMethod.GetPacketType(id) == "Response":
                    if self.file_list[id].get('pktType') == self.file_list[index].get('pktType') and self.file_list[
                        id].get('value') == self.file_list[index].get('value'):
                        pass
                    else:
                        return None
                elif self.PktMethod.GetPacketType(id) == "TesterMsg":
                    pass
                id += 1
        else:
            id = limit[0]
            # print(self.GetPacketType(id),id)
            while id < limit[1]:
                if self.PktMethod.GetPacketType(id) == "Response":
                    return id
                elif self.PktMethod.GetPacketType(id) == "Packet":
                    if self.file_list[id].get('pktType') == self.file_list[index].get('pktType') and self.file_list[id].get('value') == self.file_list[index].get('value'):
                        pass
                    else:
                        return None
                elif self.PktMethod.GetPacketType(id) == "TesterMsg":
                    pass
                id += 1
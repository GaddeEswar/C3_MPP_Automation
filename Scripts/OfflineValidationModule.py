import traceback
from MainModule import JsonOperations,APIOperations,GeneralMethods
import os
import zipfile
import io

class PacketMethods:
    def __init__(self,file_list,Header):
        # self.Product = Product
        # self.Mode = Mode
        self.file_list = file_list
        self.Header =Header
        self.Japi = JsonOperations('json/Xpath.json')
        # self.Japi = JsonOperations('json/Xpath.json')
        # JapiDatatemp =self.Japi.read_file()
        # self.JapiData = JapiDatatemp['API']

    #1.Get packet Type, testermsg/packet/response
    def GetPacketType(self,id):
        if self.Header['Product'] == "C3":
            if self.Header['Mode'] == 'TPT':
                if self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
            elif self.Header['Mode'] =="TPR":
                if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
        elif self.Header['Product'] == "MPP":
            if self.Header['Mode']=="TPR":
                if self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
            elif self.Header['Mode']=="TPT":
                if self.file_list[id]['isTesterPkt']==False and self.file_list[id]['isFWTestermessage']==False:
                    return 'Packet'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==False:
                    return 'Response'
                elif self.file_list[id]['isTesterPkt']==True and self.file_list[id]['isFWTestermessage']==True:
                    return 'TesterMsg'
        return None
    
    #2 To search a given packet in the given limit, if packet found return the packet details  [starttime,endtime,index]
    def GetPacketDetails(self,packet='',value=None,limit=[],timelimit=None,Type="Packet"):
        # print(limit,packet)
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                # print(id,self.file_list[id].get('pktType'))
                if packet.lower() in self.file_list[id].get('pktType').lower() and value.lower() in self.file_list[id].get('value').lower() if value is not None else packet.lower() in self.file_list[id].get('pktType').lower():
                    if self.GetPacketType(id)==Type:
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

    def GetexactPacketDetails(self,packet='',value=None,limit=[],timelimit=None,Type="Packet"):
        # print(limit,packet)
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                # print(id,self.file_list[id].get('pktType'))
                if packet == self.file_list[id].get('pktType') and value in self.file_list[id].get('value') if value is not None else packet == self.file_list[id].get('pktType'):
                    if self.GetPacketType(id)==Type:
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
    
    def GetPacketDetails2(self,packet='',value=None,limit=[],timelimit=None,Type="Packet"):
        # print(limit,packet)
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                # print(id,self.file_list[id].get('pktType'))
                if type(value) != list:
                    if packet in self.file_list[id].get('pktType') and value ==self.file_list[id].get('value') if value is not None else packet in self.file_list[id].get('pktType'):
                        if self.GetPacketType(id)==Type:
                            if timelimit is None:
                                return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                            else:
                                if self.file_list[id].get('startTime') >= timelimit:
                                    return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]

                else:
                    if packet in self.file_list[id].get('pktType') and any( rs== self.file_list[id].get('value') for rs in value) if value is not None else packet in self.file_list[id].get('pktType'):
                        if self.GetPacketType(id)==Type:
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
                if all(rs in self.file_list[id].get('pktType') for rs in packet) and value ==self.file_list[id].get('value') if value is not None else packet in self.file_list[id].get('pktType'):
                    return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        return[0]

    def GetExactPacketDetails(self,packet='',value=None,limit=[],timelimit=None,Type="Packet"):
        # print(limit,packet)
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
                # print(id,self.file_list[id].get('pktType'))
                if type(value) != list:
                    if packet == self.file_list[id].get('pktType') and value == self.file_list[id].get('value') if value is not None else packet == self.file_list[id].get('pktType'):
                        if self.GetPacketType(id)==Type:
                            if timelimit is None:
                                return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                            else:
                                if self.file_list[id].get('startTime') >= timelimit:
                                    return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]

                else:
                    if packet == self.file_list[id].get('pktType') and any( rs== self.file_list[id].get('value') for rs in value) if value is not None else packet == self.file_list[id].get('pktType'):
                        if self.GetPacketType(id)==Type:
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
                if all(rs == self.file_list[id].get('pktType') for rs in packet) and value == self.file_list[id].get('value') if value is not None else packet == self.file_list[id].get('pktType'):
                    return[self.file_list[id].get('startTime'),self.file_list[id].get('stopTime'),id]
                if limit[0]<limit[1]:
                    id+=1
                else: id-=1
        return[0]
    

    def GetGeneralPayloadDetails(self, index, name,Byte,Bit):
        headers = self.file_list[index].get('header_Payload', {}).get('childelement', [])
        # return [p for h in headers for p in h.get('childelement', [])
        #         if p.get('sDecodedValue') == name]
        # result = []  # Initialize an empty list to store matching elements

        # for h in headers:
        #     child_elements = h.get('childelement', [])
        #     if h.get('sFieldType') == Byte:
        #         for p in child_elements:
        #             if p.get('sBitIndex') == Bit and p.get('sDecodedValue')==name or p.get('sDescription') == name: result.append(p)  

        # # print(result)
        # return result

        return [p for h in headers if h.get('sFieldType')==Byte for p in h.get('childelement', []) if p.get('sBitIndex') == Bit and ( name in p.get('sDecodedValue') or name in p.get('sDescription'))]
                
    def hex_to_decimal(self,raw_hex):
        try:
            if isinstance(raw_hex, str) and raw_hex.lower().startswith("0x"):
                raw_hex = raw_hex[2:]
                return float(int(raw_hex, 16))
            else:return float(raw_hex)
        except Exception:
            return None

    def compare_hex_to_expected(self,raw_hex, expected_values, comparator="EQL",Type="DEC"):
        dec_val = raw_hex if Type == "HEX" or Type =="String" else self.hex_to_decimal(raw_hex)
        if dec_val is None:
            return False, None

        match comparator:
            case "NEQ": return dec_val not in expected_values, dec_val
            case "GT":  return all(dec_val > val for val in expected_values), dec_val
            case "GTE": return all(dec_val >= val for val in expected_values), dec_val
            case "LT":  return all(dec_val < val for val in expected_values), dec_val
            case "LTE": return all(dec_val <= val for val in expected_values), dec_val
            case "BTW":return (expected_values[0] <= dec_val <= expected_values[1]), dec_val
            case "IN": return dec_val in expected_values, dec_val
            case "EQL": return dec_val == expected_values[0], dec_val
            case "ANY": return True, dec_val
        
        return False, dec_val      
    #3- Find the Testcase index in group TC mode
    def GetTCindexfromGroupRun(self,BackupJson,TestID):
        BackupJson=BackupJson
        TestID=TestID
        JBkup = JsonOperations(BackupJson)
        JBkupData =JBkup.read_file()
        TClist = []
        for TCdata in JBkupData["testBkpTestResultsandPath"]:
            if TestID == TCdata['testcaseDetails']['m_DisplayName']:
                #Get same tracepath tc's 
                for TmpTcdata in JBkupData["testBkpTestResultsandPath"]:
                    if TCdata['actualTracePath'] == TmpTcdata['actualTracePath']:
                        TClist.append(TmpTcdata['testcaseDetails']['m_DisplayName'])
        # print(TClist)
        if len(TClist)>0:
            # print(TClist.index(self.TestID))
            return TClist.index(TestID)
        return 0
    #Functions related to the CTS checks

    #5. Get Stabilizied index and value
    def GetInitialVoltage(self,index,flows):
        # if str(index) in self.Json_TC['other_checks_details']:
            # if 'CEStability' in self.Json_TC['other_checks_details'][str(index)]:
        try:
            # limit=[self.timing_map[index]['General']['PD'][0][0][0],self.timing_map[index]['General']['SD'][0][0][0]]
            flows=flows
            limit = flows[index]['Limit']
            # print(limit)
            id = limit[0]
            while id < limit[1]:
                if 'MPP_XCEV_Ideal' in self.file_list[id].get('pktType'):
                    # print(id)
                    revid = id
                    while revid > limit[0]:
                        if self.file_list[revid].get('pktType') in ['Control Error','Extended Control Error']:
                            self.stability=revid
                            #GetIntital Voltage
                            # print(self.Json_TC['other_checks_details'])
                            # if 'InitialVoltage' in self.Json_TC['other_checks_details'][str(index)]:
                            res = self.CalculateVoltTwindow(revid,self.GetAllChannelData(index='2'))
                            self.initialVoltage =  res[0]
                            # print('stability',self.stability,self.initialVoltage)
                            break
                        revid-=1
                    break
                id+=1
        except Exception as e:
            traceback.print_exc()

    #6. calculate vrect min /max for all XCE twin time
    def CalculateVoltTwindow(self,indx,AllChannelData,winsize=[5,8],at='start',measure='before',max = False): 
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
        # Vrectmin = 0
        max = max
        # min = min
        while id <= xceEindex:
            VRlist.append(abs(AllChannelData['RV']['displayDataChunk'][id]))
            # print("voltages:",abs(AllChannelData['RV']['displayDataChunk'][id]))
            if max:
                if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) > Vrectmax or Vrectmax==0: 
                    Vrectmax = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
                    # print("Vrectmax:",Vrectmax)
            # if min :
            #     if round(abs(AllChannelData['RV']['displayDataChunk'][id]),4) < Vrectmin or Vrectmin==0: 
            #         Vrectmin = round(abs(AllChannelData['RV']['displayDataChunk'][id]),4)
            #         # print("Vrectmin:",Vrectmin)
            id+=1
        # print("Vrectmax:",Vrectmax)
        # print(VRlist)
        return [Vrectmax] if max else [round((sum(VRlist)/len(VRlist)),5), id-1]
   
    
    #8. Get the payload details by name
    def GetPayloadDetails(self,index,name):
        result = []
        for bits in self.file_list[index]['header_Payload']['childelement']:
            for payloads in bits['childelement']:
                if name in payloads['sDecodedValue'] or name in payloads['sDescription']:
                    result.append(payloads)
        return result
    
    #9.Find the Limits
    def GetLimits(self,Limittype,details,FlowLimit):
        # print(details['Packet'][0])
        TempLimit = FlowLimit
        id = FlowLimit[0]
        if Limittype=="Flow":
            TempLimit = FlowLimit
        elif Limittype=="FlowReverse":
            TempLimit = [FlowLimit[1],FlowLimit[0]]
        elif Limittype == "refNextAll":
            TempLimit = [FlowLimit[1],len(self.file_list)-1]
        elif Limittype == "refAllFromBack":
            TempLimit = [len(self.file_list)-1,0]
        elif Limittype == "PacketWithResponse":
            while id < FlowLimit[1]:
                Pkt = self.GetPacketDetails(packet=details['Packet'][0],value=details['Packet'][1],limit=[id,FlowLimit[1]])
                if len(Pkt)>2:
                    #Get the response
                    tmpid = Pkt[2]+1
                    while tmpid < FlowLimit[1]:
                        if self.GetPacketType(tmpid)=="Response":
                            if self.file_list[tmpid]['pktType'] == details['Response']:
                                TempLimit= [Pkt[2],FlowLimit[1]]
                                break
                        elif self.GetPacketType(tmpid)=="Packet":break
                        tmpid+=1
                    id=Pkt[2]+1
                else:break
        elif Limittype == "refPrevious":
            TempLimit = [0,FlowLimit[0]]
        elif Limittype == "refNextAll":
            TempLimit = [FlowLimit[1],len(self.file_list)-1]
        elif Limittype == "refAll":
            TempLimit=[0,len(self.file_list)-1]
        elif Limittype == "ExncnttoEND":
            exn = self.GetPacketDetails(packet="Execution_count_no",limit=[len(self.file_list)-1,0],Type="TesterMsg")
            TempLimit=[exn[2],len(self.file_list)-1] if len(exn)>2 else [0,len(self.file_list)-1]
        elif Limittype=='BTWNpkts':
            CP1 = self.GetPacketDetails(packet=details['CustomLimit']['Packet1'][0],value=details['CustomLimit']['Packet1'][1],limit=FlowLimit,Type=details['CustomLimit']['Packet1'][2])
            CP2 = self.GetPacketDetails(packet=details['CustomLimit']['Packet2'][0],value=details['CustomLimit']['Packet2'][1],limit=FlowLimit,Type=details['CustomLimit']['Packet2'][2])
            if len(CP1)>2 and len(CP2)>2: TempLimit=[CP1[2],CP2[2]]
        elif Limittype == "PreviousSD_Flow":
            #consdier the current flow starting from previous SD
            SD = self.GetPacketDetails(packet="Shutdown",limit=[FlowLimit[0],0],Type="TesterMsg")
            if len(SD)>2:
                TempLimit=[SD[2]+1,FlowLimit[1]]
        elif Limittype == "FromCustomPacket":
            CP = self.GetPacketDetails(packet=details['CustomLimit']['Packet'][0],value=details['CustomLimit']['Packet'][1],limit=FlowLimit,Type=details['CustomLimit']['Type'])
            TempLimit=[CP[2]+1,FlowLimit[1]] if len(CP)>2 else FlowLimit
        elif Limittype == "FromlatestCustomPacket":
            CP = self.GetPacketDetails(packet=details['CustomLimit']['Packet'][0],value=details['CustomLimit']['Packet'][1],limit=[FlowLimit[1],FlowLimit[0]],Type=details['CustomLimit']['Type'])
            TempLimit=[CP[2]+1,FlowLimit[1]] if len(CP)>2 else FlowLimit
        elif Limittype == "UptoCustomPacket":
            CP = self.GetPacketDetails(packet=details['CustomLimit']['Packet'][0],value=details['CustomLimit']['Packet'][1],limit=FlowLimit,Type=details['CustomLimit']['Type'])
            TempLimit=[FlowLimit[0],CP[2]] if len(CP)>2 else FlowLimit
        elif Limittype == "BeforeCustomPacket":
            CP = self.GetPacketDetails(packet=details['CustomLimit']['Packet'][0],value=details['CustomLimit']['Packet'][1],limit=FlowLimit,Type=details['CustomLimit']['Type'])
            TempLimit=[CP[2],0] if len(CP)>2 else FlowLimit
        return TempLimit

    #11- Idetify flow for MPP
    def Findflow(self,limit):
        id = limit[0]
        index = 1
        while id<limit[1]:
            if 'Identification' in self.file_list[id].get('pktType'):
                index=1
            if 'Specific Request' in self.file_list[id].get('pktType') and 'Frequency Selection: 360 Khz' in self.file_list[id].get('value'):
                index = 1
                break
            if 'Extended_Power_Receiver_Capabilities' in self.file_list[id].get('pktType'):
                index = 2
                break
            elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' in self.file_list[id].get('value'):
                index = 1
                break
            elif 'Modulation_Type' in self.file_list[id].get('pktType') and '33nF' not in self.file_list[id].get('value'):
                index = 2
                break
            elif 'FOP:' in  self.file_list[id].get('value'):
                if float(self.file_list[id].get('value').split(':')[1].split(' ')[0]) >300:
                    index =2
                    break
                else:
                    index=1
                    break
            id+=1
        return index
    #Get the proper packet Response
    def GetPacketResponse(self,index,limit):
        # print(limit)
        id = limit[0]
        while id < limit[1]:
            # print(self.GetPacketType(id),id)
            if self.GetPacketType(id)=="Response":
                return id
            elif self.GetPacketType(id)=="Packet":
                break
            id+=1
        return None
    def GetPacketResponse2(self,index,limit):
        # print(limit)
        id = limit[0]
        # print(self.GetPacketType(id),id)
        while id < limit[1]:
            if self.GetPacketType(id)=="Response":
                return id
            elif self.GetPacketType(id)=="Packet":
                if self.file_list[id].get('pktType')==self.file_list[index].get('pktType') and self.file_list[id].get('value')==self.file_list[index].get('value'):
                    pass
                else: return None 
            elif self.GetPacketType(id)=="TesterMsg":
                pass
            id += 1


    def Timeconvert(self,sec):
        if sec is not None and type(sec) is not str:
            minutes = int(sec // 60)
            seconds = round(sec % 60,3)
            return f"{minutes} min : {seconds} sec"
        else: return f"{sec} sec"

    def ms_to_time(self,ms):
        total_seconds = ms / 1000

        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)

        remaining = total_seconds - (minutes * 60 + seconds)
        milliseconds = int(remaining * 1000)
        microseconds = int((remaining * 1000 - milliseconds) * 1000)

        return f"{minutes} min : {seconds} sec : {milliseconds} ms : {microseconds} µs"

        
    ###______________Common CTS methods_________________
class PlotMethods():
    def __init__(self,Header):
        self.Header = Header
    def GetAllChannelData(self,index,JapiData,plottime=None):
        try:
            ACD={}
            TestTime = CommonMethods.GetRunTime(JapiData,self.Header)
            if plottime is None:
                if TestTime[1]/60 >15:
                    # print(TestTime[1]/60)
                    plottime = int(((TestTime[1]*1000)/2.5)-80)
                else:
                    plottime = int(((TestTime[1]*1000)/1.0510)-80)
                # print(plottime)
            
            # SignalAPI = APIOperations(url=JapiData[self.Header['Product']][self.Header['Mode']]['GetAllChannelData'],retype='json',param1=TestTime[1],param2=plottime)
            # # print(SignalAPI.url)
            # data = SignalAPI.GetRequest()
            # print("data:",len(data))

            fulldatta = []
            while len(fulldatta) == 0:
                SignalAPI = APIOperations(url=JapiData[self.Header['Product']][self.Header['Mode']]['GetAllChannelData'],retype='json',param1=TestTime[1],param2=plottime)
                # print(SignalAPI.url)
                data = SignalAPI.GetRequest()
                fulldatta = data[index]['displayDataChunk']
                # print("fulldatta:",len(fulldatta),"plottime:",plottime)
                
                # if plottime <= 100000:
                #     plottime -= 10000
                # else: plottime -= 100000
                plottime -= 10000

                if len(fulldatta) > 0: break
            # print("plottime2:",plottime)

            if index in data:
                ACD['RV']=data[index]
                ACD['starttime'] = data[index]['absoluteStartTime']
                ACD['endtime'] = data[index]['absoluteEndTime']
                ACD['records'] = len(data[index]['displayDataChunk'])
                ACD['Diff'] =  ((ACD['endtime']-ACD['starttime'])/100000) # ACD['Diff'] =  ((ACD['endtime']-ACD['starttime'])/100000)
                ACD['Interval'] = (ACD['Diff']/ACD['records'])
            return ACD
        except Exception as e:
            print(e) 
    def GetAllChannelData2(self,index,JapiData):
        try:
            ACD={}
            TestTime = CommonMethods.GetRunTime(JapiData,self.Header)
            if TestTime[1]/60 >15:
                # print(TestTime[1]/60)
                plottime = int(((TestTime[1]*1000)/2.5)-80)
            else:
                plottime = int(((TestTime[1]*1000)/1.0510)-80)
            
            plottime = 1000000 #no fo sample

            fulldatta = []
            while len(fulldatta) == 0:
                SignalAPI = APIOperations(url=JapiData[self.Header['Product']][self.Header['Mode']]['GetAllChannelData'],retype='json',param1=TestTime[1],param2=plottime)
                # print(SignalAPI.url)
                data = SignalAPI.GetRequest()
                fulldatta = data[index]['displayDataChunk']
                # print("fulldatta:",len(fulldatta),"plottime:",plottime)
                
                # if plottime <= 100000:
                #     plottime -= 10000
                # else: plottime -= 100000
                plottime -= 10000

                if len(fulldatta) > 0: break
            # print("plottime2:",plottime)
            if index in data:
                ACD['RV']=data[index]
                ACD['starttime'] = data[index]['absoluteStartTime']
                ACD['endtime'] = data[index]['absoluteEndTime']
                ACD['records'] = len(data[index]['displayDataChunk'])
                ACD['Diff'] =  ((ACD['endtime']-ACD['starttime'])/100000) # ACD['Diff'] =  ((ACD['endtime']-ACD['starttime'])/100000)
                ACD['Interval'] = (ACD['Diff']/ACD['records'])
            return ACD
        except Exception as e:
            print(e) 

    #7. Get voltage for given time
    def CalculateVoltageOnTime(self,AllChannelData,time):
        index = int(time/AllChannelData['Interval'])
        #retrun in milliVolt
        return round(abs(AllChannelData['RV']['displayDataChunk'][index]*1000),4)
    def CalculateAVGPowerTimePeriod(self,AllChannelData,AllChannelData2,STime,Etime):
        Power = []
        Sindex = int(STime/AllChannelData['Interval'])
        Eindex = int(Etime/AllChannelData['Interval'])
        id = Sindex
        while id <=Eindex:
            Power.append(round(abs(AllChannelData['RV']['displayDataChunk'][id])*abs(AllChannelData2['RV']['displayDataChunk'][id])*1000,4))
            id+=1
        if len(Power)>0:
            return round((sum(Power)/len(Power)),3)

    def CalculateHighVoltageTimePeriod(self,AllChannelData,STime,Etime):
        Voltage = []
        Sindex = int(STime/AllChannelData['Interval'])
        Eindex = int(Etime/AllChannelData['Interval'])
        id = Sindex
        # print(Sindex,Eindex)
        while id <=Eindex:
            Voltage.append(round(abs(AllChannelData['RV']['displayDataChunk'][id]),3))
            id+=1
        if len(Voltage)>0:
            # print(Voltage)
            return round(max(Voltage),3)
        return None
        
    def GetEyeData(self,AllChannelData,Time):
        Sindex = int(Time[0]/AllChannelData['Interval'])
        Eindex = int(Time[1]/AllChannelData['Interval'])
        RawData = []
        id = Sindex
        # print(id,Eindex)
        while id <= Eindex:
            RawData.append(round(abs(AllChannelData['RV']['displayDataChunk'][id]*1000),4))
            id+=1
        return RawData
        # print(RawData)

class CommonMethods():
    def __init__(self):
        pass
    #1-Get Run time of the testcase, returns start time and end in nanoseconds,
    def GetRunTime(JapiData,Header):
        TcStartAPI = APIOperations(url=JapiData[Header['Product']][Header['Mode']]['GetWaveformStartTime'],retype='json')
        TCstartTime = TcStartAPI.GetRequest()
        TcStopAPI = APIOperations(url=JapiData[Header['Product']][Header['Mode']]['GetWaveformStopTime'],retype='json')
        TCstopTime = TcStopAPI.GetRequest()
        return[TCstartTime,TCstopTime/100000000]
    #2. Find that the measured CTS checks are in limit or not
    def check_measure(exp_val,obsr_val,comp=0):
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

                elif comp =='GT':
                    if  obsr_val > exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'>{exp_val[0]}'

                elif comp =='LT':
                    if  obsr_val < exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'<{exp_val[0]}'
                elif comp =='EQL':
                    if  obsr_val == exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'=={exp_val[0]}'
                elif comp =='NEQ':
                    if  obsr_val != exp_val[0]:
                        res =  'Pass'
                    else:  
                        res = 'Fail'
                    compval=f'!={exp_val[0]}'
                #add for rql,lseql
            else:
                exp_vals=exp_val
                compval='-'.join(map(str,exp_vals))
                if obsr_val >= exp_vals[0] and obsr_val <= exp_vals[1]:
                    res =  'Pass'
                else:  
                    res = 'Fail'
        else:
            res = 'Fail'
        return [exp_vals,res,compval,obsr_val]
    #3. Get a path of file from root
    def find_file(root_path, file_name):
        for dirpath, _, filenames in os.walk(root_path):
            # print(filenames)
            if file_name in filenames:
                return os.path.join(dirpath, file_name) 
        return None 
    #4. Extract a file in memory
    def extract_zip_in_memory(zip_path):
        with open(zip_path, "rb") as file:
            zip_bytes = io.BytesIO(file.read())  # Load ZIP into memory
        
        with zipfile.ZipFile(zip_bytes, "r") as zip_file:
            file_list = zip_file.namelist()  # Get list of files inside ZIP
            extracted_files = {name: zip_file.read(name) for name in file_list}  # Extract in memory
        return extracted_files
    
    def GetCompDes(Exp,Comp):
        desp = ','.join(str(i) for i in Exp)
        match Comp:
            case "NEQ": desp=str ("!= to") +" "+desp
            case "GT":  desp=str (">") +" "+desp
            case "GTE": desp=str (">=") +" "+desp
            case "LT":  desp=str ("<") +" "+desp
            case "LTE": desp=str ("<`=") +" "+desp
            case "BTW": desp=str ("Lies between the values") +" "+desp
            case "IN":  desp=str ("Must be Equal to Any of these values") +" "+desp
            case "EQL": desp=" "+desp
            case "ANY": desp=" "+desp
        return desp

import traceback
import uuid
import os
import zipfile
import csv
import xlsxwriter
from datetime import datetime
from Scripts.MainModule import JsonOperations,APIOperations,GeneralMethods
from datetime import datetime,date
import time

class ExcerciseValidation():
    def __init__(self):
        print("TPT")
        self.mode = 'TPT'
        self.Jsettings = JsonOperations('json/setting.json')
        self.JsettingsData =self.Jsettings.read_file()
        self.Jtester = JsonOperations('json/Tester.json')
        self.JtesterData =self.Jtester.read_file()
        self.Japi = JsonOperations('json/Xpath.json')
        JapiDatatemp =self.Japi.read_file()
        self.JapiData = JapiDatatemp['API']
        self.JQI = JsonOperations('json/QIconfig.json')
        self.JQIData = self.JQI.read_file()
        self.JMOI = JsonOperations('json/MOIJson.json')
        self.JMOIData = self.JMOI.read_file()
        # self.Json_TC = self.JMOIData[self.TestID]
        self.TimeTolr = self.JMOIData['TT_4']
        self.Json_Def = self.JMOIData['default_Values']
        self.JTestConf = JsonOperations('json/TestConfig.json')
        self.JTestConfData = self.JTestConf.read_file()  
        self.JPhaPkt = JsonOperations('json/PhasePackets.json')
        self.JPhaPktData = self.JPhaPkt.read_file()  
        self.JTCP = JsonOperations('json/Test_config_properties.json')
        self.JTCPData = self.JTCP.read_file()
        # self.FinalRep = JsonOperations(self.JTCPData['test_config_data']['Report_path'])
        # self.FinalRepData = self.FinalRep.read_file()
        self.Header = {}
        self.timing_map = {}
        #Get Packets###########################
        self.PktAPI = APIOperations(url=self.JapiData[self.mode]['GetCCLinePackets'],retype='json')
        self.file_list = self.PktAPI.GetRequest()
        self.flows = self.SegricatePackets()
        print(self.flows)
        if len(self.flows)>0:
            #find last best flow and perform the validation
            for flow in self.flows:
                if self.flows[flow] is not None:
                    # print(self.flows[flow])
                    lmt = self.flows[flow]['Limit']
                    index = self.flows[flow]['Flow']
                    if self.mode == 'TPT':
                        self.CheckPktSequnce_TPT(lmt,index)
                    else: self.CheckPktSequnce_TPR(lmt,index)
                    self.ExportCSV()
        # print(self.timing_map[2])
        # for fl in self.timing_map:
        #     print(type(fl))
    def SegricatePackets(self):
        packets = {}
        cnt = 0
        sid = 0
        limit=[0,len(self.file_list)-1]
        # #Find applicable length
        # while sid < len(self.file_list)-1:
        #     if all(rs in self.file_list[sid].get('pktType') for rs in ['Test_Started',self.Json_TC['SeqID']]):
        #         eid = sid+1
        #         while eid < len(self.file_list)-1:
        #             if all(rs in self.file_list[eid].get('pktType') for rs in ['Test_Stop',self.Json_TC['SeqID']]): 
        #                 limit=[sid,eid]
        #                 break
        #             elif all(rs in self.file_list[eid].get('pktType') for rs in ['Shutdown','next_subtest']): 
        #                 limit=[sid,eid]
        #                 break
        #             eid+=1
        #         break
        #     sid+=1
        # print('Limit',limit)
        if len(limit)>1:
            id = limit[0]
            while id < limit[1]:
                start = 0
                end = 0
                if any(res in self.file_list[id].get('pktType') for res in ['Ping Initiated','Ping Detected']):
                    print('pd',id)
                    #find Shutdown
                    sd= self.GetPacketDetails(packet='Shutdown',limit=[id,limit[1]])
                    print('sd',sd)
                    if len(sd)>2:
                        # print('sd',sd)
                        #ensure no PD recevied btw PD-SD
                        ilPD = self.GetPacketDetails(packet='Ping Initiated',limit=[id+1,sd[2]])
                        if len(ilPD)>1: id = ilPD[2]
                        # #check TestStop recevied before SD
                        # ilTS = self.GetPacketDetails(packet='Shutdown',limit=[id,sd[2]])
                        # if len(ilTS)>1: sd = ilTS
                        start = id
                        end = sd[2]
                        id = end
                    else:
                        #consider for the End of packet
                        start = id
                        end = limit[1]
                        id = end
                    #consider seq. has length > 3 and ss in flow
                    SS = self.GetPacketDetails(packet='Signal strength',limit=[start,end])
                    if (end -start) > 3 and len(SS)>1:
                        cnt +=1
                        # print(start,end)
                        #print('fq',self.file_list[start].get("value"))    #returns: _128kHz and _360kHz
                        fq = GeneralMethods.GetFloatFromStr(self.file_list[start].get("value"))
                        index = 2 if fq[0] >= 300 else 1
                        packets[cnt]={"Limit":[start,end],"Flow":index}
                else: id+=1
            #consider last 2 seq.
            flow1=None
            flow2=None
            tmpflow1=None
            for seq in packets:
                if packets[seq]['Flow']!=0:
                    if packets[seq]['Flow']==1 and flow2==None:
                        flow1 = packets[seq]
                    elif packets[seq]['Flow']==2 and flow1!=None:
                        if tmpflow1 ==None:
                            flow2 = packets[seq]
                        else:
                            flow1=tmpflow1
                            flow2 = packets[seq]
                            tmpflow1=None
                    elif  packets[seq]['Flow']==1 and flow2!=None:
                        tmpflow1=packets[seq]
            # print('pkts',packets)
            return {1:flow1,2:flow2}
    def CheckPktSequnce_TPT(self,limit,index):
        # print('initial',limit,type(index))
        PkseqData = self.JPhaPkt.read_file()
        packets = PkseqData[self.mode]['Packets']
        Pkseq = PkseqData[self.mode]['PacketSeq']
        PTPkts = []
        # print(Pkseq['Standard'])
        seq = Pkseq['Standard']
        # print('ini',seq)
        # if index==1 : seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['127_nego'])
        if index not in self.timing_map:self.timing_map[index]={}
        self.timing_map[index]['Illegal']=[]
        seqpos = 1
        id = limit[0]+1
        while id < limit[1]:
            # print(id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),seq[seqpos],seq)
            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                pktstatus = False
                if len(packets[seq[seqpos]]['values']):
                    if any(rs in self.file_list[id].get('value') for rs in packets[seq[seqpos]]['values']) and packets[seq[seqpos]]['Descr'] in self.file_list[id].get('pktType'):pktstatus=True
                else:
                    if packets[seq[seqpos]]['Descr'] in self.file_list[id].get('pktType'):pktstatus=True
                if pktstatus == True:
                    if packets[seq[seqpos]]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[seq[seqpos]]['PhaseID']]={}
                    if seq[seqpos] not in self.timing_map[index][packets[seq[seqpos]]['PhaseID']] : self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]] = []
                    #check response if required, id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')
                    # if len(packets[seq[seqpos]]['Response'])>0:
                    rid = id+1
                    while rid <= limit[1]:
                        if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                            if all(rs not in self.file_list[rid].get('pktType') for rs in packets[seq[seqpos]]['Response']):
                                self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                            else:
                                self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                            break
                        elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                            self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                            # print('Received Pkt instead of response')
                            break
                        rid+=1
                    if len(self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]]) == 0: self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                    # Check for PT pkts
                    if packets[seq[seqpos]]['PhaseID'] == 'PT' and 'PT' in self.file_list[id].get('description'):
                        id+=1
                        while id < limit[1]:
                            # print(id)
                            PTpktstatus = False
                            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                                if 'PT' in self.file_list[id].get('description'):
                                    # print(PTPkts)
                                    for PTpkt in PTPkts:
                                        if packets[PTpkt]['Descr'] in self.file_list[id].get('pktType'):
                                            PTpktstatus=True
                                    # for PTpkt in PTPkts:
                                        # print(packets[PTpkt]['Descr'] ,self.file_list[id].get('pktType'))
                                        # if packets[PTpkt]['Descr'] in self.file_list[id].get('pktType') :
                                            # print(id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),PTpkt)
                                            if packets[PTpkt]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[PTpkt]['PhaseID']]={}
                                            if PTpkt not in self.timing_map[index][packets[PTpkt]['PhaseID']] : self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt] = []
                                            # if len(packets[PTpkt]['Response'])>0:
                                            rid = id+1
                                            while rid < limit[1]:
                                                if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                                                    if all(rs not in self.file_list[rid].get('pktType') for rs in packets[PTpkt]['Response']):
                                                        self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                                    else:
                                                        self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                                                    break
                                                elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                                                    self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                                    # print('Received Pkt instead of response')
                                                    break
                                                rid+=1
                                            id=rid
                                        # else: id+=1
                                    if PTpktstatus == False : id+=1
                                else:
                                    print('Not expected1')
                                    #check for Cloak
                                    if 'Cloak' in self.file_list[id].get('pktType'):
                                        self.GetCloakPkts(index,id,packets)
                                        id+=1
                                    else:
                                        #add to illegal
                                        pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                                        resp =None
                                        tmpid = id+1
                                        #check for response
                                        while tmpid < limit[1]:
                                            if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                                break
                                            elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                                resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                                            tmpid+=1
                                        self.timing_map[index]['Illegal'].append([pkt,resp])
                                        id=tmpid
                            else:id+=1
                    #Check for ID packet
                    # print(seq[seqpos])
                    if seq[seqpos] =='ID':
                        res = self.GetPayloadValue('Ext',id)
                        if all(rs in '0x01' for rs in res):
                            seq.extend(Pkseq['ExID'])
                        seq.extend(Pkseq['CNF'])
                    # ExtID
                    if seq[seqpos] =='ExID':
                        res = self.GetPayloadValue('Restricted',id)
                        # print(res,'ExID')
                        if all(rs in '0x00' for rs in res):
                            if index == 1:
                                seq.extend(Pkseq['127_nego'])
                            if index == 2:
                                seq.extend(Pkseq['360_nego'])
                                seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['MPP_PT'])
                                PTPkts = self.JPhaPktData[self.mode]['PacketSeq']['MPP_PT']
                        else:
                            if index == 2:
                                # print('BPP mode')
                                seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['BPP_PT'])
                                PTPkts = self.JPhaPktData[self.mode]['PacketSeq']['BPP_PT']
                    id=rid
                    seqpos+=1
                else:
                    print('Not expected2')
                    opt_pktstatus = False
                    opt_pkt = None
                    #if phase = Nego , check the packet is a optional packet
                    if packets[seq[seqpos]]['PhaseID'] == "Nego":
                        optseq = '360_nego_opt' if index == 2 else '128_nego_opt'
                        if optseq in  Pkseq:
                            print('Op pkt check nego')
                            for optnegopkt in Pkseq['360_nego_opt']:
                                if len(packets[optnegopkt]['values']):
                                    if any(rs in self.file_list[id].get('value') for rs in packets[optnegopkt]['values']) and packets[optnegopkt]['Descr'] in self.file_list[id].get('pktType'):
                                        opt_pktstatus=True
                                        opt_pkt = optnegopkt
                                        break
                                else:
                                    if packets[optnegopkt]['Descr'] in self.file_list[id].get('pktType'):
                                        opt_pktstatus=True
                                        opt_pkt = optnegopkt
                                        break
                    if opt_pktstatus == True:
                        if packets[opt_pkt]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[opt_pkt]['PhaseID']]={}
                        if opt_pkt not in self.timing_map[index][packets[opt_pkt]['PhaseID']] : self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt] = []
                        rid = id+1
                        while rid <= limit[1]:
                            if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                                if all(rs not in self.file_list[rid].get('pktType') for rs in packets[seq[seqpos]]['Response']):
                                    self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                else:
                                    self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                                break
                            elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                                self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                # print('Received Pkt instead of response')
                                break
                            rid+=1
                        id=rid
                        # seqpos+=1
                    else:
                        # id+=1
                        # pass
                        #check for ill / add pkts
                        # if self.file_list[id].get('description') !=  packets[seq[seqpos]]['PhaseID'] or (self.file_list[id].get('description') =='Nego' and any(rs in self.file_list[id].get('pktType') for rs in ['ADC','DSR','SADC','SADT'])):
                        pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                        resp =None
                        tmpid = id+1
                        #check for response
                        while tmpid < limit[1]:
                            # print(tmpid)
                            if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                break
                            elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                            tmpid+=1
                        self.timing_map[index]['Illegal'].append([pkt,resp])
                        # print(tmpid,id)
                        id=tmpid
            else: id+=1
        #add PD&SD
        self.timing_map[index]['General'] ={
            "PD":[limit[0],self.file_list[limit[0]].get('startTime'),self.file_list[limit[0]].get('stopTime')],
            "SD":[limit[1],self.file_list[limit[1]].get('startTime'),self.file_list[limit[1]].get('stopTime')]
        }
        #Get Freq data
        if 'PD' in self.timing_map[index]['General']:
            fq = GeneralMethods.GetFloatFromStr(self.file_list[limit[0]].get("value"))
            self.timing_map[index]['General']['FOP']=[limit[0],self.file_list[limit[0]].get('startTime'),self.file_list[limit[0]].get('stopTime'),fq[0]]
        #GetLoads
        self.timing_map[index]['Loads']={}
        id = limit[0]
        while id < limit[1]:
            # print(id,self.file_list[id].get('pktType'))
            if 'Set_Load' in self.file_list[id].get('pktType'):
                self.timing_map[index]['Loads'][self.file_list[id].get('pktType').split(':')[0].split(' ')[1]] = id
            id+=1
        # apply validations
        self.timing_map[index]['Timings']=self.timing_checks(index)
        # self.timing_map[index]['Measures'] = self.Measures(index)
        # self.timing_map[index]['OtherChecks'] = self.OtherChecks(index)
    def CheckPktSequnce_TPR(self,limit,index):
        # print('initial',limit,type(index))
        PkseqData = self.JPhaPkt.read_file()
        packets = PkseqData[self.mode]['Packets']
        Pkseq = PkseqData[self.mode]['PacketSeq']
        PTPkts = []
        # print(Pkseq['Standard'])
        seq = Pkseq['Standard']
        # print('ini',seq)
        # if index==1 : seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['127_nego'])
        if index not in self.timing_map:self.timing_map[index]={}
        self.timing_map[index]['Illegal']=[]
        seqpos = 1
        id = limit[0]+1
        while id < limit[1]:
            # print(id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),seq[seqpos],seq)
            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                pktstatus = False
                if len(packets[seq[seqpos]]['values']):
                    if any(rs in self.file_list[id].get('value') for rs in packets[seq[seqpos]]['values']) and packets[seq[seqpos]]['Descr'] in self.file_list[id].get('pktType'):pktstatus=True
                else:
                    if packets[seq[seqpos]]['Descr'] in self.file_list[id].get('pktType'):pktstatus=True
                if pktstatus == True:
                    if packets[seq[seqpos]]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[seq[seqpos]]['PhaseID']]={}
                    if seq[seqpos] not in self.timing_map[index][packets[seq[seqpos]]['PhaseID']] : self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]] = []
                    #check response if required, id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')
                    # if len(packets[seq[seqpos]]['Response'])>0:
                    rid = id+1
                    while rid <= limit[1]:
                        if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                            if all(rs not in self.file_list[rid].get('pktType') for rs in packets[seq[seqpos]]['Response']):
                                self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                            else:
                                self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                            break
                        elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                            self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                            # print('Received Pkt instead of response')
                            break
                        rid+=1
                    if len(self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]]) == 0: self.timing_map[index][packets[seq[seqpos]]['PhaseID']][seq[seqpos]].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                    # Check for PT pkts
                    if packets[seq[seqpos]]['PhaseID'] == 'PT' and 'PT' in self.file_list[id].get('description'):
                        id+=1
                        while id < limit[1]:
                            # print(id)
                            PTpktstatus = False
                            if self.file_list[id].get('isFWTestermessage') == False and self.file_list[id].get('isTesterPkt') == False:
                                if 'PT' in self.file_list[id].get('description'):
                                    print(PTPkts)
                                    for PTpkt in PTPkts:
                                        if packets[PTpkt]['Descr'] in self.file_list[id].get('pktType'):
                                            PTpktstatus=True
                                    # for PTpkt in PTPkts:
                                        # print(packets[PTpkt]['Descr'] ,self.file_list[id].get('pktType'))
                                        # if packets[PTpkt]['Descr'] in self.file_list[id].get('pktType') :
                                            # print(id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),PTpkt)
                                            if packets[PTpkt]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[PTpkt]['PhaseID']]={}
                                            if PTpkt not in self.timing_map[index][packets[PTpkt]['PhaseID']] : self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt] = []
                                            # if len(packets[PTpkt]['Response'])>0:
                                            rid = id+1
                                            while rid < limit[1]:
                                                if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                                                    if all(rs not in self.file_list[rid].get('pktType') for rs in packets[PTpkt]['Response']):
                                                        self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                                    else:
                                                        self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                                                    break
                                                elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                                                    self.timing_map[index][packets[PTpkt]['PhaseID']][PTpkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                                    # print('Received Pkt instead of response')
                                                    break
                                                rid+=1
                                            id=rid
                                        # else: id+=1
                                    if PTpktstatus == False : id+=1
                                else:
                                    print('Not expected1')
                                    #check for Cloak
                                    if 'Cloak' in self.file_list[id].get('pktType'):
                                        self.GetCloakPkts(index,id,packets)
                                        id+=1
                                    else:
                                        #add to illegal
                                        pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                                        resp =None
                                        tmpid = id+1
                                        #check for response
                                        while tmpid < limit[1]:
                                            if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                                break
                                            elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                                resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                                            tmpid+=1
                                        self.timing_map[index]['Illegal'].append([pkt,resp])
                                        id=tmpid
                            else:id+=1
                    #Check for ID packet
                    # print(seq[seqpos])
                    if seq[seqpos] =='ID':
                        res = self.GetPayloadValue('Ext',id)
                        if all(rs in '0x01' for rs in res):
                            seq.extend(Pkseq['ExID'])
                        seq.extend(Pkseq['CNF'])
                    # ExtID
                    if seq[seqpos] =='ExID':
                        res = self.GetPayloadValue('Restricted',id)
                        # print(res,'ExID')
                        if all(rs in '0x00' for rs in res):
                            if index == 1:
                                seq.extend(Pkseq['127_nego'])
                            if index == 2:
                                seq.extend(Pkseq['360_nego'])
                                seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['MPP_PT'])
                                PTPkts = self.JPhaPktData[self.mode]['PacketSeq']['MPP_PT']
                        else:
                            if index == 2:
                                # print('BPP mode')
                                seq.extend(self.JPhaPktData[self.mode]['PacketSeq']['BPP_PT'])
                                PTPkts = self.JPhaPktData[self.mode]['PacketSeq']['BPP_PT']
                    id=rid
                    seqpos+=1
                else:
                    print('Not expected2')
                    opt_pktstatus = False
                    opt_pkt = None
                    #if phase = Nego , check the packet is a optional packet
                    if packets[seq[seqpos]]['PhaseID'] == "Nego":
                        optseq = '360_nego_opt' if index == 2 else '128_nego_opt'
                        if optseq in  Pkseq:
                            print('Op pkt check nego')
                            for optnegopkt in Pkseq['360_nego_opt']:
                                if len(packets[optnegopkt]['values']):
                                    if any(rs in self.file_list[id].get('value') for rs in packets[optnegopkt]['values']) and packets[optnegopkt]['Descr'] in self.file_list[id].get('pktType'):
                                        opt_pktstatus=True
                                        opt_pkt = optnegopkt
                                        break
                                else:
                                    if packets[optnegopkt]['Descr'] in self.file_list[id].get('pktType'):
                                        opt_pktstatus=True
                                        opt_pkt = optnegopkt
                                        break
                    if opt_pktstatus == True:
                        if packets[opt_pkt]['PhaseID'] not in self.timing_map[index]:self.timing_map[index][packets[opt_pkt]['PhaseID']]={}
                        if opt_pkt not in self.timing_map[index][packets[opt_pkt]['PhaseID']] : self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt] = []
                        rid = id+1
                        while rid <= limit[1]:
                            if self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == True:
                                if all(rs not in self.file_list[rid].get('pktType') for rs in packets[seq[seqpos]]['Response']):
                                    self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                else:
                                    self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')],[rid,self.file_list[rid].get('pktType'),self.file_list[rid].get('startTime'),self.file_list[rid].get('stopTime')]])
                                break
                            elif self.file_list[rid].get('isFWTestermessage') == False and self.file_list[rid].get('isTesterPkt') == False:
                                self.timing_map[index][packets[opt_pkt]['PhaseID']][opt_pkt].append([[id,self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]])
                                # print('Received Pkt instead of response')
                                break
                            rid+=1
                        id=rid
                        # seqpos+=1
                    else:
                        # id+=1
                        # pass
                        #check for ill / add pkts
                        # if self.file_list[id].get('description') !=  packets[seq[seqpos]]['PhaseID'] or (self.file_list[id].get('description') =='Nego' and any(rs in self.file_list[id].get('pktType') for rs in ['ADC','DSR','SADC','SADT'])):
                        pkt = [id,self.file_list[id].get('pktType'),self.file_list[id].get('value'),self.file_list[id].get('startTime'),self.file_list[id].get('stopTime')]
                        resp =None
                        tmpid = id+1
                        #check for response
                        while tmpid < limit[1]:
                            print(tmpid)
                            if self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == True:
                                break
                            elif self.file_list[tmpid].get('isFWTestermessage') == False and self.file_list[tmpid].get('isTesterPkt') == False:
                                resp = [tmpid,self.file_list[tmpid].get('pktType'),self.file_list[tmpid].get('startTime'),self.file_list[tmpid].get('stopTime')]
                            tmpid+=1
                        self.timing_map[index]['Illegal'].append([pkt,resp])
                        # print(tmpid,id)
                        id=tmpid
            else: id+=1
        #add PD&SD
        self.timing_map[index]['General'] ={
            "PD":[limit[0],self.file_list[limit[0]].get('startTime'),self.file_list[limit[0]].get('stopTime')],
            "SD":[limit[1],self.file_list[limit[1]].get('startTime'),self.file_list[limit[1]].get('stopTime')]
        }
        #Get Freq data
        if 'PD' in self.timing_map[index]['General']:
            fq = GeneralMethods.GetFloatFromStr(self.file_list[limit[0]].get("value"))
            self.timing_map[index]['General']['FOP']=[limit[0],self.file_list[limit[0]].get('startTime'),self.file_list[limit[0]].get('stopTime'),fq[0]]
        #GetLoads
        self.timing_map[index]['Loads']={}
        id = limit[0]
        while id < limit[1]:
            # print(id,self.file_list[id].get('pktType'))
            if 'Set_Load' in self.file_list[id].get('pktType'):
                self.timing_map[index]['Loads'][self.file_list[id].get('pktType').split(':')[0].split(' ')[1]] = id
            id+=1
        # apply validations
        self.timing_map[index]['Timings']=self.timing_checks(index)
    def GetPacketDetails(self,packet='',value=None,limit=[],timelimit=None):
        id = limit[0]
        if type(packet) != list:
            while id != limit[1]:
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
        
    def GetPayloadValue(self,payloadname,index):
        # print('Payload check',self.file_list[index].get('pktType'))
        results=[]
        for d1 in self.file_list[index]['header_Payload']['childelement']:
            for d2 in d1['childelement']:
                # print(d2['sDecodedValue'])
                if payloadname in d2['sDecodedValue']:
                    results.append(d2['sRawData'])
        return results 
    def timing_checks(self,index):
        AllTimings={"tresponse":[],"twake":[],"tstart":[],"tsilent":[],"tintervalXCE-XCE":[],"treceviedPLA-PLA":[]}
        ##Twake check--------------------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['twake']
        AllTimings['twake_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['twake']='NA'
        AllTimings['twake_res']='NA'
        twakelist = []
        try:
            if 'Ping' in self.timing_map[index] and 'General' in self.timing_map[index]:
                AllTimings['twake']=[]
                res = round((self.timing_map[index]['Ping']['SS'][0][0][1] - self.timing_map[index]['General']['PD'][1])*1000,2)+5.5
                twakelist.append(res) 
                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                    AllTimings['twake'].append(res)
                    remarks.append(f"Measured twake {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{self.timing_map[index]['General']['PD'][0]}-{self.timing_map[index]['Ping']['SS'][0][0][0]}")
                if len(remarks)>0:
                    AllTimings['twake_res'] ='Fail'
                    AllTimings['twake']=','.join(map(str,AllTimings['twake']))
                else:
                    AllTimings['twake_res'] ='Pass'
                    AllTimings['twake']=res
                AllTimings['twake_remark'] = '.'.join(remarks)
        except Exception as e:
            er = traceback.print_exc()
            AllTimings['twake_remark'] = '' if er is None else er
            AllTimings['twake_res'] ='Fail'
        ##Tstart check-------------------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['tstart']
        AllTimings['tstart_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tstart_res']='NA'
        AllTimings['tstart']='NA'
        tstartlist =[]
        Pktslist =[]
        for phase in self.timing_map[index]:
            if phase in ['Ping','ID&CFG']:
                for pkts in self.timing_map[index][phase]:
                    pk = self.timing_map[index][phase][pkts]
                    if type(pk)==list:
                        Pktslist.append(pk[0][0])
        if len(Pktslist)>0:
            id=0
            AllTimings['tstart']=[]
            AllTimings['tstart_res']='Fail'
            while id < len(Pktslist)-1:
                res = round((Pktslist[id+1][1]-Pktslist[id][2])*1000,2)+5.5
                tstartlist.append(res)
                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                    AllTimings['tstart'].append(res)
                    remarks.append(f"Measured tstart {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{Pktslist[id][0]}-{Pktslist[id+1][0]}")
                id+=1
            if len(remarks)>0:
                AllTimings['tstart_res'] ='Fail'
                AllTimings['tstart']=','.join(map(str,AllTimings['tstart']))
            else:
                AllTimings['tstart_res'] ='Pass'
                AllTimings['tstart']=','.join(map(str,tstartlist))
            AllTimings['tstart_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
            AllTimings['tstart_remark'] = '.'.join(remarks)
        ##tsilent check-------------------------------------------------------------------------
        remarks = []
        tol= self.Json_Def['tsilent']
        AllTimings['tsilent_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tsilent_res']='NA'
        AllTimings['tsilent']='NA'
        tsilentlist = []
        Pktslist =[]
        for phase in self.timing_map[index]:
            if phase in ['Ping','ID&CFG']:
                for pkts in self.timing_map[index][phase]:
                    pk = self.timing_map[index][phase][pkts]
                    if type(pk)==list:
                        Pktslist.append(pk[0][0])
        if len(Pktslist)>0:
            id=0
            AllTimings['tsilent']=[]
            AllTimings['tsilent_res']='Fail'
            while id < len(Pktslist)-1:
                res = round((Pktslist[id+1][1]-Pktslist[id][2])*1000,2)
                tsilentlist.append(res)
                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                    AllTimings['tsilent'].append(res)
                    remarks.append(f"Measured tsilent {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{Pktslist[id][0]}-{Pktslist[id+1][0]}")
                id+=1
            if len(remarks)>0:
                AllTimings['tsilent_res'] ='Fail'
                AllTimings['tsilent']=','.join(map(str,AllTimings['tsilent']))
            else:
                AllTimings['tsilent_res'] ='Pass'
                AllTimings['tsilent']=','.join(map(str,tsilentlist))
            AllTimings['tsilent_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
            AllTimings['tsilent_remark'] = '.'.join(remarks)
        #tresponse, pass all flows and get the tresponse for the pkts has response
        remarks = []
        tresponselist =[]
        tol= self.Json_Def['tresponse']
        for phase in self.timing_map[index]:
            if phase not in ['Illegal','Cloak']:
                for pkts in self.timing_map[index][phase]:
                    pk = self.timing_map[index][phase][pkts]
                    if type(pk) == list:
                        for pks in pk:
                            if type(pks) == list:
                                if len(pks)>1:
                                    # print(pks)
                                    res = round((pks[1][2] - pks[0][2])*1000,2)
                                    tresponselist.append(res)
                                    if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                                        AllTimings['tresponse'].append(res)
                                        remarks.append(f"Measured tresponse {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{pks[1][0]} ")
        if len(remarks)>0:
            AllTimings['tresponse_res'] ='Fail'
            AllTimings['tresponse']=','.join(map(str,AllTimings['tresponse']))
        else:
            AllTimings['tresponse_res'] ='Pass'
            AllTimings['tresponse']=','.join(map(str,tresponselist))
        AllTimings['tresponse_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tresponse_remark'] = '.'.join(remarks)
        #Tintervel XCE-----------------------------------------------------------
        remarks = []
        TintervelXCElist = []
        tol= self.Json_Def['tintervalXCE-XCE']
        AllTimings['tintervalXCE-XCE_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['tintervalXCE-XCE_res']='NA'
        AllTimings['tintervalXCE-XCE']='NA'
        try:
            if 'PT' in self.timing_map[index]:
                if 'XCE' in self.timing_map[index]['PT']:
                    XCEpkt = self.timing_map[index]['PT']['XCE']
                    AllTimings['tintervalXCE-XCE']=[]
                    if len(XCEpkt)>0:
                        id = 0
                        while id < len(XCEpkt)-1:
                            if (XCEpkt[id+1][0][0] - XCEpkt[id][0][0]) <=4:
                                res= round((XCEpkt[id+1][0][1] - XCEpkt[id][0][2])*1000,2)
                                TintervelXCElist.append(res)
                                if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                                        AllTimings['tintervalXCE-XCE'].append(res)
                                        remarks.append(f"Measured tintervalXCE-XCE {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{XCEpkt[id][0][0]}-{XCEpkt[id+1][0][0]}")
                            id+=1
                        if len(remarks)>0:
                            AllTimings['tintervalXCE-XCE_res'] ='Fail'
                            AllTimings['tintervalXCE-XCE']=','.join(map(str,AllTimings['tintervalXCE-XCE']))
                        else:
                            AllTimings['tintervalXCE-XCE_res'] ='Pass'
                            AllTimings['tintervalXCE-XCE']=','.join(map(str,TintervelXCElist))
                        AllTimings['tintervalXCE-XCE_remark'] = '.'.join(remarks)  
        except Exception as e:
            er = traceback.print_exc()
            AllTimings['tintervalXCE-XCE_remark'] = '' if er is None else er
            AllTimings['tintervalXCE-XCE_res'] ='Fail'
        #Treceived PLA--------------------------------------------------------------
        remarks = []
        TreceivedPLAlist = []
        tol= self.Json_Def['treceviedPLA-PLA']
        AllTimings['treceviedPLA-PLA_exp'] = str(tol[0]-tol[1])+'-'+str(tol[0]+tol[1])
        AllTimings['treceviedPLA-PLA_res']='NA'
        AllTimings['treceviedPLA-PLA']='NA'
        try:
            if 'PT' in self.timing_map[index]:
                if 'PLA' in self.timing_map[index]['PT']:
                    PLApkt = self.timing_map[index]['PT']['PLA']
                    AllTimings['treceviedPLA-PLA']=[]
                    if len(PLApkt)>0:
                        id = 0
                        while id < len(PLApkt)-1:
                            res= round((PLApkt[id+1][0][1] - PLApkt[id][0][2])*1000,2)
                            TreceivedPLAlist.append(res)
                            if res < tol[0]-tol[1] or res >tol[0]+tol[1]:
                                    AllTimings['treceviedPLA-PLA'].append(res)
                                    remarks.append(f"Measured treceviedPLA-PLA {res} Not in Limit({(tol[0]-tol[1])}-{(tol[0]+tol[1])}) @index:{PLApkt[id][0][0]}-{PLApkt[id+1][0][0]}")
                            id+=1
                        if len(remarks)>0:
                            AllTimings['treceviedPLA-PLA_res'] ='Fail'
                            AllTimings['treceviedPLA-PLA']=','.join(map(str,AllTimings['treceviedPLA-PLA']))
                        else:
                            AllTimings['treceviedPLA-PLA_res'] ='Pass'
                            AllTimings['treceviedPLA-PLA']=','.join(map(str,TreceivedPLAlist))
                        AllTimings['treceviedPLA-PLA_remark'] = '.'.join(remarks)  
        except Exception as e:
            er = traceback.print_exc()
            AllTimings['treceviedPLA-PLA_remark'] = '' if er is None else er
            AllTimings['treceviedPLA-PLA_res'] ='Fail'
        # print(AllTimings)
        return(AllTimings)
    def ExportCSV(self):
        try:
            self.apptimings = {1:["twake","tstart","tsilent","tresponse","tintervalXCE-XCE","treceviedPLA-PLA"],2:["twake","tstart","tsilent","tresponse","tintervalXCE-XCE","treceviedPLA-PLA"]}
            now = datetime.now()
            timestamp = now.strftime("%d%m%Y_%H%M%S")
            self.Reprot_loc = './Results/MPP Excel Results/'
            self.Wb = xlsxwriter.Workbook(self.Reprot_loc+'ExcerciserTimingChecks'+timestamp+'.xlsx')
            self.Ws = self.Wb.add_worksheet("Details")
            #Formats 
            self.Heading1 = self.Wb.add_format({'bold': True, 'font_color': '#FFFFFF','bg_color':'#833C0C','center_across':True,'border':True})
            self.Heading2 = self.Wb.add_format({'bold': True, 'font_color': '#000000','bg_color':'#F4B084','center_across':True,'border':True})
            self.Heading3 = self.Wb.add_format({'bold': True, 'font_color': '#000000','bg_color':'#F8CBAD','center_across':True,'border':True})
            self.Pass_frmt = self.Wb.add_format({'font_color': '#000000','bg_color':'#00B050','border':True})
            self.Fail_frmt = self.Wb.add_format({'font_color': '#000000','bg_color':'#FF0000','border':True})
            self.INCL_frmt = self.Wb.add_format({'font_color': '#000000','bg_color':'#F79646','border':True})
            self.NA_frmt = self.Wb.add_format({'font_color': '#000000','bg_color':'#BFBFBF','border':True,'center_across':True})
            self.exp_frmt =self.Wb.add_format({'font_color': '#000000','bg_color':'#F79646','border':True,'center_across':True})
            TimeHeader=["Flow","Timing Desc","Timing Exp.","Timing Val.","Timing Result","Remarks"]
            row =0
            col =0
            for i in TimeHeader:
                self.Ws.write(row,col, i,self.Heading3)
                col+=1
            self.Ws.merge_range(row-1,col-5,row-1,col-1,"Timings",self.Heading1)
            row =1
            col =0
            for flw in self.apptimings:
                # if len(self.timing_map[str(flw)]['Timings'])>0:
                for tm in self.apptimings[flw]:
                    print(tm)
                    self.Ws.write(row,col,flw)
                    self.Ws.write(row,col+1,tm)
                    self.Ws.write(row,col+2,self.timing_map[int(flw)]['Timings'][tm+'_exp'])
                    self.Ws.write(row,col+3,self.timing_map[int(flw)]['Timings'][tm])
                    self.UpdateResults(row,col+4,self.timing_map[int(flw)]['Timings'][tm+'_res'])
                    if tm+'_remark' in self.timing_map[int(flw)]['Timings']:
                        self.Ws.write(row,col+5,self.timing_map[int(flw)]['Timings'][tm+'_remark'])
                    else:self.Ws.write(row,col+5,'NA')
                    row+=1
                row+=1
            # self.Ws.autofit()
            self.Wb.close()
        except Exception as e:
            traceback.print_exc()
    def UpdateResults(self,row,col,value):
        if value in ['Pass','PASS']:
            self.Ws.write(row,col,value,self.Pass_frmt)
        elif value in ['Fail','FAIL']:
            self.Ws.write(row,col,value,self.Fail_frmt)
        elif value in ['Inconclusive','INCONCLUSIVE','NA']:
            self.Ws.write(row,col,value,self.INCL_frmt) 
#obj = ExcerciseValidation()


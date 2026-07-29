# import os
# import zipfile
# import csv
# #Eye plot checks

# #Extract Eye
# TCpath ="D:\\Automation Data\\MPP\\Traces\\iPhone14Plus_00_MPP_210224_193455\\iPhone14Plus_00_MPP_210224_193455\\Run2\\TD_194_P1L1\\TD_194_P1L1.grltrace"
# TCfolderList = TCpath.split("\\")
# path = "\\".join(TCfolderList[0:len(TCfolderList)-1])
# EyEdigpath = None
# EyeResult={"Phase":{},"Magnitude":{}}
# Expvalue ={"Phase":{"AmplitudeDiff":[220],"SNR":[13],"Fclk":[1920,2080],"HalfBitPeriod":[0.9,1.1],"EyeWidth":[0.75]},"Magnitude":{"AmplitudeDiff":[30],"SNR":[13],"Fclk":[1920,2080],"HalfBitPeriod":[0.9,1.1],"EyeWidth":[0.75]}}
# #Unzip Eyedig file
# for subdir, dirs, files in os.walk(path):
#     for file in files:
#         if file.endswith('.GrlEyeInfo'):
#             if os.path.exists(os.path.join(subdir,'EyeDebugInfo')):
#                 EyEdigpath = os.path.join(subdir,'EyeDebugInfo')
#             else:
#                 #Perform unzip
#                 with zipfile.ZipFile(os.path.join(subdir,file), 'r') as zip_ref:
#                     zip_ref.extractall(os.path.join(subdir,'EyeDebugInfo'))
#                 EyEdigpath = os.path.join(subdir,'EyeDebugInfo')
# if EyEdigpath is not None:
#     MagnitudeResultCSV = []
#     PhaseResultCSV = []
#     Temresult = {"Phase":{},"Magnitude":{}}
#     for subdir, dirs, files in os.walk(path):
#         for file in files:
#             if 'Eye_Magnitude_' in file and file.endswith("Results_EYE.csv"):
#                 MagnitudeResultCSV.append(os.path.join(subdir,file))
#             if 'Eye_Phase' in file and file.endswith("Results_EYE.csv"):
#                 PhaseResultCSV.append(os.path.join(subdir,file))
#     if len(MagnitudeResultCSV) >0:
#         for MagPath in MagnitudeResultCSV:
#             PktName = (MagPath.split("\\")[len(MagPath.split("\\"))-2]).split("_TS")[0]
#             Temresult["Magnitude"][PktName]={}
#             # reading the CSV file
#             data = open(MagPath)
#             csvFile = csv.reader(data)
#             #update csvdata to res
#             for lines in csvFile:
#                 if len(lines)>0:
#                     if 'AmplitudeHigh' in lines: Temresult["Magnitude"][PktName]['AmplitudeHigh'] = float(lines[1])
#                     if 'AmplitudeLow' in lines: Temresult["Magnitude"][PktName]['AmplitudeLow'] = float(lines[1])
#                     if 'SNR' in lines: Temresult["Magnitude"][PktName]['SNR'] = float(lines[1])
#                     if 'Fclk' in lines: Temresult["Magnitude"][PktName]['Fclk'] = float(lines[1])
#                     if 'HalfBitPeriod' in lines: Temresult["Magnitude"][PktName]['HalfBitPeriod'] = float(lines[1])
#                     if 'EyeWidth' in lines: Temresult["Magnitude"][PktName]['EyeWidth'] = float(lines[1])
#     if len(PhaseResultCSV) >0:
#         for MagPath in PhaseResultCSV:
#             PktName = (MagPath.split("\\")[len(MagPath.split("\\"))-2]).split("_TS")[0]
#             Temresult['Phase'][PktName]={}
#             # reading the CSV file
#             data = open(MagPath)
#             csvFile = csv.reader(data)
#             #update csvdata to res
#             for lines in csvFile:
#                 if len(lines)>0:
#                     if 'AmplitudeHigh' in lines: Temresult['Phase'][PktName]['AmplitudeHigh'] = float(lines[1])
#                     if 'AmplitudeLow' in lines: Temresult['Phase'][PktName]['AmplitudeLow'] = float(lines[1])
#                     if 'SNR' in lines: Temresult['Phase'][PktName]['SNR'] = float(lines[1])
#                     if 'Fclk' in lines: Temresult['Phase'][PktName]['Fclk'] = float(lines[1])
#                     if 'HalfBitPeriod' in lines: Temresult['Phase'][PktName]['HalfBitPeriod'] = float(lines[1])
#                     if 'EyeWidth' in lines: Temresult['Phase'][PktName]['EyeWidth'] = float(lines[1])
#     if len(Temresult['Magnitude'])>0:
#         try:
#             for pkts in Temresult['Magnitude']:
#                 Ampdiff = round((Temresult['Magnitude'][pkts]['AmplitudeHigh']-Temresult['Magnitude'][pkts]['AmplitudeLow'])*1000,2)
#                 EyeResult['Magnitude'][pkts]={}
#                 EyeResult['Magnitude'][pkts]['Amplitude Diff'] = f"{Ampdiff}|>={Expvalue['Magnitude']['AmplitudeDiff'][0]}|Pass" if Ampdiff >= Expvalue['Magnitude']['AmplitudeDiff'][0] else f"{Ampdiff}|>={Expvalue['Magnitude']['AmplitudeDiff'][0]}|Fail"
#                 EyeResult['Magnitude'][pkts]['SNR'] = f"{Temresult['Magnitude'][pkts]['SNR']}|>={Expvalue['Magnitude']['SNR'][0]}|Pass" if Temresult['Magnitude'][pkts]['SNR'] >= Expvalue['Magnitude']['SNR'][0] else f"{Temresult['Magnitude'][pkts]['SNR']}|>={Expvalue['Magnitude']['SNR'][0]}|Fail"
#                 EyeResult['Magnitude'][pkts]['Fclk'] = f"{Temresult['Magnitude'][pkts]['Fclk']}|{Expvalue['Magnitude']['Fclk'][0]}-{Expvalue['Magnitude']['Fclk'][1]}|Pass" if Temresult['Magnitude'][pkts]['Fclk'] >= Expvalue['Magnitude']['Fclk'][0] and Temresult['Magnitude'][pkts]['Fclk'] <= Expvalue['Magnitude']['Fclk'][1] else f"{Temresult['Magnitude'][pkts]['Fclk']}|{Expvalue['Magnitude']['Fclk'][0]}-{Expvalue['Magnitude']['Fclk'][1]}|Fail"
#                 EyeResult['Magnitude'][pkts]['HalfBitPeriod'] = f"{Temresult['Magnitude'][pkts]['HalfBitPeriod']}|{Expvalue['Magnitude']['HalfBitPeriod'][0]}-{Expvalue['Magnitude']['HalfBitPeriod'][1]}|Pass" if Temresult['Magnitude'][pkts]['HalfBitPeriod'] >= Expvalue['Magnitude']['HalfBitPeriod'][0] and Temresult['Magnitude'][pkts]['HalfBitPeriod'] <= Expvalue['Magnitude']['HalfBitPeriod'][1] else f"{Temresult['Magnitude'][pkts]['HalfBitPeriod']}|{Expvalue['Magnitude']['HalfBitPeriod'][0]}-{Expvalue['Magnitude']['HalfBitPeriod'][1]}|Fail"
#                 EyeResult['Magnitude'][pkts]['EyeWidth'] = f"{Temresult['Magnitude'][pkts]['EyeWidth']}|>={Expvalue['Magnitude']['EyeWidth'][0]}|Pass" if Temresult['Magnitude'][pkts]['EyeWidth'] >= Expvalue['Magnitude']['EyeWidth'][0] else f"{Temresult['Magnitude'][pkts]['EyeWidth']}|>={Expvalue['Magnitude']['EyeWidth'][0]}|Fail"
#         except Exception as e:
#             pass 
#     if len(Temresult['Phase'])>0:
#         try:
#             for pkts in Temresult['Phase']:
#                 Ampdiff = round((Temresult['Phase'][pkts]['AmplitudeHigh']-Temresult['Phase'][pkts]['AmplitudeLow'])*1000,2)
#                 EyeResult['Phase'][pkts]={}
#                 EyeResult['Phase'][pkts]['Amplitude Diff'] = f"{Ampdiff}|>={Expvalue['Phase']['AmplitudeDiff'][0]}|Pass" if Ampdiff >= Expvalue['Phase']['AmplitudeDiff'][0] else f"{Ampdiff}|>={Expvalue['Phase']['AmplitudeDiff'][0]}|Fail"
#                 EyeResult['Phase'][pkts]['SNR'] = f"{Temresult['Phase'][pkts]['SNR']}|>={Expvalue['Phase']['SNR'][0]}|Pass" if Temresult['Phase'][pkts]['SNR'] >= Expvalue['Phase']['SNR'][0] else f"{Temresult['Phase'][pkts]['SNR']}|>={Expvalue['Phase']['SNR'][0]}|Fail"
#                 EyeResult['Phase'][pkts]['Fclk'] = f"{Temresult['Phase'][pkts]['Fclk']}|{Expvalue['Phase']['Fclk'][0]}-{Expvalue['Phase']['Fclk'][1]}|Pass" if Temresult['Phase'][pkts]['Fclk'] >= Expvalue['Phase']['Fclk'][0] and Temresult['Phase'][pkts]['Fclk'] <= Expvalue['Phase']['Fclk'][1] else f"{Temresult['Phase'][pkts]['Fclk']}|{Expvalue['Phase']['Fclk'][0]}-{Expvalue['Phase']['Fclk'][1]}|Fail"
#                 EyeResult['Phase'][pkts]['HalfBitPeriod'] = f"{Temresult['Phase'][pkts]['HalfBitPeriod']}|{Expvalue['Phase']['HalfBitPeriod'][0]}-{Expvalue['Phase']['HalfBitPeriod'][1]}|Pass" if Temresult['Phase'][pkts]['HalfBitPeriod'] >= Expvalue['Phase']['HalfBitPeriod'][0] and Temresult['Phase'][pkts]['HalfBitPeriod'] <= Expvalue['Phase']['HalfBitPeriod'][1] else f"{Temresult['Phase'][pkts]['HalfBitPeriod']}|{Expvalue['Phase']['HalfBitPeriod'][0]}-{Expvalue['Phase']['HalfBitPeriod'][1]}|Fail"
#                 EyeResult['Phase'][pkts]['EyeWidth'] = f"{Temresult['Phase'][pkts]['EyeWidth']}|>={Expvalue['Phase']['EyeWidth'][0]}|Pass" if Temresult['Phase'][pkts]['EyeWidth'] >= Expvalue['Phase']['EyeWidth'][0] else f"{Temresult['Phase'][pkts]['EyeWidth']}|>={Expvalue['Phase']['EyeWidth'][0]}|Fail"
#         except Exception as e:
#             pass 
# print(EyeResult)

# from MainModule import GeneralMethods
# message = "Position the Power Transmitter at X= -2.5 mm and Y= 0.0mm.\nProgress: 0/11\nClick OK to Procced, Click Cancel to Abort!"

# pos = GeneralMethods.GetFloatFromStr(message)

# print(pos)


import sqlite3
import pandas as pd
#1. get the Data from SQL DB
# Define the path to the SQLite database
database_path = 'Resources/GRLDB.db'
# Connect to the SQLite database
connection = sqlite3.connect(database_path)

# Define your SQL query
Header_Qry = '''
SELECT Header.Certification,Header.SWVersion,Header.FWVersion,Header.BoardNo,Header.TestcaseName,
	   ChecksHeader.SEQID,ChecksHeader.Description,ChecksHeader.Type,ChecksHeader.ExpValue,ChecksHeader.MinValue,ChecksHeader.MaxValue,ChecksHeader.Result
FROM Header
LEFT JOIN ChecksHeader on Header.UID = ChecksHeader.UID
WHERE Header.DUTID="S24" and ChecksHeader.Type ="Timing" and Header.Certification in ("2.1")
'''

#and Header.BoardNo in ("GRL-C3-MP-2023058","GRL-C3-MP-2024126","GRL-C3-MP-2023105")
# Load the query result into a DataFrame
Header_df = pd.read_sql_query(Header_Qry, connection)
# Close the connection
connection.close()

# print(Header_df)

# Create a pivot table
pivot = pd.pivot_table(
    Header_df,
    index=['TestcaseName','SEQID','Description','ExpValue'],  # Rows
    columns=['BoardNo'],  # Columns
    values=['MinValue','MaxValue','Result'],  # Data to aggregate
    aggfunc='sum',  # Aggregation function
    fill_value="NA"
)
# pivot['Comparison'] = 'Pass' if pivot['']
# print(pivot)
output_file = 'C3TPT_Board_Comparison_Report_EPP.xlsx'
# Write both the original data and the pivot table to an Excel file
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # Write the original data
    # pivot_table.to_excel(writer, sheet_name='Data', index=False)
    # Write the pivot table
    pivot.to_excel(writer, sheet_name='Pivot Table')
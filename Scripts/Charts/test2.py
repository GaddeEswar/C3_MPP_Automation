

import csv

path = "D:\\TPTPFO\\sample\\(0,0,0)\\Run1\\10W\\TPT__QiSignalCapture_2024_01_23_12_51_59.csv"
data = open(path)
csvFile = csv.reader(data)
#update csvdata to res
for lines in csvFile:


    print(lines[2],lines[14])
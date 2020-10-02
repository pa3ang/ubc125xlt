# PA3ANG, September - 2020
# version 1.0
# This program connects to a UBC125XLT scanner and reads the RX frequency channel it is receiving (stopped during scan).
# It will then :
#     - display the channel info on the ribbon and display the last heard channels in the given sort
#     - when channel opens create entry in history file or update the hit counter and set last heard pointer
#     - when channel closes again update the total air time seconds 
#     - based on a channel selection send an alarm to a telegram bot 
#
# Very straight forward program for educational purpose using serial and tkinter.
#
# You need to create to files in the working directory:
#     - ubc125xlt_history.txt  
#
# The histroy file is capturing the received channels and contains the following field:
#     - Rank      : number of times channel opened
#     - Ch#       : channel number in the ubc125xlt
#     - Name      : channel name as stored in the ubc125xlt
#     - Freq-Mod  : frequnecy and modulation type
#     - Date Time : the last heard date and time
#     - Open      : total time the cnhannel was open since
#     - LH        : Last Heard pointer as being the channel last received
#
# The program uses the GLG command to interrogate the ubc125xlt.
# This rather undocumented command (refer to Uniden BC125AT Programming Protocol) returns the following:
# (i used a serial port sniffer on butel software to find this command)
#     0. GLG (echo command)
#     1. Frequency in kHz
#     2. Modulation
#     3. empty
#     4. ?
#     5. empty
#     6. empty
#     7. Channel Name
#     8. 0 = Squelch open ?
#     9. 1 = Squelch open ?
#    10. empty
#    11. Channel number
#    12. \r (carrige return)
#
# you need to pip3 install python-telegram-bot 

import serial, time, tempfile, telegram
from tkinter import *
from tkinter import ttk

# Serial port  (Raspberry Pi port in /dev)
SERIAL_PORT = "/dev/ttyACM0"

# Serial port settings
SERIAL_SPEED    = 115200
SERIAL_STOPBITS = serial.STOPBITS_TWO
SERIAL_TIMEOUT  = 1.0

# Global variables
previous_channel = '0'
current_channel  = '0'
start_time       = time.time()
stopped          = False
sort_column      = 4

# make a TkInter Window
root = Tk()
root.geometry("810x480")
root.title("UBC125XLT -- Channel logger.  @"+SERIAL_PORT+", "+str(SERIAL_SPEED)+" Bd")

# create the main window and then the 3 containers
window = ttk.Panedwindow(root, orient = VERTICAL)
window.pack()
ribbon_frame  = ttk.Frame(window, height=44)
ribbon_frame.pack()
header_frame  = ttk.Frame(window)
header_frame.pack()
history_frame = ttk.Frame(window)
history_frame.pack()

# labels on the ribbon
label_1 = Label(ribbon_frame, font=('Arial', 28, 'bold'  ), width=20, fg='blue')
label_1.grid(row=0, column=0)
label_2 = Label(ribbon_frame, font=('Arial', 14, 'normal'), width=17, fg='black')
label_2.grid(row=0, column=1, sticky="e")
label_3 = Label(ribbon_frame, font=('Arial', 14, 'normal'), width=5,  fg='black')
label_3.grid(row=0, column=2, sticky="e")

# text area configurations and fixed text     note: height=# of lines
# justify text in center  font is courier and spaces are included in justification!
header_text = Text(header_frame, height=2, font=('Courier', 14, 'normal'),  pady=1, padx=1, bg='white', fg='red')
header_text.tag_configure("center", justify='center')
header_text.insert("1.0", "  0"+u'\u25B2'+"| 1"+u'\u25BC'+"|              2"+u'\u25BC'+"|           3"+u'\u25BC'+"|                 4"+u'\u25B2'+"|  5"+u'\u25B2'+"|   \n")
header_text.tag_add("center", "1.0", "end")
header_text.insert(END, "Rank|Ch#|Channel Name    |Frequency-Mod|Date       Time    |Open|LH ")
# line has 68 characters. See above fixed line and will create a correct outlined tabel 
header_text.pack()
history_text = Text(history_frame, height=17, font=('Courier', 14, 'normal'), pady=1, padx=1, bg='white', fg='black')
history_text.pack()

# open serial port  
ser = serial.Serial(port=SERIAL_PORT, baudrate=SERIAL_SPEED, stopbits=SERIAL_STOPBITS, timeout=SERIAL_TIMEOUT)
 
# subroutines
def read_channel ():
    global previous_channel, start_time, current_channel, stopped
    # read channel values from the ubc125xlt
    # first send a non documented GLG command to 125xlt
    # then read line (we are expecting a line with Squelch info in positon 8 or 9 from the array) 
    # split line into individual variables. Delimeter is , and use position 8 to determine.
    ser.write('GLG\r\n'.encode())
    result = ser.readline()
    current_channel = (result.decode()).split(",")

    if current_channel[8] == '1' :
        # scanning stopped.  Is this the start of reception or (else) was it still open  
        if current_channel[11] != previous_channel :
            previous_channel = current_channel[11]
            start_time = time.time()
            stopped = True
            # info to statistics file, ribbon and check if alarm needs to be send through telegram
            statistics(True)
            ribbon(current_channel[7],current_channel[1][1:4]+"."+current_channel[1][4:8]+" - "+current_channel[2]+" ("+'{:>3}'.format(current_channel[11])+")")
            send_telegram()
        else :
            # update elapse time and only ribbon
            ribbon(current_channel[7],current_channel[1][1:4]+"."+current_channel[1][4:8]+" - "+current_channel[2]+" ("+'{:>3}'.format(current_channel[11])+")")
    else :
        # scanning. So show scanning and closed elapse seconds on the ribbon
        if stopped :
            #store receive time in statistics file when channel just closed before re-set flag to excute once
            if stopped == True:
                statistics(False)
                stopped = False
            start_time = time.time()
            previous_channel = '0'
        ribbon('scanning','')
    # and keep looping in this subroutine 
    window.after(1, read_channel)
    
def ribbon (label1,label2):
    global start_time
    label_1.config(text=label1)
    label_2.config(text=label2)
    label_3.config(text=int(time.time() - start_time))
    # update also the statistics 
    display_history()

def statistics (stopped):
    global current_channel, previous_channel
    # open history file
    # and read all the lines
    # set boolean for sub routine control
    # create temp file
    stat_file = open("ubc125xlt_history.txt", 'r+')
    lines = stat_file.readlines()
    known_channel = False
    tmpfile = tempfile.NamedTemporaryFile(delete=True)

    # read history file  if channel is open do this
    if stopped :
        for line in lines:
            column = line.split('|')
            if column[1].lstrip() == current_channel[11]:
                # found channel record in the file so update the counter only
                known_channel = True 
                tmpfile.write(("{:>4}".format(str(int(column[0])+1))+'|'+column[1]+'|'+column[2]+'|'+column[3]+'|'+time.strftime("%d/%m/%Y %H:%M:%S")+'|'+column[5]+'| '+u'\u25C0'+' \r\n').encode())
            else:
                # channel is not corresponding so rewrite channel record without update 
                tmpfile.write((column[0]+'|'+column[1]+'|'+column[2]+'|'+column[3]+'|'+column[4]+'|'+column[5]+'|   \r\n').encode())
        if known_channel == False :
                # seems this is a new channel for history file to create new reord
                tmpfile.write(('   1|'+"{:>3}".format(current_channel[11])+'|'+"{:16}".format(current_channel[7])+'|'+current_channel[1][1:4]+'.'+current_channel[1][4:8]+' - '+current_channel[2]+'|'+time.strftime("%d/%m/%Y %H:%M:%S")+'|   0| '+u'\u25C0'+' \r\n').encode())

    # if channel has closed do this once       
    else:
        for line in lines:
            column = line.split('|')

            if column[1].lstrip() == previous_channel:
                # found channel record in the file so update the receive time only
                tmpfile.write(("{:>4}".format(str(int(column[0])))+'|'+column[1]+'|'+column[2]+'|'+column[3]+'|'+time.strftime("%d/%m/%Y %H:%M:%S")+'|'+"{:>4}".format(str(int(column[5])+int(time.time() - start_time)))+'| '+u'\u25C0'+' \r\n').encode())
            else:
                # channel is not corresponding so rewrite channel record without update 
                tmpfile.write((column[0]+'|'+column[1]+'|'+column[2]+'|'+column[3]+'|'+column[4]+'|'+column[5]+'|   \r\n').encode())

    # now rewrite the history file set pointer to the top and clean file
    # set the pointer to the top of the temp file and rewrite the history file
    # close both files and distroy tempfile
    stat_file.seek(0)
    stat_file.truncate()
    tmpfile.seek(0)
    tmplines = tmpfile.readlines()
    for tmpline in tmplines:
        stat_file.write(tmpline.decode('utf-8'))
    tmpfile.close()
    stat_file.close()

def send_telegram ():
    global current_channel
    # input here your telegram bot token 
    bot = telegram.Bot('54xxxx895:AAHaMNyxxxxxxxxxxxxxLUTMfOxaZf6dCz0')
    # store the channel number(s) of the ones you want to receive an alarm through telegram in the alarm_channels array
    # send your message to the right telegram id
    alarm_channels  = ['51','53','101','112','135','136','151','157']
    if current_channel[11] in alarm_channels:
        bot.sendMessage(2xxxxxx764, 'ubc125xlt: '+current_channel[7])

def truncate_file ():
    stat_file = open("ubc125xlt_history.txt", 'r+')
    stat_file.seek(0)
    stat_file.truncate()
    stat_file.close()
    
def change_sort_sequence ():
    global sort_column
    sort_column += 1
    if sort_column == 6:
        sort_column = 0
    button_sort.configure(text='Sort:'+str(sort_column))
    display_history()

def sort_by_column(lines):
    global sort_column
    element = lines.split('|')
    # will sort on the column indent 0=Hits DESC, 1=Channel ASC, 2=Name ASC, 3=Frequency ASC, 4=Date/Time DESC, 5=Airtime DESC
    return element[sort_column]

def display_history ():
    # open history file
    # clear text frame
    # write new file content based on the sort sequence and justify the text in the center
    input_file = open("ubc125xlt_history.txt", "r")
    history_text.tag_configure("center", justify='center')
    history_text.delete("1.0",END)
    lines = input_file.readlines()
    if sort_column == 1 or sort_column == 2 or sort_column == 3 :
        lines.sort(reverse=False, key=sort_by_column)
    else:
        # 0 , 4 and 5
        lines.sort(reverse=True, key=sort_by_column)
    # tabel header
    for line in lines:
        history_text.insert(END, line)
        history_text.tag_add("center", "1.0", "end")

  
# create clear history and sort button
Button(ribbon_frame, text = "Clear",  command = truncate_file,    font=('Arial', 11, 'normal')).grid(column=4, row=0)
button_sort = Button(ribbon_frame, text = 'Sort='+str(sort_column),  command = change_sort_sequence,   font=('Arial', 11, 'normal'))
button_sort.grid(row=0, column=5)

# mainloop (will loop inside sub read_channel)
# speed is dependent on the ubc125xlt response which seems to be slow sub 
read_channel()
root.mainloop()
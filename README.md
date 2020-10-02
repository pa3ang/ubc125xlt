# UBC125XLT logger

PA3ANG, September - 2020
version 1.0
This program connects to a UBC125XLT scanner and reads the RX frequency channel it is receiving (stopped during scan).
It will then :
    - display the channel info on the ribbon and display the last heard channels in the given sort
    - when channel opens create entry in history file or update the hit counter and set last heard pointer
    - when channel closes again update the total air time seconds 
    - based on a channel selection send an alarm to a telegram bot 

Very straight forward program for educational purpose using serial and tkinter.

You need to create to files in the working directory:
    - ubc125xlt_history.txt  

The histroy file is capturing the received channels and contains the following field:
    - Rank      : number of times channel opened
    - Ch      : channel number in the ubc125xlt
    - Name      : channel name as stored in the ubc125xlt
    - Freq-Mod  : frequnecy and modulation type
    - Date Time : the last heard date and time
    - Open      : total time the cnhannel was open since
    - LH        : Last Heard pointer as being the channel last received

The program uses the GLG command to interrogate the ubc125xlt.
This rather undocumented command (refer to Uniden BC125AT Programming Protocol) returns the following:
(i used a serial port sniffer on butel software to find this command)
    0. GLG (echo command)
    1. Frequency in kHz
    2. Modulation
    3. empty
    4. ?
    5. empty
    6. empty
    7. Channel Name
    8. 0 = Squelch open ?
    9. 1 = Squelch open ?
   10. empty
   11. Channel number
   12. \r (carrige return)

you need to pip3 install python-telegram-bot

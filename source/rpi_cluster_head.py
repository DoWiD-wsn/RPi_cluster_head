#####
# @brief    Raspberry Pi-based cluster head
#
# Python script running on a raspberry pi to serve as a cluster head in
# a ZigBee-based wireless sensor network. The script connects serially
# to an Xbee 3 module, continuously receives and evaluates messages
# received and stores the data of correct messages in a remote database.
#
# @file     rpi_cluster_head.py
# @author   Dominik Widhalm
# @version  0.1.0
# @date     2020/08/04
#####


##### LIBRARIES #####
# Import the sleep function
from time import sleep
# For byte array hex output
import binascii
# To terminate the program in case of error
import sys
# To catch system signals
import signal
# To convert (and print) timestamps
from datetime import datetime
# To convert bytearray to float
import struct
# To connect to MySQL DB (including possible error codes)
import mysql.connector
from mysql.connector import errorcode
# Import the Xbee library
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
from digi.xbee.models.address import XBee64BitAddress


##### GLOBAL VARIABLES #####
# Path to the Xbee serial interface (adapt if necessary!)
XBEE_SERIAL_DEV     = "/dev/ttyUSB0"

# database connection details (adapt if necessary!)
DB_CON_HOST         = "10.0.0.xx"
DB_CON_USER         = "USER"
DB_CON_PASS         = "PASS"
DB_CON_BASE         = "wsn_testbed"
# database insert template
DB_INSERT_VALUE = ("INSERT INTO sensordata (snid, sntime, dbtime, type, value, sreg, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)")

### LOG FILES ###
ERROR_LOG_FILE      = "./error.log"
WARNING_LOG_FILE    = "./warning.log"
NOTE_LOG_FILE       = "./note.log"

# timeouts [tries]
TIMEOUT_A           = 100                   # Timeout A -- xbee initial connect
TIMEOUT_B           = 100                   # Timeout B -- DB initial connect
TIMEOUT_C           = 250                   # Timeout C -- xbee re-connect
TIMEOUT_D           = 250                   # Timeout D -- DB re-connect

# delays [s]
DELAY_A             = 10                    # Delay A -- xbee initial connect
DELAY_B             = 10                    # Delay B -- DB initial connect
DELAY_C             = 30                    # Delay C -- xbee re-connect
DELAY_D             = 30                    # Delay D -- DB re-connect

# Marker for callback whether program needs to terminate
terminate = 0


##### CALLBACK #####
# SIGINT CALLBACK
def sigint_callback(sig, frame):
    # Need to make terminate global
    global terminate
    # Set terminate to 1
    terminate = 1


##### MAIN #####
# Add CRTL-C callback (needed for program termination)
signal.signal(signal.SIGINT, sigint_callback)

# Open log files
try:
    error_f = open(ERROR_LOG_FILE, "a")
    warning_f = open(WARNING_LOG_FILE, "a")
    note_f = open(NOTE_LOG_FILE, "a")
except:
    # Couldn't open log files ... not good
    sys.exit()
else:
    # Write starting-message to log file
    error_f.write("=== STARTUP - " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " ===\n")
    warning_f.write("=== STARTUP - " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " ===\n")
    note_f.write("=== STARTUP - " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " ===\n")
 
# Initial timeout counter
cnt_A = 0
cnt_B = 0
cnt_C = 0
cnt_D = 0

# Connection status
xbee_connect = 0
db_connect = 0
xbee = None
db_con = None
db_cur = None
sender = dict()

##### STAGE 1 #####
#
# Initial connect to xbee
while (xbee_connect != 1):
    # Increment timeout counter A
    cnt_A = cnt_A + 1
    # Check if timeout has been reached
    if (cnt_A >= TIMEOUT_A):
        # That's a big problem
        error_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not connect to xbee device at all!\n")
        # Check if log files are still open
        if error_f.closed:
            # Close log file
            error_f.close()
        if warning_f.closed:
            # Close log file
            warning_f.close()
        if note_f.closed:
            # Close log file
            note_f.close()
        # Terminate
        sys.exit()
    # Try to open a connection to xbee
    try:
        # Instantiate a generic xbee device
        xbee = XBeeDevice(XBEE_SERIAL_DEV, 9600)
        # Open the connection with the device
        xbee.open()
    except:
        # So far it's only a warning
        warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not connect to xbee device (try " + str(cnt_A+1) + "/" + str(TIMEOUT_A) + ") \"" + sys.exc_info()[0] + "\"\n")
        # Wait some time (DELAY_A)
        sleep(DELAY_A)
    else:
        # Check if really connected
        if xbee is not None and xbee.is_open():
            # Log message (note)
            note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Connected to xbee module!\n")
            # Set connection status to 1
            xbee_connect = 1
            # Reset timeout counter
            cnt_A = 0
        else:
            # So far it's only a warning
            warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not connect to xbee device (try " + str(cnt_A+1) + "/" + str(TIMEOUT_A) + ") \"" + sys.exc_info()[0] + "\"\n")
            # Wait some time (DELAY_A)
            sleep(DELAY_A)


##### STAGE 2 #####
#
# Initial connect to DB
while (db_connect != 1):
    # Increment timeout counter B
    cnt_B = cnt_B + 1
    # Check if timeout has been reached
    if (cnt_B >= TIMEOUT_B):
        # Check if the xbee connection is still alive
        if xbee is not None and xbee.is_open():
            # Close the xbee connection
            xbee.close()
        # That's a big problem
        error_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not connect to DB at all!\n")
        # Check if log files are still open
        if error_f.closed:
            # Close log file
            error_f.close()
        if warning_f.closed:
            # Close log file
            warning_f.close()
        if note_f.closed:
            # Close log file
            note_f.close()
        # Terminate
        sys.exit()
    # Try to open a connection to DB
    try:
        # Open a connection to the MySQL database
        db_con = mysql.connector.connect(host=DB_CON_HOST, user=DB_CON_USER, password=DB_CON_PASS, database=DB_CON_BASE)
    except:
        # So far it's only a warning
        warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not connect to the DB (try " + str(cnt_B+1) + "/" + str(TIMEOUT_B) + ") \"" + sys.exc_info()[0] + "\"\n")
        # Wait some time (DELAY_B)
        sleep(DELAY_B)
    else:
        # Check if DB is really connected
        if db_con.is_connected():
            # Log message (note)
            note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Connected to the DB!\n")
            # Get an cursor for the DB
            db_cur = db_con.cursor()
            # Set connection status to 1
            db_connect = 1
            # Reset timeout counter
            cnt_B = 0
        else:
            # So far it's only a warning
            warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not connect to the DB (try " + str(cnt_B+1) + "/" + str(TIMEOUT_B) + ") \"" + sys.exc_info()[0] + "\"\n")
            # Wait some time (DELAY_B)
            sleep(DELAY_B)


##### STAGE 3 #####
#
# Wait for messages

# Run loop as long as no SIGINT was received
while (terminate != 1):
    # Check if something has been received
    try:
        # Clear previous data
        msg = None
        # Try to read a message
        msg = xbee.read_data()
    except:
        # So far it's only a warning
        warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Problem receiving a message \"" + sys.exc_info()[0] + "\"\n")
    
    # Check if there was a message available
    if msg is not None:
        ### Read message content ###
        # Source address (64-bit MAC address)
        src    = msg.remote_device._64bit_addr
        # Receive timestamp (need to use UTC for Grafana)
        tstamp = datetime.utcfromtimestamp(msg.timestamp)
        # Broadcast flag (true / false)
        bcast  = msg.is_broadcast
        # Payload length
        m_size = len(msg.data)
        
        # Check message payload size (should be 14 bytes)
        if m_size == 14:
            ### SEN-MSG data ###
            # 0..3  -> Sensor Node ID
            snid      = bytes(msg.data[0:4]).hex().upper()
            # 4..7  -> Sensor Node "timestamp"
            sntime    = int.from_bytes(msg.data[4:8], byteorder='big', signed=False)
            # 8     -> Measurement type
            m_type    = msg.data[8]
            # 9..12 -> Measurement value (float)
            [m_value] = struct.unpack('f', msg.data[9:13])
            # 13    -> SREG value (status register)
            sreg      = msg.data[13]
            
            # Log received data
            note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Got a message from " + str(src) + " at " + str(tstamp.strftime('%Y-%m-%d %H:%M:%S')) + "\n")
            note_f.write("                    ID   : " + str(snid) + "\n")
            note_f.write("                    TIME : " + str(sntime) + "\n")
            note_f.write("                    TYPE : " + str(hex(m_type).upper().replace('X', 'x')) + "\n")
            note_f.write("                    VALUE: " + str(m_value) + "\n")
            note_f.write("                    SREG : " + str(hex(sreg).upper().replace('X', 'x')) + "\n")
            
            # Check if this sender already sent a message (noted by its "timestamp")
            if snid in sender:
                # Check if current "sntime" is previous one plus one
                if (sender[snid]+1) != sntime:
                    # Log warning
                    warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- SNID mismatch: had " + str(sender[snid]) + " and got " + str(sntime) + "\n")
            # Update/add current "sntime" to the dictionary
            sender[snid] = sntime
            
            # Check if the DB connection is still alive
            if db_con.is_connected():
                # Insert data into DB
                try:
                    # Try execute DB insert
                    db_cur.execute(DB_INSERT_VALUE, (snid, sntime, tstamp, m_type, m_value, sreg, ""))
                    # Commit data to the DB
                    db_con.commit()
                except:
                    # So far it's only a warning
                    warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Problem writing to DB \"" + sys.exc_info()[0] + "\"\n")
                    # Try to re-connect
                    if db_con.is_connected():
                        db_cur.close()
                        db_con.close()
                else:
                    # Log successful DB write
                    note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Added new data to DB with row_id=" + str(db_cur.lastrowid) + "\n")
                    # Continue with next message
                    continue
            
            # Looks like we've lost the connection to the DB (or need a re-connect)
            db_connect = 0
            db_con = None
            db_cur = None
            # Log incident
            warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Lost connection to the DB\n")
            
            
            ##### STAGE 3.2 #####
            #
            # Re-connect to DB
            while (db_connect != 1):
                # Increment timeout counter D
                cnt_D = cnt_D + 1
                # Check if timeout has been reached
                if (cnt_D >= TIMEOUT_D):
                    # Check if the xbee connection is still alive
                    if xbee is not None and xbee.is_open():
                        # Close the xbee connection
                        xbee.close()
                    # That's a big problem
                    error_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not re-connect to DB at all!\n")
                    # Check if log files are still open
                    if error_f.closed:
                        # Close log file
                        error_f.close()
                    if warning_f.closed:
                        # Close log file
                        warning_f.close()
                    if note_f.closed:
                        # Close log file
                        note_f.close()
                    # Terminate
                    sys.exit()
                # Try to open a connection to DB
                try:
                    # Open a connection to the MySQL database
                    db_con = mysql.connector.connect(host=DB_CON_HOST, user=DB_CON_USER, password=DB_CON_PASS, database=DB_CON_BASE)
                except:
                    # So far it's only a warning
                    warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not re-connect to the DB (try " + str(cnt_D+1) + "/" + str(TIMEOUT_D) + ") \"" + sys.exc_info()[0] + "\"\n")
                    # Wait some time (DELAY_D)
                    sleep(DELAY_D)
                else:
                    # Check if DB is really connected
                    if db_con.is_connected():
                        # Log message (note)
                        note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Re-connected to the DB!\n")
                        # Get an cursor for the DB
                        db_cur = db_con.cursor()
                        # Set connection status to 1
                        db_connect = 1
                        # Reset timeout counter
                        cnt_D = 0
                        # Insert data into DB
                        try:
                            # Try execute DB insert
                            db_cur.execute(DB_INSERT_VALUE, (snid, sntime, tstamp, m_type, m_value, sreg, ""))
                            # Commit data to the DB
                            db_con.commit()
                        except:
                            # So far it's only a warning
                            warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Problem writing to DB \"" + sys.exc_info()[0] + "\"\n")
                            # Try to re-connect
                            if db_con.is_connected():
                                db_cur.close()
                                db_con.close()
                        else:
                            # Log successful DB write
                            note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Added new data to DB with row_id=" + str(db_cur.lastrowid) + "\n")
                            # Continue with next message
                            continue
                    else:
                        # So far it's only a warning
                        warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not re-connect to the DB (try " + str(cnt_B+1) + "/" + str(TIMEOUT_B) + ") \"" + sys.exc_info()[0] + "\"\n")
                        # Wait some time (DELAY_D)
                        sleep(DELAY_D)
        else:
            # Log erroneous message
            warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Got a message from " + str(src) + " with a wrong format at " + str(tstamp.strftime('%Y-%m-%d %H:%M:%S')))
            warning_f.write("                    -> PAYLOAD: \"" + str(bytes(msg.data).hex().upper()) + "\" (" + str(m_size) + " bytes)")
    else:
        # Check if the xbee connection is still alive
        if xbee is not None and xbee.is_open():
            # Looks like everything is fine
            continue
        else:
            # Looks like we've lost the connection to xbee
            xbee_connect = 0
            xbee = None
            # Log incident
            warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Lost connection to xbee\n")
            
            ##### STAGE 3.1 #####
            #
            # Re-connect to xbee
            while (xbee_connect != 1):
                # Increment timeout counter C
                cnt_C = cnt_C + 1
                # Check if timeout has been reached
                if (cnt_C >= TIMEOUT_C):
                    # That's a big problem
                    error_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not re-connect to xbee device at all!\n")
                    # Check if DB connection is open
                    if db_con.is_connected():
                        # Close connection
                        db_cur.close()
                        db_con.close()
                    # Check if log files are still open
                    if error_f.closed:
                        # Close log file
                        error_f.close()
                    if warning_f.closed:
                        # Close log file
                        warning_f.close()
                    if note_f.closed:
                        # Close log file
                        note_f.close()
                    # Terminate
                    sys.exit()
                # Try to open a connection to xbee
                try:
                    # Instantiate a generic xbee device
                    xbee = XBeeDevice(XBEE_SERIAL_DEV, 9600)
                    # Open the connection with the device
                    xbee.open()
                except:
                    # So far it's only a warning
                    warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not re-connect to xbee device (try " + str(cnt_C+1) + "/" + str(TIMEOUT_C) + ") \"" + sys.exc_info()[0] + "\"\n")
                    # Wait some time (DELAY_C)
                    sleep(DELAY_C)
                else:
                    # Check if really connected
                    if xbee is not None and xbee.is_open():
                        # Log message (note)
                        note_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Re-connected to xbee module!\n")
                        # Set connection status to 1
                        xbee_connect = 1
                        # Reset timeout counter
                        cnt_C = 0
                    else:
                        # So far it's only a warning
                        warning_f.write(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " -- Could not re-connect to xbee device (try " + str(cnt_C+1) + "/" + str(TIMEOUT_C) + ") \"" + sys.exc_info()[0] + "\"\n")
                        # Wait some time (DELAY_C)
                        sleep(DELAY_C)


##### STAGE 4 #####
#
# Termination

# Check if the DB connection is still alive
if db_con.is_connected():
    db_cur.close()
    db_con.close()

# Check if the xbee connection is still alive
if xbee is not None and xbee.is_open():
    # Close the xbee connection
    xbee.close()

# Write starting-message to log file
error_f.write("=== TERMINATION - " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " ===\n\n")
warning_f.write("=== TERMINATION - " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " ===\n\n")
note_f.write("=== TERMINATION - " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " ===\n\n")

# Check if log files are still open
if error_f.closed:
    # Close log file
    error_f.close()
if warning_f.closed:
    # Close log file
    warning_f.close()
if note_f.closed:
    # Close log file
    note_f.close()

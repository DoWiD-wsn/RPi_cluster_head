#####
# @brief    Raspberry Pi-based cluster head
#
# Python script running on a raspberry pi to serve as a cluster head in
# a ZigBee-based wireless sensor network. The script connects serially
# to an Xbee 3 module, continuously receives and evaluates messages
# received and stores the data of correct messages in a remote database.
# Additionally, specified information is written into a log file.
#
# This is the version used in the centralized DCA WSN testbed.
#
# @file     rpi_cluster_head.py
# @author   Dominik Widhalm
# @version  0.1.0
# @date     2021/10/19
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
# For logging functionality
import logging
# To connect to MySQL DB
import mysql.connector
from mysql.connector import errorcode
# Import the Xbee library
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
from digi.xbee.models.address import XBee64BitAddress


##### GLOBAL VARIABLES #####
# Path to the Xbee serial interface (adapt if necessary!)
XBEE_SERIAL_DEV     = "/dev/ttyUSB0"

# database connection details (adapt if necessary!)
DB_CON_HOST         = "192.168.13.98"
DB_CON_USER         = "mywsn"
DB_CON_PASS         = "$MyWSNdemo$"
DB_CON_BASE         = "wsn_testbed"
# database insert template
DB_INSERT_VALUE     = ("INSERT INTO sensordata (snid, sntime, dbtime, t_air, t_soil, h_air, h_soil, x_nt, x_vs, x_bat, x_art, x_rst, x_ic, x_adc, x_usart) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

### logging level
# DEBUG -> INFO -> WARNING -> ERROR -> CRITICAL
LOG_LEVEL           = logging.WARNING
LOG_FILE            = "cluster_head.log"

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

##### FUNCTIONS ########################
def fixed16_to_float(value, f_bits):
    # Convert fixed16 to float
    tmp = (float(value & 0x7FFF) / float(1 << f_bits))
    # Check sign of input
    if(value & 0x8000):
        tmp *= -1
    # Return the float value
    return tmp


##### MAIN #############################
# Add CRTL-C callback (needed for program termination)
signal.signal(signal.SIGINT, sigint_callback)

# Prepare logging module
logging.basicConfig(filename=LOG_FILE, filemode='a', format="%(levelname)-8s %(asctime)s -- %(message)s", datefmt="%Y-%m-%d %H:%M:%S",level=LOG_LEVEL)
# Do not use the xbee or mysql logger
logging.getLogger("digi.xbee").setLevel(logging.CRITICAL)
logging.getLogger("mysql").setLevel(logging.CRITICAL)
# Write starting-message to log file
logging.info("===== STARTUP =====")
 
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
        logging.error("Could not connect to xbee device!")
        # Terminate
        sys.exit()
    # Try to open a connection to xbee
    try:
        # Instantiate a generic xbee device
        xbee = XBeeDevice(XBEE_SERIAL_DEV, 115200)
        # Open the connection with the device
        xbee.open()
    except Exception as e:
        # So far it's only a warning
        logging.warning("Connection to xbee failed! (try %s of %s)",(cnt_A+1),TIMEOUT_A, exc_info=False)
        # Wait some time (DELAY_A)
        sleep(DELAY_A)
    else:
        # Check if really connected
        if xbee is not None and xbee.is_open():
            # Log message (note)
            logging.info("Connected to xbee module!")
            # Set connection status to 1
            xbee_connect = 1
            # Reset timeout counter
            cnt_A = 0
        else:
            # So far it's only a warning
            logging.warning("Connection to xbee failed! (try %s of %s)",(cnt_A+1),TIMEOUT_A)
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
        logging.error("Could not connect to DB!")
        # Terminate
        sys.exit()
    # Try to open a connection to DB
    try:
        # Open a connection to the MySQL database
        db_con = mysql.connector.connect(host=DB_CON_HOST, user=DB_CON_USER, password=DB_CON_PASS, database=DB_CON_BASE)
    except Exception as e:
        # So far it's only a warning
        logging.warning("Connection to the DB failed! (try %s of %s)",(cnt_B+1),TIMEOUT_B, exc_info=False)
        # Wait some time (DELAY_B)
        sleep(DELAY_B)
    else:
        # Check if DB is really connected
        if db_con.is_connected():
            # Log message (note)
            logging.info("Connected to the DB!")
            # Get an cursor for the DB
            db_cur = db_con.cursor()
            # Set connection status to 1
            db_connect = 1
            # Reset timeout counter
            cnt_B = 0
        else:
            # So far it's only a warning
            logging.warning("Connection to the DB failed! (try %s of %s)",(cnt_B+1),TIMEOUT_B)
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
    except Exception as e:
        # So far it's only a warning
        logging.warning("Problem receiving a message!", exc_info=False)
    
    # Check if there was a message available
    if msg is not None:
        ### Read message content ###
        # Source address (64-bit MAC address)
        src    = msg.remote_device._64bit_addr
        # Sensor Node ID
        snid   = bytes(src.address[4:8]).hex().upper()
        
        # Receive timestamp (need to use UTC for Grafana)
        tstamp = datetime.utcfromtimestamp(msg.timestamp)
        # Broadcast flag (true / false)
        bcast  = msg.is_broadcast
        # Payload length
        m_size = len(msg.data)
        
        # Check message payload size (should be 26 bytes)
        if m_size == 26:
            ### SEN-MSG data ###
            # 0..1  -> Sensor Node "timestamp"
            sntime    = int.from_bytes(msg.data[0:2], byteorder='little', signed=False)
            
            # Log received data
            logging.info("Got a message from %s at %s (UTC) with %d bytes (sntime: %d)",src,tstamp.strftime('%Y-%m-%d %H:%M:%S'),m_size,sntime)
            
            # -> Use case data
            t_air   = fixed16_to_float(int.from_bytes(msg.data[2:4],   byteorder='little', signed=False), 6)
            t_soil  = fixed16_to_float(int.from_bytes(msg.data[4:6],   byteorder='little', signed=False), 6)
            h_air   = fixed16_to_float(int.from_bytes(msg.data[6:8],   byteorder='little', signed=False), 6)
            h_soil  = fixed16_to_float(int.from_bytes(msg.data[8:10],  byteorder='little', signed=False), 6)
            
            # -> Fault indicator
            x_nt    = fixed16_to_float(int.from_bytes(msg.data[10:12], byteorder='little', signed=False), 6)
            x_vs    = fixed16_to_float(int.from_bytes(msg.data[12:14], byteorder='little', signed=False), 6)
            x_bat   = fixed16_to_float(int.from_bytes(msg.data[14:16], byteorder='little', signed=False), 6)
            x_art   = fixed16_to_float(int.from_bytes(msg.data[16:18], byteorder='little', signed=False), 6)
            x_rst   = fixed16_to_float(int.from_bytes(msg.data[18:20], byteorder='little', signed=False), 6)
            x_ic    = fixed16_to_float(int.from_bytes(msg.data[20:22], byteorder='little', signed=False), 6)
            x_adc   = fixed16_to_float(int.from_bytes(msg.data[22:24], byteorder='little', signed=False), 6)
            x_usart = fixed16_to_float(int.from_bytes(msg.data[24:26], byteorder='little', signed=False), 6)
            
            # Insert data into DB
            if db_con.is_connected():
                try:
                    # Try execute DB insert
                    db_cur.execute(DB_INSERT_VALUE, (snid, sntime, tstamp, t_air, t_soil, h_air, h_soil, x_nt, x_vs, x_bat, x_art, x_rst, x_ic, x_adc, x_usart))
                    # Commit data to the DB
                    db_con.commit()
                except Exception as e:
                    # So far it's only a warning
                    logging.warning("Problem writing to the DB", exc_info=False)
                    # Try to re-connect
                    if db_con.is_connected():
                        db_cur.close()
                        db_con.close()
                        break
                else:
                    # Log successful DB write
                    logging.info("Added new data to DB with row_id=%d",db_cur.lastrowid)
            else:
                # Looks like we've lost the connection to the DB (or need a re-connect)
                db_connect = 0
                db_con = None
                db_cur = None
                # Log incident
                logging.warning("Lost connection to the DB")
                break
            
            # Check if this sender already sent a message (noted by its "timestamp")
            if snid in sender:
                # Check if current "sntime" is previous one plus one
                if (sender[snid]+1) != sntime:
                    # Log warning
                    logging.warning("SNID mismatch for %s: had %d and got %d",src,sender[snid],sntime)
            # Update/add current "sntime" to the dictionary
            sender[snid] = sntime
            
            # Check if still connected to DB
            if db_connect:
                continue
            
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
                    logging.error("Could not re-connect to DB at all!")
                    # Terminate
                    sys.exit()
                # Try to open a connection to DB
                try:
                    # Open a connection to the MySQL database
                    db_con = mysql.connector.connect(host=DB_CON_HOST, user=DB_CON_USER, password=DB_CON_PASS, database=DB_CON_BASE)
                except Exception as e:
                    # So far it's only a warning
                    logging.warning("Could not re-connect to the DB (try %d / %d)",(cnt_D+1),TIMEOUT_D, exc_info=False)
                    # Wait some time (DELAY_D)
                    sleep(DELAY_D)
                else:
                    # Check if DB is really connected
                    if db_con.is_connected():
                        # Log message (note)
                        logging.warning("Re-connected to the DB!")
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
                        except Exception as e:
                            # So far it's only a warning
                            logging.warning("Problem writing to DB", exc_info=False)
                            # Try to re-connect
                            if db_con.is_connected():
                                db_cur.close()
                                db_con.close()
                        else:
                            # Log successful DB write
                            logging.info("Added new data to DB with row_id=%d",db_cur.lastrowid)
                            # Continue with next message
                            continue
                    else:
                        # So far it's only a warning
                        logging.warning("Could not re-connect to the DB (try %d / %d)",(cnt_B+1),TIMEOUT_B)
                        # Wait some time (DELAY_D)
                        sleep(DELAY_D)
        else:
            # Log erroneous message
            logging.warning("Got a message from %s with a wrong size (%d bytes) at %s (UTC)",src,m_size,tstamp.strftime('%Y-%m-%d %H:%M:%S'))
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
            logging.warning("Lost connection to xbee")
            
            ##### STAGE 3.1 #####
            #
            # Re-connect to xbee
            while (xbee_connect != 1):
                # Increment timeout counter C
                cnt_C = cnt_C + 1
                # Check if timeout has been reached
                if (cnt_C >= TIMEOUT_C):
                    # That's a big problem
                    logging.error("Could not re-connect to xbee device!")
                    # Check if DB connection is open
                    if db_con.is_connected():
                        # Close connection
                        db_cur.close()
                        db_con.close()
                    # Terminate
                    sys.exit()
                # Try to open a connection to xbee
                try:
                    # Instantiate a generic xbee device
                    xbee = XBeeDevice(XBEE_SERIAL_DEV, 9600)
                    # Open the connection with the device
                    xbee.open()
                except Exception as e:
                    # So far it's only a warning
                    logging.warning("Could not re-connect to xbee device (try %d / %d)",(cnt_C+1),TIMEOUT_C, exc_info=False)
                    # Wait some time (DELAY_C)
                    sleep(DELAY_C)
                else:
                    # Check if really connected
                    if xbee is not None and xbee.is_open():
                        # Log message (note)
                        logging.info("Re-connected to xbee module!")
                        # Set connection status to 1
                        xbee_connect = 1
                        # Reset timeout counter
                        cnt_C = 0
                    else:
                        # So far it's only a warning
                        logging.warning("Could not re-connect to xbee device (try %d / %d)",(cnt_C+1),TIMEOUT_C)
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
logging.info("===== TERMINATION =====\n\n\n")

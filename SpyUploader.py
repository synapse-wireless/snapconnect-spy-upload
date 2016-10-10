# (c) Copyright 2012-2015 Synapse Wireless, Inc.
"""
SpyUploader() - This class provides an API for sending new SPY files to SNAP Nodes.

In addition to showing which SNAPconnect functions to invoke to perform the transfer,
this class also adds "upload retries" - if an upload times out, this object will try
again, up to MAX_PROG_RETRIES.

Look towards the bottom of the file for the usual "__main__" section that
demonstrates how to use this module.
"""

import sys
import os

from snapconnect import snap

import time
import datetime
import binascii
from snaplib import ScriptsManager
from snaplib import SnappyUploader

NO_INSTANCE = -1 # You have tried to initiate a SPY Upload but you have not yet provided a SNAPconnect instance to perform the underlying communications
NO_SUCH_FILE = -2 # You tried to upload a SPY file that does not exist (check the PATH)
TOO_MANY_RETRIES = -3 # Maximum number of upload attempts exceeded

# NOTE: Ensure that the Feature bits setting on this device has both (0x100) second data CRC
#       and (0x400) packet CRC disabled
BRIDGE_NODE = "\x03\xF9\x5A" # <- Replace this with the address of your bridge node

# Note the hardcoded COM1 usage.
# You should set these to match YOUR available hardware
SERIAL_TYPE = snap.SERIAL_TYPE_RS232
#SERIAL_TYPE = snap.SERIAL_TYPE_SNAPSTICK100
#SERIAL_TYPE = snap.SERIAL_TYPE_SNAPSTICK200

# If you're on a unix platform, you'll need to specify the interface type differently than windows
# An example for a typical interface device is shown below
SERIAL_PORT = 0 # COM1
#SERIAL_PORT = '/dev/ttyS1'

# This included file will work on all Atmel platforms (RF200, RF220, SS200, etc.) that are installed in a proto-board (SN171) or USB stick
SPY_FILE = "Atmel_blink_2.6.2.spy"

class SpyUploader:

    def __init__(self):

        self.debug_SpyUploader = True    # Enable/disable debug messages

        self.progInProgress = False      # True WHILE a file upload is in progress

        self.WAIT_TIME = 100             # Time to wait for a remote device to respond to upload requests
        self.respTimer = 0               # Timer used to tell if commands are taking too long (during the programming process)
        self.stopTimer = False           # Flag that keeps the timer tick from rescheduling itself
        self.MAX_PROG_RETRIES = 3        # The system will attempt to retry the programming process this number of times
        self.progRetryNum = 0            # Track the number of retries
        self.retryFlag = False

        # The following get filled in on-the-fly
        
        # Filled in by beginUpload()
        self.fileName = ''               # The file to be transferred
        self.targetAddr = None           # SNAP Address of the remote device to update

        # Filled in by assign_SnapCom()
        self.snapCom = None

        # Filled in by assign_Callback()
        self.ourCallback = None

    ##-------------------------------------------------------------------------------------------
    ##
    ##  Assign an instance of SNAPconnect for the uploader to use.
    ##
    ##  This must be done after the creation of the class itself in order to properly
    ##  expose uploader functions to the network. The uploader will not operate if it
    ##  does not know about a proper SNAPconnect.
    ##
    ##  Parameters: snapComInstance - SNAPconnect object
    ##
    ##-------------------------------------------------------------------------------------------
    def assign_SnapCom(self, snapComInstance):
        """Assign the SNAPconnect instance to use for this SNAPpy Script uploader"""
        self.snapConn = snapComInstance

    ##-------------------------------------------------------------------------------------------
    ##
    ## Tell this object who to report the outcome to
    ##
    ##
    ##  Parameters: callbackInstance - any object implementing the spyUploadFinished() method
    ##
    ##-------------------------------------------------------------------------------------------
    def assign_Callback(self, callbackInstance):
        """Assign the callback instance to use for this SNAPpy Script uploader"""
        self.ourCallback = callbackInstance

    ##-------------------------------------------------------------------------------------------
    ##
    ## Function to begin the upload process
    ## - Requires a SNAPconnect instance to be in place
    ## - Requires a callback instance to be in place
    ##
    ##
    ##  Parameters:
    ##      destAddr - the SNAP Address of the SNAP Node to be uploaded with the script (SPY file)
    ##      filename - the exact file name (including path if needed) of the SPY file to be uploaded
    ##
    ##-------------------------------------------------------------------------------------------
    def beginUpload(self, destAddr, filename):
        """Function that kicks off the script upload process"""
        if self.snapConn == None:
            self.completeProcess(NO_INSTANCE)
            return

        self.targetAddr = destAddr
        self.filename = filename
        self.startupload()

    #*****************************************************************************
    def startupload(self):
        """Called internally for every upload attempt. You should be calling beginUpload()"""
        f = None
        uploadImage = None
        try:
            f = open(self.filename, 'rb')
            uploadImage = ScriptsManager.getSnappyStringFromExport(f.read())
        except:
            errStr = "RF Script Upload: Upload RF Script Failed at file read"
            self.debugPrint(errStr)
            self.completeProcess(NO_SUCH_FILE)
        finally:
            if f is not None:
                f.close()

        # Kickoff upload
        if uploadImage:
            if self.retryFlag == False:
                self.snapConn.scheduler.schedule(1.0, self.timerTick) # Setup the timer tick
            self.resetRespTimer()

            upload = self.snapConn.spy_upload_mgr.startUpload(self.targetAddr, uploadImage)
            upload.registerFinishedCallback(self.app_upload_hook)
            self.progInProgress = True
        return

    #*****************************************************************************
    def app_upload_hook(self, snappy_upload_obj, result):
        if result == SnappyUploader.SNAPPY_PROGRESS_COMPLETE:
            errStr = "RF Script Upload: Successfully uploaded the script"
            self.debugPrint(errStr)
        elif result == snap.SNAPPY_PROGRESS_TIMEOUT:
            errStr = "RF Script Upload: There was a problem uploading the application, some type of timeout"
            self.debugPrint(errStr)
        else:
            errStr = "RF Script Upload: There was a problem uploading the application"
            self.debugPrint(errStr)

        self.completeProcess(result)


    #*****************************************************************************
    def completeProcess(self, errCode):
        """
        Process has completed (either in failure or success)
        Reset for the next time
        """

        # Keep the next timer tick from rescheduling itself
        self.stopTimer = True
        self.progInProgress = False
        self.retryFlag = False
        self.respTimer = 0                  # Timer used to tell if commands are taking too long
        self.progRetryNum = 0
        self.targetAddr = None              # Clear out the SNAP Address of the remote device
        self.fileName = ''                  # Clear out the filename of the remote device

        self.ourCallback.finishedSpyUpgrade(errCode)

#
# Timer related code
#-----------------------------------------------------------------------
    #*****************************************************************************
    def timerTick(self):
        """Function called by timing mechanism on a regular basis
        Keeps track of when retries are needed"""

        if self.progInProgress == True:
            self.respTimer -= 1;
            self.debugPrint("timerTick %d" % (self.respTimer)) # TEMP DEBUG
            if self.respTimer == 0:
                self.respTimer = self.WAIT_TIME
                self.progRetryNum += 1
                if self.progRetryNum < self.MAX_PROG_RETRIES:
                    self.startupload()
                else:
                    # Too many retries - End things here
                    self.debugPrint( "RF Script Upload: Process halted due to excessive retries - %s \n" % (self.convertAddr(self.targetAddr)) )
                    self.completeProcess(TOO_MANY_RETRIES)
                    return False # Do not reschedule the tick

        if self.stopTimer: # The way to stop the timer if necessary
            self.stopTimer = False
            return False

        return True #Reschedule yourself

    #*****************************************************************************
    def resetRespTimer(self):
        self.respTimer = self.WAIT_TIME

#
# Helpers
#-----------------------------------------------------------------------
    #*****************************************************************************
    def debugPrint(self,data):
        """Conditionally print debug message"""
        if self.debug_SpyUploader:
            print str(data)

    def enableDebug(self):
        """Dynamically enable debug print messages"""
        self.debug_SpyUploader = True

    def disableDebug(self):
        """Dynamically disable debug print messages"""
        self.debug_SpyUploader = False

    #*****************************************************************************
    def convertAddr(self, addr):
        """Converts binary address string to hex-ASCII address string"""
        return binascii.hexlify(addr)

#
# Test code, also demonstrates usage of the SpyUploader class
#
if __name__ == "__main__":

    #
    # There are 3 integration points to this module
    # 1) You have to provide a "callback object" so that the module can
    #    tell you how the upload turned out.
    # 2) You must "pass-through" any tellVmStat() messages to the
    #    spy_upload_mgr (SPY Upload Manager) in SNAPconnect.
    # 3) You must forward a "reboot received" RPC call to spy_upload_mgr
    #
    
    #
    # 1) Provide callback object
    # Provide an object implementing the finishedSpyUpgrade() method
    # This should print a status message, update a graphical GUI, etc.
    # (It can even do NOTHING, if your intent is for uploads to take
    # place silently, in the background).
    # Parameter errCode will be one of:
    # NO_INSTANCE - You have tried to initiate a SPY Upload but you have
    #               not yet provided a SNAP Connect instance to perform
    #               the underlying communications.
    # NO_SUCH_FILE - Did you specify the correct file name and PATH?
    # TOO_MANY_RETRIES - Maximum number of upload attempts exceeded
    # snap.SNAPPY_PROGRESS_COMPLETE - Success!
    #
    class ExampleCallback:
        def finishedSpyUpgrade(self, errCode):
            """Report the final result to the user"""
            print "errCode=" + str(errCode) # How to format and print the result is up to you
    
    #
    # 2) Pass along any tellVmStat() responses
    # The module above does not provide a tellVmStat() handler directly because you
    # may want to take additional actions based on tellVmStat() responses.
    #
    def tellVmStat(arg, val):
        """Handle received tellVmStat() RPC calls"""
        comm.spy_upload_mgr.onTellVmStat(comm.rpc_source_addr(), arg, val)
        
        # Your program might take additional actions here...

    #
    # 3) Pass along any "reboot received" responses
    #
    def su_recvd_reboot(dummy):
        comm.spy_upload_mgr.on_recvd_reboot(comm.rpc_source_addr())

        # Your program might take additional actions here...
        
    #
    # Just a quick example of sending a hardcoded file to a hardcoded node
    # For an example of command line processing, refer to simpleSnapRouter.py
    #
    def main():
        global comm
        # The functions required for this demo. Your program will likely add additional functions
        funcdir = { 'tellVmStat' : tellVmStat,
                    'su_recvd_reboot' : su_recvd_reboot }

        # Create a SNAPconnect object to do communications (comm) for us
        comm = snap.Snap(funcs=funcdir)
        
        # Note the hardcoded COM1 usage. See other examples for other connection possibilities.
        # Here the focus is on the script upload process, not all the different ways SNAPconnect
        # can communicate with other nodes.
        comm.open_serial(SERIAL_TYPE, SERIAL_PORT)
        
        # Make a SpyUploader object
        uploader = SpyUploader()
        # Tell it who to use for communications
        uploader.assign_SnapCom(comm)

        # Here we need to make a callback object. Your program may already have a GUI (etc.)
        # that implementes the required finishedSpyUpgrade() method
        callbackInstance = ExampleCallback()
        # Tell the SpyUploader who to report back to
        uploader.assign_Callback(callbackInstance)        
        
        # Initiate an upload. Notice that the node and SPY file are defined at the top of this file
        uploader.beginUpload(BRIDGE_NODE, SPY_FILE)

        # For this example, only keep communications open until the transfer has been
        # completed, or the number of transfer attempts have been exhausted.
        # If we changed it to a "while True:" loop, then the SNAPconnect instance
        # would continue to run and route traffic even after the transfer was done.
        while uploader.progInProgress:
            comm.poll()
        
    # Standard Python logging. Here you might redirect the output to a file,
    # change the logging level (verbosity), etc.
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Run the example
    main()

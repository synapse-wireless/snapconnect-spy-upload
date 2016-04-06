[![](https://cloud.githubusercontent.com/assets/1317406/12406044/32cd9916-be0f-11e5-9b18-1547f284f878.png)](http://www.synapse-wireless.com/)

# SNAPconnect Example - SNAPconnect SPY File Uploader

This example application allows you to upload a compiled SNAPpy "SPY" file to a node using SNAPconnect.

# Background

Many networks use Portal to commission nodes, upload new SNAPpy scripts into them, etc.

Portal can upload either source (.py) or binary (.spy) files into embedded SNAP Nodes.
Portal can also export ".py" files into ".spy" files.

SNAPconnect applications can also upload SPY files into SNAP Nodes, but doing so requires
a handful of function calls. The SpyUploader class encapsulates some of the details, plus
adds a high-level retry mechanism (it will attempt the entire script upload process up
to three times).

## Running This Example

In order to run this example, you will need to make sure that SNAPconnect is installed on your system:

```bash
pip install --extra-index-url https://update.synapse-wireless.com/pypi snapconnect
```
    
You will also need to make a few modifications to SpyUploader.py to configure your bridge address,
serial type, and serial port. Some of the values that you can change include:

```python
BRIDGE_NODE = "\x4B\x42\x34"
SERIAL_TYPE = snap.SERIAL_TYPE_RS232
SERIAL_PORT = 0 # COM1
```

Once you have configured the example, simply run:

```
$ python SpyUploader.py
2016-04-06 15:52:05 DEBUG: Querying for remote addr
2016-04-06 15:52:05 DEBUG: send: 0001.callback('7XombsadNuFWVJEP', 'getInfo', 3)
2016-04-06 15:52:05 DEBUG: Directing multi-cast to RS-232 Interface: 30
...
2016-04-06 15:52:08 DEBUG: send: 610dec.callback('su_recvd_reboot', 'reboot')
2016-04-06 15:52:08 DEBUG: rpc: 610dec.su_recvd_reboot(None,)
RF Script Upload: Successfully uploaded the script
errCode=3
```


## Using SpyUploader in Your Own Application

You can use SpyUploader in your own SNAPconnect application by importing and setting up a SpyUploader instance:
    
1.  Import SpyUploader into your application:

    ```python
    import SpyUploader
    ```
    
1.  Create an instance of the SpyUploader object:

    ```python
    uploader = SpyUploader()
    ```

1.  Tell the SpyUploader which SNAPconnect instance to use:

    ```python
    uploader.assign_SnapCom(xxx)
    ```

1.  Tell the SpyUploader which callback function to invoke at the end of the upload process:

    ```python
    uploader.assign_Callback(yyy)
    ```

1.  Initiate the actual script upload:

    ```python
    uploader.beginUpload(nodeAddress, filename)
    ```

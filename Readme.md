# Oracle Data Visualization Web

This repository implements Oracle Data (including block Price feed and latency) and AAVE collateral risk visualization Web based application.

## Setup
### 1. SSH to Archive Node
Before using ssh to connect, please get in touch with lzhou1110@gmail.com and send your computer ssh public key to store in the archive node of the server
```
ssh username@watson.lowland.fun -NL 19545:192.168.0.70:19545
```
This ssh command will build the connection at port 19545 (i.e., http://localhost:19545). 
To change the port, please modify the above ssh command and also the code below in files: oracleWeb/datastorage/views.py and oracleWeb/debtmonitor/views.py
```
archive_node = "http://localhost:19545"
```
### 2. Connection to MySQL
a. Before connecting to the local MySQL server, we need to install it first. Please refer to https://docs.djangoproject.com/en/4.1/ref/databases/#mysql-notes

b. Change the setting in oracleWeb/oracleWeb/settings.py to your own setting (i.e., change database NAME, User, PASSOWRD, HOST and PORT)
```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'oracle_web',
        'User': 'root',
        'PASSWORD': '123456789',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```


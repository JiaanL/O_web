# Oracle Data Visualization Web

This repository implements Oracle Data (including block Price feed and latency) and AAVE collateral risk visualization Web based application.

## 1.Setup

### 1.1. Prepare Envionment
Python version 3.8.12 <br />
Django (4, 0, 6, 'final', 0) <br />
Pandas 1.4.3 <br />
Numpy 1.22.3 <br />
Statsmodels 0.13.2 <br />
Pyecharts 1.9.1 <br />
pandarallel 1.6.1 <br />
ctypes 1.1.0 <br />

Go version go1.18.2 darwin/amd64 <br />
GoEthereum 1.10.17-stable <br />

MySQL  Ver 8.0.30 for macos12.4 on x86_64 (Homebrew)

R version 4.0.2 (2020-06-22) <br />

Node.js v18.7.0 <br />
Bootstrap 5.2.0 <br />

### 1.2. SSH to Archive Node
Before using ssh to connect, please get in touch with lzhou1110@gmail.com and send your computer ssh public key to store in the archive node of the server
```
ssh username@watson.lowland.fun -NL 19545:192.168.0.70:19545
```
This ssh command will build the connection at port 19545 (i.e., http://localhost:19545). 
To change the port, please modify the above ssh command and also the code below in files: oracleWeb/datastorage/views.py and oracleWeb/debtmonitor/views.py
```
archive_node = "http://localhost:19545"
```
### 1.3. Connection to MySQL
a. Before connecting to the local MySQL server, we need to install MySQL first. Please refer to https://docs.djangoproject.com/en/4.1/ref/databases/#mysql-notes

b. Download and restore the MySQL Dump to locol MySQL Server from https://1drv.ms/u/s!AuU01Mwe0FZKjqA6JhSV8KrN0EtW3Q?e=zvsS6v (oracle_web3.sql is the latest data)
```
mysql -u [user] -p [database_name] < [filename].sql
```

c. Change the setting in oracleWeb/oracleWeb/settings.py to your own setting (i.e., change database NAME, User, PASSOWRD, HOST and PORT)
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

### 1.4. Start the Web application
Django Command
```
python manage.py runserver [port] # run server in local host
python manage.py shell # open a terminal
python manage.py makemigrations datastorage # prepare the update of database
python manage.py migrate # execute the update of database
python manage.py shell_plus --notebook # open a jupyter server
```

### 1.5. Use a borwser to 
After starting the "runserver", we will get the following message in the 
terminal:
```
> python manage.py runserver


Django version 4.0.6, using settings 'oracleWeb.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```
Direcly copy the link to the browser and we will get:
![Alt text](images/Browser.png?raw=true "Browser")


## 2. Functions

### 2.1. Data Manually Update
There are two way to udpate price data, the first one is automatically update all existed data to the latest block. The second one is manually select the range that user want to update:
![Alt text](images/DataUpdateDetails.png?raw=true "Data Update")
example of clicked auto update:
![Alt text](images/AutoUpdateData.png?raw=true "Data Auto Update")
example of cliced manual update:
![Alt text](images/ManualUpdateData.png?raw=true "Data Manual Update")

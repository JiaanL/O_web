# Oracle Data Visualization Web

This repository implements Oracle Data (including block Price feed and latency) and AAVE collateral risk visualization Web based application.


### Table of Contents
**[1. Setup](#1-setup)**<br>
**[2. Functions of Manual Plot Section](#2-functions-of-manual-plot-section)**<br>
**[3. Functions of Auto Plot Section](#3-functions-of-auto-plot-section)**<br>
**[4. Setup without loading sql](#4-setup-without-loading-sql)**<br>
**[5. Example of Plot](#5-example-of-plot)**<br>

## 1. Setup

please cd into ./oracleWeb first.

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

(Some packages above have been downloaded and saved in this repository; however, there isn't any change on them. It only aims to run the code faster and automatically save by using "go", "node", and "npm".)

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
Directly copy the link to the browser, and we will get:
![Alt text](images/Browser.png?raw=true "Browser")


## 2. Functions of Manual Plot Section

### 2.1. Price Data Update
There are two way to udpate price data, the first one is automatically update all existed data to the latest block. The second one is manually select the range that user want to update:
![Alt text](images/DataUpdateDetails.png?raw=true "Data Update")
example of clicked auto update:
![Alt text](images/AutoUpdateData.png?raw=true "Data Auto Update")
example of clicked manual update:
![Alt text](images/ManualUpdateData.png?raw=true "Data Manual Update")

### 2.2. Block Price Data Update
Before generating the price plot, we need to unify the granularity of the price data. For example, we need to aggregate all prices in a block to one. For this part, we do not need to select the data range manually; instead, the web application will automatically use all data in the database to generate the block price.
![Alt text](images/GranularityUpdate.png?raw=true "Price Granularity Update")

### 2.3. Block Price Plot
After crawling and preprocessing the data, we could start to plot the price from different Oracle. Below is the panel for choosing which data to plot.
![Alt text](images/PlotPrice.png?raw=true "Price Plot")

### 2.4. Latency Data Calculation and Plot
Similar to 2.2. and 2.3., the latency also has two-step. We need to calculate the data first, then select the target pair of data with range to plot.
![Alt text](images/PlotLatency.png?raw=true "Latency Plot")

### 2.5. AAVE Liquidation Call Prediction
We also need to crawl the data for Health Factor Historical Plot and Liquidation Risk Analysis Visualization (probability of HF drop below 1). Below is the input example for plot generating.
![Alt text](images/DebtMonitor.png?raw=true "Health Factor")

## 3. Functions of Auto Plot Section
### 3.1. Switch to auto plot
On the top-right corner of the webpage, there is a link to the page which can fully update the plot.
![Alt text](images/SwitchToAuto.png?raw=true "Health Factor")
### 3.2. Auto plot all
On this page, there is no need to click multiple bottoms to update the different databases. Instead, with only one click after inputting the information of your address, it will automatically start all database updating and also update the plot. All the plot generation is a "while True loop", which will generate the next one after the previous one is made.
![Alt text](images/AutoPlot.png?raw=true "Health Factor")


## 4. Setup without loading sql
1. open the link
```
http://127.0.0.1:8000/datastorage/initialize
```

2. after seeing the "done", go to
```
http://127.0.0.1:8000/datastorage/update_data
```
Input the data that you want to include in the database.

Currently, we only support eth against usd, usdt, usdc, dai for data in uniswapv2, uniswapv3 and chainlink.
![Alt text](images/UpdateDataStorage.png?raw=true "Health Factor")
All data need to be in lower case.

3. Back to the main web to start auto update


## 5. Example of Plot
Please refer to the report in section 8
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  7 12:18:30 2024
adding text at 12:43 EST
@author: prave
"""

from ib_insync import *
import nest_asyncio
import datetime
import pandas as pd
from discord import SyncWebhook
import requests
from datetime import timedelta
import json, time
nest_asyncio.apply()



## reading text file 
cred_file = pd.read_csv('next_gen_v2_cred_aws.txt', header=None)
custId = cred_file.iloc[0][0].split('=')[1].strip()
api_url = cred_file.iloc[1][0].split('=')[1].strip()
authCode = cred_file.iloc[2][0].split('=')[1].strip()
portNum = cred_file.iloc[3][0].split('=')[1].strip()
# qty = cred_file.iloc[4][0].split('=')[1].strip()
contractName = cred_file.iloc[5][0].split('=')[1].strip()
post_url = cred_file.iloc[6][0].split('=')[1].strip()
# custId = "TEST1"


# TTB channel
token = authCode

headers2 = {
    'Authorization': token
}

def extract_datetime(text):
    # Regular expression pattern to match ISO 8601 datetime format
    pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
    matches = re.findall(pattern, text)
    return matches

def retrieve_messages(token,api_url):
    API_URL = api_url

    # Headers including the authorization token
    token = token

    headers2 = {
                    'Authorization': token
                }

    response = requests.get(API_URL, headers = headers2)
    
    if response.status_code == 200:
        list1 = []
        for x in response.json():
            if "Time:" in x['Message']:
                list1.append(x['Message'])
                
        df = pd.DataFrame(list1)
        df['time'] = df[0].apply(lambda x:x.split("//")[0].split("Time:")[1].strip())
        df['message'] = df[0].apply(lambda x:x.split("//")[1])
        
        df = df.sort_values(by = 'time', ascending = False)
        last_message= df[0].iloc[0]
        
        return last_message
    else:
        print('Failed to fetch data. Status code:', response.status_code)

    return df


# Connect to IB TWS or Gateway
# util.startLoop()
clientId = 1
def connect_with_retry(host, port, max_retries, clientId):
    
    connected = False
    ib = IB()

    while not connected and clientId <= max_retries:
        try:
            print(f'Trying to connect with clientId = {clientId}')
            ib.connect(host, port, clientId=clientId)
            time.sleep(2)
            ib.accountSummary()
            connected = True
            
            account_summary = ib.accountSummary()
            available_funds = None
            TotalCashValue = None
            for item in account_summary:
                if item.tag == 'ExcessLiquidity':
                    available_funds = item.value
                    
                if item.tag == 'TotalCashValue':
                    TotalCashValue  = item.value 
                    
            
                    
            print(f'Successfully connected with clientId = {clientId}, available funds = {available_funds}, total cash value = {TotalCashValue}')
        except Exception as e:
            print(type(e))
            e1 = e
            print(f'Connection failed with clientId = {clientId}. Retrying...')
            if "name 'host' is not defined" in str(e1):
                # send_discord_message('Login to the IB Account.')
                break
            clientId += 1
            time.sleep(1)  # Sleep for a short while before retrying

    if not connected:
        raise ConnectionError(f'Unable to connect to IB TWS/Gateway after {max_retries} attempts.')

    return ib, clientId, TotalCashValue


ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 10, clientId)


keyname = custId# + "@" + timenow 

def postClientSummTable(json_data,post_url):
    headers_json = {
        "Content-Type" : "application/json"}
    
    api_url_client = post_url
    response = requests.post(api_url_client, data = json_data, headers = headers_json)
    while response.status_code != 200:
        print(response.status_code)
        time.sleep(2)
    
    

pos_df = pd.DataFrame(ib.reqPositions())

def tradeStatusCheck(pos_df):
    tradestatus = ""
    if len(pos_df) > 0:
        
        positions = pos_df[pos_df['position'] != 0]
        print('positions is ')
        print(positions)
        for pos in range(0,len(positions)):
            position = positions.iloc[pos]
            if position.contract.symbol == contractName:
                # Close the position
                if position.position > 0:
                    tradestatus= "Long"
                elif position.position < 0:
                    tradestatus = "Short"
                    
        if len(positions) == 0:
            tradestatus = "NoPosition"
    else:
        tradestatus = "NoPosition"
        
    print('tradestatus is ',tradestatus)
    return tradestatus

tradestatus = tradeStatusCheck(pos_df)
    
timenow = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
data = {
        "clientId":keyname,
        "TradeStatus":tradestatus,
        "AccountSize":str(TotalCashValue),
        "TradeTime":timenow
        }
json_data = json.dumps(data)

postClientSummTable(json_data,post_url)


## getting account balance 
account_summary = ib.accountSummary()
available_funds = None
for item in account_summary:
    if item.tag == 'ExcessLiquidity':
        available_funds = item.value
        break
    
available_funds = float(available_funds)
# textdiscord = "Connection established with ClientID"+str(clientId)+" with $" + str(available_funds)
# send_discord_message(textdiscord)
# estimate position size for this account 


# getting 
cnt = Future(symbol = 'ES', lastTradeDateOrContractMonth="", exchange="CME")
details = ib.reqContractDetails(cnt)
total_details = len(details)
crntexp = []
for i in range(total_details):
    crntexp.append(details[i].contract.lastTradeDateOrContractMonth)

dates_datetime = [datetime.datetime.strptime(date, '%Y%m%d') for date in crntexp]
latest_date_2 = pd.to_datetime(dates_datetime).sort_values()[0].strftime('%Y-%m-%d')
latest_date = pd.to_datetime(dates_datetime).sort_values()[0].strftime('%Y%m%d')
latest_exp_month = latest_date[:-2]
    
specific_date = datetime.datetime.strptime(latest_date, '%Y%m%d')

# Get the current date
current_date = datetime.datetime.now()
difference = specific_date - current_date
days_difference = difference.days

if days_difference < 7:     
    nextexp = specific_date + timedelta(days = 90)
    latest_exp_month = nextexp.strftime('%Y%m')
    
    
# Define contract details for ES (E-mini S&P 500)
contract = Future(symbol = contractName, lastTradeDateOrContractMonth = latest_exp_month, exchange = "CME")
 
## position sizing
qtyOverride = 1


qty = None 
import math 
if contractName == "MES":
    qty = math.floor(available_funds/2000)
elif contractName == "ES":
    qty = math.floor(available_funds/20000)
    
if qty > 200 and qtyOverride == 1:
    qty = 3

# if qty == 0:
#     send_discord_message('0 QTY, fix the issue!')
# else:
#     send_discord_message('Qty detected by logic: '+str(qty))

    
def bktOrderFunc(side,qty,limit_price,take_profit_price,stop_loss_price):
    
    limit_price = limit_price
    take_profit_price = take_profit_price  # take profit price
    stop_loss_price = stop_loss_price  # stop loss price

    # Create bracket order
    
    ######### code block for bracket orders..
    # Create a list to hold all bracket orders
    bracket_order = ib.bracketOrder(
            action = 'BUY' if side == 'BUY' else "SELL",
            quantity =  qty,
            limitPrice = limit_price, 
            takeProfitPrice = take_profit_price,
            stopLossPrice =  stop_loss_price)

    for o in bracket_order:
        o.outsideRth = True
        o.tif = "GTC"
        # o.transmit = True
        
    # Iterate over each order in the bracket and place it
    for o in bracket_order:
         ib.placeOrder(contract, o)

# Function to cancel all bracket orders and close position
def cancel_bracket_orders_and_close_position():
    
    
    ib.reqGlobalCancel()
    
    # Check open positions
    pos_df = pd.DataFrame(ib.reqPositions())
    if len(pos_df) > 0:
        positions = pos_df[pos_df['position'] != 0]
        # positions = ib.positions()
        print('got positions when contractname is ',contractName)
        try:
            print('the dataframe is :')
            print(positions)
            for pos in range(0,len(positions)):
                position = positions.iloc[pos]
                print('position is ',position)
                if position.contract.symbol == contractName:
                    # Close the position
                    if position.position > 0: # currently long contract is open 
                        order = MarketOrder('SELL', position.position)
                        ib.placeOrder(contract, order)
                    elif position.position < 0: # currently in short 
                        order = MarketOrder('BUY', abs(position.position))
                        ib.placeOrder(contract, order)
                        
                    break ## this is to avoid issue when multiple rows are returned in position for some reason by IB when we just have one
        except Exception as e:
            print(e)
                    
    
        ib.sleep(1)
    

import pytz 
newYorkTz = pytz.timezone("US/Eastern")
UtcTz = pytz.timezone("UTC")
timeInNewYork = datetime.datetime.now(newYorkTz)
#### core logic below 
# initialize discord messages

crntmsg = '1'
prevmsg = '2'

import datetime
from datetime import timedelta
exitTime = datetime.datetime.now() + timedelta(minutes=29, seconds=50)
print('exitTime is ', exitTime)
while crntmsg != prevmsg:
    try:
        crnthour = timeInNewYork.hour
        prevhour = crnthour
        crntmin = timeInNewYork.minute
        prevmin = crntmin
        msg = retrieve_messages(token,api_url)
        crntmsg = msg
        prevmsg = crntmsg
        print(crntmsg)
        
    except:
        time.sleep(.5)
 

def round_nearest_qtr(number):
    base = 0.25
    return round(base * round(number / base), 2)


breakcode = 0 
checkPosition = 0 # this is to check if any orders exist without brackets 
while True:#datetime.datetime.now() < exitTime:
    if breakcode == 1:
        break
    timeInNewYork = datetime.datetime.now(newYorkTz)
    
    
    if checkPosition == 1 and datetime.datetime.now().second > 45:
        checkPosition = 0 
        
    if datetime.datetime.now().minute % 2 == 0 and datetime.datetime.now().second > 30 and datetime.datetime.now().second < 35 and checkPosition == 0: 
        
        ib.disconnect()
        time.sleep(1)
        ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 100, clientId)
        
        checkPosition = 1
        pos_df = pd.DataFrame(ib.reqPositions())
        
        posdf = pos_df#positions
        
        account_summary = ib.accountSummary()
        available_funds = None
        for item in account_summary:
            if item.tag == 'ExcessLiquidity':
                available_funds = item.value
                break
            
        available_funds = float(available_funds)
        qty = None 
        import math 
        if contractName == "MES":
            qty = math.floor(available_funds/2000)
        elif contractName == "ES":
            qty = math.floor(available_funds/20000)
            
        if qty > 200 and qtyOverride == 1:
            qty = 3
        
        time.sleep(1.2)
        print('check position logic.')
        print(posdf)
        if len(posdf) > 0:
            positions = pos_df[pos_df['position'] != 0]
            for pos in range(0,len(positions)):
                if positions['position'].iloc[pos] > 0: # in long position 
                    openorderdf = ib.reqAllOpenOrders()
                    time.sleep(1)
                    print('in long')
                    print(openorderdf)
                    
                    if len(openorderdf) == 2:
                        a = 1
                    else:
                        # send_discord_message("NAKED LONG POSITION!!! PLEASE CHECK and RESOLVE NOW!!!!")
                        cancel_bracket_orders_and_close_position()
                elif positions['position'].iloc[pos] < 0: # in short position
                    openorderdf = ib.reqAllOpenOrders()
                    
                    time.sleep(1)
                    print('in short')
                    print(openorderdf)
                    
                    if len(openorderdf) == 2:
                        a = 1
                    else:
                        # send_discord_message("NAKED SHORT POSITION!!! PLEASE CHECK and RESOLVE NOW!!!!")
                        cancel_bracket_orders_and_close_position()
                        
        elif len(posdf) == 0:
            orders = ib.reqAllOpenOrders() 
            ib.sleep(.5)
            if len(orders) >= 2: ## code found position is 0 but open orders
                cancel_bracket_orders_and_close_position()
                # send_discord_message("Close Bracket Orders since no open position found!")
            

    try: # running the whole code in try except loop to check for errors
        msg = retrieve_messages(token,api_url)
        crntmsg = msg
        
        # trying the print of all open positions 
        # positions = ib.positions()
        # for position in positions:
        #     print(position)
        incMsg = 0 
        if crntmsg!=prevmsg: 
            forcust = crntmsg.split('for:')[-1].split(' ')[0] 
            if forcust == "all" or custId in forcust: #trade is intended for all or particular user
                incMsg += 1 
                print('crntmsg is ',crntmsg)
                print(incMsg)
                if 'Enter Long' in crntmsg or 'Close entry(s) order Short' in crntmsg:
                    print('in enter long found in crntmsg')
                    cancel_bracket_orders_and_close_position()
                    time.sleep(.5)
                    print('after initial closes done')
                    # enter long trade - bracket order
                    x22 = crntmsg.split("@")
                    limit_price = round_nearest_qtr(float(x22[1].split(' ')[0]))
                    stop_loss_price = round_nearest_qtr(float(x22[-1]))
                    side = "BUY"
                    if stop_loss_price > limit_price:
                        # send_discord_message("Stop loss price is adjusted")
                        stop_loss_price = limit_price - 5 
                    take_profit_price = limit_price + 100
                    bktOrderFunc(side,qty,limit_price,take_profit_price,stop_loss_price)
                    
                    time.sleep(1)
                    ib.disconnect()
                    time.sleep(1)
                    # send_discord_message('code alive again, running sanity checks.')
                    ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 100, clientId)
                    # send_discord_message('Long order placed')
                    time.sleep(1)
                    posdf = pd.DataFrame(ib.reqPositions())
                    posdf = posdf[posdf['position'] != 0]
                    print(len(posdf))
                    account_summary = ib.accountSummary()
                    available_funds = None
                    for item in account_summary:
                        if item.tag == 'ExcessLiquidity':
                            available_funds = item.value
                            break
                        
                    timenow = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    tradestatus = tradeStatusCheck(posdf)
                    
                    data = {
                            "clientId":keyname,
                            "TradeStatus":tradestatus,
                            "AccountSize":str(TotalCashValue),
                            "TradeTime":timenow
                            }
                    json_data = json.dumps(data)
    
                    postClientSummTable(json_data,post_url)
                    
                    
                elif 'Exit Long' in crntmsg:
                    print('in exit long found in crntmsg')
                    cancel_bracket_orders_and_close_position()
                    
                    # send_discord_message('Long Exit')
                    ib.disconnect()
                    time.sleep(1)
                    # send_discord_message('code alive again, running sanity checks.')
                    ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 100, clientId)
                    
                    
                    posdf = pd.DataFrame(ib.reqPositions())
                    # posdf = posdf[posdf['position'] != 0]
                    time.sleep(2)
                    account_summary = ib.accountSummary()
                    available_funds = None
                    for item in account_summary:
                        if item.tag == 'ExcessLiquidity':
                            available_funds = item.value
                            break
                        
                    timenow = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    tradestatus = tradeStatusCheck(posdf)
                    
                    available_funds = float(available_funds)
                    
                    data = {
                            "clientId":keyname,
                            "TradeStatus":tradestatus,
                            "AccountSize":str(TotalCashValue),
                            "TradeTime":timenow
                            }
                    json_data = json.dumps(data)
    
                    postClientSummTable(json_data,post_url)
                        
                    qty = None 
                    import math 
                    if contractName == "MES":
                        qty = math.floor(available_funds/2000)
                    elif contractName == "ES":
                        qty = math.floor(available_funds/20000)
                        
                    if qty > 200 and qtyOverride == 1:
                        qty = 3
                    
                elif 'Enter Short' in crntmsg or 'Close entry(s) order Long' in crntmsg:
                    print('in enter short found in crntmsg')
                    cancel_bracket_orders_and_close_position()
                    time.sleep(.5)
                    print('after initial closes done')
                    x22 = crntmsg.split("@")
                    limit_price = round_nearest_qtr(float(x22[1].split(' ')[0]))
                    stop_loss_price = round_nearest_qtr(float(x22[-1]))
                    if stop_loss_price < limit_price:
                        # send_discord_message("SL adjusted")
                        stop_loss_price = limit_price + 5
                    side = "SELL"
                    take_profit_price = limit_price - 100
                    bktOrderFunc(side,qty,limit_price,take_profit_price,stop_loss_price)
                    
                    time.sleep(1)
                    ib.disconnect()
                    time.sleep(1)
                    ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 100, clientId)
                    # send_discord_message('Short order placed')
                    posdf = pd.DataFrame(ib.reqPositions())
                    posdf = posdf[posdf['position'] != 0]
                    
                    timenow = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    tradestatus = tradeStatusCheck(posdf)
                    
                    data = {
                            "clientId":keyname,
                            "TradeStatus":tradestatus,
                            "AccountSize":str(TotalCashValue),
                            "TradeTime":timenow
                            }
                    json_data = json.dumps(data)
    
                    postClientSummTable(json_data,post_url)
                    
                    account_summary = ib.accountSummary()
                    available_funds = None
                    for item in account_summary:
                        if item.tag == 'ExcessLiquidity':
                            available_funds = item.value
                            break
                        
                    available_funds = float(available_funds)
                    qty = None 
                    import math 
                    if contractName == "MES":
                        qty = math.floor(available_funds/2000)
                    elif contractName == "ES":
                        qty = math.floor(available_funds/20000)
                        
                    if qty > 200 and qtyOverride == 1:
                        qty = 3
                    
                elif 'Exit Short' in crntmsg:
                    print('in exit short found in crntmsg')
                    cancel_bracket_orders_and_close_position()
                    # send_discord_message('Short Exit')
                    ib.disconnect()
                    time.sleep(1)
                    # send_discord_message('code alive again, running sanity checks.')
                    ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 100, clientId)
                    
                    
                    posdf = pd.DataFrame(ib.reqPositions())
                    # posdf = posdf[posdf['position'] != 0]
                    
                    timenow = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    tradestatus = tradeStatusCheck(posdf)
                    
                    data = {
                            "clientId":keyname,
                            "TradeStatus":tradestatus,
                            "AccountSize":str(TotalCashValue),
                            "TradeTime":timenow
                            }
                    json_data = json.dumps(data)
    
                    postClientSummTable(json_data,post_url)
                    
                    account_summary = ib.accountSummary()
                    available_funds = None
                    for item in account_summary:
                        if item.tag == 'ExcessLiquidity':
                            available_funds = item.value
                            break
                        
                    available_funds = float(available_funds)
                    qty = None 
                    import math 
                    if contractName == "MES":
                        qty = math.floor(available_funds/2000)
                    elif contractName == "ES":
                        qty = math.floor(available_funds/20000)
                        
                    if qty > 200 and qtyOverride == 1:
                        qty = 3
                    
                    
                elif 'time left' in crntmsg:
                    timeleft = exitTime - datetime.datetime.now()
                    cstr = "code will end in "+str(timeleft.seconds)+ " seconds."
                    # send_discord_message(cstr)
                    time.sleep(.1)
                    
                elif 'close all' in crntmsg or 'Take Profit' in crntmsg or 'Stop Loss' in crntmsg:
                    cancel_bracket_orders_and_close_position()
                    
                    ib.disconnect()
                    time.sleep(1)
                    # send_discord_message('code alive again, running sanity checks.')
                    ib, clientId, TotalCashValue = connect_with_retry('127.0.0.1', portNum, 100, clientId)
                    
                    
                    posdf = pd.DataFrame(ib.reqPositions())
                    # posdf = posdf[posdf['position'] != 0]
                    
                    timenow = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    tradestatus = tradeStatusCheck(posdf)
                    
                    data = {
                            "clientId":keyname,
                            "TradeStatus":tradestatus,
                            "AccountSize":str(TotalCashValue),
                            "TradeTime":timenow
                            }
                    json_data = json.dumps(data)
    
                    postClientSummTable(json_data,post_url)
                    
                    account_summary = ib.accountSummary()
                    available_funds = None
                    for item in account_summary:
                        if item.tag == 'ExcessLiquidity':
                            available_funds = item.value
                            break
                        
                    available_funds = float(available_funds)
                    qty = None 
                    import math 
                    if contractName == "MES":
                        qty = math.floor(available_funds/2000)
                    elif contractName == "ES":
                        qty = math.floor(available_funds/20000)
                        
                    if qty > 200 and qtyOverride == 1:
                        qty = 3
                    
                prevmsg = crntmsg
            else:
                prevmsg = crntmsg
        print('read @',datetime.datetime.now())
        time.sleep(1.5)
        
    except Exception as e:
        df3 = pd.DataFrame([e])

#### end of core logic
# Disconnect from IB TWS or Gateway
ib.disconnect()

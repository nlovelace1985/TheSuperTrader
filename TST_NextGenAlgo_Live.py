from ib_insync import *
import nest_asyncio
import datetime
import pandas as pd
from discord import SyncWebhook
import requests
from datetime import timedelta
import json
import time

nest_asyncio.apply()

# Reading credentials from text file
cred_file = pd.read_csv('next_gen_v2_cred_text.txt', header=None)
webhook_link = cred_file.iloc[0][0].split('=')[1].strip()
discordChLink = cred_file.iloc[1][0].split('=')[1].strip()
authCode = cred_file.iloc[2][0].split('=')[1].strip()
portNum = cred_file.iloc[3][0].split('=')[1].strip()
contractName = cred_file.iloc[5][0].split('=')[1].strip()

# Setting up Discord webhook
webhook = SyncWebhook.from_url(webhook_link)
discordChannel = discordChLink
authorizationCode = authCode

def retrieve_messages():
    headers = {
        'authorization': authorizationCode
    }
    r = requests.get(discordChannel, headers=headers)
    jobj = json.loads(r.text)
    df = pd.DataFrame()
    for i, value in enumerate(jobj):
        if i > 2:
            break
        df = pd.concat([df, pd.DataFrame([value['content'], value['timestamp']]).transpose()])
    return df

def send_discord_message(message):
    webhook.send(message)

# Connect to IB TWS or Gateway
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
                    TotalCashValue = item.value
            print(f'Successfully connected with clientId = {clientId}, available funds = {available_funds}, total cash value = {TotalCashValue}')
        except Exception as e:
            print(type(e))
            e1 = e
            print(f'Connection failed with clientId = {clientId}. Retrying...')
            if "name 'host' is not defined" in str(e1):
                send_discord_message('Login to the IB Account.')
                break
            clientId += 1
            time.sleep(1)  # Sleep for a short while before retrying

    if not connected:
        raise ConnectionError(f'Unable to connect to IB TWS/Gateway after {max_retries} attempts.')

    return ib, clientId

ib, clientId = connect_with_retry('127.0.0.1', portNum, 10, clientId)

# Getting account balance
account_summary = ib.accountSummary()
available_funds = None
for item in account_summary:
    if item.tag == 'ExcessLiquidity':
        available_funds = item.value
        break
available_funds = float(available_funds)
textdiscord = "Connection established with ClientID" + str(clientId) + " with $" + str(available_funds)
send_discord_message(textdiscord)

# Estimate position size for this account
cnt = Future(symbol='ES', lastTradeDateOrContractMonth="", exchange="CME")
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
current_date = datetime.datetime.now()
difference = specific_date - current_date
days_difference = difference.days

if days_difference < 7:
    nextexp = specific_date + timedelta(days=90)
    latest_exp_month = nextexp.strftime('%Y%m')

contract = Future(symbol=contractName, lastTradeDateOrContractMonth=latest_exp_month, exchange="CME")

# Position sizing
qty = None
import math
if contractName == "MES":
    qty = math.floor(available_funds / 1500)
elif contractName == "ES":
    qty = math.floor(available_funds / 15000)

if qty == 0:
    send_discord_message('0 QTY, fix the issue!')
else:
    send_discord_message('Qty detected by logic: ' + str(qty))

def bktOrderFunc(side, qty, limit_price, take_profit_price, stop_loss_price):
    limit_price = limit_price
    take_profit_price = take_profit_price  # take profit price
    stop_loss_price = stop_loss_price  # stop loss price
    bracket_order = ib.bracketOrder(
        action='BUY' if side == 'BUY' else "SELL",
        quantity=qty,
        limitPrice=limit_price,
        takeProfitPrice=take_profit_price,
        stopLossPrice=stop_loss_price
    )
    for o in bracket_order:
        o.outsideRth = True
        o.tif = "GTC"
    for o in bracket_order:
        ib.placeOrder(contract, o)

def cancel_bracket_orders_and_close_position():
    retry_count = 3
    for _ in range(retry_count):
        try:
            open_orders = ib.openOrders()
            print(f'Open orders: {open_orders}')
            for order in open_orders:
                ib.cancelOrder(order)
                print('Cancel order:', order)
            positions = ib.positions()
            print(f'Positions: {positions}')
            for position in positions:
                print(position)
                if position.contract.symbol == contractName:
                    if position.position > 0:  # currently long contract is open
                        order = MarketOrder('SELL', position.position)
                        ib.placeOrder(contract, order)
                    elif position.position < 0:  # currently in short
                        order = MarketOrder('BUY', abs(position.position))
                        ib.placeOrder(contract, order)
            break  # Exit retry loop if successful
        except Exception as e:
            print(f'Error: {e}')
            time.sleep(1)  # Sleep for a short while before retrying

import pytz
newYorkTz = pytz.timezone("US/Eastern")
UtcTz = pytz.timezone("UTC")
timeInNewYork = datetime.datetime.now(newYorkTz)
crntmsg = '1'
prevmsg = '2'
exitTime = datetime.datetime.now() + timedelta(minutes=29, seconds=50)
print('exitTime is', exitTime)

while crntmsg != prevmsg:
    try:
        crnthour = timeInNewYork.hour
        prevhour = crnthour
        crntmin = timeInNewYork.minute
        prevmin = crntmin
        msg = retrieve_messages()
        crntmsg = msg.iloc[0][0]
        prevmsg = crntmsg
        print(crntmsg)
    except:
        time.sleep(.5)

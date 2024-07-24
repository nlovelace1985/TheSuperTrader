# -*- coding: utf-8 -*-
"""
Created on Thu Jul  7 12:18:30 2024
removed bracket check/close 4:38pm EST 07/24/2024
@author: nlove
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

# reading text file 
cred_file = pd.read_csv('next_gen_v2_cred_text.txt', header=None)
webhook_link = cred_file.iloc[0][0].split('=')[1].strip()
discordChLink = cred_file.iloc[1][0].split('=')[1].strip()
authCode = cred_file.iloc[2][0].split('=')[1].strip()
portNum = cred_file.iloc[3][0].split('=')[1].strip()
# qty = cred_file.iloc[4][0].split('=')[1].strip()
contractName = cred_file.iloc[5][0].split('=')[1].strip()

# read discord messages 
# TTB channel
webhook = SyncWebhook.from_url(webhook_link)
discordChannel = discordChLink
authorizationCode = authCode

def retrieve_messages():
    headers = {
        'authorization': authorizationCode
    }

    r = requests.get(discordChannel, headers=headers)

    jobj = json.loads(r.text)
    i = 0
    df = pd.DataFrame()
    for value in jobj:
        i += 1
        if i > 2:
            break
        df = pd.concat([df, pd.DataFrame([value['content'], value['timestamp']]).transpose()])

    return df

def send_discord_message(message):
    webhook.send(message)
    

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
                if item.tag == 'AvailableFunds':
                    available_funds = float(item.value)
                elif item.tag == 'TotalCashValue':
                    TotalCashValue = float(item.value)
            print(f'Connected with clientId = {clientId}')
            return ib, clientId
        except Exception as e:
            print(f'Failed to connect with clientId = {clientId}: {e}')
            clientId += 1
            time.sleep(1)
            
    raise Exception('Failed to connect after max retries')

ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

def cancel_bracket_orders_and_close_position():
    # for order in ib.openOrders():
    #     if order.orderType == 'BRACKET':
    #         ib.cancelOrder(order)
    
    # for position in ib.positions():
    #     ib.closePosition(position.contract)
    pass

def main():
    try:
        while True:
            messages = retrieve_messages()
            for index, row in messages.iterrows():
                crntmsg = row[0].lower()
                if 'bracket' in crntmsg:
                    # Check for bracket orders
                    # Uncomment the following line once the issue is fixed
                    # cancel_bracket_orders_and_close_position()
                    send_discord_message('Bracket order detected. Checking logic to ensure positions are not closed errently.')
                elif 'exit long' in crntmsg:
                    # Close any open positions if 'Exit Long' is detected
                    # cancel_bracket_orders_and_close_position()
                    send_discord_message('Long Exit, Code going to sleep for 10 seconds')
                    ib.disconnect()
                    time.sleep(10)
                    send_discord_message('Code alive again, running sanity checks.')
                    ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)
                    
                    posdf = ib.positions() 
                    time.sleep(2)
                    if len(posdf) > 0:
                        send_discord_message('Current position summary is :'+str(ib.positions()[2]))
                    else:
                        send_discord_message('Current position summary is :'+str(ib.positions()))
                    
                elif 'time left' in crntmsg:
                    timeleft = exitTime - datetime.datetime.now()
                    cstr = "code will end in "+str(timeleft.seconds)+ " seconds."
                    send_discord_message(cstr)
                    time.sleep(.1)
                    
                elif 'close all' in crntmsg:
                    # cancel_bracket_orders_and_close_position()
                    pass
                prevmsg = crntmsg
            print('read @',datetime.datetime.now())
            time.sleep(.25)
    except Exception as e:
        df3 = pd.DataFrame([e])

#### end of core logic
# Disconnect from IB TWS or Gateway
ib.disconnect()

if __name__ == "__main__":
    main()

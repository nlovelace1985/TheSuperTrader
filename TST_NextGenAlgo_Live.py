
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

# Reading text file 
cred_file = pd.read_csv('next_gen_v2_cred_text.txt', header=None)
webhook_link = cred_file.iloc[0][0].split('=')[1].strip()
discordChLink = cred_file.iloc[1][0].split('=')[1].strip()
authCode = cred_file.iloc[2][0].split('=')[1].strip()
portNum = cred_file.iloc[3][0].split('=')[1].strip()
contractName = cred_file.iloc[5][0].split('=')[1].strip()

# Read discord messages 
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
textdiscord = "Connection established with ClientID"+str(clientId)+" with $" + str(available_funds)
send_discord_message(textdiscord)

# Position sizing
qty = None 
import math 
if contractName == "MES":
    qty = math.floor(available_funds/1500)
elif contractName == "ES":
    qty = math.floor(available_funds/15000)

if qty == 0:
    send_discord_message('0 QTY, fix the issue!')
else:
    send_discord_message('Qty detected by logic: '+str(qty))

def bktOrderFunc(side, qty, limit_price, take_profit_price, stop_loss_price):
    limit_price = limit_price
    take_profit_price = take_profit_price  # take profit price
    stop_loss_price = stop_loss_price  # stop loss price

    take_profit_order = LimitOrder('SELL' if side == 'BUY' else "BUY", qty, take_profit_price, tif='GTC')
    stop_loss_order = StopOrder('SELL' if side == 'BUY' else "BUY", qty, stop_loss_price, tif='GTC')

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

# Improved function to cancel all bracket orders and close position
def cancel_bracket_orders_and_close_position():
    print("Starting the process to cancel bracket orders and close position...")

    open_orders = ib.openOrders()
    bracket_order_ids = set()

    # Identify bracket orders by checking for orders with the same parentId
    for order in open_orders:
        if order.orderType in ['LMT', 'STP'] and order.parentId != 0:
            bracket_order_ids.add(order.parentId)
    
    if not bracket_order_ids:
        print("No bracket orders found to cancel.")
        return
    
    print(f"Identified bracket order IDs: {bracket_order_ids}")

    for parentId in bracket_order_ids:
        for order in open_orders:
            if order.parentId == parentId:
                print(f"Cancelling order ID: {order.orderId} of type {order.orderType}")
                ib.cancelOrder(order)
    
    time.sleep(2)

    for parentId in bracket_order_ids:
        for order in ib.openOrders():
            if order.parentId == parentId:
                print(f"Order ID: {order.orderId} of type {order.orderType} still open after cancellation attempt.")
                return
    
    positions = ib.positions()
    for position in positions:
        if position.contract.symbol == contract.symbol:
            action = 'SELL' if position.position > 0 else 'BUY'
            qty = abs(position.position)
            market_order = MarketOrder(action, qty)
            print(f"Placing market order to close position: {action} {qty} {contract.symbol}")
            ib.placeOrder(contract, market_order)
    
    print("Bracket orders cancelled and position closed successfully.")

# Example usage of the function
cancel_bracket_orders_and_close_position()

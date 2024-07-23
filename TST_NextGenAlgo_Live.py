# -*- coding: utf-8 -*-
"""
Created on Thu Jul  7 12:18:30 2024
adding text at 12:43 EST
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

# Read credentials from file
cred_file = pd.read_csv('next_gen_v2_cred_text.txt', header=None)
webhook_link = cred_file.iloc[0][0].split('=')[1].strip()
discordChLink = cred_file.iloc[1][0].split('=')[1].strip()
authCode = cred_file.iloc[2][0].split('=')[1].strip()
portNum = int(cred_file.iloc[3][0].split('=')[1].strip())
contractName = cred_file.iloc[5][0].split('=')[1].strip()

# Discord webhook setup
webhook = SyncWebhook.from_url(webhook_link)
discordChannel = discordChLink
authorizationCode = authCode

# Retrieve messages from Discord channel
def retrieve_messages():
    headers = {
        'authorization': authorizationCode
    }
    r = requests.get(discordChannel, headers=headers)
    jobj = json.loads(r.text)
    df = pd.DataFrame()
    for value in jobj[:2]:
        df = pd.concat([df, pd.DataFrame([value['content'], value['timestamp']]).transpose()])
    return df

def send_discord_message(message):
    webhook.send(message)

# Connect to IB TWS or Gateway
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
        except Exception as e:
            print(e)
            clientId += 1
    return ib, clientId

# Create bracket order
def create_bracket_order(action, quantity, limit_price, take_profit_price, stop_loss_price):
    main_order = LimitOrder(
        action=action,
        totalQuantity=quantity,
        lmtPrice=limit_price
    )
    
    take_profit_order = LimitOrder(
        action='SELL' if action == 'BUY' else 'BUY',
        totalQuantity=quantity,
        lmtPrice=take_profit_price,
        parentId=main_order.orderId
    )
    
    stop_loss_order = StopOrder(
        action='SELL' if action == 'BUY' else 'BUY',
        totalQuantity=quantity,
        stopPrice=stop_loss_price,
        parentId=main_order.orderId
    )
    
    return [main_order, take_profit_order, stop_loss_order]

# Submit bracket order
def submit_bracket_order(ib, contract, action, quantity, limit_price, take_profit_price, stop_loss_price):
    bracket_orders = create_bracket_order(action, quantity, limit_price, take_profit_price, stop_loss_price)
    
    # Ensure main order gets its orderId
    ib.qualifyContracts(contract)
    main_order = bracket_orders[0]
    trade_main = ib.placeOrder(contract, main_order)
    while not main_order.orderId:
        ib.sleep(0.01)
    
    # Place child orders with correct parentId
    for order in bracket_orders[1:]:
        order.parentId = main_order.orderId
        ib.placeOrder(contract, order)

# Monitor open orders
def monitor_open_orders(ib):
    open_orders = ib.openOrders()
    print(f"Number of Open Orders: {len(open_orders)}")
    for trade in ib.trades():
        print(f"Order: {trade.order.action} - {trade.order.orderType} - Limit/Stop: {trade.order.lmtPrice}/{trade.order.auxPrice} - Status: {trade.orderStatus.status}")

# Cancel bracket orders and close positions
def cancel_bracket_orders_and_close_position(ib):
    open_orders = ib.openOrders()
    for order in open_orders:
        if order.orderType in ['LIMIT', 'STOP']:
            ib.cancelOrder(order)
    
    positions = ib.positions()
    for position in positions:
        contract = position.contract
        action = 'SELL' if position.position > 0 else 'BUY'
        quantity = abs(position.position)
        close_order = MarketOrder(action, quantity)
        ib.placeOrder(contract, close_order)

# Main logic
clientId = 1
ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

# Define the contract (example: AAPL stock)
contract = Stock(contractName, 'SMART', 'USD')

# Example of submitting a bracket order
submit_bracket_order(
    ib=ib,
    contract=contract,
    action='BUY',
    quantity=100,
    limit_price=145.00,
    take_profit_price=150.00,
    stop_loss_price=140.00
)

# Monitor open orders
monitor_open_orders(ib)

# Example of cancelling orders and closing positions
# cancel_bracket_orders_and_close_position(ib)

# Disconnect from IB
ib.disconnect()

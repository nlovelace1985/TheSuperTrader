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

cred_file = pd.read_csv('next_gen_v2_cred_text.txt', header=None)

webhook_link = cred_file.iloc[0][0].split('=')[1].strip()

discordChLink = cred_file.iloc[1][0].split('=')[1].strip()

authCode = cred_file.iloc[2][0].split('=')[1].strip()

portNum = cred_file.iloc[3][0].split('=')[1].strip()

# qty = cred_file.iloc[4][0].split('=')[1].strip()

contractName = cred_file.iloc[5][0].split('=')[1].strip()



## read discord messages 

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









## getting account balance 

account_summary = ib.accountSummary()

available_funds = None

for item in account_summary:

    if item.tag == 'ExcessLiquidity':

        available_funds = item.value

        break

    

available_funds = float(available_funds)

textdiscord = "Connection established with ClientID"+str(clientId)+" with $" + str(available_funds)

send_discord_message(textdiscord)

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



    

def bktOrderFunc(side,qty,limit_price,take_profit_price,stop_loss_price):

    

    limit_price = limit_price

    take_profit_price = take_profit_price  # take profit price

    stop_loss_price = stop_loss_price  # stop loss price



    # Create bracket order

    

    take_profit_order = LimitOrder('SELL' if side == 'BUY' else "BUY", qty, take_profit_price, tif='GTC')

    

    stop_loss_order = StopOrder('SELL' if side == 'BUY' else "BUY", qty, stop_loss_price, tif='GTC')



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

        

    # Iterate over each order in the bracket and place it

    for o in bracket_order:

         ib.placeOrder(contract, o)

        





# Function to cancel all bracket orders and close position


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



def round_nearest_qtr(number):

    base = 0.25

    return round(base * round(number / base), 2)





breakcode = 0 

checkPosition = 0 # this is to check if any orders exist without brackets 

while datetime.datetime.now() < exitTime:

    if breakcode == 1:

        break

    timeInNewYork = datetime.datetime.now(newYorkTz)

    

    

    if checkPosition == 1 and datetime.datetime.now().second > 15:

        checkPosition = 0 

        

    if datetime.datetime.now().minute % 2 == 0 and datetime.datetime.now().second < 5 and checkPosition == 0: 

        

        ib.disconnect()

        time.sleep(1)

        ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

        

        checkPosition = 1

        posdf = ib.positions() 

        

        time.sleep(1.2)

        print('check position logic.')

        print(posdf)

        if len(posdf) > 0:

            for pos in posdf:

                if pos[2] > 0: # in long position 

                    openorderdf = ib.openOrders()

                    time.sleep(1)

                    print('in long')

                    print(openorderdf)

                    

                    if len(openorderdf) > 0:

                        a = 1

                    else:

                        send_discord_message("NAKED LONG POSITION!!! PLEASE CHECK and RESOLVE NOW!!!!")

                        cancel_bracket_orders_and_close_position()

                elif pos[2] < 0: # in short position

                    openorderdf = ib.openOrders()

                    

                    time.sleep(1)

                    print('in short')

                    print(openorderdf)

                    

                    if len(openorderdf) > 0:

                        a = 1

                    else:

                        send_discord_message("NAKED SHORT POSITION!!! PLEASE CHECK and RESOLVE NOW!!!!")

                        cancel_bracket_orders_and_close_position()

                        

        elif len(posdf) == 0:

            orders = ib.openOrders() 

            ib.sleep(.5)

            if len(orders) == 2: ## code found position is 0 but open orders

                cancel_bracket_orders_and_close_position()

                send_discord_message("Close Bracket Orders since no open position found!")

            



    try: # running the whole code in try except loop to check for errors

        msg = retrieve_messages()

        crntmsg = msg.iloc[0][0]

        crntmtime = msg.iloc[0][1]

        

        # trying the print of all open positions 

        # positions = ib.positions()

        # for position in positions:

        #     print(position)

        incMsg = 0 

        if crntmsg!=prevmsg: 

            incMsg += 1 

            print('crntmsg is ',crntmsg)

            print(incMsg)

            if 'Enter Long' in crntmsg or 'Close entry(s) order Short' in crntmsg:

                

                cancel_bracket_orders_and_close_position()

                time.sleep(.5)

                # enter long trade - bracket order

                x22 = crntmsg.split("@")

                limit_price = round_nearest_qtr(float(x22[1].split(' ')[0]))

                stop_loss_price = round_nearest_qtr(float(x22[-1]))

                side = "BUY"

                if stop_loss_price > limit_price:

                    send_discord_message("Stop loss price is adjusted")

                    stop_loss_price = limit_price - 5 

                take_profit_price = limit_price + 100

                bktOrderFunc(side,qty,limit_price,take_profit_price,stop_loss_price)

                send_discord_message('Code going to sleep for 20 seconds')

                time.sleep(20)

                ib.disconnect()

                time.sleep(1)

                send_discord_message('code alive again, running sanity checks.')

                ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

                send_discord_message('Long order placed')

                posdf = ib.positions() 

                print(len(posdf))

                print(posdf)

                time.sleep(2)

                if len(posdf)>0:

                    

                    txt = 'Current position summary:\n' 

                    txt = txt + "Number of Positions: " + str(len(posdf)) + "\n"

                    for pos in posdf:

                        txt = txt + str(int(pos[2])) + " of " + pos[1].symbol 

                    

                    lenoo = len(ib.openOrders()) # open orders

                    txt = txt+ " \n" + "Open Order Summary:\nNumber of Open Orders: "+str(lenoo)+"\n"

                    for oo in ib.openOrders():

                        oTxt = oo.action +" - " + oo.orderType + " - lmt/stp:"+str(oo.lmtPrice)+"/"+str(oo.auxPrice) + ", orderType:"+oo.tif  + "\n"

                        txt = txt + oTxt

                    

                    

                    send_discord_message(txt)

                else:

                    send_discord_message('Current position summary is :'+str(ib.positions()))

            elif 'Exit Long' in crntmsg:

                cancel_bracket_orders_and_close_position()

                

                send_discord_message('Long Exit, Code going to sleep for 10 seconds')

                ib.disconnect()

                time.sleep(10)

                send_discord_message('code alive again, running sanity checks.')

                ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

                

                

                posdf = ib.positions() 

                time.sleep(2)

                if len(posdf)>0:

                    send_discord_message('Current position summary is :'+str(ib.positions()[2]))

                else:

                    send_discord_message('Current position summary is :'+str(ib.positions()))

            elif 'Enter Short' in crntmsg or 'Close entry(s) order Long' in crntmsg:

                cancel_bracket_orders_and_close_position()

                time.sleep(.5)

                x22 = crntmsg.split("@")

                limit_price = round_nearest_qtr(float(x22[1].split(' ')[0]))

                stop_loss_price = round_nearest_qtr(float(x22[-1]))

                if stop_loss_price < limit_price:

                    send_discord_message("SL adjusted")

                    stop_loss_price = limit_price + 5

                side = "SELL"

                take_profit_price = limit_price - 100

                bktOrderFunc(side,qty,limit_price,take_profit_price,stop_loss_price)

                send_discord_message('Code going to sleep for 20 seconds')

                time.sleep(20)

                ib.disconnect()

                time.sleep(1)

                ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

                send_discord_message('Short order placed')

                posdf = ib.positions() 

                print(len(posdf))

                print(posdf)

                time.sleep(2)

                if len(posdf)>0:

                    

                    txt = 'Current position summary:\n' 

                    txt = txt + "Number of Positions: " + str(len(posdf)) + "\n"

                    for pos in posdf:

                        txt = txt + str(int(pos[2])) + " of " + pos[1].symbol 

                    

                    lenoo = len(ib.openOrders()) # open orders

                    txt = txt+ " \n" + "Open Order Summary:\nNumber of Open Orders: "+str(lenoo)+"\n"

                    for oo in ib.openOrders():

                        oTxt = oo.action +" - " + oo.orderType + " - lmt/stp:"+str(oo.lmtPrice)+"/"+str(oo.auxPrice) + ", orderType:"+oo.tif  + "\n"

                        txt = txt + oTxt

                    

                    

                    send_discord_message(txt)

                else:

                    send_discord_message('Current position summary is :'+str(ib.positions()))

            elif 'Exit Short' in crntmsg:

                cancel_bracket_orders_and_close_position()

                send_discord_message('Short Exit, Code going to sleep for 10 seconds')

                ib.disconnect()

                time.sleep(10)

                send_discord_message('code alive again, running sanity checks.')

                ib, clientId = connect_with_retry('127.0.0.1', portNum, 100, clientId)

                

                

                posdf = ib.positions() 

                time.sleep(2)

                if len(posdf)>0:

                    send_discord_message('Current position summary is :'+str(ib.positions()[2]))

                else:

                    send_discord_message('Current position summary is :'+str(ib.positions()))

                

            elif 'time left' in crntmsg:

                timeleft = exitTime - datetime.datetime.now()

                cstr = "code will end in "+str(timeleft.seconds)+ " seconds."

                send_discord_message(cstr)

                time.sleep(.1)

                

            elif 'close all' in crntmsg:

                cancel_bracket_orders_and_close_position()

                

            prevmsg = crntmsg

        print('read @',datetime.datetime.now())

        time.sleep(.25)

        

    except Exception as e:

        df3 = pd.DataFrame([e])



#### end of core logic

# Disconnect from IB TWS or Gateway

ib.disconnect()

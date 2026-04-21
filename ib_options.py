from ib_insync import IB, Stock, Option
import asyncio

ib = IB()

def connect_ib():
    try:
        if not ib.isConnected():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ib.connect('127.0.0.1', 7497, clientId=1)
        return ib
    except Exception as e:
        print(f"IB ERROR: {e}")
        return None

def get_best_option_ib(symbol, price, direction):

    try:
        ib = connect_ib()
        if ib is None:
            return None, None

        stock = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(stock)

        chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)

        chain = chains[0]

        strikes = sorted(chain.strikes)
        expirations = sorted(chain.expirations)

        strike = min(strikes, key=lambda x: abs(x - price))
        expiry = expirations[0]

        return strike, expiry

    except Exception as e:
        print(f"IB ERROR: {e}")
        return None, None

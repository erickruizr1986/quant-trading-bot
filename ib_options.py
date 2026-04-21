from ib_insync import *

ib = IB()

def connect_ib():
    if not ib.isConnected():
        ib.connect('127.0.0.1', 7497, clientId=1)
    return ib


def get_best_option_ib(symbol, price, direction):

    try:
        ib = connect_ib()

        stock = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(stock)

        chains = ib.reqSecDefOptParams(
            stock.symbol, '', stock.secType, stock.conId
        )

        chain = chains[0]

        expirations = sorted(chain.expirations)
        strikes = sorted(chain.strikes)

        exp = expirations[0]  # nearest expiry

        right = 'C' if direction == "CALL" else 'P'

        candidates = []

        for strike in strikes:

            # limitar rango cercano al precio
            if abs(strike - price) > price * 0.03:
                continue

            contract = Option(symbol, exp, strike, right, 'SMART')
            ib.qualifyContracts(contract)

            ticker = ib.reqMktData(contract, "", False, False)

            ib.sleep(0.2)

            if ticker.modelGreeks is None:
                continue

            delta = ticker.modelGreeks.delta
            bid = ticker.bid
            ask = ticker.ask

            if bid is None or ask is None:
                continue

            spread = ask - bid

            if delta is None:
                continue

            delta = abs(delta)

            # 🎯 FILTRO PRO
            if 0.55 <= delta <= 0.70 and spread < 0.15:

                candidates.append({
                    "strike": strike,
                    "expiry": exp,
                    "delta": delta,
                    "spread": spread,
                    "contract": contract
                })

        if not candidates:
            return None, None

        # elegir mejor por delta cercano a 0.6
        best = sorted(candidates, key=lambda x: abs(x["delta"] - 0.6))[0]

        return best["strike"], best["expiry"]

    except Exception as e:
        print(f"IB ERROR: {e}")
        return None, None

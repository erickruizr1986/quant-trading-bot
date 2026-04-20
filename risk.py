ACCOUNT_SIZE = 5000
RISK_PER_TRADE = 0.02  # 2%


def position_size(premium):

    risk_amount = ACCOUNT_SIZE * RISK_PER_TRADE

    contracts = int(risk_amount / (premium * 100))

    return max(1, contracts)

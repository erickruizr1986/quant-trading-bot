ACCOUNT_SIZE = 1000

def position_size(premium, prob):

    risk = 0.10

    if prob > 0.7:
        risk = 0.03
    elif prob > 0.6:
        risk = 0.02

    capital = ACCOUNT_SIZE * risk

    contracts = int(capital / (premium * 100))

    return max(1, contracts)

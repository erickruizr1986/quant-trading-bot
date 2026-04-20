ACCOUNT_SIZE = 5000
RISK_PER_TRADE = 0.02


def get_multiplier(score):

    score = abs(score)

    if score >= 5:
        return 1.0
    elif score == 4:
        return 0.7
    elif score == 3:
        return 0.4
    else:
        return 0


def position_size(premium, score):

    base_risk = ACCOUNT_SIZE * RISK_PER_TRADE
    multiplier = get_multiplier(score)

    adjusted = base_risk * multiplier

    contracts = int(adjusted / (premium * 100))

    return max(1, contracts) if multiplier > 0 else 0

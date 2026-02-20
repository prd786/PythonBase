import logging

#logging.basicConfig(level=logging.INFO)

class InsufficientBalanceError(Exception):
    pass

def withdraw(balance, amount):
    logging.info(f"Attempting to withdraw {amount} from balance {balance}")

    if amount > balance:
        logging.error("Insufficient balance for withdrawal")
        raise InsufficientBalanceError(
            "You do not have enough balance to withdraw this amount."
        )

    logging.info("Withdrawal successful")
    return balance - amount

try:
    new_balance = withdraw(1000, 1500)
    print(f"New balance: {new_balance}")
except InsufficientBalanceError:
    logging.exception("Transaction failed")

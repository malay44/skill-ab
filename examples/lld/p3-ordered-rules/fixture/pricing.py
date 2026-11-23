def member_discount(cart, price):
    return price * 0.9 if cart["member"] else price


def coupon(cart, price):
    return price - cart.get("coupon_cents", 0)


def floor_at_zero(cart, price):
    return max(price, 0)


RULES = {member_discount, coupon, floor_at_zero}


def final_price(cart):
    price = cart["subtotal_cents"]
    for rule in RULES:
        price = rule(cart, price)
    return round(price)

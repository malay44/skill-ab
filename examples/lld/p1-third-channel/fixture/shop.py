from services import email_service, sms_service


class Shop:
    def __init__(self, orders):
        self.orders = orders

    def place_order(self, user, order):
        self.orders[order.id] = order
        email_service.send(user.email, f"Order {order.id} placed")
        sms_service.send(user.phone, f"Order {order.id} placed")

    def ship_order(self, user, order_id):
        self.orders[order_id].status = "shipped"
        email_service.send(user.email, f"Order {order_id} shipped")
        sms_service.send(user.phone, f"Order {order_id} shipped")

    def cancel_order(self, user, order_id):
        self.orders[order_id].status = "cancelled"
        email_service.send(user.email, f"Order {order_id} cancelled")
        sms_service.send(user.phone, f"Order {order_id} cancelled")

    def refund_order(self, user, order_id):
        self.orders[order_id].status = "refunded"
        email_service.send(user.email, f"Order {order_id} refunded")
        sms_service.send(user.phone, f"Order {order_id} refunded")

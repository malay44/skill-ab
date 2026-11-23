class _Service:
    def __init__(self, name):
        self.name, self.sent = name, []

    def send(self, to, text):
        self.sent.append((to, text))


email_service = _Service("email")
sms_service = _Service("sms")
push_service = _Service("push")  # send(device_token, text)

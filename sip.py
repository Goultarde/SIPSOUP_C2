import hashlib
import hmac
import time
import uuid


def build(method, target, sender, body, secret):
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    payload = "\n".join((method, target, sender, timestamp, nonce, body))
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    data = (
        f"{method} sip:{target} SIP/2.0\r\n"
        f"From: <sip:{sender}>\r\n"
        f"To: <sip:{target}>\r\n"
        f"X-Timestamp: {timestamp}\r\n"
        f"X-Nonce: {nonce}\r\n"
        f"X-Signature: {signature}\r\n"
        f"Content-Length: {len(body.encode())}\r\n\r\n{body}"
    )
    return data.encode()


def parse(data, secret, seen, now=None):
    head, separator, body = data.decode("utf-8").partition("\r\n\r\n")
    if not separator:
        raise ValueError("message SIP incomplet")
    lines = head.split("\r\n")
    first = lines[0].split()
    if len(first) != 3 or first[2] != "SIP/2.0" or not first[1].startswith("sip:"):
        raise ValueError("ligne SIP invalide")
    method, target = first[0], first[1][4:]
    headers = {}
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError("en-tete SIP invalide")
        headers[key.lower()] = value.strip()
    required = ("from", "x-timestamp", "x-nonce", "x-signature", "content-length")
    if any(key not in headers for key in required):
        raise ValueError("en-tete SIP manquant")
    sender = headers["from"].removeprefix("<sip:").removesuffix(">")
    timestamp, nonce = headers["x-timestamp"], headers["x-nonce"]
    current = int(time.time() if now is None else now)
    if abs(current - int(timestamp)) > 30:
        raise ValueError("message SIP expire")
    if nonce in seen:
        raise ValueError("message SIP rejoue")
    if int(headers["content-length"]) != len(body.encode()):
        raise ValueError("taille SIP invalide")
    payload = "\n".join((method, target, sender, timestamp, nonce, body))
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(headers["x-signature"], expected):
        raise ValueError("signature SIP invalide")
    seen.add(nonce)
    return method, target, sender, body

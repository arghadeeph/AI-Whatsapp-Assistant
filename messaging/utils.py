from django.core.signing import Signer, BadSignature

signer = Signer()

def sign_phone(phone):
    return signer.sign(phone)

def unsign_phone(signed_phone):
    try:
        return signer.unsign(signed_phone)
    except BadSignature:
        return None
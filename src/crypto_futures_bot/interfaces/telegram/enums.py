from enum import Enum


class SessionKeysEnum(str, Enum):
    """
    Enum for session keys used in the application.
    """

    USER_CONTEXT = "user_ctx"
    SIGNAL_PARAMETRIZATION_CRYPTO_CURRENCY_FORM = "signal_parametrization_crypto_currency_form"

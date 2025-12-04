from crypto_futures_bot.config.configuration_properties import ConfigurationProperties


class KeyboardsBuilder:
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties

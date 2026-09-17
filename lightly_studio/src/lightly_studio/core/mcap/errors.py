"""Errors raised by the MCAP access layer."""


class McapAccessError(Exception):
    """Exception signaling that an MCAP file cannot be read as expected."""


class TopicNotFoundError(McapAccessError):
    """Exception signaling that a topic is not present in an MCAP file."""


class DataNotLoadedError(McapAccessError):
    """Exception signaling that a topic was not loaded with `load_data_for_topics`."""


class TransformNotFoundError(McapAccessError):
    """Exception signaling that no transform chain connects two coordinate frames."""

"""Domain-level exceptions raised by the store and translated to HTTP errors by routers."""


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass

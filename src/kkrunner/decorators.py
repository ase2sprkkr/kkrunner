class class_property:
    """
    Decorator that converts a method with a single cls argument into a property
    that can be accessed directly from the class. The value is not cached, see
    :func:`cached_class_property`, if caching is desirable.

    Example
    -------

    .. code-block::

       class Cls:
          @class_property
          def cls_property():
              return some_value

          x = Cls.cls_property
    """

    def __init__(self, method=None):
        self.fget = method

    def __get__(self, instance, cls=None):
        return self.fget(cls)

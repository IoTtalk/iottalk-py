class ColorBase:
    default = "\033[0m"
    data = "\033[1;33m"

    @classmethod
    def wrap(cls, color, s):
        """
        wrap string with color
        """
        return "{}{}{}".format(color, s, cls.default)


class DANColor(ColorBase):
    logger = "\033[1;35m"


class DAIColor(ColorBase):
    logger = "\033[1;34m"

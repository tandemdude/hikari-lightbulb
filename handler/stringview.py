from handler import errors

_quotes = {
    '"': '"',
    "‘": "’",
    "‚": "‛",
    "“": "”",
    "„": "‟",
    "⹂": "⹂",
    "「": "」",
    "『": "』",
    "〝": "〞",
    "﹁": "﹂",
    "﹃": "﹄",
    "＂": "＂",
    "｢": "｣",
    "«": "»",
    "‹": "›",
    "《": "》",
    "〈": "〉",
}


class UnclosedQuotes(errors.CommandError):
    """Error raised when no closing quote is found for a quoted argument"""

    def __init__(self, text: str):
        self.text = text


class StringView:
    def __init__(self, raw_string: str):
        self.text = raw_string
        self.index = 0
        self.final_args = []
        self.current_arg = []
        self.expect_quote = None

    def next_str(self):
        buff = []
        while self.index < len(self.text):
            char = self.text[self.index]
            if char == " " and self.expect_quote is None:
                self.index += 1
                return "".join(buff)
            elif not self.expect_quote and char in _quotes:
                self.expect_quote = char
                self.index += 1
                continue
            elif char == self.expect_quote:
                self.expect_quote = None
                self.index += 1
                return "".join(buff)
            elif char == "\\":
                self.index += 1
                buff.append(self.text[self.index])
                self.index += 1
                continue
            else:
                buff.append(char)
                self.index += 1

        if self.expect_quote:
            raise UnclosedQuotes("".join(buff))
        if buff:
            return "".join(buff)

    def deconstruct_str(self):
        finished = False
        args_list = []
        while not finished:
            arg = self.next_str()
            if arg is not None:
                args_list.append(arg)
            else:
                finished = True
        return args_list

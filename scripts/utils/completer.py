options = [
    'clear',
    'courses',
    'date',
    'exit',
    'flat',
    'help',
    'jumps',
    'options',
    'quit',
    'regions'
]


class Completer:
    
    def __init__(self):
        self.options = sorted(options)
        self.matches = []

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            return self.matches[state]
        except IndexError:
            return None

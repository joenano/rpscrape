from random import choice, sample


class RandomHeader:
    def __init__(self) -> None:
        self.user_agents: list[str] = []
        self.load_user_agents()

    def header(self) -> dict[str, str]:
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://www.google.com/',
            'Dnt': choice(('0', '1')),
            'Connection': 'keep-alive',
            'X-Forwarded-For': self.random_ip(),
            'User-Agent': choice(self.user_agents),
            'Upgrade-Insecure-Requests': '1',
        }

    def load_user_agents(self):
        with open('utils/agents/user-agents.txt') as f:
            for line in f:
                self.user_agents.append(line.strip())

    def random_ip(self) -> str:
        return '{}.{}.{}.{}'.format(*sample(range(0, 255), 4))

from typing import Tuple
from datetime import datetime, timedelta

Task = Tuple[str, datetime, bool]

FILE = 'db.txt'
class Db(dict[str, list[Task]]):
    def add_task(self, user_id, task):
        if user_id not in self:
            self[user_id] = []
        self[user_id].append(task)


    def read(self):
        with open(FILE, 'r') as f:
            for line in f:
                if len(line.strip()) == 0:
                    continue
                user_id, desc, date, is_recurring = line.strip().split("\t")
                date = datetime.fromisoformat(date)
                is_recurring = bool(str(is_recurring))
                if date < datetime.now():
                    if is_recurring:
                        while date < datetime.now():
                            date = date + timedelta(days=7)
                    else:
                        continue
                self.add_task(user_id, (desc, date, is_recurring))


    def save(self):
        with open(FILE, 'w') as f:
            for user_id in self:
                for task in self[user_id]:
                    f.write(f"{user_id}\t{task[0]}\t{task[1].isoformat()}\t{1 if task[2] else 0}\n")

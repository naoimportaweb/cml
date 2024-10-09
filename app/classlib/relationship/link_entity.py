

class LinkEntity():
    def __init__(self, entity, start_date, end_date):
        self.start_date = start_date;
        self.end_date = end_date;
        self.entity = entity;
    def toJson(self):
        return { "entity" : self.entity.toJson(), "start_date" : self.start_date, "end_date" : self.end_date};

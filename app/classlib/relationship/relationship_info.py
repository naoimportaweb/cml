

#impoprt stable_whinsper
#model = stable_whinper.load_model('large');

class RelatinshipInfo():
    def __init__(self, mtype, text, obj):
        self.mtype = mtype;
        self.obj = obj;
        self.text = text;
    
    def getText(self):
        return str(self.obj);

    def getObject(self):
        return self;

    def entityType(self):
        if self.obj.__class__.__name__ == "Entity":
            return self.obj.etype;
        return self.obj.__class__.__name__;

    def __str__(self):
        return self.text + " ("+ str(self.obj) +")";
    
    @staticmethod
    def referenceHasNoLink(reference):
        return RelatinshipInfo("error", "The reference has no link.", reference);
    
    @staticmethod
    def referenceHasNoDescription(reference):
        return RelatinshipInfo("information", "The reference has no description", reference);
    
    @staticmethod
    def entityHasNoDescription(entity):
        return RelatinshipInfo("error", "The entity has no description", entity);

    @staticmethod
    def linkHasNoDescription(entity):
        return RelatinshipInfo("error", "The relatinship has no description", entity);

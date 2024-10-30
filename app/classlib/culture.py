from spellchecker import SpellChecker

class Culture:
    def __init__(self, label):
        self.label = label;
        self.stopwords = [".", ",", ";", ":", "/", "?", "]", "[", "}", "{"];

    def spellCheck(self, text):
        if text == None:
            return None;

        for stop in self.stopwords:
            text = text.replace( stop, "" );
        buffer_inclear = text.split(' ');
        buffer_clear = [];
        for buffer in buffer_inclear:
            if buffer.strip() != "" and not buffer.strip() in self.stopwords:
                buffer_clear.append( buffer.strip() );

        spell = SpellChecker( language=self.label );
        misspelled = spell.unknown( buffer_clear );
        returned = [];
        for word in misspelled:
            returned.append({"word" : word, "correction" : spell.correction(word)});
        return returned;
    
    def errors(self, text):
        buffers = self.spellCheck( text );
        if buffers == None:
            return [];
        retornar = [];
        for buffer in buffers:
            retornar.append( buffer["word"] );
        return retornar;

    def correct(self, text):
        words = self.spellCheck( text );
        result = True;
        for word in words:
            if word["correction"] == None:
                result = False;
                continue;
            text = text.replace(word["word"], word["correction"]);
        return {"status" : result, "text" : text};


#c = Culture("pt");
#texto = "Um texto correcao";
#retorno = c.correct( texto );
#print( retorno["text"] );
#print( retorno["status"] );

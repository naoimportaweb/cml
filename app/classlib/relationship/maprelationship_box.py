import os, sys, inspect, json, uuid;

CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append( os.path.dirname(  os.path.dirname( CURRENTDIR ) ) );

from PySide6.QtWidgets import (QStyle,QColorDialog,)
from PySide6.QtCore import Qt, Slot, QStandardPaths,QRectF,QByteArray
from PySide6.QtGui import (QMouseEvent,QPaintEvent,QFont,QPen,QAction,QPainter,QColor,QBrush,QPixmap,QIcon,QKeySequence,);

from classlib.configuration import Configuration
from classlib.entity import Entity
from classlib.relationship.relationship_info import RelatinshipInfo;

FACE_LADO = 64;   # maior lado da imagem quando ela substitui a caixinha com o nome

class MapRelationshipBox():
    def __init__(self, mapa, x, y, w, h, text=None, id_=None, entity_id_=None):
        self.id =         uuid.uuid4().hex + "_" + uuid.uuid4().hex + "_" + uuid.uuid4().hex;
        self.mapa = mapa;
        if id_ != None:
            self.id = id_;
        self.entity = Entity(entity_id_);
        self.entity.text = text;
        self.entity.full_description = "";
        self._dirt = False;
        self.x = x;
        self.y = y;
        self.w = w;
        self.h = h;
        self.start_date = None;
        self.end_date = None;
        self.format_date = "yyyy-MM-dd";
    
    def __str__(self):
        return self.entity.text;
    
    def getWarnings(self, arr):
        if self.entity.full_description == None or self.entity.full_description.strip() == "":
            if self.entity.etype == "link":
                arr.append( RelatinshipInfo.linkHasNoDescription( self ) );
            elif self.entity.etype == "other":
                arr.append( RelatinshipInfo.entityHasNoDescription( self ) );
        for reference in self.entity.references:
            reference.getWarnings(arr);

    def getErros(self, arr):
        if self.entity.full_description == None or self.entity.full_description.strip() == "":
            if self.entity.etype != "link" and self.entity.etype != "other":
                arr.append( RelatinshipInfo.entityHasNoDescription( self ) );
        for reference in self.entity.references:
            reference.getErros(arr);

    def getText(self):
        return self.entity.getText();
    
    def getDirt(self):
        return self._dirt or self.entity.getDirt();
    
    def setX(self, x):
        self.x = x;
        self._dirt = True;

    def setY(self, y):
        self.y = y;
        self._dirt = True;

    def toJson(self):
        objeto = { "id" : self.id, "entity_id": self.entity.id , "x" : self.x, "y" : self.y, "w" : self.w, "h" : self.h, "text" : self.entity.text, "full_description" : self.entity.full_description, "etype" : self.entity.etype, "references" : [], "time_slices" : [], "data_extra" : self.entity.data_extra, "wikipedia" : self.entity.wikipedia, "classification" : self.entity.classification, "small_label" : self.entity.small_label, "start_date" : self.start_date, "end_date" : self.end_date, "format_date" : self.format_date,
            "entity_start_date" : self.entity.start_date, "entity_end_date" : self.entity.end_date, "entity_format_date" : self.entity.format_date, "default_url" : self.entity.default_url  };
        
        for reference in self.entity.references:
            buffer = reference.toJson();
            buffer["entity_id"] = self.entity.id;
            objeto["references"].append( buffer );
        
        for time_slice in self.entity.time_slices:
            buffer = time_slice.toJson();
            buffer["entity_id"] = self.entity.id;
            objeto["time_slices"].append( buffer );
        return objeto;
    
    def merge_to(self, old_entity_id):
        self.entity.merge_to( old_entity_id);
    def duplicate(self):
        return self.entity.duplicate();   
    def setType(self, etype):
        if etype == self.entity.etype:
            return True;
        return self.mapa.switchType(self, etype);

    def addReference(self, title, link1, link2 = "", link3 = "", id_=None, descricao=""):
        return self.entity.addReference(title, link1, link2, link3, id_, descricao=descricao);

    def addTimeSlice(self, text_label, date_start=None, date_end=None, id_=None):
        return self.entity.addTimeSlice(text_label, date_start, date_end, id_);
    
    def mostra_rosto(self):
        # "Exibir PNG de rosto" ligado no mapa E a entidade tem rosto: a imagem SUBSTITUI a
        # caixinha com o nome (nao desenha retangulo nem texto). Vinculo nunca tem rosto.
        return bool(getattr(self.mapa, "show_face", False)) and self.entity.face != None and self.entity.face != "";

    def recalc(self, painter):
        if self.mostra_rosto():
            # A caixa VIRA a imagem: dimensiona w/h pela miniatura, para a area de clique e as
            # linhas de vinculo baterem na imagem, nao no antigo retangulo do texto.
            pix = self.__face_pixmap__();
            if pix != None and not pix.isNull():
                thumb = pix.scaled(FACE_LADO, FACE_LADO, Qt.KeepAspectRatio, Qt.SmoothTransformation);
                self.w = thumb.width();
                self.h = thumb.height();
                return;
        painter.setFont(QFont(Configuration.instancia().relationshihp_font_family, Configuration.instancia().relationshihp_font_size))
        buffer_text_for_calc = self.entity.text;
        if self.entity.etype == "person" or self.entity.etype == "other":
            if self.entity.small_label != None and self.entity.small_label.strip() != "":
                buffer_text_for_calc = self.entity.small_label;
        elif self.entity.etype == "organization":
            if  self.entity.small_label != None and self.entity.small_label.strip() != "":
                buffer_text_for_calc = self.entity.text + " (" + self.entity.small_label + ")";
        frame_text = painter.boundingRect(0, 0, 150, 30, 0, buffer_text_for_calc);

        self.w = frame_text.width() + 10;
        self.h = frame_text.height() + 2;
    def __face_pixmap__(self):
        # Decodifica o PNG base64 do rosto uma vez e reaproveita enquanto o base64 nao muda
        # (o draw roda a cada repaint; decodificar toda vez pesaria).
        if self.entity.face == None:
            return None;
        if getattr(self, "_face_src", None) == self.entity.face and getattr(self, "_face_pix", None) != None:
            return self._face_pix;
        ba = QByteArray.fromBase64( QByteArray(self.entity.face.encode("ascii")) );
        pix = QPixmap();
        pix.loadFromData(ba, "PNG");
        self._face_pix = pix;
        self._face_src = self.entity.face;
        return pix;

    def draw_face_only(self, painter):
        # Desenha SO a imagem, no retangulo da caixa (recalc ja ajustou w/h pela miniatura).
        # Devolve False se o PNG nao decodificou, para o chamador cair na caixa com o nome.
        pix = self.__face_pixmap__();
        if pix == None or pix.isNull():
            return False;
        thumb = pix.scaled(FACE_LADO, FACE_LADO, Qt.KeepAspectRatio, Qt.SmoothTransformation);
        painter.drawPixmap(self.x, self.y, thumb);
        return True;

    def __subtype_pixmap__(self):
        # Cache do PNG do rosto default do subtipo (badge), como o do rosto proprio.
        face = getattr(self.entity, "subtype_face", None);
        if face == None:
            return None;
        if getattr(self, "_subface_src", None) == face and getattr(self, "_subface_pix", None) != None:
            return self._subface_pix;
        ba = QByteArray.fromBase64( QByteArray(face.encode("ascii")) );
        pix = QPixmap();
        pix.loadFromData(ba, "PNG");
        self._subface_pix = pix;
        self._subface_src = face;
        return pix;

    def draw_subtype_badge(self, painter):
        # Pequena imagem do subtipo (rosto default) ANTES do texto, na MESMA linha (a
        # esquerda, alinhada verticalmente ao centro da caixa) — como um icone que faz parte
        # do nome. Nao substitui nada; so com "Exibir PNG de rosto" ligado e se houver rosto
        # de subtipo. A esquerda fica fora do caminho das setinhas, que chegam pela borda.
        if not getattr(self.mapa, "show_face", False):
            return;
        # Rosto PROPRIO da entidade tem preferencia: se existe, o badge do subtipo nao aparece
        # (o proprio ja substitui a caixa). O badge so entra quando nao ha rosto proprio.
        if self.entity.face != None:
            return;
        if getattr(self.entity, "subtype_face", None) == None:
            return;
        pix = self.__subtype_pixmap__();
        if pix == None or pix.isNull():
            return;
        # Tamanho ~ altura da caixa (acompanha o texto), com um teto para nao ficar enorme
        # quando a caixa e o rosto proprio (alta).
        lado = self.h if self.h > 0 else 22;
        if lado > 30: lado = 30;
        if lado < 16: lado = 16;
        thumb = pix.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation);
        px = self.x - thumb.width() - 2;                            # ANTES (a esquerda)
        py = self.y + int(self.h / 2) - int(thumb.height() / 2);    # alinhado com o texto
        painter.drawPixmap(px, py, thumb);

    def draw(self, painter):
        if self.mostra_rosto() and self.draw_face_only(painter):
            return;
        penRectangle = QPen(Qt.black)
        penRectangle.setWidth(1)
        painter.setPen(penRectangle)
        painter.fillRect( self.x, self.y, self.w, self.h, QBrush(Qt.white));
        painter.drawRect( self.x, self.y, self.w, self.h);
        if self.entity.text != None:
            painter.drawText(QRectF(self.x , self.y, self.w, self.h), Qt.AlignCenter | Qt.AlignTop, self.entity.text)

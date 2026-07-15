<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";
require_once dirname(dirname(dirname(__DIR__))) . "/api/json.php";

class EntityBox{
    // O dre.w gravado pelo cliente é sempre o default (100) e não acompanha o texto,
    // por isso a largura é recalculada aqui. CHAR_W tem que bater com a fonte do canvas
    // declarada na view (14px Courier): mudou lá, muda aqui.
    const CHAR_W  = 9;
    const PADDING = 10;

    private $id = null;
    private $entity_id = null;
    private $etype = null;
    private $mapa = null;
    private $domain = null;
    private $x = null;
    private $y = null;
    private $h = null;
    private $w = null;
    private $center_x = null;
    private $center_y = null;
    private $text_label = null;
    private $data_extra = null;
    private $full_description = null;
    private $wikipedia = null;
    private $references = [];
    private $to_entity = [];
    private $from_entity = [];

    function __construct($mapa, $domain) {
        $this->domain = $domain;
        $this->mapa = $mapa;
    }

    // strlen conta bytes: num rotulo acentuado ("Ministerio Publico" com acentos = 18
    // chars, 20 bytes) a caixa sai mais larga que o texto desenhado. O mbstring existe no
    // PHP que serve o site, mas nem todo ambiente de dev tem — dai o fallback por PCRE,
    // que nao depende de extensao.
    private static function tamanhoTexto($texto){
        $texto = (string) $texto;
        if( function_exists("mb_strlen") ){
            return mb_strlen($texto, "UTF-8");
        }
        $n = preg_match_all('/./u', $texto);
        return $n === false ? strlen($texto) : $n;
    }

    private function recalculateCenter(){
        $this->center_x = $this->x + intval( $this->w / 2 );
        $this->center_y = $this->y + intval( $this->h / 2 );
    }

    // Desloca nos dois eixos de uma vez: separado em subtractX/subtractY, o centro ficava
    // inconsistente entre as duas chamadas e era recalculado em dobro.
    public function subtract($min_x, $min_y){
        $this->x = $this->x - $min_x + 5;
        $this->y = $this->y - $min_y + 5;
        $this->recalculateCenter();
    }

    public function loadData($data_table){
        $this->id           = $data_table["id"];
        $this->entity_id    = $data_table["entity_id"];
        $this->etype        = $data_table["etype"];
        $this->x            = intval( $data_table["x"] );
        $this->y            = intval( $data_table["y"] );
        $this->h            = intval( $data_table["h"] );
        $this->text_label   = $data_table["text_label"];
        $this->data_extra   = $data_table["data_extra"];
        $this->full_description = $data_table["full_description"];
        $this->wikipedia        = $data_table["wikipedia"];
        $this->w            = ( self::tamanhoTexto( $this->text_label ) * self::CHAR_W ) + self::PADDING;
        $this->recalculateCenter();
    }

    public function toJson(){
        $buffer = array("id" => $this->id, "entity_id" => $this->entity_id, "etype" => $this->etype, "x" => $this->x, "y" => $this->y, "h" => $this->h, "w" => $this->w, "text_label" => $this->text_label, "full_description" => $this->full_description, "wikipedia" => $this->wikipedia, "references" => $this->references, "to" => [], "from" => [], "center_x" => $this->center_x, "center_y" => $this->center_y);

        if( $this->etype == "link") {
            foreach( $this->to_entity as $_to ) {
                array_push($buffer["to"], $_to->toJsonShallow() );
            }
            foreach( $this->from_entity as $_from ) {
                array_push($buffer["from"], $_from->toJsonShallow() );
            }
        }
        return $buffer;
    }

    // Dentro de to/from o desenho só precisa do centro da caixa apontada. Serializar o
    // objeto inteiro repetiria as referências dela dentro de cada link.
    public function toJsonShallow(){
        return array("id" => $this->id, "etype" => $this->etype, "text_label" => $this->text_label, "center_x" => $this->center_x, "center_y" => $this->center_y);
    }

    public function setReferences($references){
        $this->references = $references;
    }

    public function addTo($element){
        array_push( $this->to_entity, $element );
    }

    public function addFrom($element){
        array_push( $this->from_entity, $element );
    }

    public function getId(){
        return $this->id;
    }

    public function getEntityId(){
        return $this->entity_id;
    }

    public function getX(){
        return $this->x;
    }

    public function getY(){
        return $this->y;
    }

    public function getW(){
        return $this->w;
    }

    public function getH(){
        return $this->h;
    }

}

?>

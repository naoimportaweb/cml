
<?php
//ini_set('display_errors', '1');
//ini_set('display_startup_errors', '1');
//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Entity
{
    private $id = null;
    private $name = "";

    public function import_all($ip, $user, $post_data, $domain){
        $mysql = new Mysql( $domain );
        $entitys = $post_data["parameters"]["entitys"];
        $sqls = [];
        $values = [];
        $date = new DateTime(); //now
        $sub_etype_adicionado = [];
        $aka_adicionado = [];
        for( $i = 0; $i < count($entitys); $i++ ){
            $entity_id = $mysql->gen_uuid();
            $existe = $mysql->DataTable("SELECT id FROM entity WHERE text_label= ?", [ $entitys[$i]["text_label"] ]);
            if( count( $existe) > 0 ){
                $entity_id = $existe[0]["id"];
            }
            $existe = $mysql->DataTable("SELECT id FROM sub_etype WHERE name= ?", [ $entitys[$i]["sub_etype"] ]);
            if( $entitys[$i]["sub_etype"] != "" && count( $existe) == 0 && ! in_array($entitys[$i]["sub_etype"] , $sub_etype_adicionado)){
                array_push($sqls,                 "INSERT INTO sub_etype(id, name ) values (?,?) ON DUPLICATE KEY UPDATE name= ?");
                array_push($values,               [ md5($entitys[$i]["sub_etype"]) , $entitys[$i]["sub_etype"], $entitys[$i]["sub_etype"] ]);
                array_push($sub_etype_adicionado, $entitys[$i]["sub_etype"]);
            }
            
            array_push($sqls, "INSERT INTO entity(id, text_label, small_label, description, etype, sub_etype_id, wikipedia, creation_time, modification_time, default_url, icon ) values (?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE description=?");
            array_push($values, [ $entity_id , $entitys[$i]["text_label"], $entitys[$i]["small_label"], $entitys[$i]["description"], $entitys[$i]["etype"], md5($entitys[$i]["sub_etype"]), $entitys[$i]["wikipedia"], $date->format('Y-m-d H:i:s'), $date->format('Y-m-d H:i:s'), $entitys[$i]["default_url"], $entitys[$i]["icon"], $entitys[$i]["description"] ]);

            $akas = $entitys[$i]["aka"];
            if ($akas != ""){
                $akas = explode(",", $akas);
                for($j = 0; $j < count($akas); $j++){
                    $akas[$j] = trim($akas[$j]);
                    if ( ! in_array($akas[$j] , $aka_adicionado) ) {
                        array_push($sqls,           "INSERT INTO entity_aka (id, entity_id, name) values(?, ?, ?) ON DUPLICATE KEY UPDATE entity_id = ?");
                        array_push($values,         [ md5($akas[$j]) ,$entity_id, $akas[$j],$entity_id]);
                        array_push($aka_adicionado, $akas[$j]);
                    }
                }
            }

            $references = $entitys[$i]["references"];
            for($j = 0; $j < count($references); $j++){
                array_push($sqls,           "INSERT INTO diagram_relationship_element_reference (id, entity_id, title, link1, about) values(?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE title = ?, description=?, about=?");
                array_push($values,         [ md5($references[$j]["title"]), $entity_id ,$references[$j]["title"], $references[$j]["link1"],$references[$j]["about"], $references[$j]["title"],$references[$j]["description"],$references[$j]["about"]]);
            }

        }
        return $mysql->ExecuteNoQuery($sqls, $values) ;
    }

    public function merge_to( $ip, $user, $post_data, $domain) {
        $mysql = new Mysql( $domain );
        $old_entity_id = $post_data["parameters"]["old_entity_id"];
        $new_entity_id = $post_data["parameters"]["new_entity_id"];
        $sqls = [];
        $values = [];

        $old_object = $mysql->DataTable("select * from entity where id= ?", [ $old_entity_id ])[0];
        $new_object = $mysql->DataTable("select * from entity where id= ?", [ $new_entity_id ])[0];

        if( $old_object["text_label"] !=  $new_object["text_label"]) {
            throw new Exception("O nome dos objetos são diferentes.");
        }
        array_push($sqls, "UPDATE entity_classification_item set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "UPDATE diagram_relationship_element set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "UPDATE diagram_relationship_element_reference set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "UPDATE organization_chart_item_entity set entity_id = ? where entity_id = ?");
        array_push($values, [$new_entity_id, $old_entity_id]);

        array_push($sqls, "DELETE FROM entity where id= ?");
        array_push($values, [$old_entity_id]);

        return $mysql->ExecuteNoQuery($sqls, $values);
    }

    public function to_type( $ip, $user, $post_data, $domain) {
        $mysql = new Mysql( $domain );
        $sql = "UPDATE entity SET etype= ? WHERE id = ?";
        return $mysql->ExecuteNoQuery($sql, [ $post_data["parameters"]["type"], $post_data["parameters"]["id"] ]);
    }

    public function search( $ip, $user, $post_data, $domain ) {
        //error_log("domain:" . $domain, 0);
        $mysql = new Mysql( $domain );
        $sql = "";
        $valores = [];
        if( $post_data["parameters"]["etype"] != "" ) {
            $sql = "SELECT ent.* from entity as ent WHERE ent.etype = ? and ( LOWER(ent.text_label) LIKE LOWER( ? )  or LOWER(ent.small_label) LIKE LOWER( ? )   )";
            $valores = [ $post_data["parameters"]["etype"], $post_data["parameters"]["text_label"], $post_data["parameters"]["text_label"]];
        } else {
            $sql = "SELECT ent.* from entity as ent WHERE  LOWER(ent.text_label) LIKE LOWER( ? )  or LOWER(ent.small_label) LIKE LOWER( ? )  ";
            $valores = [ $post_data["parameters"]["text_label"], $post_data["parameters"]["text_label"]];           
        }
        //error_log($sql, 0);
        //error_log(json_encode($valores), 0);
        $elements = $mysql->DataTable($sql, $valores);
        for($i = 0; $i < count($elements); $i++) {
            $elements[$i] = Entity::appendData($elements[$i], $domain);
        }
        return $elements;
    }

    public function duplicate( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "SELECT ent.* from entity as ent WHERE ent.etype = ? and ent.id <> ? and ent.text_label = ?  ";
        $valores = [ $post_data["parameters"]["etype"], $post_data["parameters"]["id"], $post_data["parameters"]["text_label"]];
        $elements = $mysql->DataTable($sql, $valores);
        for($i = 0; $i < count($elements); $i++) {
            $elements[$i] = Entity::appendData($elements[$i], $domain);
        }
        return $elements;
    }

    // Imagens da entidade: uma lista de PNGs (base64) mais um "rosto" opcional (1 PNG).
    // Endpoint dedicado, separado do save do mapa, porque os base64 sao grandes e nao devem
    // ser copiados para o diagram_relationship_history a cada save.
    public function load_images( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $entity_id = $post_data["parameters"]["entity_id"];
        $imagens = $mysql->DataTable("SELECT id, png_base64 FROM entity_image WHERE entity_id = ? ORDER BY creation_time ASC", [ $entity_id ]);
        $rosto = $mysql->DataTable("SELECT png_base64 FROM entity_face WHERE entity_id = ?", [ $entity_id ]);
        // Retorna um array (o cliente recebe dict direto; so faz base64-decode quando o
        // return e string). A face fica como string DENTRO do dict, entao chega intacta.
        return array( "images" => $imagens, "face" => ( count($rosto) > 0 ? $rosto[0]["png_base64"] : "" ) );
    }

    public function save_images( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $p = $post_data["parameters"];
        $entity_id = $p["entity_id"];
        $images = array_key_exists("images", $p) ? $p["images"] : array();
        $face   = array_key_exists("face", $p)   ? $p["face"]   : "";
        $sqls = array();
        $valuess = array();

        // entity_image tem FK para entity(id): garante que a entity exista antes de gravar.
        // Upsert nao-destrutivo (ON DUPLICATE KEY UPDATE id=id nao mexe em nada); se a caixa
        // ainda nao foi salva no mapa, cria uma linha minima que o save do mapa completa.
        array_push($sqls, "INSERT INTO entity (id, text_label, etype) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE id = id");
        array_push($valuess, [ $entity_id, $p["text_label"], $p["etype"] ]);

        // Upsert de cada imagem da lista.
        for($i = 0; $i < count($images); $i++) {
            array_push($sqls, "INSERT INTO entity_image (id, entity_id, png_base64) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE png_base64 = ?");
            array_push($valuess, [ $images[$i]["id"], $entity_id, $images[$i]["png_base64"], $images[$i]["png_base64"] ]);
        }

        // Apaga as que nao vieram na lista (mesmo padrao do delete de referencias no save do mapa).
        $existentes = $mysql->DataTable("SELECT id FROM entity_image WHERE entity_id = ?", [ $entity_id ]);
        for($i = 0; $i < count($existentes); $i++) {
            $achou = false;
            for($j = 0; $j < count($images); $j++) {
                if( $existentes[$i]["id"] == $images[$j]["id"] ) { $achou = true; break; }
            }
            if( ! $achou ) {
                array_push($sqls, "DELETE FROM entity_image WHERE id = ?");
                array_push($valuess, [ $existentes[$i]["id"] ]);
            }
        }

        // Rosto: grava (upsert) ou remove quando vazio.
        if( trim($face) != "" ) {
            array_push($sqls, "INSERT INTO entity_face (entity_id, png_base64) VALUES (?, ?) ON DUPLICATE KEY UPDATE png_base64 = ?");
            array_push($valuess, [ $entity_id, $face, $face ]);
        } else {
            array_push($sqls, "DELETE FROM entity_face WHERE entity_id = ?");
            array_push($valuess, [ $entity_id ]);
        }

        $mysql->ExecuteNoQuery($sqls, $valuess);
        return true;
    }

    // Subtipos (sub_etype) das entidades Other. Cada subtipo (chave = md5(nome), como no
    // import_all) pode ter um "rosto default" em base64 usado no mapa quando a Other nao tem
    // rosto proprio (fallback resolvido no load do mapa).
    public function load_subetypes( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        // Lista para o combo + o face_default de cada um (o cliente mostra o preview).
        return $mysql->DataTable("SELECT id, name, face_default FROM sub_etype ORDER BY name ASC", []);
    }

    public function set_subetype( $ip, $user, $post_data, $domain ) {
        // Define (ou limpa) o subtipo de UMA entidade. Nao mexe no rosto default do subtipo.
        $mysql = new Mysql( $domain );
        $p = $post_data["parameters"];
        $entity_id = $p["entity_id"];
        $nome = trim( $p["sub_etype_name"] );
        $sqls = array();
        $valuess = array();
        // Garante a entity (mesmo motivo do save_images: FK e caixa nao salva ainda).
        array_push($sqls, "INSERT INTO entity (id, text_label, etype) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE id = id");
        array_push($valuess, [ $entity_id, $p["text_label"], $p["etype"] ]);
        if( $nome != "" ) {
            $sub_id = md5( $nome );
            array_push($sqls, "INSERT INTO sub_etype (id, name) VALUES (?, ?) ON DUPLICATE KEY UPDATE name = name");
            array_push($valuess, [ $sub_id, $nome ]);
            array_push($sqls, "UPDATE entity SET sub_etype_id = ? WHERE id = ?");
            array_push($valuess, [ $sub_id, $entity_id ]);
        } else {
            array_push($sqls, "UPDATE entity SET sub_etype_id = NULL WHERE id = ?");
            array_push($valuess, [ $entity_id ]);
        }
        $mysql->ExecuteNoQuery($sqls, $valuess);
        return true;
    }

    public function set_subetype_face( $ip, $user, $post_data, $domain ) {
        // Define/remove o rosto default de um SUBTIPO (compartilhado por todas as Others dele).
        $mysql = new Mysql( $domain );
        $p = $post_data["parameters"];
        $nome = trim( $p["sub_etype_name"] );
        if( $nome == "" ) { return false; }
        $face = array_key_exists("face", $p) ? $p["face"] : "";
        $sub_id = md5( $nome );
        $sqls = array();
        $valuess = array();
        array_push($sqls, "INSERT INTO sub_etype (id, name) VALUES (?, ?) ON DUPLICATE KEY UPDATE name = name");
        array_push($valuess, [ $sub_id, $nome ]);
        if( trim($face) != "" ) {
            array_push($sqls, "UPDATE sub_etype SET face_default = ? WHERE id = ?");
            array_push($valuess, [ $face, $sub_id ]);
        } else {
            array_push($sqls, "UPDATE sub_etype SET face_default = NULL WHERE id = ?");
            array_push($valuess, [ $sub_id ]);
        }
        $mysql->ExecuteNoQuery($sqls, $valuess);
        return true;
    }

    // Gerencia o CONJUNTO de subtipos validos (tela global, nivel banco). Separado de
    // set_subetype (que so atribui um subtipo ja existente a uma entidade).
    public function create_subetype( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $nome = trim( $post_data["parameters"]["name"] );
        if( $nome == "" ) { return false; }
        $mysql->ExecuteNoQuery("INSERT INTO sub_etype (id, name) VALUES (?, ?) ON DUPLICATE KEY UPDATE name = name", [ md5($nome), $nome ]);
        return true;
    }

    public function delete_subetype( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $nome = trim( $post_data["parameters"]["name"] );
        if( $nome == "" ) { return false; }
        $id = md5( $nome );
        // Desvincula as entidades antes de apagar (FK entity.sub_etype_id -> sub_etype.id).
        $mysql->ExecuteNoQuery( array( "UPDATE entity SET sub_etype_id = NULL WHERE sub_etype_id = ?",
                                       "DELETE FROM sub_etype WHERE id = ?" ),
                                array( [ $id ], [ $id ] ) );
        return true;
    }

    public static function appendData($entity_json, $domain){
        $mysql = new Mysql( $domain );
        $entity_json["references"] = $mysql->DataTable("SELECT drer.id, drer.title, drer.link1, drer.link2, drer.link3, drer.description as descricao FROM diagram_relationship_element_reference AS drer where drer.entity_id = ?", [$entity_json["id"]]);

        $entity_json["classification"] = $mysql->DataTable("select eci.format_date as format_date, eci.entity_id as entity_id, eci.start_date as start_date, eci.end_date as end_date, eci.id as id, clsi.text_label as text_label_choice, cls.text_label as text_label, clsi.id as classification_item_id from entity_classification_item as eci inner join classification_item as clsi on eci.classification_item_id = clsi.id inner join classification as cls on clsi.classification_id = cls.id where eci.entity_id = ?", [$entity_json["id"]]);
        return $entity_json;
    }
}

?>

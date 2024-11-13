<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class OrganizationChart
{
    public function create( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $sql = "INSERT INTO organization_chart (id, organization_id, text_label, person_id) values(?, ?, ?, ?)";
        $valores = [$post_data["parameters"]["id"], $post_data["parameters"]["organization_id"]  , $post_data["parameters"]["text_label"], $user->id ];
        return $mysql->ExecuteNoQuery($sql, $valores);
    }    

    public function save($ip, $user, $post_data, $domain ){
        $mysql = new Mysql( $domain );
        $sqls = array();
        $valuess = array();

        array_push($sqls,  "INSERT INTO organization_chart (id, organization_id, text_label, person_id) values(?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ? " );
        array_push( $valuess, [$post_data["parameters"]["id"], $post_data["parameters"]["organization_id"]  , $post_data["parameters"]["text_label"], $user->id, $post_data["parameters"]["text_label"] ] );

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];

            array_push($sqls, "INSERT INTO organization_chart_item(id, text_label, etype, organization_chart_id, organization_chart_item_parent_id, sequencia, x) values(?, ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?,  sequencia=?, x=?");
            array_push( $valuess,[ $element["id"], $element["text_label"], $element["etype"], $post_data["parameters"]["id"], $element["organization_chart_item_parent_id"], $i, $element["x"], $element["text_label"], $i , $element["x"] ]);

            for($j = 0; $j < count($element["entitys"]); $j++){
                $entity = $element["entitys"][$j];
                array_push($sqls, "INSERT INTO organization_chart_item_entity(id, organization_chart_item_id, entity_id) values(?, ?, ?) ON DUPLICATE KEY UPDATE  entity_id=?");
                array_push( $valuess,[ substr( $element["id"] , 0, 20)  . $entity["id"], $element["id"], $entity["id"], $entity["id"]  ]);
            }
        }

        // LIMPEZAS DE DADOS QUE NAO QUEREMOS MAIS, EXCLUIDOS PELO USU[ARIO]
        

        array_push( $sqls ,"INSERT INTO organization_chart_history(id, person_id, organization_chart_id, json) values(?, ?, ?, ?)");
        array_push($valuess, [ $mysql->gen_uuid(), $user->id, $post_data["parameters"]["id"], json_encode($post_data["parameters"]) ]);

        return ( $mysql->ExecuteNoQuery($sqls, $valuess) > 0 );
    }

    public function load( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        $buffer_diagram =  $mysql->DataTable("SELECT * from organization_chart where id = ?", [ $post_data["parameters"]["id"] ])[0];
        $buffer_diagram["elements"] =  $mysql->DataTable("select * from organization_chart_item where organization_chart_id = ? order by sequencia asc", [ $post_data["parameters"]["id"] ]);
        
        for($i = 0; $i < count($buffer_diagram["elements"]); $i++) {
            $buffer_diagram["elements"][$i]["entitys"] = $mysql->DataTable("SELECT et.* FROM organization_chart_item_entity as ci inner join entity as et on ci.entity_id = et.id where ci.organization_chart_item_id = ?", [$buffer_diagram["elements"][$i]["id"]]);
        }

        $buffer_diagram["organization"] = $mysql->DataTable("select * from entity where id= ?", [$buffer_diagram["organization_id"]])[0];

        return $buffer_diagram;
    }

}

?>

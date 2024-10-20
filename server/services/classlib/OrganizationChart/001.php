<?php

//error_reporting(E_ALL);

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class OrganizationChart
{

    public function load( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        
        return $buffer_diagram;
    }



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

        //$lock = $this->has_lock($post_data["parameters"]["id"]);
        //if( $lock != null ){
        //    if( $lock["person_id"] != $user->id ) {
        //        return false;
        //    }
        //}
        array_push($sqls,  "INSERT INTO organization_chart (id, organization_id, text_label, person_id) values(?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ? " );
        array_push( $valuess, [$post_data["parameters"]["id"], $post_data["parameters"]["organization_id"]  , $post_data["parameters"]["text_label"], $user->id, $post_data["parameters"]["text_label"] ] );

        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];

            array_push($sqls, "INSERT INTO organization_chart_item(id, text_label, etype, organization_chart_id, organization_chart_item_parent_id) values(?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE text_label = ?");
            array_push( $valuess,[ $element["id"], $element["text_label"], $element["etype"], $element["organization_chart_id"], $element["organization_chart_item_parent_id"], $element["text_label"]  ]);
            
        }

        // LIMPEZAS DE DADOS QUE NAO QUEREMOS MAIS, EXCLUIDOS PELO USU[ARIO]
        // Assim nao tem performance, mas estou envitando ijeçao de sql tal como pode ser feito em NOT IN()
        // se fosse garantido NOT IN() contra injeçao de sql eu faria com notint mais performatico e mais fáci.
        for($i = 0; $i < count($post_data["parameters"]["elements"]); $i++) {
            $element = $post_data["parameters"]["elements"][$i];
            $buffer_links = $mysql->DataTable("select * from organization_chart_item where organization_chart_id = ?", [ $post_data["parameters"]["id"] ]);
            for($j = 0; $j < count($buffer_links); $j++) {
                $existe = false;
                for($k = 0; $k < count($element["to"]); $k++) {
                    if( $buffer_links[$j]["id"] ==  $element["to"][$k]["id"]) {
                        $existe = true;
                        break;
                    }
                }
                if( ! $existe ){
                    for($k = 0; $k < count($element["from"]); $k++) {
                        if( $buffer_links[$j]["id"] ==  $element["from"][$k]["id"]) {
                            $existe = true;
                            break;
                        }
                    }
                }
                if( ! $existe ){
                    array_push($sqls, "DELETE FROM organization_chart_item WHERE id = ?");
                    array_push($valuess, [ $buffer_links[$j]["id"] ]);
                }
            }
        }


        array_push( $sqls ,"INSERT INTO organization_chart_history(id, person_id, organization_chart_id, json) values(?, ?, ?, ?)");
        array_push($valuess, [ $mysql->gen_uuid(), $user->id, $post_data["parameters"]["id"], json_encode($post_data["parameters"]) ]);


        
        return ( $mysql->ExecuteNoQuery($sqls, $valuess) > 0 );
    }


}

?>

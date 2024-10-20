<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class Domain
{
    public static function list() {
        return Mysql::domains();
    }

    public static function domain($name){
        $domains = Mysql::domains();
        for($i = 0; $i < count($domains); $i++) {
            if( $domains[$i]["name"] == $name){
                return $domains[$i];
            }
        }
        return null;
    }
}

?>
<?php
require_once dirname(__DIR__) . "/api/json.php";
require_once dirname(__DIR__) . "/api/mysql.php";

function millisecsBetween($dateOne, $dateTwo, $abs = true) {
    $func = $abs ? 'abs' : 'intval';
    return $func(strtotime($dateOne) - strtotime($dateTwo)) * 1000;
}

$ip = null;
if (!empty($_SERVER['HTTP_CLIENT_IP'])) {
    $ip = $_SERVER['HTTP_CLIENT_IP'];
} elseif (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
    $ip = $_SERVER['HTTP_X_FORWARDED_FOR'];
} else {
    $ip = $_SERVER['REMOTE_ADDR'];
}

// DADOS QUE VEM DO JSON POST + url
$part = explode("/", $_SERVER["REQUEST_URI"]);
$post_data = json_decode(file_get_contents('php://input'), true); 
$token_request = md5(uniqid(rand(), true));
try{
    $antes = (new \DateTime());
    $return_metehod = "";
    $CONFIG = Json::FromFile_v2(dirname(__DIR__) . "/data/config.json");
    $federation_element = $CONFIG["federation"][ $post_data["federation_id"] ];
    if( $federation_element == null){
        throw new Exception('Key inválida.');
    }
    if(! in_array( $post_data["class"] . "." . $post_data["method"] , $federation_element["method"])){
        throw new Exception('A Class.Method não está na lista de permissões.');
    }
    require_once __DIR__ . "/classlib/". $post_data["class"] . "/" . $post_data["version"] . ".php";
    $class = $post_data["class"];
    $method = $post_data["method"];
    $domain = $post_data["domain"];
    $return_metehod = (new $class)->$method( $ip, null, $post_data, $federation_element["domain"]  ); 
    $agora = (new \DateTime());
    $post_data["status"] = true;
    $post_data["return"] = $return_metehod;
    $post_data["parameters"] = "";
    echo json_encode($return_metehod);
} catch (Exception $e) {
    echo json_encode(array("status" => false, "return" => null, "error" => $e->getMessage() ));
} 

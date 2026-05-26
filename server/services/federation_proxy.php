<?php
require_once dirname(__DIR__) . "/api/json.php";
require_once dirname(__DIR__) . "/api/mysql.php";

require_once __DIR__ . "/classlib/session.php";
require_once __DIR__ . "/classlib/User/001.php";
require_once __DIR__ . "/classlib/Domain/001.php";

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

function request_federation($url, $data){
    $url = $url . "/cml/services/federation.php";
    try{
        //$postdata = http_build_query($data);
        $opts = array(
          'http' => array(
            'method'  => 'POST',
            'header'  => 'Content-type: application/json',
            'content' => json_encode($data, true)
          )
        );
        $context  = stream_context_create($opts);
        //error_log($context, 0);
        $returned = file_get_contents( $url, false, $context);
        error_log($returned, 0);
        return json_decode( $returned , true);
    } catch (Exception $e) {
        echo json_encode(array("status" => false, "return" => null, "error" => $e->getMessage() ));
    }
}

// DADOS QUE VEM DO JSON POST + url
$part = explode("/", $_SERVER["REQUEST_URI"]);
$post_data = json_decode(file_get_contents('php://input'), true); 

$token_request = md5(uniqid(rand(), true));
try{
    $session = new Session();
    $antes = (new \DateTime());
    $CONFIG = Json::FromFile_v2(dirname(__DIR__) . "/data/config.json");
    
    // -------------------- FORCAR O CARREGAMENTO AQUI ENQUATNO NAO FAÇO SISTEMA DE LOGIN
    // TUDO QUE VAI AQUI É CRIPTOGRAFIA SIMÉTRICA...... QUE NAO FIZ AINDA....
    $post_data["parameters"] = substr($post_data["parameters"], 8);
    $post_data["parameters"] = json_decode(  $post_data["parameters"], true );
    $person_session = $session->getKeyDecrypt($post_data["session"], $post_data["domain"]);
    $user = new User();
    $user->load($person_session["person_id"], $post_data["domain"]); 
    //-------------------------------------------------------------------------
    $end_array = [];
    foreach( $CONFIG["connections"][ $post_data["domain"] ]["federation"] as $federation_id ){
        $federation = $CONFIG["federation"][ $federation_id ];
        if( in_array( $post_data["class"] . "." . $post_data["method"], $federation["method"]) ){
            $post_data["federation_id"] = $federation_id;
            array_push( $end_array, array( "name" => $federation["name"], "return" => request_federation($federation["url"], $post_data)) );
        }
    }

    $agora = (new \DateTime());
    $post_data["status"] = true;
    $post_data["return"] = $end_array;

    $post_data["parameters"] = "";
    echo json_encode($post_data);
} catch (Exception $e) {
    echo json_encode(array("status" => false, "return" => null, "error" => $e->getMessage() ));
} 


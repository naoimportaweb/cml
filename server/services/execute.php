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

// DADOS QUE VEM DO JSON POST + url
$part = explode("/", $_SERVER["REQUEST_URI"]);

$post_data = json_decode(file_get_contents('php://input'), true); 
//(class, version, method, parameters) // OR //(public_key)


$token_request = md5(uniqid(rand(), true));
try{
    $session = new Session();
    $antes = (new \DateTime());
    $CONFIG = Json::FromFile_v2(dirname(__DIR__) . "/data/config.json");
    //https://www.slingacademy.com/article/ways-to-create-an-object-in-php/
    //https://stackoverflow.com/questions/1005857/how-to-call-a-function-from-a-string-stored-in-a-variable

    // se tiver criptografado, entao temos que descriptografar
    //if (array_key_exists('token',$post_data)){
    //    $post_data["parameters"] = Session::decrypt( $post_data["token"], $post_data["parameters"] );
    //}

    $return_metehod = "";
    // chamar os métodos, alguns sao fixos pela logica, os outros são dinamicos pelo uso.
    if( $post_data["class"] == "Domain" && $post_data["method"] == "list" ) {
        $post_data["parameters"] = json_decode(  substr($post_data["parameters"], 8), true ) ;
        $return_metehod = Domain::list();
    } else if( $post_data["class"] == "Session" && $post_data["method"] == "publickey" ) {
        $post_data["parameters"] = json_decode(  substr($post_data["parameters"], 8), true ) ;
        $return_metehod = $session->publickey($post_data, $post_data["domain"]); 
    } else if( $post_data["class"] == "Session" && $post_data["method"] == "login" ) {
        $post_data["parameters"] = json_decode(  substr($post_data["parameters"], 8), true ) ;
        $return_metehod = $session->login($post_data["parameters"]["username"], $post_data["parameters"]["password"], $post_data["parameters"]["simetric_key"], $post_data["domain"]); 
        $return_metehod = $session->encrypt($post_data["parameters"]["simetric_key"], "000", json_encode( $return_metehod )); // aqui mandei para 000 para tirar a criptotgrafia de retorno...
    } else if( $post_data["class"] == "Session" && $post_data["method"] == "register" ) {
        $post_data["parameters"] = json_decode(  substr($post_data["parameters"], 8), true ) ;
        $return_metehod = $session->register($ip, null, $post_data, $post_data["domain"]); 
    } else{
        // -------------------- FORCAR O CARREGAMENTO AQUI ENQUATNO NAO FAÇO SISTEMA DE LOGIN
        // TUDO QUE VAI AQUI É CRIPTOGRAFIA SIMÉTRICA...... QUE NAO FIZ AINDA....
        $post_data["parameters"] = substr($post_data["parameters"], 8);
        $post_data["parameters"] = json_decode(  $post_data["parameters"], true );
        $person_session = $session->getKeyDecrypt($post_data["session"], $post_data["domain"]);
        $user = new User();
        $user->load($person_session["person_id"], $post_data["domain"]); 
        //-------------------------------------------------------------------------
        require_once __DIR__ . "/classlib/". $post_data["class"] . "/" . $post_data["version"] . ".php";
        $class = $post_data["class"];
        $method = $post_data["method"];
        $domain = $post_data["domain"];
        $return_metehod = (new $class)->$method( $ip, $user, $post_data, $domain  );        
    }
    $agora = (new \DateTime());
    $post_data["status"] = true;
    $post_data["return"] = $return_metehod;

    // tem que ver na federacao quem tem também retorno.
    
    if (array_key_exists('token',$post_data) and $post_data["token"] != ""){
        $post_data["return"] = $session->encrypt( $post_data["token"], $post_data["return"] );
    }
    $post_data["parameters"] = "";
    echo json_encode($post_data);
} catch (Exception $e) {
    echo json_encode(array("status" => false, "return" => null, "error" => $e->getMessage() ));
} 

// User, 001.php, 
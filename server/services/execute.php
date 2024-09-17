<?php
require_once dirname(__DIR__) . "/api/json.php";
require_once dirname(__DIR__) . "/api/mysql.php";
require_once __DIR__ . "/classlib/session.php";
require_once __DIR__ . "/classlib/User/001.php";

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
error_log(file_get_contents('php://input'), 0);


$token_request = md5(uniqid(rand(), true));
try{
    $antes = (new \DateTime());
    //https://www.slingacademy.com/article/ways-to-create-an-object-in-php/
    //https://stackoverflow.com/questions/1005857/how-to-call-a-function-from-a-string-stored-in-a-variable

    // se tiver criptografado, entao temos que descriptografar
    if (array_key_exists('token',$post_data)){
        $post_data["parameters"] = Session::decrypt( $post_data["token"], $post_data["parameters"] );
    }

    $return_metehod = "";
    // chamar os métodos, alguns sao fixos pela logica, os outros são dinamicos pelo uso.
    if( $post_data["class"] == "Session" && $post_data["method"] == "getkey" ) {
        $return_metehod = Session::getkey( $post_data["parameters"]["public_key"] );
    } else if( $post_data["class"] == "Session" && $post_data["method"] == "create" ) {
        $return_metehod = Session::create($post_data["token"], $post_data["parameters"]["user"], $post_data["parameters"]["password"]);
    } else{
        // -------------------- FORCAR O CARREGAMENTO AQUI ENQUATNO NAO FAÇO SISTEMA DE LOGIN
        $user = new User();
        $user->load("1");
        //-------------------------------------------------------------------------

        require_once __DIR__ . "/classlib/". $post_data["class"] . "/" . $post_data["version"] . ".php";
        $class = $post_data["class"];
        $method = $post_data["method"];
        $return_metehod = (new $class)->$method( $ip, $user, $post_data  );        
    }
    //error_log( json_encode($return_metehod), 0);
    $agora = (new \DateTime());
    $post_data["status"] = true;
    $post_data["return"] = $return_metehod;
    if (array_key_exists('token',$post_data)){
        $post_data["return"] = Session::encrypt( $post_data["token"], $post_data["return"] );
    }
    error_log(json_encode($post_data), 0);
    echo json_encode($post_data);
} catch (Exception $e) {
    echo json_encode(array("status" => false, "return" => null, "error" => $e->getMessage() ));
} 

// User, 001.php, 
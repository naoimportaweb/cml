<?php

class Session
{
    //https://stackoverflow.com/questions/4629537/how-to-encrypt-data-in-php-using-public-private-keys
    public static function getkey( $public_key ) {
        $mysql = Mysql("");
        $encrypted = "";
        $objeto = array("key" => Session::getToken(128), "token" => md5( $public_key ));
        if( $mysql->ExecuteNoQuery( "INSERT INTO session ('token', 'key', 'login') values( ?, ?, ? )", [$objeto["token"], $objeto["key"], 0 ] ) ){
            $text = json_decode($objeto, true);
            openssl_public_encrypt($text, $encrypted, $public_key);
            return $encrypted;
        }
        return null;
    }

    public static function create( $token, $user, $password ) {
        return "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678";
    }

    public static function decrypt( $token, $data) {
        return $data;
    }
    public static function encrypt( $token, $data) {
        return $data;
    }

    public static function get( $token ) {
        $mysql = Mysql("");
        return $mysql->DataTable("select * from session where toke = ? ")[0];
    }

    public static function getToken($length)
    {
        $token = "";
        $codeAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        $codeAlphabet.= "abcdefghijklmnopqrstuvwxyz";
        $codeAlphabet.= "0123456789";
        $codeAlphabet.= "!@#$%¨&*";
        $max = strlen($codeAlphabet); // edited

        for ($i=0; $i < $length; $i++) {
            $token .= $codeAlphabet[crypto_rand_secure(0, $max-1)];
        }
        return $token;
    }
}

// usuario loga e solicita uma chave secreta (cliente envia publick key)
// o servidor gera uma nova chave secreta e assosia ao publickey do cliente
//

?>




<?php
//https://stackoverflow.com/questions/4629537/how-to-encrypt-data-in-php-using-public-private-keys



require_once dirname(dirname(__DIR__)) . "/api/mysql.php";
require_once dirname(dirname(__DIR__)) . "/api/aeshelper.php";
require_once dirname(dirname(__DIR__)) . "/api/json.php";

class Session
{
    public $public_key;
    public $privete_key;
    public $path_certs;
    function __construct() {
        $config = Json::FromFile(    dirname(dirname(__DIR__))   . "/data/config.json");
        $this->path_certs = $config->crypto->path;
        $this->public_key = $this->__load();

    }
    
    function __load() {
        //creating private key
        if( ! file_exists( $this->path_certs . '/cml.pem' )) {
            $privkey = openssl_pkey_new();
            openssl_pkey_export_to_file( $privkey, $this->path_certs . '/cml.pem');
        }
       
        //using .pem file with private key.
        $this->privete_key = openssl_get_privatekey(file_get_contents($this->path_certs . '/cml.pem'));
        if ($this->privete_key === false) {
            var_dump(openssl_error_string());
            return null;
        } else {
            $key_details = openssl_pkey_get_details($this->privete_key);
            return $key_details["key"]; 
        }
    }

    function publickey(){
        return array( "public" => $this->public_key, "salt" => "1111" ); #forca
    }

    function login( $username, $password, $simetric_key){
        $mysql = new Mysql("");
        $sql = "select * from person where username=? and password=?";

        $user_databse = $mysql->DataTable( $sql, [ $username, $password ])[0];
        if( $user_databse["username"] == $username && $user_databse["password"] == $password ) {
            //$token = Session::getToken(32 );
            $id    = Session::getToken(128);

            $sql = "INSERT INTO person_sesion(id, person_id, simetric_key) values(?,?, ?)";
            $values = [$id, $user_databse["id"], $simetric_key];

            $mysql->ExecuteNoQuery([$sql], [$values]);
            $retorno = array( "id" => $user_databse["id"], "token" => $id );
            return $retorno;
        }
        return array();
    }
    
    public function decrypt( $token, $data) {
        $version =       substr($data, 0, 5);
        $alg =           substr($data, 5, 3);
        $encrypted =     base64_decode(substr($data, 8));
        
        if( $alg == "000") {
            return $encrypted ;
        }
        if( $alg == "001") {
            $decrypted = "";
            openssl_private_decrypt($encrypted, $decrypted, $this->privete_key);
            return $decrypted;
        }  
        if( $alg == "002") {
            return $encrypted ;
            //error_log("Decriptar: " . $encrypted, 0);
            //$decrypted = AesHelper::decrypt($encrypted, $token);
            //error_log("Decriptado final: " . $decrypted, 0);
            //return $decrypted;
        }        
    }
    public function encrypt( $token, $alg, $data) {
        if ($alg == "001") {
            $encrypted = "";
            openssl_public_encrypt($data, $encrypted, $this->public_key);
            $data = "000000" . $alg . base64_encode($encrypted);
        } else if ($alg == "002") {
            $data = "00000002" . base64_encode($data);
            //$encrypted = AesHelper::encrypt($data, $token, $token);
            //$data = "00000002" . $encrypted;
        } else {
            $data = "00000000" . base64_encode($data);
        }
        return $data;
    }

    

    public function getKeyDecrypt( $session_id ) {
        $mysql = new Mysql("");
        return $mysql->DataTable("select * from person_sesion where id = ? ", [$session_id])[0];
    }

    public static function getToken($length)
    {
        $token = "";
        $codeAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        $codeAlphabet.= "abcdefghijklmnopqrstuvwxyz";
        $codeAlphabet.= "0123456789";
        $codeAlphabet.= "!@#$%&*";
        $max = strlen($codeAlphabet); // edited

        for ($i=0; $i < $length; $i++) {
            $token .= $codeAlphabet[random_int(0, $max-1)];
        }
        return $token;
    }
}

// usuario loga e solicita uma chave secreta (cliente envia publick key)
// o servidor gera uma nova chave secreta e assosia ao publickey do cliente
//

?>




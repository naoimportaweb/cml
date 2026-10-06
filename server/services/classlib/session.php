<?php
//https://stackoverflow.com/questions/4629537/how-to-encrypt-data-in-php-using-public-private-keys



require_once dirname(dirname(__DIR__)) . "/api/mysql.php";
require_once dirname(dirname(__DIR__)) . "/api/aeshelper.php";
require_once dirname(dirname(__DIR__)) . "/api/json.php";
require_once __DIR__ . "/Domain/001.php";

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

    public function exists( $username, $domain ) {
        $mysql = new Mysql( $domain );
        $buffer = $mysql->DataTable("select * from person where username = ? ", [$username]);
        return count($buffer) > 0;
    }

    //public function exists( $ip, $user, $post_data, $domain ) {
    //    return array( "status" => $this->__exists($post_data["parameters"]["username"]) );
    //}

    public function register( $ip, $user, $post_data, $domain ) {
        $mysql = new Mysql( $domain );
        // CONVITE, AGORA NÁO É MAIS OBRIGATÓRIO, TEM QUE OLHAR NO JSON DE CONFIGURACAO CONFIG.JSON
        if ($this->exists($post_data["parameters"]["username"], $domain )) {
            return array( "status" => false, "mensage" => "Usuário já existe." );
        } else {
            $domain_json = Domain::domain(  $domain );
            if( $domain_json == null ){
                return array( "status" => false, "mensage" => "Não foi possível realizar cadastro." );
            }
            if( $domain_json["restricted"] ){
                $person_enter = $mysql->DataTable("select * from person_enter where person_id is null and key_enter = ? ", [$post_data["parameters"]["invitation"]]);
                if (count($person_enter) == 0) {
                    return array( "status" => false, "mensage" => "Convite inválido" );
                }
            }

            $user_id = $mysql->gen_uuid();
            $sqlss   = [];
            $valuess = [];
            
            // password_hash do que o cliente mandou: a coluna deixa de ser a propria
            // credencial. Ver o comentario em __confere_senha__.
            $sql1 = "INSERT INTO person(id, name, username, password, salt, email) values( ?, ?, ?, ?, ?, ?);";
            $valores1 = [ $user_id , $post_data["parameters"]["username"], $post_data["parameters"]["username"], password_hash( $post_data["parameters"]["password"], PASSWORD_DEFAULT ),$post_data["parameters"]["salt"],$post_data["parameters"]["email"]];
            array_push($sqlss, $sql1);
            array_push($valuess, $valores1);

            if( $domain_json["restricted"] ){
                $sql2 = "UPDATE person_enter set person_id= ? where key_enter = ?";
                $valores2 = [ $user_id,  $post_data["parameters"]["invitation"]];
                array_push($sqlss,   $sql2);
                array_push($valuess, $valores2);
            }
            
            if( $mysql->ExecuteNoQuery( $sqlss, $valuess ) > 0) {
                return array( "status" => true, "mensage" => "Realize o Login" );
            } else {
                return array( "status" => false, "mensage" => "Convite inválido" );
            }
        } // else do usuário já existe
    }

    function publickey($post_data, $domain){
        $mysql = new Mysql( $domain );
        $sql = "select salt from person where username=?";
        $salt = $mysql->DataTable($sql, [ $post_data["parameters"]["username"] ]) [0]["salt"];
        return array( "public" => $this->public_key, "salt" => $salt ) ; 
    }

    // O que o cliente envia e sha256(senha + salt). ANTES isto era comparado DIRETO com a
    // coluna, no proprio SELECT -- ou seja, o valor guardado ERA a credencial: quem lesse a
    // coluna (ou o create.sql, que publicava a do usuario semeado) entrava sem quebrar nada.
    //
    // Agora a coluna guarda password_hash() desse valor e a conferencia e com password_verify.
    // O CLIENTE NAO MUDA: ele continua mandando o mesmo sha256. E a migracao e calculavel a
    // partir da propria coluna -- basta reescrever cada linha com o bcrypt dela mesma, uma vez
    // (bloco no fim de server/data/create.sql).
    //
    // A busca passou a ser so por username: com bcrypt o hash tem sal proprio e muda a cada
    // gravacao, entao procurar pelo valor no WHERE nunca mais acharia nada.
    private static function __confere_senha__( $enviado, $guardado ) {
        if( $guardado === null || $guardado === "" ) {
            return false;
        }
        if( password_verify( $enviado, $guardado ) ) {
            return true;
        }
        // Compatibilidade com instalacao ainda nao migrada: aceita o formato antigo, mas so
        // ele -- hash_equals em vez de == para nao vazar tempo. Quem cair aqui tem a linha
        // reescrita logo abaixo, entao a segunda entrada ja e pelo caminho novo.
        return hash_equals( (string)$guardado, (string)$enviado );
    }

    function login( $username, $password, $simetric_key, $domain){
        $mysql = new Mysql( $domain );
        $sql = "select * from person where username=?";

        // A recusa devolve id/token nulos, e nao array(): o json_encode manda array()
        // vazio como [] — uma lista — e o cliente indexa o retorno por "id".
        $recusado = array( "id" => null, "token" => null );

        $buffer = $mysql->DataTable( $sql, [ $username ]);
        if( count( $buffer ) == 0 ) {
            // Sem esta guarda o [0] de um resultado vazio vira null e a comparacao
            // abaixo acessa indice de null.
            return $recusado;
        }
        $user_databse = $buffer[0];
        if( Session::__confere_senha__( $password, $user_databse["password"] ) ) {
            // Entrou pelo formato antigo? Reescreve a linha no formato novo agora, sem pedir
            // nada ao usuario: a migracao acontece sozinha no primeiro login de cada conta.
            if( !password_verify( $password, (string)$user_databse["password"] ) ) {
                $mysql->ExecuteNoQuery(
                    ["UPDATE person SET password=? WHERE id=?"],
                    [[ password_hash( $password, PASSWORD_DEFAULT ), $user_databse["id"] ]] );
            }
            //$token = Session::getToken(32 );
            $id    = Session::getToken(128);

            $sql = "INSERT INTO person_sesion(id, person_id, simetric_key) values(?,?, ?)";
            $values = [$id, $user_databse["id"], $simetric_key];

            $mysql->ExecuteNoQuery([$sql], [$values]);
            $retorno = array( "id" => $user_databse["id"], "token" => $id );
            return $retorno;
        }
        return $recusado;
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
            //$decrypted = AesHelper::decrypt($encrypted, $token);
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

    

    public function getKeyDecrypt( $session_id, $domain ) {
        $mysql = new Mysql( $domain );
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




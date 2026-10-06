<?php

require_once dirname(dirname(dirname(__DIR__))) . "/api/mysql.php";

class User
{
    public $id;
    public $name;
    public $username;

    

    public function teste( $ip, $user, $post_data, $domain ) {
        return array("username" => $post_data["parameters"]["username"]);
    }

    public function load( $id , $domain ) {
        $mysql = new Mysql( $domain );
        $this->load_data( $mysql->DataTable("SELECT * from person where id = ?", [ $id ])[0] );
        return ( $this->id != null);
    }

    public function load_data( $datatable ) {
        $this->id       = $datatable["id"];
        $this->name     = $datatable["name"];
        $this->username = $datatable["username"];
    }

    // Trocar a propria senha. Metodo dinamico: a assinatura de 4 argumentos e o contrato do
    // execute.php, e o $user ja chega resolvido pelo token da sessao -- e por isso que nao ha
    // (nem pode haver) um "username" nos parametros: ninguem troca a senha de outro por aqui.
    //
    // Exige a SENHA ATUAL junto. Sem isso, uma sessao sequestrada trocaria a senha e trancaria
    // o dono para fora -- o roubo de sessao passa a ser roubo da conta.
    //
    // O cliente manda sha256(senha + salt), como no login; o salt novo vem junto porque trocar
    // a senha e a hora certa de girar um salt que pode ser fraco (o semeado era '1111').
    public function change_password( $ip, $user, $post_data, $domain ) {
        if( $user == null || $user->id == null ) {
            return array( "status" => false, "mensage" => "Sessão inválida." );
        }
        $atual = isset($post_data["parameters"]["atual"]) ? $post_data["parameters"]["atual"] : "";
        $nova  = isset($post_data["parameters"]["nova"])  ? $post_data["parameters"]["nova"]  : "";
        $salt  = isset($post_data["parameters"]["salt"])  ? $post_data["parameters"]["salt"]  : "";
        if( $atual === "" || $nova === "" || $salt === "" ) {
            return array( "status" => false, "mensage" => "Informe a senha atual e a nova." );
        }

        $mysql = new Mysql( $domain );
        $linha = $mysql->DataTable("SELECT id, password FROM person WHERE id = ?", [ $user->id ]);
        if( count($linha) == 0 ) {
            return array( "status" => false, "mensage" => "Sessão inválida." );
        }
        $guardado = (string)$linha[0]["password"];
        $confere = password_verify( $atual, $guardado )
                   || ( $guardado !== "" && hash_equals( $guardado, (string)$atual ) );
        if( !$confere ) {
            return array( "status" => false, "mensage" => "A senha atual não confere." );
        }
        if( hash_equals( (string)$atual, (string)$nova ) ) {
            return array( "status" => false, "mensage" => "A senha nova é igual à atual." );
        }

        // A senha nova entra ja no formato novo, e o salt gira junto.
        $mysql->ExecuteNoQuery(
            ["UPDATE person SET password=?, salt=? WHERE id=?"],
            [[ password_hash( $nova, PASSWORD_DEFAULT ), $salt, $user->id ]] );

        // As OUTRAS sessoes caem: trocar a senha e o que se faz quando se desconfia de alguem
        // dentro, e manter as sessoes vivas esvaziaria o gesto. A desta janela sobrevive.
        $mysql->ExecuteNoQuery(
            ["DELETE FROM person_sesion WHERE person_id = ? AND id <> ?"],
            [[ $user->id, $post_data["session"] ]] );

        return array( "status" => true, "mensage" => "Senha alterada." );
    }

}

?>
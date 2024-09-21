<?php

//use PDO;
//DROP USER root@localhost;
//CREATE USER root@localhost IDENTIFIED BY '123456';
//GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost';
//FLUSH PRIVILEGES;

require_once __DIR__ . '/json.php';

class Mysql
{
    var $con = null;
    var $action = false;
    
    function __construct($config) {
        if( $config == "" ) {
            $config = Json::FromFile(dirname(__DIR__) . "/data/config.json");
        }
        $this->CONFIG = $config;
    }
    
    public function __destruct() { 
        //$this->con->query('KILL CONNECTION_ID()');
        //unset($this->con);
        $this->con = null;
    }

    public function  Connection(){
        try
        {
            if($this->con == null){
                $port = 3306;
                $this->con = new PDO('mysql:host=' . $this->CONFIG->connection->host . ';port='. $port .';charset=utf8;dbname=' . $this->CONFIG->connection->name, $this->CONFIG->connection->user, $this->CONFIG->connection->password);
                $this->con->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            }
            return $this->con;
        } catch (PDOException $e) {
            throw $e;
        }
    }
    
    public function hasColumn($database, $entity, $field){
        $values = [$database, $entity, $field->name];
        $sql = "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=? and column_name =?";
        try{
            $query = $this->Connection()->prepare($sql);
            $query->execute($values);
            return count($query->fetchAll(PDO::FETCH_ASSOC)) > 0;
        }catch(Exception $e){
            throw $e;
        }
        return false;
    }
    
    public function createColumn($database, $entity, $field){
        $values = [$database, $entity, $field->name];
        $sql = "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=? and column_name =?";
        try{
            $query = $this->Connection()->prepare($sql);
            $query->execute($values);
            if( count($query->fetchAll(PDO::FETCH_ASSOC)) == 0){
                
                //{"name" : "processo_vesao_id", "type" :  "integer"}
                if($field->type == "integer"){
                    $field->type = "bigint";
                }
                if($field->type == "decimal"){
                    $field->type = "decimal(10,10)";
                }
                if($field->type == "monetary"){
                    $field->type = "decimal(10,2)";
                }
                if($field->type == "varchar"){
                    $field->type = "varchar(255)";
                }
                $sql = "ALTER TABLE ". $entity ." ADD ". $field->name ." " . $field->type;
                $query = $this->Connection()->prepare($sql);
                $query->execute($values);
                return $query->rowCount(); 
            } 
        }catch(Exception $e){
            error_log('Error: ' . $e->getMessage() . ' in ' . $sql . ' parms ' . json_encode($values), 0);
            throw $e;
        } finally {
            if($this->action == false) {
                $this->con = null;
            }
        }
        return null;
    }
    
    //{"fk" : "processo_vesao_id", "table" : "processo_vesao", "key" : "_id" }
    public function createFk($database, $entity, $fk) {
        $name = "FK_" . $entity .  $fk->fk ;
        $values = [ $name];
        $sql = "SELECT * FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_NAME   = ? AND CONSTRAINT_TYPE   = 'FOREIGN KEY' ";
        try{
            $query = $this->Connection()->prepare($sql);
            $query->execute($values);
            if( count($query->fetchAll(PDO::FETCH_ASSOC)) == 0){
                $sql = "ALTER TABLE `". $entity ."` ADD CONSTRAINT `". $name ."` FOREIGN KEY (`". $fk->fk ."`) REFERENCES `". $fk->table ."`(`_id`) ; ";
                $query = $this->Connection()->prepare($sql);
                $query->execute([]);
                return $query->rowCount(); 
            } 
        }catch(Exception $e){
            error_log('Error: ' . $e->getMessage() . ' in ' . $sql . ' parms ' . json_encode($values), 0);
            throw $e;
        } finally {
            if($this->action == false) {
                $this->con = null;
            }
        }
        return null;
    }
    
    public function createTable($database, $entity){
        $values = [$database, $entity];
        $sql = "SELECT *  FROM information_schema.tables WHERE table_schema = ? AND table_name = ? LIMIT 1";
        try{
            $query = $this->Connection()->prepare($sql);
            $query->execute($values);
            if( count($query->fetchAll(PDO::FETCH_ASSOC)) == 0){
                $sql = "CREATE TABLE ". $entity ."(_id varchar(255) not null, PRIMARY KEY (_id))";
                $query = $this->Connection()->prepare($sql);
                $query->execute($values);
                return $query->rowCount(); 
            } 
        }catch(Exception $e){
            error_log('Error: ' . $e->getMessage() . ' in ' . $sql . ' parms ' . json_encode($values), 0);
            throw $e;
        } finally {
            //if($this->action == false) {
                $this->con = null;
            //}
        }
        return null;
    }

    // preparement state pdo: https://www.w3schools.com/php/php_mysql_prepared_statements.asp
    public function Datatable($sql, $values){
        try{
            $query = $this->Connection()->prepare($sql);
            $query->execute($values);
            return $query->fetchAll(PDO::FETCH_ASSOC);

        }catch(Exception $e){
            //throw $e;
            throw new Exception('Erro: ' .  $e->getMessage() . " - " . $sql);
        } finally {
            //if($this->action == false) {
                $this->con = null;
            //}
        }
    }
    
    public function Procedure($procedure, $values, $tables){
        //$stmt = $this->Connection()->query("call " . $procedure . "();");
        $sql = "CALL " . $procedure . " (";
        for($i = 0; $i < count($values); $i++){
            $sql = $sql . " ? ";
            if($i < count($values) - 1){
                $sql = $sql . " , ";
            }                     
        }
        $sql = $sql . ")";
        $stmt = $this->Connection()->prepare($sql);
        for($i = 0; $i < count($values); $i++){
            $stmt->bindParam($i + 1, $values[$i]); 
        }
        $stmt->execute();
        
        $retorno = Array();
        $i = 0;
        //do {
        $tabela = Array();
        //https://www.php.net/manual/pt_BR/pdostatement.fetch.php
        //$rowset = $stmt->fetchAll(PDO::FETCH_NUM);
        $rowset = $stmt->fetchAll(PDO::FETCH_OBJ);

        if ($rowset) {
            foreach ($rowset as $row) {
                array_push($tabela, $row);
            }
        }


        return [$tabela];
    }

    public function ExecuteNoQuery($sqls, $valuess){
        try{
            $row_count = 0;
            if( ! is_array($sqls)){
                $sqls = [$sqls];
                $valuess = [$valuess];
            }
            //$this->Connection()->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            if( count( $sqls ) > 1 ){
                $this->Connection()->beginTransaction();
            }

            for($i = 0; $i < count($sqls); $i++) {
                $sql = $sqls[$i];
                $values = $valuess[$i];
                $query = $this->Connection()->prepare($sql);
                $query->execute($values);
                $row_count = $row_count + $query->rowCount();
                error_log( $row_count, 0);
            }

            if( count( $sqls ) > 1 ){
                $this->Connection()->commit();
            }
            
            return $row_count; 
            
        }catch(Exception $e){
            $this->Connection()->rollback();
            error_log("Falha de sql", 0);
            error_log($e, 0);
            throw $e;
        } finally {
            if($this->action == false) {
                $this->con = null;
            }
        }
        return 0;
    }





    public function BeginTransaction(){
        $this->Connection()->beginTransaction();
        $this->action = true;
    }

    public function CommitTransaction(){
        $this->Connection()->commit();
        $this->action = false;
    }

    public function RollbackTransaction(){
        $this->Connection()->rollback();
        $this->action = false;
    }

}

?>

<?php


function create_directory_recur($path_dir, $is_file){
    $path_dir = substr($path_dir, 0, strrpos($path_dir, "/"));
    if (file_exists($path_dir)){
        return;
    }
    mkdir($path_dir, 0777, true);
}

class Json {
    static public function FromFile($path){
        try {
            $json = file_get_contents($path);
            return json_decode($json);
        }catch(Exception $error){
            echo $error;
        }
        return null;
    }
    
    static public function FromFile_v2($path){
        try {
            $json = file_get_contents($path);
            return json_decode($json, true);
        }catch(Exception $error){
            echo $error;
        }
        return null;
    }
    
    static public function WriteFile($path, $json){
        try{
            create_directory_recur($path, true);
            $fp = fopen($path, 'w');
            fwrite($fp, json_encode($json));
            fclose($fp);
            return true;
        }catch(Exception $error){
            echo $error;
        }
        return null;
    }
    
    static public function InArray($json_array, $field_name, $field_value){
        //error_log(json_encode($json_array),0);
        //error_log($field_name);
        //error_log($field_value);
        try{
            for($i = 0; $i < count($json_array); $i++){
                //if($json_array[$i]->{$field_name} == $field_value){
                //  return true;
                //}
            } 
        }catch(Exception $error){
            error_log($error, 0);
        }
        return false;
    }

}
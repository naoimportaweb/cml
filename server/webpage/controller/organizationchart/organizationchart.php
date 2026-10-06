<?php
require_once dirname(dirname(__DIR__)) . "/model/organizationchart/organizationchart.php";

class OrganizationChartController{
    private $chart = null;

    function __construct($id, $domain) {
        $this->chart = new OrganizationChart( $id, $domain );
    }

    public function getChart(){
        return $this->chart;
    }

    public function toJson(){
        return $this->chart->toJson();
    }
}

?>

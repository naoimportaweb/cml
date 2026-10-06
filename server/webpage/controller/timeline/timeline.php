<?php
require_once dirname(dirname(__DIR__)) . "/model/timeline/timeline.php";

class TimelineController{
    private $timeline = null;

    function __construct($id, $domain) {
        $this->timeline = new Timeline( $id, $domain );
    }

    public function getTimeline(){
        return $this->timeline;
    }

    public function toJson(){
        return $this->timeline->toJson();
    }
}

?>

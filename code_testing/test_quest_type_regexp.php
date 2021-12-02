<?php
require_once('../extracting_data_from_xml_line.php');

function test($input, $expected) {
    if (get_quest_type($input) !== $expected ) {
        echo "((((((((";
        echo "\n";
        echo $input;
        echo "\n";
        echo $expected;
        echo "\n";
        echo get_quest_type($input);
        echo "\n";
        echo "\n";
    } else {
        #echo "OK\n";
    }
}

$input = '<tag k="StreetComplete:quest_type" v="AddRoadSurface"/>';
test($input, "AddRoadSurface");
?>

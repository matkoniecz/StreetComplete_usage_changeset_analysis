<?php
require_once('../extracting_data_from_xml_line.php');

function test($input, $expected) {
    if (created_by_tag_to_identifier($input) !== $expected ) {
        echo "((((((((";
        echo "\n";
        echo $input;
        echo "\n";
        echo $expected;
        echo "\n";
        echo created_by_tag_to_identifier($input);
        echo "\n";
        echo "\n";
    } else {
        #echo "OK\n";
    }
}

$input = '<tag k="created_by" v="JOSM/1.5 (18193 de)"/>';
test($input, "JOSM/1.5 (18193 de)");
?>

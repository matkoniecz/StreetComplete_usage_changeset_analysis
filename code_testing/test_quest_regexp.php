<?php
function get_quest_type($changeset_header) {
    if (preg_match("/v=\"([^\"]+)\"/", $changeset_header, $matches)) {
        #print_r ($matches);
        #print_r ($matches[1]);
        return $matches[1];
    } else {
        return NULL;
    }
}

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

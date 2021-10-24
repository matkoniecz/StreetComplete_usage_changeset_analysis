<?php
function main() {
    $usage=array();
    $row = 0;
    if (($handle = fopen("output.csv", "r")) !== FALSE) {
        while (($data = fgetcsv($handle, 0, ",")) !== FALSE) {
            $edited_objects = $data[2];
            $quest_id = $data[3];
            $user_id = $data[4];
            $usage = register_popularity_two_layers($usage, $quest_id, $user_id, $edited_objects);
            $row += 1;
            if ($row % 100000 === 0) {
                echo (int)($row/1000) . "k rows loaded\n";
            }
        }
        fclose($handle);
    }
    echo "csv loaded";
    $user_count = 3000; //count_of_user_who_ever_edited($usage);
    echo count_of_user_who_ever_edited($usage) . "\n\n";
    foreach ($usage as $quest_id => $popularity_info) {
        $usage_numbers_by_user = array();
        $index = 0;
        foreach ($popularity_info as $user_id => $edited_elements) {
            $usage_numbers_by_user[$index] = $edited_elements;
            $index += 1;
        }
        echo "for quest " . $quest_id . " it was done by " . $index . " people out of " . $user_count . " users.\n";
        while($index < $user_count && false) {
            $usage_numbers_by_user[$index] = 0;
            $index += 1;
        }
        echo "for quest " . $quest_id . " median is " . array_median($usage_numbers_by_user) . " edited elements.\n";
        echo "\n";
    }
}

function count_of_user_who_ever_edited($usage){
    $total_usage_per_user=array();
    foreach ($usage as $quest_id => $popularity_info) {
        foreach ($popularity_info as $user_id => $edited_elements) {
            $total_usage_per_user = register_popularity($total_usage_per_user, $user_id, $edited_elements);
        }
    }

    $users_who_ever_edited = 0;
    foreach ($total_usage_per_user as $user_id => $edited_elements) {
        if ($edited_elements >= 30) {
            $users_who_ever_edited += 1;
        }
    }
    return $users_who_ever_edited;
}

function register_popularity_two_layers($dict, $index, $subindex, $number) {
    if (!isset($dict[$index])) {
        $dict[$index] = array();
    }
    if (isset($dict[$index][$subindex])) {
        $dict[$index][$subindex] += $number;
    } else {
        $dict[$index][$subindex] = $number;
    }
    return $dict;
}

function register_popularity($dict, $index, $number) {
    if (isset($dict[$index])) {
        $dict[$index] += $number;
    } else {
        $dict[$index] = $number;
    }
    return $dict;
}

function array_median($array) {
    $length = count($array);
    $middle_index = floor($length / 2);
    sort($array, SORT_NUMERIC);
    if ($length % 2 == 0) {
        return ($array[$middle_index] + $array[$middle_index - 1]) / 2;
    } else {
        return $array[$middle_index];
    }
}

main()
?>